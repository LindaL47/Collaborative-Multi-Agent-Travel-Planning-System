"""Unit tests for the Friendly Assistant orchestrator graph."""

from __future__ import annotations

from orchestrator.agent import FriendlyAssistantOrchestrator


def test_full_details_upfront_delegates_to_both_agents() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "I need a flight and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers near Shinjuku."
    )

    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"
    assert state["final_aggregated_options"]["flights"]
    assert state["final_aggregated_options"]["hotels"]
    assert "Flight options" in state["message_to_show_user"]
    assert "Hotel options" in state["message_to_show_user"]


def test_only_destination_asks_for_dates_and_travellers() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Tokyo")

    message = state["message_to_show_user"].lower()
    assert "what travel dates" in message
    assert "how many travellers" in message
    assert state["pending_clarifications"] == ["travel_dates", "travellers", "booking_scope"]
    assert state.get("flight_response") is None


def test_only_flight_details_searches_flight_then_offers_hotel() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Fly from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers.")

    assert state["flight_response"].status == "success"
    assert state.get("hotel_response") is None
    assert state["awaiting_hotel_offer"] is True
    assert "Would you like me to add hotel" in state["message_to_show_user"]


def test_user_accepts_hotel_after_flight_offer_uses_existing_dates() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Fly from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers.")
    state = assistant.chat("Yes, near Shinjuku please", state)

    assert state["hotel_response"].status == "success"
    assert state["hotel_dates_inferred"] is True
    assert state["travel_params"]["check_in_date"] == "2025-06-15"
    assert state["travel_params"]["check_out_date"] == "2025-06-20"


def test_user_changes_destination_mid_chat_resets_and_redelegates() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "I need a flight and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers near Shinjuku."
    )
    old_flight_task = state["flight_response"].task_id

    state = assistant.chat("Actually change the destination to Paris on 2025-07-10 returning 2025-07-18.", state)

    assert state["destination_changed"] is True
    assert state["travel_params"]["destination"] == "PAR"
    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"
    assert state["flight_response"].task_id != old_flight_task
    assert "Paris" in state["message_to_show_user"]


def test_no_available_flights_returns_friendly_error() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Find a flight from Singapore to Reykjavik on 2025-06-15 for 1 traveller.")

    assert state["flight_response"].status == "failed"
    message = state["message_to_show_user"]
    assert "could not find matching" in message.lower()
    assert "raw" not in message.lower()
    assert "traceback" not in message.lower()


def test_round_trip_flight_and_hotel_infers_hotel_dates() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 1 passenger.")

    assert state["hotel_dates_inferred"] is True
    assert state["travel_params"]["check_in_date"] == "2025-06-15"
    assert state["travel_params"]["check_out_date"] == "2025-06-20"
    assert state["hotel_response"].status == "success"
    assert "I used your flight dates" in state["message_to_show_user"]


def test_general_travel_question_does_not_delegate() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Is June a good time to visit Tokyo?")

    assert state["general_question"] is True
    assert state.get("flight_response") is None
    assert state.get("hotel_response") is None
    assert "June" in state["message_to_show_user"]
    assert "Tokyo" in state["message_to_show_user"]


def test_out_of_scope_question_does_not_delegate_or_ask_travel_clarification() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("tell me about calculus and how probability and statistics are needed to learn about AI")

    message = state["message_to_show_user"].lower()
    assert state["user_intent"] == "out_of_scope"
    assert state["route"] == "respond"
    assert state["active_task_ids"] == []
    assert state.get("flight_response") is None
    assert state.get("hotel_response") is None
    assert "focused on travel" in message
    assert "where are you travelling" not in message
    assert "flight options" not in message


def test_out_of_scope_question_after_multi_city_does_not_rerun_stale_itinerary() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Plan Singapore to Tokyo to Paris to Singapore starting 2026-09-01, 5 days each city. Give flights and hotels.")
    previous_plan = dict(state["multi_city_plan"])

    state = assistant.chat("tell me about calculus and how probability and statistics are needed to learn about AI", state)

    message = state["message_to_show_user"].lower()
    assert state["user_intent"] == "out_of_scope"
    assert state["route"] == "respond"
    assert state["active_task_ids"] == []
    assert state["multi_city_plan"] == previous_plan
    assert "focused on travel" in message
    assert "multi-city mock itinerary" not in message
    assert "flight segments" not in message


