"""Broad submission-readiness coverage for mock-data boundaries and A2A rigor."""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from agents.flight_agent.agent import FlightBookingAgent
from agents.flight_agent.schemas import (
    A2ARequestMetadata as FlightRequestMetadata,
    FlightTaskRequest,
    FlightTaskResponse,
)
from agents.hotel_agent.agent import HotelBookingAgent
from agents.hotel_agent.schemas import (
    A2ARequestMetadata as HotelRequestMetadata,
    HotelTaskRequest,
    HotelTaskResponse,
)
from orchestrator.agent import FriendlyAssistantOrchestrator


UNSUPPORTED_LOCATION_PROMPTS = [
    ("Find a flight from Singapore to Lahore on 2026-07-25 for 2 travellers.", "Lahore"),
    ("Find a flight from Singapore to Osaka on 2026-07-25 for 2 travellers.", "Osaka"),
    ("Find a flight from Singapore to Kyoto on 2026-07-25 for 2 travellers.", "Kyoto"),
    ("Find a flight from Singapore to Kathmandu on 2026-07-25 for 2 travellers.", "Kathmandu"),
    ("Find a flight from Singapore to Colombo on 2026-07-25 for 2 travellers.", "Colombo"),
    ("Find a flight from Singapore to Hyderabad on 2026-07-25 for 2 travellers.", "Hyderabad"),
    ("Find a flight from Singapore to Pune on 2026-07-25 for 2 travellers.", "Pune"),
    ("Find a flight from Singapore to Jaipur on 2026-07-25 for 2 travellers.", "Jaipur"),
    ("Find a flight from Singapore to Kochi on 2026-07-25 for 2 travellers.", "Kochi"),
    ("Find a flight from Singapore to Dhaka on 2026-07-25 for 2 travellers.", "Dhaka"),
    ("Find a flight from Singapore to Istanbul on 2026-07-25 for 2 travellers.", "Istanbul"),
    ("Find a flight from Singapore to Berlin on 2026-07-25 for 2 travellers.", "Berlin"),
    ("Find a flight from Singapore to Amsterdam on 2026-07-25 for 2 travellers.", "Amsterdam"),
    ("Find a flight from Singapore to Madrid on 2026-07-25 for 2 travellers.", "Madrid"),
    ("Find a flight from Singapore to Lisbon on 2026-07-25 for 2 travellers.", "Lisbon"),
    ("Find a flight from Singapore to Vienna on 2026-07-25 for 2 travellers.", "Vienna"),
    ("Find a flight from Singapore to Prague on 2026-07-25 for 2 travellers.", "Prague"),
    ("Find a flight from Singapore to Athens on 2026-07-25 for 2 travellers.", "Athens"),
    ("Find a flight from Singapore to Cairo on 2026-07-25 for 2 travellers.", "Cairo"),
    ("Find a flight from Singapore to Nairobi on 2026-07-25 for 2 travellers.", "Nairobi"),
    ("Find a flight from Lahore to Singapore on 2026-07-25 for 2 travellers.", "Lahore"),
    ("Find a flight from Osaka to Singapore on 2026-07-25 for 2 travellers.", "Osaka"),
    ("Find a flight from Kathmandu to Singapore on 2026-07-25 for 2 travellers.", "Kathmandu"),
    ("Find a flight from Berlin to Singapore on 2026-07-25 for 2 travellers.", "Berlin"),
    ("Find a flight from Cairo to Singapore on 2026-07-25 for 2 travellers.", "Cairo"),
    ("Book a hotel in Auckland from 2026-07-25 to 2026-07-30 for 2 guests.", "Auckland"),
    ("Book a hotel in Buenos Aires from 2026-07-25 to 2026-07-30 for 2 guests.", "Buenos Aires"),
    ("Book a hotel in Rio de Janeiro from 2026-07-25 to 2026-07-30 for 2 guests.", "Rio De Janeiro"),
    ("Book a hotel in Cape Town from 2026-07-25 to 2026-07-30 for 2 guests.", "Cape Town"),
    ("Book a hotel in Vancouver from 2026-07-25 to 2026-07-30 for 2 guests.", "Vancouver"),
    ("Is June a good time to visit Kyoto?", "Kyoto"),
    ("Is June a good time to visit Osaka?", "Osaka"),
    ("Is June a good time to visit Istanbul?", "Istanbul"),
    ("Is June a good time to visit Berlin?", "Berlin"),
    ("Is June a good time to visit Amsterdam?", "Amsterdam"),
    ("Plan Singapore → Osaka → Singapore starting 2026-07-25 for 2 travellers.", "Osaka"),
    ("Plan cities as follow: Singapore, Kyoto, Tokyo starting 2026-07-25.", "Kyoto"),
    ("I want to travel between Singapore and Berlin on 2026-07-25.", "Berlin"),
    ("Route: Singapore, Madrid, Singapore starting 2026-07-25.", "Madrid"),
    ("Plan Singapore -> Prague -> Singapore starting 2026-07-25.", "Prague"),
]


@pytest.mark.parametrize(("prompt", "location"), UNSUPPORTED_LOCATION_PROMPTS)
def test_explicit_unsupported_locations_never_delegate(prompt: str, location: str) -> None:
    state = FriendlyAssistantOrchestrator().chat(prompt)

    message = state["message_to_show_user"].lower()
    assert state["route"] == "respond"
    assert state["active_task_ids"] == []
    assert state.get("flight_response") is None
    assert state.get("hotel_response") is None
    assert "don't have mock data" in message
    assert location.lower() in message
    assert "try with singapore" in message


