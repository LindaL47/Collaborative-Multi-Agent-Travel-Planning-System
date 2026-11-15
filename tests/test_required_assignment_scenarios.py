"""Explicit coverage for the six minimum assignment scenarios and senior demo checks."""

from __future__ import annotations

from datetime import date, timedelta

from agents.flight_agent.schemas import FlightTaskRequest
from agents.hotel_agent.schemas import HotelTaskRequest
from orchestrator.agent import FriendlyAssistantOrchestrator


def _next_month_day(month: int, day: int) -> date:
    today = date.today()
    candidate = date(today.year, month, day)
    if candidate < today:
        candidate = date(today.year + 1, month, day)
    return candidate


def test_required_1_full_details_upfront_delegates_to_both_agents() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers near Shinjuku."
    )

    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"
    assert state["route"] == "both"
    assert "Flight options" in state["message_to_show_user"]
    assert "Hotel options" in state["message_to_show_user"]
    assert len(state["active_task_ids"]) == 4


def test_pdf_problem_statement_example_asks_for_exact_date_before_delegating() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "I'd like to fly from Singapore to Tokyo, arriving around the 15th of June, and I'll need a hotel for 5 nights near Shinjuku."
    )

    expected_check_in = _next_month_day(6, 15)
    expected_check_out = expected_check_in + timedelta(days=5)
    assert state["route"] == "respond"
    assert state["pending_clarifications"] == ["date_precision", "travellers"]
    assert state["travel_params"]["origin"] == "SIN"
    assert state["travel_params"]["destination"] == "TYO"
    assert state["travel_params"]["departure_date"] == expected_check_in.isoformat()
    assert state["travel_params"]["check_in_date"] == expected_check_in.isoformat()
    assert state["travel_params"]["check_out_date"] == expected_check_out.isoformat()
    assert state.get("flight_response") is None
    assert state.get("hotel_response") is None
    assert "confirm the exact" in state["message_to_show_user"].lower()
    assert "travellers" in state["message_to_show_user"].lower()


def test_pdf_problem_statement_followup_delegates_after_clarification() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "I'd like to fly from Singapore to Tokyo, arriving around the 15th of June, and I'll need a hotel for 5 nights near Shinjuku."
    )
    state = assistant.chat("Use 2026-06-15 for 2 travellers.", state)

    assert state["route"] == "both"
    assert state["pending_clarifications"] == []
    assert state["travel_params"]["departure_date"] == "2026-06-15"
    assert state["travel_params"]["check_in_date"] == "2026-06-15"
    assert state["travel_params"]["check_out_date"] == "2026-06-20"
    assert state["travel_params"]["passengers"] == 2
    assert state["travel_params"]["guests"] == 2
    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"
    assert "Flight options" in state["message_to_show_user"]
    assert "Hotel options" in state["message_to_show_user"]
    assert "Shinjuku" in state["message_to_show_user"]


def test_required_2_only_destination_asks_for_dates_travellers_and_scope() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Tokyo")

    message = state["message_to_show_user"].lower()
    assert "what travel dates" in message
    assert "how many travellers" in message
    assert "flights, hotels, or both" in message
    assert state["pending_clarifications"] == ["travel_dates", "travellers", "booking_scope"]
    assert state.get("flight_response") is None
    assert state.get("hotel_response") is None


def test_required_2_city_pair_without_travellers_asks_for_date_and_travellers_then_waits() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("i want to travel from singapore to tokyo")

    message = state["message_to_show_user"].lower()
    assert "departure date" in message
    assert "how many travellers" in message
    assert state["pending_clarifications"] == ["departure_date", "travellers"]
    assert state.get("flight_response") is None

    state = assistant.chat("25th July 2026, 5 travellers", state)
    assert state["pending_clarifications"] == []
    assert state["travel_params"]["departure_date"] == "2026-07-25"
    assert state["travel_params"]["passengers"] == 5
    assert state["flight_response"].status == "success"
    assert state.get("hotel_response") is None
    assert state["awaiting_hotel_offer"] is True


def test_required_2_city_pair_date_only_followup_still_waits_for_travellers() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("i want to travel from singapore to tokyo")
    state = assistant.chat("2026-07-15", state)

    assert state["pending_clarifications"] == ["travellers"]
    assert state.get("flight_response") is None
    assert "how many travellers" in state["message_to_show_user"].lower()

    state = assistant.chat("2 travellers", state)
    assert state["pending_clarifications"] == []
    assert state["flight_response"].status == "success"
    assert state.get("hotel_response") is None
    assert state["awaiting_hotel_offer"] is True


