"""Decision support through the real conversational travel graph."""

from orchestrator.agent import FriendlyAssistantOrchestrator


PACKAGE = (
    "Book flight and hotel from Singapore to Tokyo on 2025-06-15 "
    "returning 2025-06-20 for 2 travellers."
)
MULTI_CITY = (
    "Plan Singapore to Tokyo to Paris to Singapore starting 2027-09-01, "
    "5 days each city. Give flights and hotels for 2 travellers."
)


def test_package_runs_both_decision_agents_after_price_filtering():
    state = FriendlyAssistantOrchestrator().chat(PACKAGE + " Choose the cheapest options.")
    assert state["budget_assessment"].minimum_total_cost_usd == 2765
    assert state["recommendation"].estimated_total_usd == 2765
    assert state["recommendation"].is_complete
    assert len(state["recommendation"].flights) == 2
    assert len(state["recommendation"].hotels) == 1
    assert state["debug_trace"][-4:] == [
        "budget_filter", "budget_assessment", "option_recommendation", "user_response_formatting",
    ]
    assert "**Recommended plan" in state["message_to_show_user"]
    assert "**Budget assessment**" in state["message_to_show_user"]
    assert "one room" in state["message_to_show_user"].lower()


def test_decision_tasks_join_the_existing_correlated_a2a_log():
    state = FriendlyAssistantOrchestrator().chat(PACKAGE)
    requests = [entry for entry in state["a2a_messages"] if entry["direction"] == "orchestrator_to_sub_agent"]
    responses = {entry["task_id"]: entry for entry in state["a2a_messages"] if entry["direction"] == "sub_agent_to_orchestrator"}
    assert {entry["task_type"] for entry in requests} == {
        "flight_search", "hotel_search", "budget_assessment", "option_recommendation",
    }
    assert len(state["active_task_ids"]) == 4
    for entry in requests:
        response = responses[entry["task_id"]]
        assert response["trace_id"] == entry["trace_id"]
        assert response["payload"]["metadata"]["agent_id"] == entry["agent_id"]


def test_comfort_choices_yield_to_an_explicit_total_budget():
    state = FriendlyAssistantOrchestrator().chat(PACKAGE + " Prioritize comfort, total budget $3,000.")
    assert state["trip_budget"]["total_budget_usd"] == 3000
    assert state["recommendation"].strategy == "comfort"
    assert state["recommendation"].budget_adjusted
    assert state["recommendation"].estimated_total_usd == 2765
    assert state["recommendation"].within_budget is True


def test_infeasible_total_budget_shows_shortfall():
    state = FriendlyAssistantOrchestrator().chat(PACKAGE + " Total budget of $2000.")
    assert state["budget_assessment"].shortfall_usd == 765
    assert state["recommendation"].within_budget is False
    assert "765" in state["message_to_show_user"]


def test_strategy_only_followup_recommends_again_using_the_active_trip():
    assistant = FriendlyAssistantOrchestrator()
    first = assistant.chat(PACKAGE + " Choose cheapest.")
    second = assistant.chat("Prioritize comfort.", first)
    assert second["recommendation"].strategy == "comfort"
    assert second["recommendation"].estimated_total_usd == 3140
    assert second["travel_params"]["destination"] == "TYO"


def test_new_trip_resets_previous_strategy_and_total_budget():
    assistant = FriendlyAssistantOrchestrator()
    first = assistant.chat(PACKAGE + " Prioritize comfort, total budget $3000.")
    second = assistant.chat("New trip. " + PACKAGE, first)
    assert second["decision_strategy"] == "balanced"
    assert "total_budget_usd" not in second["trip_budget"]
    assert second["recommendation"].within_budget is None


def test_general_and_clarification_turns_clear_previous_decision_results():
    assistant = FriendlyAssistantOrchestrator()
    first = assistant.chat(PACKAGE)
    general = assistant.chat("Is June a good time to visit Tokyo?", first)
    assert general["budget_assessment"] is None
    assert general["recommendation"] is None
    assert general["active_task_ids"] == []
    assert "option_recommendation" not in general["debug_trace"]
    clarification = assistant.chat("New trip to Paris.", first)
    assert clarification["budget_assessment"] is None
    assert clarification["recommendation"] is None


def test_per_ticket_and_per_night_limits_are_applied_before_decisions():
    state = FriendlyAssistantOrchestrator().chat(PACKAGE + " Flight under $1 and hotel under $1 per night.")
    assert state["budget_assessment"].is_complete is False
    assert state["recommendation"].is_complete is False
    assert state["recommendation"].flights == []
    assert state["recommendation"].hotels == []
    assert "subtotal" in state["message_to_show_user"].lower()


def test_multi_city_decisions_cover_every_leg_and_every_stay():
    state = FriendlyAssistantOrchestrator().chat(MULTI_CITY + " Choose cheapest.")
    assert state["route"] == "multi_city"
    assert len(state["recommendation"].flights) == 3
    assert len(state["recommendation"].hotels) == 2
    assert state["budget_assessment"].is_complete
    assert state["recommendation"].estimated_total_usd == state["budget_assessment"].minimum_total_cost_usd
    assert len(state["active_task_ids"]) == 7


def test_failed_multi_city_leg_is_counted_as_missing(monkeypatch):
    from agents.flight_agent import agent as flight_module

    real_search = flight_module.search_mock_flights

    def search_with_unavailable_paris(**kwargs):
        return [] if kwargs["destination"] == "PAR" else real_search(**kwargs)

    monkeypatch.setattr(flight_module, "search_mock_flights", search_with_unavailable_paris)
    state = FriendlyAssistantOrchestrator().chat(MULTI_CITY)
    assert state["budget_assessment"].is_complete is False
    assert len(state["budget_assessment"].missing_groups) == 1
    assert state["recommendation"].is_complete is False
    assert "subtotal" in state["message_to_show_user"].lower()


def test_hotel_only_does_not_create_a_missing_flight_group():
    state = FriendlyAssistantOrchestrator().chat(
        "Only hotels in Tokyo from 2025-06-15 to 2025-06-20 for 2 guests. Choose cheapest."
    )
    assert state["recommendation"].is_complete
    assert state["recommendation"].flights == []
    assert state["recommendation"].estimated_total_usd == 675
