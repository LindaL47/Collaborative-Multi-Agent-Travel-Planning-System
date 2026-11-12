from __future__ import annotations

from orchestrator.agent import FriendlyAssistantOrchestrator


def _new_assistant():
    return FriendlyAssistantOrchestrator()


def _assert_contains_all(text: str, needles: list[str]) -> None:
    for needle in needles:
        assert needle in text


def test_city_list_with_repeated_return_cities_generates_every_leg() -> None:
    s = _new_assistant().chat("Plan a trip through these cities: Tokyo, Singapore, Paris, Tokyo, Paris, Tokyo. I start on 2026-09-05 and want to stay 10 days in each city. Show flights and hotels.")
    _assert_contains_all(s["message_to_show_user"], ["Leg 1: Tokyo → Singapore", "Leg 2: Singapore → Paris", "Leg 3: Paris → Tokyo", "Leg 4: Tokyo → Paris", "Leg 5: Paris → Tokyo"])
    assert len(s["active_task_ids"]) >= 9


def test_variable_duration_prompt_generates_tokyo_and_paris_stays() -> None:
    s = _new_assistant().chat("I will fly from Singapore to Tokyo for 3 days, then Paris for 6 days, then back to Singapore. Start date is 2026-10-01. Need flights and hotels.")
    _assert_contains_all(s["message_to_show_user"], ["Singapore → Tokyo on 2026-10-01", "Tokyo → Paris on 2026-10-04", "Paris → Singapore on 2026-10-10", "Tokyo: 2026-10-01 to 2026-10-04", "Paris: 2026-10-04 to 2026-10-10"])


def test_remove_intermediate_city_and_directly_reconnects_route() -> None:
    a = _new_assistant()
    s = a.chat("I want to travel from Tokyo to Singapore to Paris to Tokyo starting 2026-11-01. Stay 5 days in each place. Give flights and hotels.")
    s = a.chat("change in plan i dont want to go paris. from singapore i will directly go to tokyo, give me flights and hotels details", s)
    _assert_contains_all(s["message_to_show_user"], ["Leg 1: Tokyo → Singapore on 2026-11-01", "Leg 2: Singapore → Tokyo on 2026-11-06", "Singapore: 2026-11-01 to 2026-11-06"])
    assert "Paris → Tokyo" not in s["message_to_show_user"]


def test_skip_city_natural_edit_uses_existing_dates() -> None:
    a = _new_assistant()
    s = a.chat("Tokyo to Singapore to Paris to Tokyo starting 2026-11-01. Stay 5 days each city. Give flights and hotels.")
    s = a.chat("skip Paris and keep the rest same", s)
    _assert_contains_all(s["message_to_show_user"], ["Tokyo → Singapore on 2026-11-01", "Singapore → Tokyo on 2026-11-06"])
    assert "Paris:" not in s["message_to_show_user"]


def test_ambiguous_replace_with_city_asks_target_and_keeps_old_plan() -> None:
    a = _new_assistant()
    s = a.chat("Singapore to Tokyo to Paris to Singapore starting 2026-10-01, stay 5 days each city. Give flights and hotels.")
    old_plan = dict(s["multi_city_plan"])
    s = a.chat("Actually replace with Paris and keep everything the same", s)
    assert "which city should be replaced with Paris" in s["message_to_show_user"]
    assert s["multi_city_plan"] == old_plan


def test_specific_replace_with_non_duplicate_city_rebuilds_plan() -> None:
    a = _new_assistant()
    s = a.chat("Tokyo to Singapore to Paris to Tokyo starting 2026-11-01, stay 5 days each city. Give flights and hotels.")
    s = a.chat("replace Singapore with Dubai, keep everything else same", s)
    _assert_contains_all(s["message_to_show_user"], ["Tokyo → Dubai on 2026-11-01", "Dubai → Paris on 2026-11-06", "Paris → Tokyo on 2026-11-11"])


def test_replace_city_that_creates_duplicate_asks_clarification() -> None:
    a = _new_assistant()
    s = a.chat("Paris to Singapore to Tokyo to Paris starting 2026-08-01, stay 7 days each city. Show flights and hotels.")
    s = a.chat("replace Tokyo with Singapore", s)
    assert "two consecutive Singapore stops" in s["message_to_show_user"]


