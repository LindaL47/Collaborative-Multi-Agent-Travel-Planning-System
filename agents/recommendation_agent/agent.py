"""Explainable, deterministic recommendations for grouped travel options."""

from __future__ import annotations

import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from agents.decision_schemas import (
    DecisionParameters,
    FlightDecisionGroup,
    HotelDecisionGroup,
    Recommendation,
    RecommendationResponseMetadata,
    RecommendationTaskRequest,
    RecommendationTaskResponse,
    RecommendedFlight,
    RecommendedHotel,
)

# Price, duration, stops; price, hotel rating, preferred area, refundability.
FLIGHT_WEIGHTS = {"balanced": (0.40, 0.35, 0.25), "budget": (0.80, 0.15, 0.05), "comfort": (0.15, 0.45, 0.40)}
HOTEL_WEIGHTS = {"balanced": (0.40, 0.35, 0.15, 0.10), "budget": (0.80, 0.10, 0.05, 0.05), "comfort": (0.15, 0.45, 0.25, 0.15)}


def _normalized(values: list[float], lower_is_better: bool = True) -> list[float]:
    low, high = min(values), max(values)
    if low == high:
        return [1.0] * len(values)
    return [(high - value if lower_is_better else value - low) / (high - low) for value in values]


def _duration_minutes(duration: str) -> int:
    hours = re.search(r"(\d+)\s*h", duration, re.I)
    minutes = re.search(r"(\d+)\s*m", duration, re.I)
    return (int(hours.group(1)) * 60 if hours else 0) + (int(minutes.group(1)) if minutes else 0)


def _location_matches(group_option, preference: str | None) -> bool:
    if not preference:
        return False
    needle = re.sub(r"\b(near|around|close to|by|next to|in|at)\b", " ", preference.lower())
    needle = " ".join(needle.split()).strip(" .,")
    return bool(needle) and needle in f"{group_option.area} {group_option.distance_from_landmark}".lower()


def _score_flights(group: FlightDecisionGroup, params: DecisionParameters) -> list[RecommendedFlight]:
    if not group.options:
        return []
    prices = _normalized([option.price_usd for option in group.options])
    durations = _normalized([_duration_minutes(option.duration) for option in group.options])
    weights = FLIGHT_WEIGHTS[params.strategy]
    lowest = min(option.price_usd for option in group.options)
    scored = []
    for index, option in enumerate(group.options):
        score = sum(weight * value for weight, value in zip(weights, (prices[index], durations[index], 1 / (1 + option.stops))))
        fare = "Lowest fare in this leg" if option.price_usd == lowest else "Fare"
        scored.append(RecommendedFlight(
            group_id=group.group_id, label=group.label, option=option, score=round(score * 100, 1),
            reasons=[f"{fare}: ${option.price_usd} per traveller.", f"{option.duration}, " + ("nonstop." if option.stops == 0 else f"{option.stops} stop(s).")],
        ))
    return sorted(scored, key=lambda item: (item.option.price_usd, -item.score) if params.strategy == "budget" else (-item.score,))


def _score_hotels(group: HotelDecisionGroup, params: DecisionParameters) -> list[RecommendedHotel]:
    if not group.options:
        return []
    prices = _normalized([option.price_per_night_usd for option in group.options])
    ratings = _normalized([option.star_rating for option in group.options], lower_is_better=False)
    weights = HOTEL_WEIGHTS[params.strategy]
    scored = []
    for index, option in enumerate(group.options):
        location = _location_matches(option, params.location_preference)
        score = sum(weight * value for weight, value in zip(weights, (prices[index], ratings[index], float(location) if params.location_preference else 1.0, float(option.refundable))))
        reasons = [f"${option.price_per_night_usd}/night for {group.nights} nights; {option.star_rating:g} stars."]
        if location:
            reasons.append(f"Matches preferred area: {option.area}.")
        reasons.append("Refundable mock rate." if option.refundable else "Non-refundable mock rate.")
        scored.append(RecommendedHotel(
            group_id=group.group_id, label=group.label, nights=group.nights,
            option=option, score=round(score * 100, 1), reasons=reasons,
        ))
    return sorted(scored, key=lambda item: (item.option.price_per_night_usd, -item.score) if params.strategy == "budget" else (-item.score,))