def test_missing_cabin_class_defaults_to_economy() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Fly from Singapore to Tokyo on 2025-06-15 for 1 passenger.")

    assert state["travel_params"]["cabin_class"] == "economy"
    assert state["flight_response"].status == "success"


def test_ambiguous_message_asks_for_clarification() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Can you help me plan something?")

    assert state["pending_clarifications"]
    assert "flights, hotels, or both" in state["message_to_show_user"]


def test_bare_destination_after_completed_search_does_not_rerun_stale_results() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers near Shinjuku."
    )
    state = assistant.chat("Tokyo", state)

    assert state.get("flight_response") is None
    assert state.get("hotel_response") is None
    assert "what travel dates" in state["message_to_show_user"].lower()
    assert "Flight options" not in state["message_to_show_user"]


def test_explicit_flight_only_after_package_clears_stale_hotel_results() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers near Shinjuku."
    )
    state = assistant.chat("Fly from Singapore to Tokyo on 2025-06-15 returning 2025-06-20.", state)

    assert state["flight_response"].status == "success"
    assert state.get("hotel_response") is None
    assert "Flight options" in state["message_to_show_user"]
    assert "Hotel options" not in state["message_to_show_user"]
    assert state["awaiting_hotel_offer"] is True


def test_general_singapore_question_does_not_reuse_or_mutate_booking_context() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 1 passenger.")
    before_params = dict(state["travel_params"])
    state = assistant.chat("Is June a good time to visit Singapore?", state)

    assert state["general_question"] is True
    assert "Singapore is usually warm" in state["message_to_show_user"]
    assert state["travel_params"] == before_params
    assert "Flight options" not in state["message_to_show_user"]


def test_ambiguous_yearless_date_does_not_redelegate_using_stale_state() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 1 passenger.")
    state = assistant.chat("date 10 June, departure Tokyo", state)

    assert state["route"] == "respond"
    assert "confirm the full date with year" in state["message_to_show_user"]
    assert "Flight options" not in state["message_to_show_user"]


def test_debug_trace_proves_langgraph_nodes_executed() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Fly from Singapore to Tokyo on 2025-06-15 for 1 passenger.")

    assert state["debug_trace"][:3] == ["input_understanding", "state_update", "clarification"]
    assert "flight_delegation" in state["debug_trace"]
    assert state["debug_trace"][-1] == "user_response_formatting"


def test_contextual_origin_followup_fills_origin_not_destination() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("tokyo")
    state = assistant.chat("2026-07-26. 5 travellers are going, yeah both flights and hotels", state)
    assert "Which city" in state["message_to_show_user"]
    assert state["travel_params"]["destination"] == "TYO"

    state = assistant.chat("singapore", state)
    assert state["travel_params"]["origin"] == "SIN"
    assert state["travel_params"]["destination"] == "TYO"
    assert "check" in state["message_to_show_user"].lower() or "return" in state["message_to_show_user"].lower()


def test_natural_date_with_year_is_not_rejected_as_yearless() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("tokyo")
    state = assistant.chat("25 july 2026, 5 travellers both flights and hotels", state)
    assert "YYYY-MM-DD" not in state["message_to_show_user"]
    assert state["travel_params"]["departure_date"] == "2026-07-25"
    assert state["travel_params"]["destination"] == "TYO"


def test_iso_date_followup_continues_existing_pending_flow() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("tokyo")
    state = assistant.chat("26 July, 5, both", state)
    assert "YYYY-MM-DD" in state["message_to_show_user"]
    state = assistant.chat("2026-07-26", state)
    assert state["travel_params"]["departure_date"] == "2026-07-26"
    assert "Where are you travelling" not in state["message_to_show_user"]
    assert "Which city" in state["message_to_show_user"] or "flying from" in state["message_to_show_user"]


def test_places_in_japan_is_general_advice_not_booking_clarification() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("no i want to go to japan, can you tell me places in japan?")
    assert state["general_question"] is True
    assert "Tokyo" in state["message_to_show_user"]
    assert "Kyoto" in state["message_to_show_user"]
    assert "Where are you travelling" not in state["message_to_show_user"]


