"""LangGraph implementation of the Hotel Booking Agent."""

from __future__ import annotations

from typing import Any, List, Optional, TypedDict
from uuid import UUID, uuid4

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from agents.hotel_agent.mock_data import available_hotel_destinations, search_mock_hotels
from agents.hotel_agent.schemas import A2AResponseMetadata, HotelOption, HotelTaskRequest, HotelTaskResponse


class HotelAgentState(TypedDict, total=False):
    """Internal state passed through the Hotel Agent StateGraph."""

    request: HotelTaskRequest | dict[str, Any]
    validated_request: Optional[HotelTaskRequest]
    matches: List[HotelOption]
    response: Optional[HotelTaskResponse]
    validation_error: Optional[str]


def _request_task_id(raw_request: Any) -> str:
    if isinstance(raw_request, HotelTaskRequest):
        return raw_request.task_id
    candidate = raw_request.get("task_id") if isinstance(raw_request, dict) else None
    try:
        return str(UUID(str(candidate)))
    except (TypeError, ValueError, AttributeError):
        return str(uuid4())


def _validation_clarification(exc: Exception) -> str:
    """Build a concise A2A clarification from schema validation details."""
    if isinstance(exc, ValidationError):
        missing = []
        invalid = []
        for error in exc.errors():
            loc = ".".join(str(part) for part in error.get("loc", []))
            if error.get("type") == "missing":
                missing.append(loc)
            else:
                invalid.append(loc or str(error.get("msg", "invalid value")))
        pieces = []
        if missing:
            pieces.append("missing " + ", ".join(sorted(set(missing))))
        if invalid:
            pieces.append("invalid " + ", ".join(sorted(set(invalid))))
        if pieces:
            return "Hotel search needs clarification: " + "; ".join(pieces) + "."
    return (
        "Hotel search needs a structured A2A request with destination, check_in_date, "
        "check_out_date, guests, room_type, and optional location_preference."
    )


def _metadata_for_request(request: HotelTaskRequest, result_count: int = 0) -> A2AResponseMetadata:
    """Create response metadata correlated to the incoming A2A request."""
    return A2AResponseMetadata(trace_id=request.metadata.trace_id, result_count=result_count)


def _with_request_trace(response: HotelTaskResponse, request: HotelTaskRequest) -> HotelTaskResponse:
    """Return a response whose trace metadata matches the triggering request."""
    return response.model_copy(update={"metadata": _metadata_for_request(request, len(response.results))})


def validate_input_node(state: HotelAgentState) -> HotelAgentState:
    """Validate the incoming A2A request before search."""
    raw_request = state.get("request")
    task_id = _request_task_id(raw_request or {})
    try:
        request = raw_request if isinstance(raw_request, HotelTaskRequest) else HotelTaskRequest.model_validate(raw_request)
        return {**state, "validated_request": request, "validation_error": None}
    except (ValidationError, ValueError, TypeError) as exc:
        response = HotelTaskResponse.needs_clarification(
            task_id=task_id,
            clarification=_validation_clarification(exc),
        )
        return {**state, "validated_request": None, "validation_error": str(exc), "response": response}


def search_retrieval_node(state: HotelAgentState) -> HotelAgentState:
    """Search stable mock data for matching hotel options."""
    if state.get("response") is not None:
        return state

    request = state["validated_request"]
    assert request is not None
    params = request.parameters
    matches = search_mock_hotels(
        destination=params.destination,
        room_type=str(params.room_type),
        location_preference=params.location_preference,
    )

    if not matches:
        suggestions = available_hotel_destinations()
        response = HotelTaskResponse.failed(
            task_id=request.task_id,
            error=(
                f"No mock hotels were found for {params.destination}. "
                f"Try one of these destinations: {', '.join(suggestions)}."
            ),
        )
        return {**state, "matches": [], "response": _with_request_trace(response, request)}

    return {**state, "matches": matches}


def response_formatting_node(state: HotelAgentState) -> HotelAgentState:
    """Format search results into the mandated A2A response schema."""
    if state.get("response") is not None:
        return state

    request = state["validated_request"]
    assert request is not None
    matches = state.get("matches", [])
    response = HotelTaskResponse.success(task_id=request.task_id, results=matches)
    return {**state, "response": _with_request_trace(response, request)}


def build_hotel_graph():
    """Build and compile the Hotel Booking Agent graph."""
    graph = StateGraph(HotelAgentState)
    graph.add_node("validate_input", validate_input_node)
    graph.add_node("search_retrieval", search_retrieval_node)
    graph.add_node("response_formatting", response_formatting_node)

    graph.add_edge(START, "validate_input")
    graph.add_edge("validate_input", "search_retrieval")
    graph.add_edge("search_retrieval", "response_formatting")
    graph.add_edge("response_formatting", END)
    return graph.compile()


class HotelBookingAgent:
    """Runnable wrapper around the Hotel Agent StateGraph."""

    agent_id = "hotel-agent"

    def __init__(self) -> None:
        self.graph = build_hotel_graph()

    def invoke(self, request: HotelTaskRequest | dict[str, Any]) -> HotelTaskResponse:
        """Run the hotel graph independently and return a typed A2A response."""
        state = self.graph.invoke({"request": request})
        response = state.get("response")
        if isinstance(response, HotelTaskResponse):
            return response
        return HotelTaskResponse.model_validate(response)

    @staticmethod
    def mermaid_diagram() -> str:
        """Return an accurate Mermaid diagram for documentation."""
        return """flowchart TD
    START([START]) --> validate_input[Validate A2A HotelTaskRequest]
    validate_input --> search_retrieval[Static + dynamic mock hotel retrieval]
    search_retrieval --> response_formatting[Format HotelTaskResponse with trace metadata]
    response_formatting --> END([END])"""


def run_hotel_agent(request: HotelTaskRequest | dict[str, Any]) -> HotelTaskResponse:
    """Convenience function used by tests and the orchestrator."""
    return HotelBookingAgent().invoke(request)
