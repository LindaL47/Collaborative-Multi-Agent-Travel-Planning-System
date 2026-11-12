"""LangGraph implementation of the Flight Booking Agent."""

from __future__ import annotations

from typing import Any, List, Optional, TypedDict
from uuid import UUID, uuid4

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from agents.flight_agent.mock_data import available_route_suggestions, search_mock_flights
from agents.flight_agent.schemas import A2AResponseMetadata, FlightOption, FlightTaskRequest, FlightTaskResponse, TaskStatus


class FlightAgentState(TypedDict, total=False):
    """Internal state passed through the Flight Agent StateGraph."""

    request: FlightTaskRequest | dict[str, Any]
    validated_request: Optional[FlightTaskRequest]
    matches: List[FlightOption]
    response: Optional[FlightTaskResponse]
    validation_error: Optional[str]


def _request_task_id(raw_request: Any) -> str:
    if isinstance(raw_request, FlightTaskRequest):
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
            return "Flight search needs clarification: " + "; ".join(pieces) + "."
    return (
        "Flight search needs a structured A2A request with origin, destination, "
        "departure_date, optional return_date, passengers, and cabin_class."
    )


def _metadata_for_request(request: FlightTaskRequest, result_count: int = 0) -> A2AResponseMetadata:
    """Create response metadata correlated to the incoming A2A request."""
    return A2AResponseMetadata(trace_id=request.metadata.trace_id, result_count=result_count)


def _with_request_trace(response: FlightTaskResponse, request: FlightTaskRequest) -> FlightTaskResponse:
    """Return a response whose trace metadata matches the triggering request."""
    return response.model_copy(update={"metadata": _metadata_for_request(request, len(response.results))})


def validate_input_node(state: FlightAgentState) -> FlightAgentState:
    """Validate the incoming A2A request before search."""
    raw_request = state.get("request")
    task_id = _request_task_id(raw_request or {})
    try:
        request = raw_request if isinstance(raw_request, FlightTaskRequest) else FlightTaskRequest.model_validate(raw_request)
        return {**state, "validated_request": request, "validation_error": None}
    except (ValidationError, ValueError, TypeError) as exc:
        response = FlightTaskResponse.needs_clarification(
            task_id=task_id,
            clarification=_validation_clarification(exc),
        )
        return {**state, "validated_request": None, "validation_error": str(exc), "response": response}


def search_retrieval_node(state: FlightAgentState) -> FlightAgentState:
    """Search stable mock data for matching flight options."""
    if state.get("response") is not None:
        return state

    request = state["validated_request"]
    assert request is not None
    params = request.parameters
    matches = search_mock_flights(
        origin=params.origin,
        destination=params.destination,
        departure_date=params.departure_date,
        return_date=params.return_date,
        cabin_class=str(params.cabin_class),
        return_destination=params.return_destination,
    )

    if not matches:
        suggestions = available_route_suggestions(params.origin)
        suggestion_text = f" Available destinations from {params.origin}: {', '.join(suggestions)}." if suggestions else ""
        response = FlightTaskResponse.failed(
            task_id=request.task_id,
            error=(
                f"No mock flights were found for {params.origin} to {params.destination} "
                f"on {params.departure_date.isoformat()}.{suggestion_text}"
            ),
        )
        return {**state, "matches": [], "response": _with_request_trace(response, request)}

    if params.return_date:
        has_outbound = any(option.trip_leg == "outbound" for option in matches)
        has_inbound = any(option.trip_leg == "inbound" for option in matches)
        if has_outbound and not has_inbound:
            response = FlightTaskResponse.partial(
                task_id=request.task_id,
                results=matches,
                clarification="I found outbound flights but no matching return flights in the mock data.",
            )
            return {**state, "matches": matches, "response": _with_request_trace(response, request)}

    return {**state, "matches": matches}


def response_formatting_node(state: FlightAgentState) -> FlightAgentState:
    """Format search results into the mandated A2A response schema."""
    if state.get("response") is not None:
        return state

    request = state["validated_request"]
    assert request is not None
    matches = state.get("matches", [])
    response = FlightTaskResponse.success(task_id=request.task_id, results=matches)
    return {**state, "response": _with_request_trace(response, request)}


def build_flight_graph():
    """Build and compile the Flight Booking Agent graph."""
    graph = StateGraph(FlightAgentState)
    graph.add_node("validate_input", validate_input_node)
    graph.add_node("search_retrieval", search_retrieval_node)
    graph.add_node("response_formatting", response_formatting_node)

    graph.add_edge(START, "validate_input")
    graph.add_edge("validate_input", "search_retrieval")
    graph.add_edge("search_retrieval", "response_formatting")
    graph.add_edge("response_formatting", END)
    return graph.compile()


class FlightBookingAgent:
    """Runnable wrapper around the Flight Agent StateGraph."""

    agent_id = "flight-agent"

    def __init__(self) -> None:
        self.graph = build_flight_graph()

    def invoke(self, request: FlightTaskRequest | dict[str, Any]) -> FlightTaskResponse:
        """Run the flight graph independently and return a typed A2A response."""
        state = self.graph.invoke({"request": request})
        response = state.get("response")
        if isinstance(response, FlightTaskResponse):
            return response
        return FlightTaskResponse.model_validate(response)

    @staticmethod
    def mermaid_diagram() -> str:
        """Return an accurate Mermaid diagram for documentation."""
        return """flowchart TD
    START([START]) --> validate_input[Validate A2A FlightTaskRequest]
    validate_input --> search_retrieval[Static + dynamic mock flight retrieval]
    search_retrieval --> response_formatting[Format FlightTaskResponse with trace metadata]
    response_formatting --> END([END])"""


def run_flight_agent(request: FlightTaskRequest | dict[str, Any]) -> FlightTaskResponse:
    """Convenience function used by tests and the orchestrator."""
    return FlightBookingAgent().invoke(request)
