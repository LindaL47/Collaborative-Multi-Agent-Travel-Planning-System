"""Translate planner/search state into decision tasks and readable summaries."""

from __future__ import annotations

import re
from datetime import date

from agents.decision_schemas import DecisionParameters, FlightDecisionGroup, HotelDecisionGroup


def extract_decision_preferences(message: str) -> dict:
    preferences = {}
    budget = re.search(
        r"\b(?:total|trip|overall)\s+budget\s*(?:(?:of|is|under|below|up to)\s*)?[:=]?\s*\$?\s*([1-9]\d*(?:,\d{3})*)\b",
        message, re.I,
    )
    if budget:
        preferences["total_budget_usd"] = int(budget.group(1).replace(",", ""))
    strategies = {
        "budget": r"\b(?:cheapest|lowest[- ]cost|budget[- ]friendly|save money|prioriti[sz]e (?:price|cost))\b",
        "comfort": r"\b(?:prioriti[sz]e comfort|prefer comfort|comfort first|most comfortable|fastest|shortest flights?)\b",
        "balanced": r"\b(?:balanced|balance cost and comfort)\b",
    }
    matches = [(match.start(), strategy) for strategy, pattern in strategies.items() for match in re.finditer(pattern, message, re.I)]
    if matches:
        preferences["strategy"] = max(matches)[1]
    return preferences


def build_decision_parameters(state: dict) -> DecisionParameters:
    params = state.get("travel_params", {})
    aggregated = state.get("final_aggregated_options", {})
    flight_groups = []
    hotel_groups = []
    if "multi_city" in aggregated:
        itinerary = aggregated["multi_city"]
        plan = state["multi_city_plan"]
        scope = plan.get("scope", "both")
        flights = {(segment["origin"], segment["destination"], segment["departure_date"]): segment["options"] for segment in itinerary["flights"]}
        hotels = {(segment["destination"], segment["check_in_date"], segment["check_out_date"]): segment["options"] for segment in itinerary["hotels"]}
        if scope not in {"hotels_only", "hotel_only", "only_hotels"}:
            for index, leg in enumerate(plan["legs"], 1):
                key = (leg["origin"], leg["destination"], leg["departure_date"])
                flight_groups.append(FlightDecisionGroup(
                    group_id=f"flight-leg-{index}", label=f"{leg['origin']} → {leg['destination']} on {leg['departure_date']}",
                    options=flights.get(key, []),
                ))
        if scope not in {"flights_only", "flight_only", "only_flights"}:
            for index, stay in enumerate(plan["stays"], 1):
                key = (stay["destination"], stay["check_in_date"], stay["check_out_date"])
                nights = (date.fromisoformat(stay["check_out_date"]) - date.fromisoformat(stay["check_in_date"])).days
                hotel_groups.append(HotelDecisionGroup(
                    group_id=f"hotel-stay-{index}", label=f"{stay['destination']} ({stay['check_in_date']} to {stay['check_out_date']})",
                    nights=nights, options=hotels.get(key, []),
                ))
    else:
        flights = aggregated.get("flights", [])
        if params.get("needs_flight") or flights:
            legs = ["outbound", "inbound"] if params.get("return_date") else ["outbound"]
            for leg in legs:
                flight_groups.append(FlightDecisionGroup(
                    group_id=leg, label="Outbound flight" if leg == "outbound" else "Return / onward flight",
                    options=[option for option in flights if option.trip_leg == leg],
                ))
        hotels = aggregated.get("hotels", [])
        if params.get("needs_hotel") or hotels:
            nights = (date.fromisoformat(str(params["check_out_date"])) - date.fromisoformat(str(params["check_in_date"]))).days
            hotel_groups.append(HotelDecisionGroup(
                group_id="hotel-stay", label=f"{params['destination']} hotel stay", nights=nights, options=hotels,
            ))
    return DecisionParameters(
        flight_groups=flight_groups, hotel_groups=hotel_groups,
        passengers=int(params.get("passengers", params.get("guests", 1))),
        strategy=state.get("decision_strategy", "balanced"), location_preference=params.get("location_preference"),
        total_budget_usd=state.get("trip_budget", {}).get("total_budget_usd"),
    )


def format_decision_summary(state: dict) -> list[str]:
    assessment = state.get("budget_assessment")
    recommendation = state.get("recommendation")
    if assessment is None or recommendation is None:
        return []
    lines = ["\n**Budget assessment**"]
    label = "Lowest available total" if assessment.is_complete else "Available-options subtotal"
    lines.append(
        f"{label}: **${assessment.minimum_total_cost_usd:,}** "
        f"(flights ${assessment.minimum_flight_cost_usd:,}; hotels ${assessment.minimum_hotel_cost_usd:,})."
    )
    if assessment.total_budget_usd is not None:
        if assessment.within_budget is True:
            lines.append(f"A complete mock plan fits your ${assessment.total_budget_usd:,} total budget.")
        elif assessment.shortfall_usd:
            lines.append(f"The {'lowest-cost plan' if assessment.is_complete else 'available subtotal'} exceeds your total budget by ${assessment.shortfall_usd:,}.")
        else:
            lines.append("Budget feasibility is pending prices for missing legs or stays.")
    travellers = state.get("travel_params", {}).get("passengers", state.get("travel_params", {}).get("guests", 1))
    lines.append(f"Estimates cover mock flights for {travellers} traveller(s) and one room per stay; meals, local transport, and other expenses are excluded.")
    if assessment.missing_groups:
        groups = build_decision_parameters(state)
        labels = {group.group_id: group.label for group in [*groups.flight_groups, *groups.hotel_groups]}
        lines.append("Missing options: " + "; ".join(labels[key] for key in assessment.missing_groups) + ".")

    if recommendation.flights or recommendation.hotels:
        title = "Closest mock plan" if recommendation.within_budget is False else "Recommended plan"
        lines.append(f"\n**{title} ({recommendation.strategy})**")
        for item in recommendation.flights:
            lines.append(f"- {item.label}: **{item.option.flight_number}** — " + " ".join(item.reasons))
        for item in recommendation.hotels:
            lines.append(f"- {item.label}: **{item.option.hotel_name}** — " + " ".join(item.reasons))
        label = "Estimated selected total" if recommendation.is_complete else "Selected-options subtotal"
        lines.append(f"{label}: **${recommendation.estimated_total_usd:,}**.")
    lines.extend(recommendation.warnings)
    return lines