SUPPORTED_FLIGHT_DESTINATIONS = [
    "Tokyo",
    "Paris",
    "Dubai",
    "London",
    "Sydney",
    "Bangkok",
    "Hong Kong",
    "Seoul",
    "Kuala Lumpur",
    "Bengaluru",
    "Delhi",
    "Mumbai",
    "Bali",
    "Zurich",
    "Rome",
    "Barcelona",
    "San Francisco",
    "Toronto",
    "New York",
    "Mexico City",
]


@pytest.mark.parametrize("destination", SUPPORTED_FLIGHT_DESTINATIONS)
def test_every_supported_flight_destination_has_mock_results(destination: str) -> None:
    state = FriendlyAssistantOrchestrator().chat(
        f"Find a flight from Singapore to {destination} on 2026-10-15 for 2 travellers."
    )

    assert state["flight_response"].status == "success"
    assert state["flight_response"].results
    assert "Flight options" in state["message_to_show_user"]
    assert "don't have mock data" not in state["message_to_show_user"].lower()


SUPPORTED_HOTEL_CODES = [
    "SIN",
    "TYO",
    "PAR",
    "DXB",
    "LON",
    "SYD",
    "BKK",
    "HKG",
    "SEL",
    "KUL",
    "BLR",
    "DEL",
    "BOM",
    "DPS",
    "ZRH",
    "ROM",
    "BCN",
    "SFO",
    "YYZ",
    "NYC",
    "MEX",
]


@pytest.mark.parametrize("destination", SUPPORTED_HOTEL_CODES)
def test_every_supported_hotel_destination_has_mock_results(destination: str) -> None:
    request = HotelTaskRequest.model_validate(
        {
            "session_id": "11111111-1111-1111-1111-111111111111",
            "parameters": {
                "destination": destination,
                "check_in_date": "2026-10-15",
                "check_out_date": "2026-10-20",
                "guests": 2,
                "room_type": "standard",
            },
        }
    )

    response = HotelBookingAgent().invoke(request)

    assert response.status == "success"
    assert response.results
    assert all(option.destination == destination for option in response.results)


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            FlightTaskRequest,
            {
                "session_id": "11111111-1111-1111-1111-111111111111",
                "parameters": {
                    "origin": "SIN",
                    "destination": "TYO",
                    "departure_date": "2026-07-25",
                    "passengers": 2,
                    "cabin_class": "economy",
                    "unexpected": True,
                },
            },
        ),
        (
            HotelTaskRequest,
            {
                "session_id": "11111111-1111-1111-1111-111111111111",
                "parameters": {
                    "destination": "TYO",
                    "check_in_date": "2026-07-25",
                    "check_out_date": "2026-07-30",
                    "guests": 2,
                    "room_type": "standard",
                    "unexpected": True,
                },
            },
        ),
    ],
)
def test_a2a_requests_reject_unknown_fields(model: type, payload: dict) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(payload)


@pytest.mark.parametrize(
    ("metadata_model", "payload"),
    [
        (FlightRequestMetadata, {"timestamp": "2026-07-25T10:00:00"}),
        (HotelRequestMetadata, {"timestamp": "2026-07-25T10:00:00"}),
        (FlightRequestMetadata, {"receiver_agent_id": "hotel-agent"}),
        (HotelRequestMetadata, {"receiver_agent_id": "flight-agent"}),
        (FlightRequestMetadata, {"trace_id": "not-a-uuid"}),
        (HotelRequestMetadata, {"trace_id": "not-a-uuid"}),
    ],
)
def test_a2a_metadata_rejects_invalid_identity_time_and_trace(metadata_model: type, payload: dict) -> None:
    with pytest.raises(ValidationError):
        metadata_model.model_validate(payload)


@pytest.mark.parametrize(
    ("agent", "task_type"),
    [
        (FlightBookingAgent(), "flight_search"),
        (HotelBookingAgent(), "hotel_search"),
    ],
)
def test_agents_return_typed_clarification_for_malformed_task_ids(agent: object, task_type: str) -> None:
    response = agent.invoke(
        {
            "task_id": "not-a-uuid",
            "task_type": task_type,
            "session_id": "11111111-1111-1111-1111-111111111111",
            "parameters": {},
        }
    )

    UUID(response.task_id)
    assert response.status == "needs_clarification"
    assert response.results == []
    assert response.clarification_needed
    assert response.error is None


@pytest.mark.parametrize(
    ("response_model", "payload"),
    [
        (
            FlightTaskResponse,
            {
                "task_id": "11111111-1111-1111-1111-111111111111",
                "status": "success",
                "results": [],
            },
        ),
        (
            FlightTaskResponse,
            {
                "task_id": "11111111-1111-1111-1111-111111111111",
                "status": "failed",
                "results": [],
            },
        ),
        (
            HotelTaskResponse,
            {
                "task_id": "11111111-1111-1111-1111-111111111111",
                "status": "needs_clarification",
                "results": [],
            },
        ),
        (
            HotelTaskResponse,
            {
                "task_id": "11111111-1111-1111-1111-111111111111",
                "status": "partial",
                "results": [],
                "clarification_needed": "More details are needed.",
            },
        ),
    ],
)
def test_a2a_responses_reject_inconsistent_status_payloads(response_model: type, payload: dict) -> None:
    with pytest.raises(ValidationError):
        response_model.model_validate(payload)
