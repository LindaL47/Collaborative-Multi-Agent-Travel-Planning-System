"""Offline budget assessment over every required flight leg and hotel stay."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from agents.decision_schemas import (
    BudgetAssessment,
    BudgetResponseMetadata,
    BudgetTaskRequest,
    BudgetTaskResponse,
)


class BudgetAgentState(TypedDict, total=False):
    request: BudgetTaskRequest | dict
    validated_request: BudgetTaskRequest
    assessment: BudgetAssessment
    response: BudgetTaskResponse


def validate_input_node(state: BudgetAgentState) -> dict:
    return {"validated_request": BudgetTaskRequest.model_validate(state["request"])}


def assess_budget_node(state: BudgetAgentState) -> dict:
    params = state["validated_request"].parameters
    flight_cost = sum(
        min(option.price_usd for option in group.options) * params.passengers
        for group in params.flight_groups if group.options
    )
    hotel_cost = sum(
        min(option.price_per_night_usd for option in group.options) * group.nights
        for group in params.hotel_groups if group.options
    )
    total = flight_cost + hotel_cost
    within_budget = total <= params.total_budget_usd if params.is_complete and params.total_budget_usd is not None else None
    assessment = BudgetAssessment(
        minimum_flight_cost_usd=flight_cost,
        minimum_hotel_cost_usd=hotel_cost,
        minimum_total_cost_usd=total,
        is_complete=params.is_complete,
        missing_groups=params.missing_groups,
        total_budget_usd=params.total_budget_usd,
        within_budget=within_budget,
        shortfall_usd=max(total - params.total_budget_usd, 0) if params.total_budget_usd is not None else 0,
    )
    return {"assessment": assessment}


def response_formatting_node(state: BudgetAgentState) -> dict:
    request = state["validated_request"]
    assessment = state["assessment"]
    return {"response": BudgetTaskResponse(
        task_id=request.task_id,
        status="success" if assessment.is_complete else "partial",
        results=[assessment],
        clarification_needed=None if assessment.is_complete else "Missing mock options for: " + (", ".join(assessment.missing_groups) or "the requested trip"),
        metadata=BudgetResponseMetadata(trace_id=request.metadata.trace_id),
    )}


class BudgetDecisionAgent:
    """Stateless, independently runnable budget decision graph."""

    agent_id = "budget-agent"

    def __init__(self) -> None:
        graph = StateGraph(BudgetAgentState)
        graph.add_node("validate_input", validate_input_node)
        graph.add_node("assess_budget", assess_budget_node)
        graph.add_node("response_formatting", response_formatting_node)
        graph.add_edge(START, "validate_input")
        graph.add_edge("validate_input", "assess_budget")
        graph.add_edge("assess_budget", "response_formatting")
        graph.add_edge("response_formatting", END)
        self.graph = graph.compile()

    def invoke(self, request: BudgetTaskRequest | dict) -> BudgetTaskResponse:
        return self.graph.invoke({"request": request})["response"]

    @staticmethod
    def mermaid_diagram() -> str:
        return """flowchart TD
    START([START]) --> validate_input[Validate BudgetTaskRequest]
    validate_input --> assess_budget[Estimate all legs and stays; assess budget]
    assess_budget --> response_formatting[BudgetTaskResponse with cost and missing groups]
    response_formatting --> END([END])"""