def test_hotel_date_followup_preserves_flight_scope_for_package_request() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("help me with both flights and hotels. travelling to singapore from tokyo on 2026-07-31")
    assert set(state["pending_clarifications"]) == {"hotel_dates", "travellers"}

    state = assistant.chat("check in 2026-07-31 check out 2026-08-05 for 2 travellers", state)

    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"
    assert "Flight options" in state["message_to_show_user"]
    assert "Hotel options" in state["message_to_show_user"]


def test_both_keyword_sets_package_scope_even_outside_pending_scope() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("singapore")
    state = assistant.chat("2026-07-25, 5, both", state)

    assert state["travel_params"]["needs_flight"] is True
    assert state["travel_params"]["needs_hotel"] is True
    assert "flying from" in state["message_to_show_user"].lower()


def test_new_destination_with_date_and_scope_starts_a_fresh_package_request() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers")
    state = assistant.chat("Paris on 2025-07-10 returning 2025-07-18 for 2 travellers, both", state)

    assert state["travel_params"]["destination"] == "PAR"
    assert state["travel_params"]["origin"] == "SIN"
    assert state["travel_params"]["needs_flight"] is True
    assert state["travel_params"]["needs_hotel"] is True
    assert "Paris" in state["message_to_show_user"]


def test_mock_data_question_is_general_support_answer_not_booking_mutation() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("is there no mock data tokyo?")

    assert state["general_question"] is True
    assert "Tokyo mock data" in state["message_to_show_user"]
    assert "Where are you travelling" not in state["message_to_show_user"]


def test_change_date_flow_preserves_trip_memory_and_redelegates() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("tokyo")
    state = assistant.chat("2026-07-25, 5, both", state)
    state = assistant.chat("singapore, 2026-07-31", state)
    assert "Return:" in state["message_to_show_user"]

    state = assistant.chat("i want to change the date", state)
    assert state["pending_clarifications"] == ["date_change"]
    assert state["travel_params"]["origin"] == "SIN"
    assert state["travel_params"]["destination"] == "TYO"
    assert "update the dates" in state["message_to_show_user"]

    state = assistant.chat("singapore, 2026-07-28", state)
    assert state["travel_params"]["origin"] == "SIN"
    assert state["travel_params"]["destination"] == "TYO"
    assert state["travel_params"]["departure_date"] == "2026-07-28"
    assert state["pending_clarifications"] == ["hotel_dates"]

    state = assistant.chat("2026-08-02", state)
    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"
    assert state["travel_params"]["return_date"] == "2026-08-02"
    assert state["travel_params"]["check_out_date"] == "2026-08-02"
    assert "Return:" in state["message_to_show_user"]
    assert "Stay: 2026-07-28 to 2026-08-02" in state["message_to_show_user"]


def test_date_pair_after_hotel_date_question_sets_checkout_and_return() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("tokyo, 2026-07-25, 5 i want both")
    state = assistant.chat("2026-07-25 and 2026-07-30", state)

    assert state["travel_params"]["return_date"] == "2026-07-30"
    assert state["travel_params"]["check_in_date"] == "2026-07-25"
    assert state["travel_params"]["check_out_date"] == "2026-07-30"
    assert state["hotel_dates_inferred"] is False
    assert state["pending_clarifications"] == ["origin"]

    state = assistant.chat("singapore", state)
    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"
    assert "Stay: 2026-07-25 to 2026-07-30" in state["message_to_show_user"]
    assert "I used your flight dates" not in state["message_to_show_user"]


def test_supported_route_uses_synthetic_mock_flight_data_for_new_dates() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("help me with both flights and hotels. travelling to singapore from tokyo on 2026-07-28")
    state = assistant.chat("check in 2026-07-28 check out 2026-08-02 for 2 travellers", state)

    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"
    assert "TYO → SIN, 2026-07-28" in state["message_to_show_user"]
    assert "I could not find" not in state["message_to_show_user"]


def test_natural_destination_first_then_origin_return_phrase_books_package() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("want to go singapore")
    state = assistant.chat(
        "2026-07-25, from tokyo, 3 travellers, give info for flights and hotels, checkout 2026-07-30 back to tokyo",
        state,
    )

    assert state["travel_params"]["origin"] == "TYO"
    assert state["travel_params"]["destination"] == "SIN"
    assert state["travel_params"]["return_date"] == "2026-07-30"
    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"
    assert "Flight options" in state["message_to_show_user"]
    assert "Hotel options" in state["message_to_show_user"]
    assert "TYO → SIN, 2026-07-25" in state["message_to_show_user"]
    assert "SIN → TYO, 2026-07-30" in state["message_to_show_user"]