def test_route_arrow_syntax_is_understood() -> None:
    s = _new_assistant().chat("Route: Paris -> Singapore -> Tokyo -> Paris. Start 2026-08-01. Stay 7 days each city. Need flights and hotels.")
    _assert_contains_all(s["message_to_show_user"], ["Paris → Singapore on 2026-08-01", "Singapore → Tokyo on 2026-08-08", "Tokyo → Paris on 2026-08-15"])


def test_travel_through_places_colon_list_is_understood() -> None:
    s = _new_assistant().chat("Travel through places: Paris, Singapore, Tokyo, Paris. Journey on 2026-08-01. One week in every place. Give package details.")
    _assert_contains_all(s["message_to_show_user"], ["Paris → Singapore on 2026-08-01", "Singapore → Tokyo on 2026-08-08", "Tokyo → Paris on 2026-08-15"])


def test_from_chain_with_via_and_then_is_understood() -> None:
    s = _new_assistant().chat("From Paris via Singapore then to Tokyo then to Paris, start 2026-08-01, 7 days each city, flights and hotels please.")
    _assert_contains_all(s["message_to_show_user"], ["Paris → Singapore on 2026-08-01", "Singapore → Tokyo on 2026-08-08", "Tokyo → Paris on 2026-08-15"])


def test_two_leg_dated_open_jaw_searches_hotels_for_middle_city() -> None:
    s = _new_assistant().chat("Book me from Singapore to Tokyo on 2026-07-25, then from Tokyo to Paris on 2026-07-30. I need hotel in Tokyo too.")
    _assert_contains_all(s["message_to_show_user"], ["Singapore → Tokyo on 2026-07-25", "Tokyo → Paris on 2026-07-30", "Tokyo: 2026-07-25 to 2026-07-30"])


def test_round_trip_after_multi_city_does_not_reuse_stale_plan() -> None:
    a = _new_assistant()
    s = a.chat("Paris to Singapore to Tokyo to Paris starting 2026-08-01, stay 7 days each city. Show flights and hotels.")
    s = a.chat("I only need flights from Paris to Singapore on 2026-08-01 and back on 2026-08-10 for 2 travellers.", s)
    _assert_contains_all(s["message_to_show_user"], ["PAR → SIN", "SIN → PAR"])
    assert "Leg 2" not in s["message_to_show_user"]


def test_incomplete_city_list_asks_for_start_and_duration() -> None:
    s = _new_assistant().chat("I want to visit Singapore, Tokyo and Paris. Give me flights and hotels.")
    assert "multi-city trip" in s["message_to_show_user"]
    assert "start date" in s["message_to_show_user"]


def test_missing_origin_destination_only_asks_planning_question() -> None:
    s = _new_assistant().chat("Tokyo")
    assert "What travel dates" in s["message_to_show_user"]


def test_invalid_return_date_does_not_delegate() -> None:
    s = _new_assistant().chat("Book flights and hotels from Singapore to Tokyo on 2026-08-20 returning 2026-08-15 for 3 travellers.")
    assert "return date is before" in s["message_to_show_user"]
    assert not s.get("active_task_ids")


def test_general_question_after_itinerary_uses_itinerary_context() -> None:
    a = _new_assistant()
    s = a.chat("Singapore to Tokyo to Paris to Singapore starting 2026-09-01, 5 days each city. Give flights and hotels.")
    s = a.chat("Which of these places is better for food and nightlife?", s)
    _assert_contains_all(s["message_to_show_user"], ["Tokyo", "Singapore", "Paris", "food", "nightlife"])
    assert s["route"] == "general"


def test_hotel_add_on_after_flight_only_reuses_dates() -> None:
    a = _new_assistant()
    s = a.chat("I only need flights from Paris to Singapore on 2026-08-01 and back on 2026-08-10 for 2 travellers.")
    s = a.chat("Add hotel also, same dates, near Marina Bay.", s)
    _assert_contains_all(s["message_to_show_user"], ["Hotel options", "2026-08-01 to 2026-08-10", "Marina Bay"])


def test_passenger_change_reuses_trip() -> None:
    a = _new_assistant()
    s = a.chat("Book both flight and hotel from Singapore to Tokyo on 2026-07-25 returning 2026-07-30 for 2 travellers")
    s = a.chat("make it 5 travellers instead", s)
    assert s["travel_params"]["passengers"] == 5
    assert s["travel_params"]["guests"] == 5
    assert "Flight options" in s["message_to_show_user"]