def test_required_3_only_flight_details_books_flight_then_offers_hotel() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("I only need flights from Paris to Singapore on 2026-08-01 and back on 2026-08-10 for 2 travellers.")

    assert state["flight_response"].status == "success"
    assert state.get("hotel_response") is None
    assert state["awaiting_hotel_offer"] is True
    assert "Would you like me to add hotel options" in state["message_to_show_user"]
    assert "Hotel options" not in state["message_to_show_user"]


def test_required_4_destination_change_resets_only_relevant_state_and_redelegates() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers near Shinjuku."
    )
    old_session_id = state["session_id"]
    old_origin = state["travel_params"]["origin"]

    state = assistant.chat("Actually change the destination to Paris on 2025-07-10 returning 2025-07-18.", state)

    assert state["destination_changed"] is True
    assert state["session_id"] == old_session_id
    assert state["travel_params"]["origin"] == old_origin
    assert state["travel_params"]["destination"] == "PAR"
    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"
    assert "Paris" in state["message_to_show_user"]


def test_required_5_no_available_flights_is_friendly_and_not_raw() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Find a flight from Singapore to Reykjavik on 2025-06-15 for 1 traveller.")

    assert state["flight_response"].status == "failed"
    message = state["message_to_show_user"].lower()
    assert "could not find matching" in message
    assert "traceback" not in message
    assert "validationerror" not in message
    assert "raw" not in message


def test_required_6_round_trip_package_infers_hotel_dates_from_flights() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 1 passenger.")

    assert state["hotel_dates_inferred"] is True
    assert state["travel_params"]["check_in_date"] == "2025-06-15"
    assert state["travel_params"]["check_out_date"] == "2025-06-20"
    assert state["hotel_response"].status == "success"
    assert "I used your flight dates" in state["message_to_show_user"]


def test_required_6_accepting_hotel_after_round_trip_flight_uses_flight_dates() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Fly from Singapore to Tokyo on 2026-07-15 returning 2026-07-25 for 2 travellers.")

    assert state["flight_response"].status == "success"
    assert state.get("hotel_response") is None
    assert state["awaiting_hotel_offer"] is True

    state = assistant.chat("yes", state)

    assert state["pending_clarifications"] == []
    assert state["hotel_dates_inferred"] is True
    assert state["travel_params"]["check_in_date"] == "2026-07-15"
    assert state["travel_params"]["check_out_date"] == "2026-07-25"
    assert state["hotel_response"].status == "success"
    assert "Hotel options" in state["message_to_show_user"]


def test_hotel_dates_after_one_way_flight_do_not_create_return_flights() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("i want to travel from singapore to tokyo")
    state = assistant.chat("25th July 2026, 5 travellers", state)
    state = assistant.chat("yes", state)

    assert state["pending_clarifications"] == ["hotel_dates"]
    assert state["travel_params"]["check_in_date"] == "2026-07-25"
    assert "2026-07-25" in state["message_to_show_user"]
    assert "check-out date or number of nights" in state["message_to_show_user"]

    state = assistant.chat("check out 2026-08-01", state)

    assert state["flight_response"].status == "success"
    assert all(option.trip_leg == "outbound" for option in state["flight_response"].results)
    assert state["hotel_response"].status == "success"
    assert "Return:" not in state["message_to_show_user"]


def test_unsupported_mock_destination_returns_clear_no_data_message() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("new plan i want to travel from BLR to Chennai, 5 travellers, 2026-07-25")

    message = state["message_to_show_user"].lower()
    assert state["route"] == "respond"
    assert state["pending_clarifications"] == []
    assert state.get("flight_response") is None
    assert state.get("hotel_response") is None
    assert "don't have mock data for chennai" in message
    assert "singapore" in message
    assert "tokyo" in message


def test_unsupported_mock_origin_and_destination_are_named() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("new plan i want to travel from Guwahati to Chennai, 5 travellers, 2026-07-25")

    message = state["message_to_show_user"].lower()
    assert "guwahati" in message
    assert "chennai" in message
    assert "try with" in message
    assert state.get("flight_response") is None