def test_city_to_city_round_trip_without_from_is_understood() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "singapore to tokyo on 2026-07-25 and tokyo to singapore on 2026-07-30 for 2 travellers, give me flight and hotel details"
    )

    assert state["travel_params"]["origin"] == "SIN"
    assert state["travel_params"]["destination"] == "TYO"
    assert state["travel_params"]["departure_date"] == "2026-07-25"
    assert state["travel_params"]["return_date"] == "2026-07-30"
    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"
    assert "Flight options" in state["message_to_show_user"]
    assert "Hotel options" in state["message_to_show_user"]


def test_return_date_change_with_date_in_same_turn_redelegates_without_reasking() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("want to go singapore")
    state = assistant.chat(
        "2026-07-25, from tokyo, 3 travellers, give info for flights and hotels, checkout 2026-07-30 back to tokyo",
        state,
    )

    state = assistant.chat("change the return date to 2026-07-28 and give me the flight details", state)

    assert state["travel_params"]["origin"] == "TYO"
    assert state["travel_params"]["destination"] == "SIN"
    assert state["travel_params"]["departure_date"] == "2026-07-25"
    assert state["travel_params"]["return_date"] == "2026-07-28"
    assert state["flight_response"].status == "success"
    assert "What new departure date" not in state["message_to_show_user"]
    assert "SIN → TYO, 2026-07-28" in state["message_to_show_user"]


def test_departure_same_return_date_change_uses_existing_departure() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("want to go singapore")
    state = assistant.chat(
        "2026-07-25, from tokyo, 3 travellers, give info for flights and hotels, checkout 2026-07-30 back to tokyo",
        state,
    )
    state = assistant.chat("i want to change the date", state)
    state = assistant.chat("departure date is same as the earlier one change the return date to 2026-07-28", state)

    assert state["travel_params"]["departure_date"] == "2026-07-25"
    assert state["travel_params"]["return_date"] == "2026-07-28"
    assert state["flight_response"].status == "success"
    assert state["hotel_response"].status == "success"
    assert "Stay: 2026-07-25 to 2026-07-28" in state["message_to_show_user"]


def test_open_jaw_returning_to_third_city_is_respected() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning to Paris 2025-06-20 for 2 travellers."
    )

    assert state["travel_params"]["origin"] == "SIN"
    assert state["travel_params"]["destination"] == "TYO"
    assert state["travel_params"]["return_destination"] == "PAR"
    assert state["flight_response"].status == "success"
    assert "SIN → TYO, 2025-06-15" in state["message_to_show_user"]
    assert "TYO → PAR, 2025-06-20" in state["message_to_show_user"]
    assert "TYO → SIN, 2025-06-20" not in state["message_to_show_user"]
    assert "Hotel options" in state["message_to_show_user"]


def test_cancel_hotels_only_flights_after_package() -> None:
    orchestrator = FriendlyAssistantOrchestrator()
    state = orchestrator.chat("Book flights and hotels from Singapore to Tokyo on 2026-07-25 returning 2026-07-30 for 2 travellers")
    state = orchestrator.chat("Actually don't show hotels, only flights", state)
    message = state["message_to_show_user"]
    assert "Flight options" in message
    assert "Hotel options" not in message


def test_passenger_count_change_reuses_existing_trip() -> None:
    orchestrator = FriendlyAssistantOrchestrator()
    state = orchestrator.chat("Book both flight and hotel from Singapore to Tokyo on 2026-07-25 returning 2026-07-30 for 2 travellers")
    state = orchestrator.chat("make it 5 travellers instead", state)
    assert state["travel_params"]["passengers"] == 5
    assert state["travel_params"]["guests"] == 5
    assert "Flight options" in state["message_to_show_user"]
    assert "Hotel options" in state["message_to_show_user"]