def test_messy_typo_input_is_understood_as_package() -> None:
    s = _new_assistant().chat("tokyo 25 july 2026 frm singapore 5 ppl both hotel flight checkout 30 july")
    _assert_contains_all(s["message_to_show_user"], ["SIN → TYO", "Hotel options", "2026-07-25 to 2026-07-30"])


def test_open_jaw_onward_hotel_followup_uses_onward_city() -> None:
    a = _new_assistant()
    s = a.chat("Book flight and hotel from Singapore to Tokyo on 2025-06-15 returning to Paris on 2025-06-20 for 2 travellers, give hotel info too")
    s = a.chat("2025-06-20, 2025-06-28", s)
    _assert_contains_all(s["message_to_show_user"], ["Paris", "2025-06-20 to 2025-06-28"])


def test_date_change_preserves_trip_memory() -> None:
    a = _new_assistant()
    s = a.chat("want to go singapore")
    s = a.chat("2026-07-25, from tokyo, 3 travellers, give info for flights and hotels, checkout 2026-07-30 back to tokyo", s)
    s = a.chat("change the return date to 2026-07-28 and give me the flight details", s)
    _assert_contains_all(s["message_to_show_user"], ["TYO → SIN", "SIN → TYO", "2026-07-28"])
    assert "Hotel options" not in s["message_to_show_user"]


def test_start_date_duration_followup_completes_pending_multi_city() -> None:
    a = _new_assistant()
    s = a.chat("from singapore to paris then to tokyo then to singapore. based on that give me flight and hotel details")
    s = a.chat("start date is 2026-08-01, in each city i will stay for 7 days", s)
    _assert_contains_all(s["message_to_show_user"], ["Singapore → Paris on 2026-08-01", "Paris → Tokyo on 2026-08-08", "Tokyo → Singapore on 2026-08-15"])


def test_two_turn_week_word_completes_pending_multi_city() -> None:
    a = _new_assistant()
    s = a.chat("from singapore to paris then to tokyo then to singapore. based on that give me flight and hotel details")
    s = a.chat("start date is 2026-08-01, every stop one week", s)
    _assert_contains_all(s["message_to_show_user"], ["2026-08-01", "2026-08-08", "2026-08-15"])


def test_starting_from_without_start_date_reuses_previous_start_date_for_edit() -> None:
    a = _new_assistant()
    s = a.chat("Paris to Singapore to Tokyo to Paris starting 2026-08-01, stay 7 days each city. Give flights and hotels.")
    s = a.chat("now starting from Tokyo to Singapore for 7 days then to Paris for 5 days then at last to Tokyo", s)
    _assert_contains_all(s["message_to_show_user"], ["Tokyo → Singapore on 2026-08-01", "Singapore → Paris on 2026-08-08", "Paris → Tokyo on 2026-08-13"])


def test_natural_fly_from_city_to_city_variable_duration() -> None:
    s = _new_assistant().chat("Starting 2026-12-01, fly from Paris to Singapore for 4 days then Tokyo for 3 days and finally Paris. Need hotels and flights.")
    _assert_contains_all(s["message_to_show_user"], ["Paris → Singapore on 2026-12-01", "Singapore → Tokyo on 2026-12-05", "Tokyo → Paris on 2026-12-08"])


def test_travel_through_multiple_cites_typo_still_understood() -> None:
    s = _new_assistant().chat("i will travel through multiple cites: tokyo, singapore, paris, tokyo. start 2026-12-01. stay 6 days each. show flight hotel details")
    _assert_contains_all(s["message_to_show_user"], ["Tokyo → Singapore on 2026-12-01", "Singapore → Paris on 2026-12-07", "Paris → Tokyo on 2026-12-13"])


def test_room_location_preference_survives_package() -> None:
    s = _new_assistant().chat("Book flight and hotel from Singapore to Tokyo on 2026-07-25 returning 2026-07-30 for 2 travellers near Shinjuku")
    _assert_contains_all(s["message_to_show_user"], ["Flight options", "Hotel options", "Shinjuku"])


def test_only_hotels_request_after_context_does_not_call_flight() -> None:
    a = _new_assistant()
    s = a.chat("Book flights from Singapore to Tokyo on 2026-07-25 returning 2026-07-30 for 2 travellers")
    s = a.chat("show only hotels for the same Tokyo dates", s)
    assert "Hotel options" in s["message_to_show_user"]
    assert "Flight options" not in s["message_to_show_user"]


