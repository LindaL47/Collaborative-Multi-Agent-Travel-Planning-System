"""Unit tests for the Flight Booking Agent graph and schemas."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agents.flight_agent.agent import FlightBookingAgent
from agents.flight_agent.mock_data import MOCK_FLIGHTS, count_distinct_city_pairs, search_mock_flights
from agents.flight_agent.schemas import CabinClass, FlightSearchParameters, FlightTaskRequest, TaskStatus


def _flight_request(**overrides):
    params = {
        "origin": "SIN",
        "destination": "TYO",
        "departure_date": date(2025, 6, 15),
        "return_date": date(2025, 6, 20),
        "passengers": 2,
        "cabin_class": CabinClass.ECONOMY,
    }
    params.update(overrides.pop("parameters", {}))
    return FlightTaskRequest(
        session_id=str(uuid4()),
        parameters=FlightSearchParameters(**params),
        **overrides,
    )


def test_mock_data_has_required_breadth() -> None:
    assert len(MOCK_FLIGHTS) >= 20
    assert count_distinct_city_pairs() >= 20
    assert any(option.origin == "SIN" for option in MOCK_FLIGHTS)


def test_flight_agent_round_trip_success() -> None:
    agent = FlightBookingAgent()
    response = agent.invoke(_flight_request())

    assert response.status == TaskStatus.SUCCESS.value
    assert response.metadata.agent_id == "flight-agent"
    assert len(response.results) >= 2
    assert {option.trip_leg for option in response.results} == {"outbound", "inbound"}


def test_flight_agent_one_way_success() -> None:
    agent = FlightBookingAgent()
    request = _flight_request(parameters={"return_date": None})
    response = agent.invoke(request)

    assert response.status == "success"
    assert response.results
    assert all(option.trip_leg == "outbound" for option in response.results)


def test_flight_agent_no_match_returns_failed_without_exception() -> None:
    agent = FlightBookingAgent()
    request = _flight_request(parameters={"destination": "KEF"})
    response = agent.invoke(request)

    assert response.status == "failed"
    assert response.results == []
    assert "No mock flights" in response.error


def test_flight_agent_validation_needs_clarification_for_missing_fields() -> None:
    agent = FlightBookingAgent()
    response = agent.invoke(
        {
            "task_id": str(uuid4()),
            "task_type": "flight_search",
            "session_id": str(uuid4()),
            "parameters": {"destination": "TYO"},
            "metadata": {"requested_by": "orchestrator", "timestamp": "2025-01-01T00:00:00+00:00"},
        }
    )

    assert response.status == "needs_clarification"
    assert response.clarification_needed
    assert "parameters.origin" in response.clarification_needed
    assert "parameters.departure_date" in response.clarification_needed


def test_flight_schema_normalizes_city_names_and_cabin_aliases() -> None:
    params = FlightSearchParameters(
        origin="Singapore",
        destination="Tokyo",
        departure_date=date(2026, 6, 15),
        return_destination="Singapore",
        passengers=1,
        cabin_class="business class",
    )

    assert params.origin == "SIN"
    assert params.destination == "TYO"
    assert params.return_destination == "SIN"
    assert params.cabin_class == "business"


def test_flight_schema_rejects_same_origin_destination() -> None:
    with pytest.raises(ValidationError):
        FlightSearchParameters(
            origin="SIN",
            destination="SIN",
            departure_date=date(2025, 6, 15),
            passengers=1,
        )


def test_flight_schema_rejects_invalid_return_date() -> None:
    with pytest.raises(ValidationError):
        FlightSearchParameters(
            origin="SIN",
            destination="TYO",
            departure_date=date(2025, 6, 20),
            return_date=date(2025, 6, 15),
            passengers=1,
        )


def test_search_mock_flights_filters_by_date_and_cabin() -> None:
    economy = search_mock_flights("SIN", "TYO", date(2025, 6, 15), None, "economy")
    business = search_mock_flights("SIN", "TYO", date(2025, 6, 15), None, "business")
    synthetic = search_mock_flights("SIN", "TYO", date(2026, 6, 15), None, "economy")
    unsupported = search_mock_flights("SIN", "KEF", date(2026, 6, 15), None, "economy")
    dynamic = search_mock_flights("DEL", "BCN", date(2026, 1, 10), None, "premium_economy")

    assert economy
    assert business
    assert synthetic
    assert dynamic
    assert all(option.departure_date == date(2026, 6, 15) for option in synthetic)
    assert unsupported == []
    assert all(option.cabin_class == "economy" for option in economy)
    assert all(option.origin == "DEL" and option.destination == "BCN" for option in dynamic)
    assert all(option.cabin_class == "premium_economy" for option in dynamic)
    assert {option.airline for option in dynamic}.isdisjoint({"Global Airways", "WorldConnect Air"})