def test_messy_human_input_with_typo_and_yearless_checkout() -> None:
    orchestrator = FriendlyAssistantOrchestrator()
    state = orchestrator.chat("tokyo 25 july 2026 frm singapore 5 ppl both hotel flight checkout 30 july")
    params = state["travel_params"]
    assert params["origin"] == "SIN"
    assert params["destination"] == "TYO"
    assert params["departure_date"] == "2026-07-25"
    assert params["return_date"] == "2026-07-30"
    assert params["passengers"] == 5
    assert "Flight options" in state["message_to_show_user"]
    assert "Hotel options" in state["message_to_show_user"]


def test_invalid_return_date_before_departure_is_blocked() -> None:
    orchestrator = FriendlyAssistantOrchestrator()
    state = orchestrator.chat("Book flight and hotel from Singapore to Tokyo on 2026-07-30 returning 2026-07-25 for 2 travellers")
    assert "return date is before the departure date" in state["message_to_show_user"].lower()
    assert "flight_delegation" not in state["debug_trace"]


def test_general_question_july_and_repair_turn() -> None:
    orchestrator = FriendlyAssistantOrchestrator()
    state = orchestrator.chat("Is July a good time to visit Tokyo?")
    assert "July" in state["message_to_show_user"]
    assert "flight_delegation" not in state["debug_trace"]
    state = orchestrator.chat("i said July", state)
    assert "July" in state["message_to_show_user"]
    assert "flight_delegation" not in state["debug_trace"]


def test_open_jaw_response_adds_onward_hotel_note() -> None:
    orchestrator = FriendlyAssistantOrchestrator()
    state = orchestrator.chat("Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning to Paris on 2025-06-20 for 2 travellers, give hotel information too")
    message = state["message_to_show_user"]
    assert "TYO → PAR" in message
    assert "hotels for Tokyo" in message
    assert "hotels in Paris" in message


def test_open_jaw_onward_city_hotel_date_followup() -> None:
    orchestrator = FriendlyAssistantOrchestrator()
    state = orchestrator.chat(
        "Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning to Paris on 2025-06-20 for 2 travellers, give hotel info too"
    )
    assert "onward_hotel_dates" in state["pending_clarifications"]
    state = orchestrator.chat("2025-06-20, 2025-06-28", state)
    message = state["message_to_show_user"]
    assert "Paris" in message
    assert "Hotel options" in message
    assert "Flight options" not in message
    assert "Stay: 2025-06-20 to 2025-06-28" in message


def test_multi_city_week_everywhere_dynamic_itinerary() -> None:
    orchestrator = FriendlyAssistantOrchestrator()
    state = orchestrator.chat(
        "from singapore to tokyo then to paris then to singapore. i will start from singapore on 2025-08-15 and stay one week everywhere. based on that give me flight and hotel details"
    )
    message = state["message_to_show_user"]
    assert state["route"] == "multi_city"
    assert "multi-city" in message.lower()
    assert "Singapore → Tokyo" in message
    assert "Tokyo → Paris" in message
    assert "Paris → Singapore" in message
    assert "Tokyo: 2025-08-15 to 2025-08-22" in message
    assert "Paris: 2025-08-22 to 2025-08-29" in message


def test_places_followup_resolves_there_from_recent_context(monkeypatch) -> None:
    monkeypatch.setenv("FRIENDLY_ASSISTANT_LLM_PROVIDER", "heuristic")
    orchestrator = FriendlyAssistantOrchestrator()
    state = orchestrator.chat("tell me about singapore")
    state = orchestrator.chat("tell me the highly reputed places i can visit there", state)
    assert "Marina Bay Sands" in state["message_to_show_user"]
    assert "Gardens by the Bay" in state["message_to_show_user"]


def test_llm_diagnostics_include_called_and_provider(monkeypatch) -> None:
    monkeypatch.setenv("FRIENDLY_ASSISTANT_LLM_PROVIDER", "heuristic")
    orchestrator = FriendlyAssistantOrchestrator()
    state = orchestrator.chat("Is July a good time to visit Tokyo?")
    diagnostics = state["llm_diagnostics"]
    assert diagnostics["provider"] == "heuristic"
    assert diagnostics["called"] is False
    assert diagnostics["used"] is False