def test_general_places_followup_resolves_there() -> None:
    a = _new_assistant()
    s = a.chat("tell me about Singapore")
    s = a.chat("tell me the highly reputed places i can visit there", s)
    _assert_contains_all(s["message_to_show_user"], ["Marina Bay Sands", "Gardens by the Bay", "Sentosa"])


def test_general_month_repair_keeps_context() -> None:
    a = _new_assistant()
    s = a.chat("Is June a good time to visit Tokyo?")
    s = a.chat("i said July", s)
    assert "July" in s["message_to_show_user"]
    assert "Tokyo" in s["message_to_show_user"]


def test_decline_hotel_after_flight_offer() -> None:
    a = _new_assistant()
    s = a.chat("I only need flights from Paris to Singapore on 2026-08-01 and back on 2026-08-10 for 2 travellers.")
    s = a.chat("no thanks", s)
    assert "keep it to flights" in s["message_to_show_user"]


def test_destination_first_flow_origin_followup() -> None:
    a = _new_assistant()
    s = a.chat("want to go singapore")
    s = a.chat("2026-07-25, from tokyo, 3 travellers, both flights and hotels, returning 2026-07-30", s)
    _assert_contains_all(s["message_to_show_user"], ["TYO → SIN", "SIN → TYO", "Hotel options"])


def test_modify_return_date_after_full_result() -> None:
    a = _new_assistant()
    s = a.chat("Book flight and hotel from Singapore to Tokyo on 2026-07-25 returning 2026-07-30 for 2 travellers")
    s = a.chat("change return date to 2026-08-01 and show both again", s)
    _assert_contains_all(s["message_to_show_user"], ["2026-08-01", "Hotel options"])


def test_fresh_single_destination_after_multi_city_starts_new_flow() -> None:
    a = _new_assistant()
    s = a.chat("Paris to Singapore to Tokyo to Paris starting 2026-08-01, stay 7 days each city. Show flights and hotels.")
    s = a.chat("Tokyo", s)
    assert "What travel dates" in s["message_to_show_user"]
    assert not s.get("active_task_ids")


def test_new_package_after_multi_city_replaces_itinerary() -> None:
    a = _new_assistant()
    s = a.chat("Paris to Singapore to Tokyo to Paris starting 2026-08-01, stay 7 days each city. Show flights and hotels.")
    s = a.chat("Book flights and hotels from Singapore to Tokyo on 2026-07-25 returning 2026-07-30 for 2 travellers", s)
    assert "Flight options" in s["message_to_show_user"]
    assert "Leg 1" not in s["message_to_show_user"]


def test_mock_data_support_question_does_not_mutate_trip() -> None:
    a = _new_assistant()
    s = a.chat("Book flights and hotels from Singapore to Tokyo on 2026-07-25 returning 2026-07-30 for 2 travellers")
    before = dict(s["travel_params"])
    s = a.chat("is there no mock data tokyo?", s)
    assert "Tokyo mock data" in s["message_to_show_user"]
    assert s["travel_params"] == before


def test_general_query_uses_city_from_question_not_old_itinerary() -> None:
    a = _new_assistant()
    s = a.chat("Book flights and hotels from Singapore to Tokyo on 2026-07-25 returning 2026-07-30 for 2 travellers")
    s = a.chat("tell me highly reputed places in Paris", s)
    _assert_contains_all(s["message_to_show_user"], ["Eiffel Tower", "Louvre", "Montmartre"])


def test_city_chain_with_commas_and_arrows_mixed() -> None:
    s = _new_assistant().chat("itinerary: Paris -> Singapore, Tokyo, Paris. Start 2026-08-01. Stay one week per city. Show flights and hotels.")
    _assert_contains_all(s["message_to_show_user"], ["Paris → Singapore on 2026-08-01", "Singapore → Tokyo on 2026-08-08", "Tokyo → Paris on 2026-08-15"])


def test_cabin_class_is_preserved_in_flight_request() -> None:
    s = _new_assistant().chat("Book business class flights and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 1 passenger")
    assert s["travel_params"]["cabin_class"] == "business"
    assert "Flight options" in s["message_to_show_user"]


def test_hotel_only_request_with_city_and_dates() -> None:
    s = _new_assistant().chat("Find hotels in Paris from 2026-08-01 to 2026-08-08 for 2 guests")
    assert "Hotel options" in s["message_to_show_user"]
    assert "Flight options" not in s["message_to_show_user"]