def test_new_plan_clears_old_travellers_and_requires_fresh_count() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("i want to travel from singapore to tokyo")
    state = assistant.chat("5 travellers, 2026-07-25", state)
    assert state["travel_params"]["passengers"] == 5

    state = assistant.chat("planning a new trip from BLR to Singapore check in date 2026-08-5. give flight and hotel details", state)

    assert "travellers" in state["pending_clarifications"]
    assert state.get("flight_response") is None
    assert state.get("hotel_response") is None
    assert "passengers" not in state["travel_params"]
    assert "guests" not in state["travel_params"]
    assert state["travel_params"]["origin"] == "BLR"
    assert state["travel_params"]["destination"] == "SIN"
    assert state["travel_params"]["departure_date"] == "2026-08-05"


def test_new_package_followup_uses_labeled_checkin_for_nights() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("i want to travel from singapore to tokyo")
    state = assistant.chat("5 travellers, 2026-07-25", state)

    state = assistant.chat("planning a new trip from BLR to Singapore check in date 2026-08-5. give flight and hotel details", state)
    assert state["travel_params"]["check_in_date"] == "2026-08-05"
    assert "travellers" in state["pending_clarifications"]
    assert "hotel_dates" in state["pending_clarifications"]

    state = assistant.chat("5 travellers, 5 nights", state)

    assert state["pending_clarifications"] == []
    assert state["travel_params"]["passengers"] == 5
    assert state["travel_params"]["check_in_date"] == "2026-08-05"
    assert state["travel_params"]["check_out_date"] == "2026-08-10"
    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"


def test_one_way_hotel_add_on_accepts_number_of_nights_from_flight_date() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("i want to travel from singapore to tokyo")
    state = assistant.chat("25th July 2026, 5 travellers", state)
    state = assistant.chat("yes", state)
    state = assistant.chat("5 nights", state)

    assert state["pending_clarifications"] == []
    assert state["travel_params"]["check_in_date"] == "2026-07-25"
    assert state["travel_params"]["check_out_date"] == "2026-07-30"
    assert state["hotel_response"].status == "success"


def test_general_travel_question_answers_directly_without_delegating() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Is July a good time to visit Tokyo with family?")

    assert state["general_question"] is True
    assert state.get("flight_response") is None
    assert state.get("hotel_response") is None
    assert state["active_task_ids"] == []
    assert "Tokyo" in state["message_to_show_user"]


def test_a2a_metadata_extensions_are_present_without_removing_required_fields() -> None:
    flight_request = FlightTaskRequest.model_validate(
        {
            "session_id": "11111111-1111-1111-1111-111111111111",
            "parameters": {
                "origin": "SIN",
                "destination": "TYO",
                "departure_date": "2026-07-25",
                "return_date": "2026-07-30",
                "passengers": 2,
                "cabin_class": "economy",
            },
        }
    )
    hotel_request = HotelTaskRequest.model_validate(
        {
            "session_id": "11111111-1111-1111-1111-111111111111",
            "parameters": {
                "destination": "TYO",
                "check_in_date": "2026-07-25",
                "check_out_date": "2026-07-30",
                "guests": 2,
                "room_type": "standard",
            },
        }
    )

    assert flight_request.task_type == "flight_search"
    assert hotel_request.task_type == "hotel_search"
    assert flight_request.metadata.protocol_version == "a2a-mock-1.0"
    assert hotel_request.metadata.protocol_version == "a2a-mock-1.0"
    assert flight_request.metadata.receiver_agent_id == "flight-agent"
    assert hotel_request.metadata.receiver_agent_id == "hotel-agent"


def test_multi_turn_scope_followup_uses_active_itinerary_without_hotels() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Plan Singapore to Tokyo to Paris to Singapore starting 2026-09-01, 5 days each city. Give flights and hotels.")
    state = assistant.chat("give flight details only", state)

    message = state["message_to_show_user"]
    assert "Flight segments" in message
    assert "Hotel stays" not in message
    assert state["last_successful_multi_city_plan"]


def test_graph_visualization_helpers_are_non_empty_mermaid() -> None:
    from agents.flight_agent.agent import FlightBookingAgent
    from agents.hotel_agent.agent import HotelBookingAgent

    assert "flowchart TD" in FriendlyAssistantOrchestrator.mermaid_diagram()
    assert "flowchart TD" in FlightBookingAgent.mermaid_diagram()
    assert "flowchart TD" in HotelBookingAgent.mermaid_diagram()