class RecommendationAgentState(TypedDict, total=False):
    request: RecommendationTaskRequest | dict
    validated_request: RecommendationTaskRequest
    flight_candidates: list[list[RecommendedFlight]]
    hotel_candidates: list[list[RecommendedHotel]]
    recommendation: Recommendation
    response: RecommendationTaskResponse


def validate_input_node(state: RecommendationAgentState) -> dict:
    return {"validated_request": RecommendationTaskRequest.model_validate(state["request"])}


def score_options_node(state: RecommendationAgentState) -> dict:
    params = state["validated_request"].parameters
    return {
        "flight_candidates": [_score_flights(group, params) for group in params.flight_groups if group.options],
        "hotel_candidates": [_score_hotels(group, params) for group in params.hotel_groups if group.options],
    }


def apply_total_budget_node(state: RecommendationAgentState) -> dict:
    params = state["validated_request"].parameters
    flights = [candidates[0] for candidates in state["flight_candidates"]]
    hotels = [candidates[0] for candidates in state["hotel_candidates"]]

    def selected_cost() -> int:
        return sum(item.option.price_usd * params.passengers for item in flights) + sum(item.option.price_per_night_usd * item.nights for item in hotels)

    total = selected_cost()
    adjusted = False
    warnings = []
    if params.total_budget_usd is not None and total > params.total_budget_usd:
        flights = [min(candidates, key=lambda item: item.option.price_usd) for candidates in state["flight_candidates"]]
        hotels = [min(candidates, key=lambda item: item.option.price_per_night_usd) for candidates in state["hotel_candidates"]]
        adjusted = selected_cost() < total
        total = selected_cost()
        if adjusted:
            warnings.append("Selected the lowest-cost combination because the preferred choices exceeded your total budget.")
        if total > params.total_budget_usd:
            warnings.append(f"Even the lowest-cost available combination exceeds your total budget by ${total - params.total_budget_usd:,}.")
    if not params.is_complete:
        warnings.append("This is an available-options subtotal; missing legs or stays still need prices.")
    return {"recommendation": Recommendation(
        strategy=params.strategy, flights=flights, hotels=hotels, estimated_total_usd=total,
        is_complete=params.is_complete, missing_groups=params.missing_groups,
        within_budget=total <= params.total_budget_usd if params.is_complete and params.total_budget_usd is not None else None,
        budget_adjusted=adjusted, warnings=warnings,
    )}


def response_formatting_node(state: RecommendationAgentState) -> dict:
    request = state["validated_request"]
    result = state["recommendation"]
    return {"response": RecommendationTaskResponse(
        task_id=request.task_id, status="success" if result.is_complete else "partial", results=[result],
        clarification_needed=None if result.is_complete else "Missing mock options for: " + (", ".join(result.missing_groups) or "the requested trip"),
        metadata=RecommendationResponseMetadata(trace_id=request.metadata.trace_id),
    )}


class RecommendationAgent:
    """Stateless scoring and budget-aware selection graph."""

    agent_id = "recommendation-agent"

    def __init__(self) -> None:
        graph = StateGraph(RecommendationAgentState)
        graph.add_node("validate_input", validate_input_node)
        graph.add_node("score_options", score_options_node)
        graph.add_node("apply_total_budget", apply_total_budget_node)
        graph.add_node("response_formatting", response_formatting_node)
        graph.add_edge(START, "validate_input")
        graph.add_edge("validate_input", "score_options")
        graph.add_edge("score_options", "apply_total_budget")
        graph.add_edge("apply_total_budget", "response_formatting")
        graph.add_edge("response_formatting", END)
        self.graph = graph.compile()

    def invoke(self, request: RecommendationTaskRequest | dict) -> RecommendationTaskResponse:
        return self.graph.invoke({"request": request})["response"]

    @staticmethod
    def mermaid_diagram() -> str:
        return """flowchart TD
    START([START]) --> validate_input[Validate RecommendationTaskRequest]
    validate_input --> score_options[Score price, duration, quality and preferences]
    score_options --> apply_total_budget[Select options within total budget when feasible]
    apply_total_budget --> response_formatting[Explain selections in RecommendationTaskResponse]
    response_formatting --> END([END])"""
