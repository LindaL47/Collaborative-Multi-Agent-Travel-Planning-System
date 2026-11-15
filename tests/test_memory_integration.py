"""Behavior tests for the local, single-user memory MVP."""

from __future__ import annotations

import pytest

import orchestrator.memory_store as memory_module
from orchestrator.agent import FriendlyAssistantOrchestrator
from orchestrator.memory_store import MemoryStore, MemoryStoreError, repeat_route_state


def test_profile_defaults_and_explicit_request_priority(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.json")
    store.save_profile({"home_airport": "SIN", "cabin_class": "economy", "room_type": "deluxe"})
    assistant = FriendlyAssistantOrchestrator(memory_store=store)

    state = assistant.chat("I need a flight and hotel to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers.")
    assert state["travel_params"]["origin"] == "SIN"
    assert state["travel_params"]["cabin_class"] == "economy"
    assert state["travel_params"]["room_type"] == "deluxe"

    changed = assistant.chat("New trip: flight and hotel from Paris to Tokyo on 2025-07-15 returning 2025-07-20, business class, suite room.", state)
    assert changed["travel_params"]["origin"] == "PAR"
    assert changed["travel_params"]["cabin_class"] == "business"
    assert changed["travel_params"]["room_type"] == "suite"
    assert store.load()["profile"]["home_airport"] == "SIN"


def test_restart_restores_active_trip_but_uses_new_a2a_session(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.json")
    first = FriendlyAssistantOrchestrator(memory_store=store).chat(
        "Fly from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers."
    )
    saved = store.load()["active"]
    assert len(saved["conversation_history"]) == 2
    assert "flight_response" not in saved
    assert "final_aggregated_options" not in saved
    assert "session_id" not in saved

    second = FriendlyAssistantOrchestrator(memory_store=store).chat("Change the return date to 2025-06-22.")
    assert second["travel_params"]["origin"] == "SIN"
    assert second["travel_params"]["destination"] == "TYO"
    assert second["travel_params"]["return_date"] == "2025-06-22"
    assert second["session_id"] != first["session_id"]
    assert len(store.load()["active"]["conversation_history"]) <= 8


def test_budget_limits_are_applied_after_search_and_can_be_overridden(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.json")
    store.save_profile({"max_flight_price_usd": 1, "max_hotel_price_usd_per_night": 1})
    assistant = FriendlyAssistantOrchestrator(memory_store=store)
    state = assistant.chat(
        "I need a flight and hotel from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers."
    )
    assert state["flight_response"].results
    assert state["hotel_response"].results
    assert not state["final_aggregated_options"]["flights"]
    assert not state["final_aggregated_options"]["hotels"]
    assert "raise the limit" in state["message_to_show_user"]

    updated = assistant.chat("Flight under $10000 and hotel under $10000 per night.", state)
    assert updated["trip_budget"] == {"max_flight_price_usd": 10000, "max_hotel_price_usd_per_night": 10000}
    assert updated["final_aggregated_options"]["flights"]
    assert updated["final_aggregated_options"]["hotels"]
    assert store.load()["profile"]["max_flight_price_usd"] == 1


def test_archive_and_repeat_route_drop_historical_dates(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.json")
    state = FriendlyAssistantOrchestrator(memory_store=store).chat(
        "Fly from Singapore to Tokyo on 2025-06-15 returning 2025-06-20 for 2 travellers."
    )
    record = store.archive_plan(state, "Morning flight", "Good route")
    assert store.load()["history"][0]["decision"] == "Morning flight"
    assert store.load()["history"][0]["feedback"] == "Good route"

    repeated = repeat_route_state(record)
    assert repeated["travel_params"]["origin"] == "SIN"
    assert repeated["travel_params"]["destination"] == "TYO"
    assert "departure_date" not in repeated["travel_params"]
    assert "return_date" not in repeated["travel_params"]
    assert repeated["pending_clarifications"] == ["travel_dates"]

    followed_up = FriendlyAssistantOrchestrator().chat("2025-07-15 returning 2025-07-20", repeated)
    assert followed_up["travel_params"]["origin"] == "SIN"
    assert followed_up["travel_params"]["destination"] == "TYO"
    assert followed_up["travel_params"]["departure_date"] == "2025-07-15"

    store.save_active(repeated)
    assert store.load()["active"]["travel_params"]["destination"] == "TYO"
    store.clear_active()
    assert store.load()["active"] == {}
    assert len(store.load()["history"]) == 1


def test_multi_city_repeat_keeps_route_and_asks_for_new_dates() -> None:
    repeated = repeat_route_state({"multi_city_plan": {"cities": ["SIN", "TYO", "PAR", "SIN"], "legs": [{"departure_date": "2025-01-01"}]}})
    assert repeated["multi_city_plan"] == {"cities": ["SIN", "TYO", "PAR", "SIN"], "missing": "date_points"}
    state = FriendlyAssistantOrchestrator().chat("Start on 2025-07-15 and stay a week in each city.", repeated)
    assert state["multi_city_plan"]["cities"] == ["SIN", "TYO", "PAR", "SIN"]
    assert "2025-01-01" not in str(state["multi_city_plan"])


def test_multi_city_plan_snapshot_is_serializable_and_restorable(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.json")
    state = FriendlyAssistantOrchestrator(memory_store=store).chat(
        "Plan flights and hotels from Singapore to Tokyo on 2025-07-15 then to Paris on 2025-07-22 then back to Singapore on 2025-07-29."
    )
    assert not state.get("memory_warning")
    assert store.load()["active"]["multi_city_plan"]["cities"] == state["multi_city_plan"]["cities"]
    assert "flight_response" not in store.load()["active"]


def test_corrupt_file_is_not_overwritten_and_chat_still_works(tmp_path) -> None:
    path = tmp_path / "memory.json"
    path.write_text("{broken", encoding="utf-8")
    store = MemoryStore(path)
    state = FriendlyAssistantOrchestrator(memory_store=store).chat("Tokyo")
    assert state["message_to_show_user"]
    assert "Cannot read local memory" in state["memory_warning"]
    assert path.read_text(encoding="utf-8") == "{broken"
    with pytest.raises(MemoryStoreError):
        store.save_profile({"home_airport": "SIN"})
    store.clear_all()
    assert store.load()["active"] == {}


def test_failed_atomic_replace_preserves_previous_file_and_chat(tmp_path, monkeypatch) -> None:
    path = tmp_path / "memory.json"
    store = MemoryStore(path)
    store.save_profile({"home_airport": "SIN"})
    before = path.read_text(encoding="utf-8")

    def denied(*_args) -> None:
        raise PermissionError("read-only folder")

    monkeypatch.setattr(memory_module.os, "replace", denied)
    state = FriendlyAssistantOrchestrator(memory_store=store).chat("Tokyo")
    assert state["message_to_show_user"]
    assert "Cannot save local memory" in state["memory_warning"]
    assert path.read_text(encoding="utf-8") == before
