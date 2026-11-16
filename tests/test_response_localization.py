"""The UI language selects the language of new agent replies."""

import pytest

from orchestrator.agent import FriendlyAssistantOrchestrator


PACKAGE = (
    "Book flight and hotel from Singapore to Tokyo on 2027-07-25 "
    "returning 2027-07-30 for 2 travellers. Choose cheapest, total budget $3000."
)


@pytest.mark.parametrize(
    ("language", "flight_heading", "budget_heading"),
    [
        ("zh", "航班选项", "预算评估"),
        ("ja", "航空券の候補", "予算評価"),
        ("es", "Vuelos", "Evaluación del presupuesto"),
    ],
)
def test_search_and_decision_reply_follow_selected_language(language, flight_heading, budget_heading):
    state = FriendlyAssistantOrchestrator().chat(PACKAGE, language=language)
    reply = state["message_to_show_user"]
    assert flight_heading in reply
    assert budget_heading in reply
    assert "SQ632" in reply
    assert "2027-07-25" in reply
    assert "3,000" in reply
    assert "**Flight options**" not in reply
    assert "**Budget assessment**" not in reply
    assert state["conversation_history"][-1]["content"] == reply


@pytest.mark.parametrize("language,expected", [
    ("zh", "目的地 Paris"), ("ja", "目的地 Paris"), ("es", "destino Paris"),
])
def test_clarification_follows_selected_language(language, expected):
    state = FriendlyAssistantOrchestrator().chat("New trip to Paris.", language=language)
    assert expected in state["message_to_show_user"]
    assert "What travel dates" not in state["message_to_show_user"]


@pytest.mark.parametrize("language,expected", [
    ("zh", "东京六月"), ("ja", "東京の6月"), ("es", "Junio en Tokio"),
])
def test_general_answer_follows_selected_language(language, expected):
    state = FriendlyAssistantOrchestrator().chat("Is June a good time to visit Tokyo?", language=language)
    assert state["message_to_show_user"].startswith(expected)


def test_english_default_and_language_change_on_next_turn():
    assistant = FriendlyAssistantOrchestrator()
    first = assistant.chat(PACKAGE)
    assert "**Flight options**" in first["message_to_show_user"]
    second = assistant.chat("Prioritize comfort.", first, language="zh")
    assert "预算评估" in second["message_to_show_user"]
    assert "**Budget assessment**" not in second["message_to_show_user"]
    assert first["conversation_history"][-1]["content"].startswith("Here are")