def test_multi_city_start_date_and_duration_same_turn_is_computed() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "from singapore to paris then to tokyo then to singapore. starting date 2026-08-01, "
        "i will stay in each place a week as per that give me flight and hotel informations"
    )

    assert state["route"] == "multi_city"
    assert state["pending_clarifications"] == []
    message = state["message_to_show_user"]
    assert "Singapore → Paris on 2026-08-01" in message
    assert "Paris → Tokyo on 2026-08-08" in message
    assert "Tokyo → Singapore on 2026-08-15" in message
    assert "Paris: 2026-08-01 to 2026-08-08" in message
    assert "Tokyo: 2026-08-08 to 2026-08-15" in message


def test_multi_city_dates_can_be_completed_from_followup_duration() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "from singapore to paris then to tokyo then to singapore. based on that give me flight and hotel informations"
    )
    assert state["pending_clarifications"] == ["multi_city_dates"]

    state = assistant.chat("start date is 2026-08-01, in each city i will stay for 7 days", state)

    assert state["route"] == "multi_city"
    assert state["pending_clarifications"] == []
    message = state["message_to_show_user"]
    assert "Singapore → Paris on 2026-08-01" in message
    assert "Paris → Tokyo on 2026-08-08" in message
    assert "Tokyo → Singapore on 2026-08-15" in message
    assert "Paris: 2026-08-01 to 2026-08-08" in message
    assert "Tokyo: 2026-08-08 to 2026-08-15" in message


def test_multi_city_chain_without_then_to_generates_all_legs_and_stays() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "from paris to singapore to tokyo to singapore to paris. starting my journey on 2026-08-01, "
        "i will stay in each place for a week. give me the flight and hotel details"
    )

    assert state["route"] == "multi_city"
    message = state["message_to_show_user"]
    assert "Leg 1: Paris → Singapore on 2026-08-01" in message
    assert "Leg 2: Singapore → Tokyo on 2026-08-08" in message
    assert "Leg 3: Tokyo → Singapore on 2026-08-15" in message
    assert "Leg 4: Singapore → Paris on 2026-08-22" in message
    assert "Singapore: 2026-08-01 to 2026-08-08" in message
    assert "Tokyo: 2026-08-08 to 2026-08-15" in message
    assert "Singapore: 2026-08-15 to 2026-08-22" in message
    assert state["pending_clarifications"] == []


def test_pending_multi_city_dates_accept_after_one_week_language() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("from paris to singapore to tokyo to paris, give me flight and hotel details")
    assert "multi_city_dates" in state["pending_clarifications"]

    state = assistant.chat("check every place after 1 week starting 2026-08-01", state)
    assert state["route"] == "multi_city"
    message = state["message_to_show_user"]
    assert "Leg 1: Paris → Singapore on 2026-08-01" in message
    assert "Leg 2: Singapore → Tokyo on 2026-08-08" in message
    assert "Leg 3: Tokyo → Paris on 2026-08-15" in message


def test_multi_city_cities_as_follow_list_generates_full_itinerary() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "i want to travel through the cites as follow: paris, singapore, tokyo, singapore, paris. "
        "starting my journey on 2026-08-01, i will stay in each place for a week. give me the flight and hotel details"
    )

    assert state["route"] == "multi_city"
    assert len(state["final_aggregated_options"]["multi_city"]["flights"]) == 4
    message = state["message_to_show_user"]
    assert "Leg 1: Paris → Singapore on 2026-08-01" in message
    assert "Leg 2: Singapore → Tokyo on 2026-08-08" in message
    assert "Leg 3: Tokyo → Singapore on 2026-08-15" in message
    assert "Leg 4: Singapore → Paris on 2026-08-22" in message
    assert "Singapore: 2026-08-01 to 2026-08-08" in message
    assert "Tokyo: 2026-08-08 to 2026-08-15" in message
    assert "Singapore: 2026-08-15 to 2026-08-22" in message


def test_multi_city_new_list_prompt_replaces_previous_itinerary_not_stale() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "from paris to singapore to tokyo to singapore to paris. starting my journey on 2026-08-01, "
        "i will stay in each place for a week. give me the flight and hotel details"
    )
    state = assistant.chat(
        "i want to travel through the cites as follow: paris, singapore, tokyo, singapore, paris. "
        "starting my journey on 2026-08-01, i will stay in each place for a week. give me the flight and hotel details",
        state,
    )
    message = state["message_to_show_user"]
    assert "Leg 4: Singapore → Paris on 2026-08-22" in message
    assert len(state["active_task_ids"]) >= 7


