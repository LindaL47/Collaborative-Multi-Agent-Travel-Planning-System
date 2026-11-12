"""Regression tests for A2A protocol and LangGraph architecture requirements."""

from __future__ import annotations

from agents.flight_agent.agent import FlightBookingAgent
from agents.flight_agent.schemas import FlightTaskRequest
from agents.hotel_agent.agent import HotelBookingAgent
from agents.hotel_agent.schemas import HotelTaskRequest
from orchestrator.agent import FriendlyAssistantOrchestrator


REQUEST_REQUIRED_KEYS = {"task_id", "task_type", "session_id", "parameters", "metadata"}
REQUEST_METADATA_REQUIRED_KEYS = {"requested_by", "timestamp"}
RESPONSE_REQUIRED_KEYS = {"task_id", "status", "results", "clarification_needed", "error", "metadata"}
RESPONSE_METADATA_REQUIRED_KEYS = {"agent_id", "timestamp"}


def _assert_request_contract(payload: dict) -> None:
    assert REQUEST_REQUIRED_KEYS <= payload.keys()
    assert REQUEST_METADATA_REQUIRED_KEYS <= payload["metadata"].keys()
    assert payload["metadata"]["requested_by"] == "orchestrator"


def _assert_response_contract(payload: dict) -> None:
    assert RESPONSE_REQUIRED_KEYS <= payload.keys()
    assert RESPONSE_METADATA_REQUIRED_KEYS <= payload["metadata"].keys()
    assert payload["status"] in {"success", "partial", "failed", "needs_clarification"}


def test_flight_a2a_request_response_contract_and_trace_correlation() -> None:
    request = FlightTaskRequest.model_validate(
        {
            "session_id": "11111111-1111-1111-1111-111111111111",
            "parameters": {
                "origin": "Singapore",
                "destination": "Tokyo",
                "departure_date": "2026-07-25",
                "return_date": "2026-07-30",
                "passengers": 2,
                "cabin_class": "economy",
            },
        }
    )
    response = FlightBookingAgent().invoke(request)

    request_payload = request.model_dump(mode="json")
    response_payload = response.model_dump(mode="json")

    _assert_request_contract(request_payload)
    _assert_response_contract(response_payload)
    assert request_payload["task_type"] == "flight_search"
    assert response_payload["metadata"]["agent_id"] == "flight-agent"
    assert response.metadata.trace_id == request.metadata.trace_id


def test_hotel_a2a_request_response_contract_and_trace_correlation() -> None:
    request = HotelTaskRequest.model_validate(
        {
            "session_id": "11111111-1111-1111-1111-111111111111",
            "parameters": {
                "destination": "Tokyo",
                "check_in_date": "2026-07-25",
                "check_out_date": "2026-07-30",
                "guests": 2,
                "room_type": "standard",
                "location_preference": "Shinjuku",
            },
        }
    )
    response = HotelBookingAgent().invoke(request)

    request_payload = request.model_dump(mode="json")
    response_payload = response.model_dump(mode="json")

    _assert_request_contract(request_payload)
    _assert_response_contract(response_payload)
    assert request_payload["task_type"] == "hotel_search"
    assert response_payload["metadata"]["agent_id"] == "hotel-agent"
    assert response.metadata.trace_id == request.metadata.trace_id


def test_orchestrator_tracks_a2a_messages_for_package_delegation() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers near Shinjuku."
    )

    messages = state["a2a_messages"]
    request_entries = [entry for entry in messages if entry["direction"] == "orchestrator_to_sub_agent"]
    response_entries = [entry for entry in messages if entry["direction"] == "sub_agent_to_orchestrator"]

    assert state["route"] == "both"
    assert state["pending_clarifications"] == []
    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"
    assert len(request_entries) == 2
    assert len(response_entries) == 2
    assert {entry["task_type"] for entry in request_entries} == {"flight_search", "hotel_search"}
    assert len(state["active_task_ids"]) == 2

    response_by_task = {entry["task_id"]: entry for entry in response_entries}
    for request_entry in request_entries:
        response_entry = response_by_task[request_entry["task_id"]]
        _assert_request_contract(request_entry["payload"])
        _assert_response_contract(response_entry["payload"])
        assert response_entry["trace_id"] == request_entry["trace_id"]
        assert response_entry["payload"]["metadata"]["trace_id"] == request_entry["trace_id"]


def test_orchestrator_tracks_a2a_messages_for_multi_city_fanout() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "Plan Singapore to Tokyo to Paris to Singapore starting 2026-09-01, 5 days each city. Give flights and hotels."
    )

    request_entries = [entry for entry in state["a2a_messages"] if entry["direction"] == "orchestrator_to_sub_agent"]

    assert state["route"] == "multi_city"
    assert state["pending_clarifications"] == []
    assert len(request_entries) == 5
    assert [entry["task_type"] for entry in request_entries].count("flight_search") == 3
    assert [entry["task_type"] for entry in request_entries].count("hotel_search") == 2
    assert len(state["active_task_ids"]) == 5


def test_general_question_routes_to_neither_agent_and_keeps_empty_a2a_log() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Is June a good time to visit Tokyo?")

    assert state["route"] == "general"
    assert state.get("flight_response") is None
    assert state.get("hotel_response") is None
    assert state["active_task_ids"] == []
    assert state["a2a_messages"] == []


def test_langgraph_diagrams_show_required_nodes_and_conditional_routing() -> None:
    orchestrator_diagram = FriendlyAssistantOrchestrator.mermaid_diagram()
    flight_diagram = FlightBookingAgent.mermaid_diagram()
    hotel_diagram = HotelBookingAgent.mermaid_diagram()

    for text in ["input_understanding", "clarification", "route{Conditional routing}", "aggregation"]:
        assert text in orchestrator_diagram
    for text in ["flight_delegation", "hotel_delegation", "parallel_a2a_delegation"]:
        assert text in orchestrator_diagram
    for text in ["validate_input", "search_retrieval", "response_formatting"]:
        assert text in flight_diagram
        assert text in hotel_diagram
