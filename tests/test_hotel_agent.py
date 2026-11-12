"""Unit tests for the Hotel Booking Agent graph and schemas."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agents.hotel_agent.agent import HotelBookingAgent
from agents.hotel_agent.mock_data import MOCK_HOTELS, search_mock_hotels
from agents.hotel_agent.schemas import HotelSearchParameters, HotelTaskRequest, RoomType


def _hotel_request(**overrides):
    params = {
        "destination": "TYO",
        "check_in_date": date(2025, 6, 15),
        "check_out_date": date(2025, 6, 20),
        "guests": 2,
        "room_type": RoomType.STANDARD,
        "location_preference": "Shinjuku",
    }
    params.update(overrides.pop("parameters", {}))
    return HotelTaskRequest(
        session_id=str(uuid4()),
        parameters=HotelSearchParameters(**params),
        **overrides,
    )


def test_mock_hotel_data_has_required_breadth() -> None:
    assert len(MOCK_HOTELS) >= 20
    assert len({hotel.destination for hotel in MOCK_HOTELS}) >= 15
    assert any(hotel.destination == "SIN" for hotel in MOCK_HOTELS)


def test_hotel_agent_success() -> None:
    response = HotelBookingAgent().invoke(_hotel_request())

    assert response.status == "success"
    assert response.metadata.agent_id == "hotel-agent"
    assert response.results
    assert response.results[0].destination == "TYO"


def test_hotel_agent_location_preference_ranking() -> None:
    options = search_mock_hotels("TYO", "standard", "Shinjuku")

    assert options
    assert "Shinjuku" in options[0].area or "Shinjuku" in options[0].distance_from_landmark


def test_hotel_agent_no_match_returns_failed_without_exception() -> None:
    request = _hotel_request(parameters={"destination": "KEF"})
    response = HotelBookingAgent().invoke(request)

    assert response.status == "failed"
    assert response.results == []
    assert "No mock hotels" in response.error


def test_hotel_agent_validation_needs_clarification_for_missing_fields() -> None:
    response = HotelBookingAgent().invoke(
        {
            "task_id": str(uuid4()),
            "task_type": "hotel_search",
            "session_id": str(uuid4()),
            "parameters": {"destination": "TYO"},
            "metadata": {"requested_by": "orchestrator", "timestamp": "2025-01-01T00:00:00+00:00"},
        }
    )

    assert response.status == "needs_clarification"
    assert response.clarification_needed
    assert "parameters.check_in_date" in response.clarification_needed
    assert "parameters.check_out_date" in response.clarification_needed


def test_hotel_schema_normalizes_destination_and_room_aliases() -> None:
    params = HotelSearchParameters(
        destination="Mexico City",
        check_in_date=date(2026, 2, 10),
        check_out_date=date(2026, 2, 15),
        guests=2,
        room_type="junior suite",
        location_preference="Roma Norte",
    )

    assert params.destination == "MEX"
    assert params.room_type == "suite"


def test_mock_hotels_generate_supported_dynamic_city_options() -> None:
    options = search_mock_hotels("Mexico City", "suite", "Roma Norte")

    assert len(options) == 3
    assert all(option.destination == "MEX" for option in options)
    assert all(option.room_type == "suite" for option in options)
    assert "Roma Norte" in options[0].area or "Roma Norte" in options[0].distance_from_landmark


def test_hotel_schema_rejects_checkout_before_checkin() -> None:
    with pytest.raises(ValidationError):
        HotelSearchParameters(
            destination="TYO",
            check_in_date=date(2025, 6, 20),
            check_out_date=date(2025, 6, 15),
            guests=1,
        )


def test_hotel_schema_nights_property() -> None:
    params = HotelSearchParameters(
        destination="TYO",
        check_in_date=date(2025, 6, 15),
        check_out_date=date(2025, 6, 20),
        guests=1,
    )

    assert params.nights == 5