def test_multi_city_variable_duration_route_replaces_previous_itinerary() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "i want to travel through the cites as follow: paris, singapore, tokyo, singapore, paris. "
        "starting my journey on 2026-08-01, i will stay in each place for a week. give me the flight and hotel details"
    )
    state = assistant.chat(
        "i will be travelling through multiple cites starting from tokyo to singapore for 7 days "
        "then to paris for 5 days then at last to tokyo. give me the flight and hotel details",
        state,
    )
    message = state["message_to_show_user"]
    assert state["route"] == "multi_city"
    assert "Leg 1: Tokyo → Singapore on 2026-08-01" in message
    assert "Leg 2: Singapore → Paris on 2026-08-08" in message
    assert "Leg 3: Paris → Tokyo on 2026-08-13" in message
    assert "Singapore: 2026-08-01 to 2026-08-08" in message
    assert "Paris: 2026-08-08 to 2026-08-13" in message
    assert "Paris → Singapore on 2026-08-01" not in message


def test_multi_city_variable_duration_without_prior_start_asks_for_start_date() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "i will be travelling through multiple cites starting from tokyo to singapore for 7 days "
        "then to paris for 5 days then at last to tokyo. give me the flight and hotel details"
    )
    assert state["route"] == "respond"
    assert "start date" in state["message_to_show_user"].lower() or "travel date" in state["message_to_show_user"].lower()
    assert "multi_city_dates" in state["pending_clarifications"]


def test_duration_edit_recalculates_existing_multi_city_dates() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("I want to travel from Tokyo to Singapore to Paris to Tokyo starting 2026-11-01. Stay 5 days in each place. Give flights and hotels.")
    state = assistant.chat("Make Singapore 7 days instead, keep Paris 5 days.", state)
    message = state["message_to_show_user"]
    assert "Leg 2: Singapore → Paris on 2026-11-08" in message
    assert "Leg 3: Paris → Tokyo on 2026-11-13" in message
    assert "Singapore: 2026-11-01 to 2026-11-08" in message
    assert "Paris: 2026-11-08 to 2026-11-13" in message


def test_explicit_two_leg_open_jaw_with_hotel_dates_does_not_ask_duration() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Book me from Singapore to Tokyo on 2026-07-25, then from Tokyo to Paris on 2026-07-30. I need hotel in Tokyo too.")
    message = state["message_to_show_user"]
    assert state["route"] == "multi_city"
    assert state["pending_clarifications"] == []
    assert "Leg 1: Singapore → Tokyo on 2026-07-25" in message
    assert "Leg 2: Tokyo → Paris on 2026-07-30" in message
    assert "Tokyo: 2026-07-25 to 2026-07-30" in message


def test_normal_roundtrip_after_multi_city_clears_stale_itinerary() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Plan Paris to Singapore to Tokyo to Paris starting 2026-08-01, staying 7 days in each city. Show flights and hotels.")
    state = assistant.chat("I only need flights from Paris to Singapore on 2026-08-01 and back on 2026-08-10 for 2 travellers.", state)
    assert state["route"] == "flight"
    assert state["pending_clarifications"] == []
    assert "Flight options" in state["message_to_show_user"]
    assert "multi-city" not in state["message_to_show_user"].lower()


def test_duplicate_city_replacement_asks_clarification_not_bad_leg() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Plan Paris to Singapore to Tokyo to Paris starting 2026-08-01, staying 7 days in each city. Show flights and hotels.")
    state = assistant.chat("Actually replace Tokyo with Singapore again, keep everything else same.", state)
    assert state["route"] == "respond"
    assert "two consecutive Singapore stops" in state["message_to_show_user"]
    assert "Singapore → Singapore" not in state["message_to_show_user"]


def test_itinerary_food_nightlife_followup_uses_active_multi_city_context() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Plan Singapore to Tokyo to Paris to Singapore starting 2026-09-01, 5 days each city. Give flights and hotels.")
    state = assistant.chat("Which of these places is better for food and nightlife?", state)
    message = state["message_to_show_user"]
    assert "Tokyo" in message
    assert "Singapore" in message
    assert "Paris" in message
    assert "flight" not in state["route"]
