"""Regression tests for the v18 LLM-first planner data-flow.

The LLM can be disabled in pytest, but the deterministic planner must still
model the same canonical TravelPlan operations that the LLM is asked to return
in production.
"""

from orchestrator.agent import FriendlyAssistantOrchestrator


class _BadOllamaPlanner:
    last_error = None

    def generate_json(self, system_prompt: str, user_prompt: str, timeout_seconds: int = 25):
        return {
            "scope": "both",
            "needs_flight": True,
            "needs_hotel": True,
            "multi_city_segments": [
                {
                    "origin": "Tokyo",
                    "destination": "Singapore",
                    "departure_date": "2026-11-01",
                }
            ],
        }


class _StaleOllamaPlanner:
    last_error = None

    def generate_json(self, system_prompt: str, user_prompt: str, timeout_seconds: int = 25):
        return {
            "scope": "both",
            "needs_flight": True,
            "needs_hotel": True,
            "multi_city_segments": [
                {
                    "origin": "Singapore",
                    "destination": "Tokyo",
                    "departure_date": "2026-09-01",
                    "hotel_destination": "Tokyo",
                    "hotel_check_in": "2026-09-01",
                    "hotel_check_out": "2026-09-06",
                },
                {
                    "origin": "Tokyo",
                    "destination": "Bengaluru",
                    "departure_date": "2026-09-06",
                    "hotel_destination": "Bengaluru",
                    "hotel_check_in": "2026-09-06",
                    "hotel_check_out": "2026-09-11",
                },
                {
                    "origin": "Bengaluru",
                    "destination": "Singapore",
                    "departure_date": "2026-09-11",
                },
            ],
        }


class _OvereagerYesPlanner:
    last_error = None

    def generate_json(self, system_prompt: str, user_prompt: str, timeout_seconds: int = 25):
        return {
            "scope": "both",
            "needs_flight": True,
            "needs_hotel": True,
            "multi_city_segments": [
                {
                    "origin": "Singapore",
                    "destination": "Tokyo",
                    "departure_date": "2026-07-15",
                    "hotel_destination": "Tokyo",
                    "hotel_check_in": "2026-07-15",
                    "hotel_check_out": "2026-07-25",
                },
                {
                    "origin": "Tokyo",
                    "destination": "Singapore",
                    "departure_date": "2026-07-25",
                },
            ],
            "clarification_question": "Do you want this as a multi-city route?",
        }


class _ScopeCreepPlanner:
    last_error = None

    def generate_json(self, system_prompt: str, user_prompt: str, timeout_seconds: int = 25):
        return {
            "scope": "both",
            "needs_flight": True,
            "needs_hotel": True,
            "clarification_question": "What departure date should I use, and how many travellers are going?",
        }


def test_llm_cannot_add_hotel_scope_to_complete_flight_followup() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("i want to travel from singapore to tokyo")

    assistant.nlu.ollama = _ScopeCreepPlanner()
    state = assistant.chat("25th July 2026, 5 travellers", state)

    assert state["pending_clarifications"] == []
    assert state["route"] == "flight"
    assert state["travel_params"]["departure_date"] == "2026-07-25"
    assert state["travel_params"]["passengers"] == 5
    assert state["flight_response"].status == "success"
    assert state.get("hotel_response") is None


def test_llm_cannot_reinterpret_yes_after_hotel_offer_as_new_itinerary() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Fly from Singapore to Tokyo on 2026-07-15 returning 2026-07-25 for 2 travellers.")

    assistant.nlu.ollama = _OvereagerYesPlanner()
    state = assistant.chat("yes", state)

    assert state["route"] == "both"
    assert state["hotel_dates_inferred"] is True
    assert state["hotel_response"].status == "success"
    assert state["pending_clarifications"] == []
    assert "I used your flight dates" in state["message_to_show_user"]


def test_leg_date_update_recalculates_bengaluru_stay_and_keeps_itinerary() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "i will be travelling Singapore to Tokyo to Paris to Singapore from 2026-07-21, 1 week each city. Give flights and hotels."
    )
    state = assistant.chat("change in plan replace paris with BLR.", state)
    state = assistant.chat("again change in plan replace the date for BLR to SIN from 2026-08-04 to 2026-08-08.", state)
    msg = state["message_to_show_user"]
    assert "Leg 3: Bengaluru → Singapore on 2026-08-08" in msg
    assert "Bengaluru: 2026-07-28 to 2026-08-08" in msg
    assert state["route"] == "multi_city"


def test_replace_city_and_extend_stay_in_same_turn_keeps_whole_journey() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "I want to travel from Tokyo to Singapore on 2026-11-01 for 5 days then to Paris for 8 days then to Tokyo for 1 week. Give flights and hotels."
    )
    state = assistant.chat(
        "change in plan replace paris with BLR and extend the stay in BLR for 2 days, give me flight and hotel details for the whole travel journey",
        state,
    )
    msg = state["message_to_show_user"]
    assert state["route"] == "multi_city"
    assert state["multi_city_plan"]["cities"] == ["TYO", "SIN", "BLR", "TYO"]
    assert "Leg 1: Tokyo" in msg and "Singapore on 2026-11-01" in msg
    assert "Leg 2: Singapore" in msg and "Bengaluru on 2026-11-06" in msg
    assert "Leg 3: Bengaluru" in msg and "Tokyo on 2026-11-16" in msg
    assert "Bengaluru: 2026-11-06 to 2026-11-16" in msg


def test_replace_city_and_generic_extend_stay_applies_to_replacement_city() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Plan Singapore to Tokyo to Paris to Singapore starting 2026-09-01, 5 days each city. Give flights and hotels.")
    state = assistant.chat("change in plan replace Paris with BLR and extend the stay by 2 days", state)
    msg = state["message_to_show_user"]
    assert state["multi_city_plan"]["cities"] == ["SIN", "TYO", "BLR", "SIN"]
    assert "Leg 3: Bengaluru" in msg and "Singapore on 2026-09-13" in msg
    assert "Bengaluru: 2026-09-06 to 2026-09-13" in msg


def test_bad_llm_edit_plan_cannot_collapse_existing_multi_city_memory() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat(
        "I want to travel from Tokyo to Singapore on 2026-11-01 for 5 days then to Paris for 8 days then to Tokyo for 1 week. Give flights and hotels."
    )
    assistant.nlu.ollama = _BadOllamaPlanner()
    assistant.nlu.provider = "ollama"

    state = assistant.chat(
        "change in plan replace paris with BLR and extend the stay in BLR for 2 days, give me flight and hotel details for the whole travel journey",
        state,
    )

    assert state["llm_diagnostics"]["used"] is True
    assert state["multi_city_plan"]["cities"] == ["TYO", "SIN", "BLR", "TYO"]
    assert len(state["multi_city_plan"]["legs"]) == 3
    assert "Leg 3: Bengaluru" in state["message_to_show_user"]


def test_fresh_route_prompt_overrides_stale_multi_city_memory_even_if_llm_anchors_old_plan() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Plan Singapore to Tokyo to Paris to Singapore starting 2026-09-01, 5 days each city. Give flights and hotels.")
    state = assistant.chat("change in plan replace Paris with BLR", state)
    assistant.nlu.ollama = _StaleOllamaPlanner()
    assistant.nlu.provider = "ollama"

    state = assistant.chat(
        "Singapore to Tokyo starting 2026-09-01 for 3 days then to Paris for 1 week then to Singapore. Give flights and hotels.",
        state,
    )

    msg = state["message_to_show_user"]
    assert state["llm_diagnostics"]["used"] is True
    assert state["multi_city_plan"]["cities"] == ["SIN", "TYO", "PAR", "SIN"]
    assert "Leg 2: Tokyo" in msg and "Paris on 2026-09-04" in msg
    assert "Paris: 2026-09-04 to 2026-09-11" in msg
    assert "Bengaluru" not in msg


def test_short_flight_details_followup_on_multi_city_returns_flights_only() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Singapore to Tokyo to Paris to Singapore starting 2026-09-01, 5 days each city. Give flights and hotels.")
    state = assistant.chat("give flight details", state)
    msg = state["message_to_show_user"]
    assert "Flight segments" in msg
    assert "Hotel stays" not in msg


def test_historical_food_contextual_question_uses_all_itinerary_cities() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Plan Singapore to Tokyo to Paris to Singapore starting 2026-09-01, 5 days each city. Give flights and hotels.")
    state = assistant.chat("Which of these places is better for food and travel historical places?", state)
    msg = state["message_to_show_user"]
    assert "Paris" in msg and "Tokyo" in msg and "Singapore" in msg
    assert "historical" in msg or "history" in msg


def test_normal_roundtrip_after_multi_city_is_not_leg_date_edit() -> None:
    assistant = FriendlyAssistantOrchestrator()
    state = assistant.chat("Paris to Singapore to Tokyo to Paris starting 2026-08-01, stay 7 days each city. Show flights and hotels.")
    state = assistant.chat("I only need flights from Paris to Singapore on 2026-08-01 and back on 2026-08-10 for 2 travellers.", state)
    assert state["route"] == "flight"
    msg = state["message_to_show_user"]
    assert "PAR → SIN" in msg
    assert "SIN → PAR" in msg
    assert "Tokyo" not in msg
