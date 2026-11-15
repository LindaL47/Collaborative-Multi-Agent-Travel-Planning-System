"""Small, local-only memory store for the single-user Streamlit demo."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Dict
from uuid import uuid4


DEFAULT_MEMORY_PATH = Path(__file__).resolve().parents[1] / ".synctrip" / "memory.json"
PROFILE_FIELDS = {
    "home_airport", "cabin_class", "room_type",
    "max_flight_price_usd", "max_hotel_price_usd_per_night",
}
TRAVEL_FIELDS = {
    "origin", "destination", "departure_date", "return_date", "return_destination",
    "passengers", "guests", "cabin_class", "room_type", "location_preference",
    "check_in_date", "check_out_date", "stay_duration_days", "one_way",
    "needs_flight", "needs_hotel", "_hotel_add_on_after_one_way",
}
ACTIVE_FIELDS = {
    "multi_city_plan", "last_successful_multi_city_plan", "pending_clarifications",
    "last_completed_params", "conversation_focus", "awaiting_hotel_offer",
    "planner_revision", "trip_budget",
}


class MemoryStoreError(RuntimeError):
    """The local memory file could not be read or safely updated."""


def _empty_data() -> Dict[str, Any]:
    return {"version": 1, "profile": {}, "active": {}, "history": []}


def _travel_params(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {key: val for key, val in value.items() if key in TRAVEL_FIELDS and val is not None}


def active_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only JSON-safe planner context, never A2A responses or results."""
    if not isinstance(state, dict):
        return {}
    snapshot = {key: state[key] for key in ACTIVE_FIELDS if key in state}
    snapshot["travel_params"] = _travel_params(state.get("travel_params"))
    history = state.get("conversation_history", [])
    snapshot["conversation_history"] = [
        {"role": turn["role"], "content": turn["content"]}
        for turn in history[-8:]
        if isinstance(turn, dict)
        and turn.get("role") in {"user", "assistant"}
        and isinstance(turn.get("content"), str)
    ] if isinstance(history, list) else []
    snapshot["last_completed_params"] = _travel_params(state.get("last_completed_params"))
    # Fails rather than silently writing a partial or invalid memory file.
    json.dumps(snapshot, ensure_ascii=False)
    return snapshot


def repeat_route_state(record: Dict[str, Any]) -> Dict[str, Any]:
    """Use a saved route as a fresh draft; historical dates never return."""
    plan = record.get("multi_city_plan", {})
    if isinstance(plan, dict) and isinstance(plan.get("cities"), list) and len(plan["cities"]) >= 3:
        cities = [str(city) for city in plan["cities"]]
        return {
            "multi_city_plan": {"cities": cities, "missing": "date_points"},
            "pending_clarifications": ["multi_city_dates"],
            "conversation_history": [{"role": "assistant", "content": "I restored your saved route. Please give new travel dates for each leg, or a start date and stay duration for each city."}],
        }
    params = _travel_params(record.get("travel_params"))
    route = {key: params[key] for key in ("origin", "destination", "needs_flight", "needs_hotel") if key in params}
    return {
        "travel_params": route,
        "pending_clarifications": ["travel_dates"],
        "conversation_history": [{"role": "assistant", "content": "I restored your saved route. What new travel dates should I use?"}],
    }


class MemoryStore:
    """One JSON file, one local demo user, no external services."""

    def __init__(self, path: Path = DEFAULT_MEMORY_PATH) -> None:
        self.path = Path(path)
        self._lock = RLock()

    def load(self) -> Dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return _empty_data()
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise MemoryStoreError(f"Cannot read local memory: {exc}") from exc
            if (
                not isinstance(data, dict)
                or data.get("version") != 1
                or not isinstance(data.get("profile"), dict)
                or not isinstance(data.get("active"), dict)
                or not isinstance(data.get("history"), list)
            ):
                raise MemoryStoreError("Local memory has an unsupported or invalid format.")
            active = data["active"]
            profile = data["profile"]
            turns = active.get("conversation_history", [])
            limits = active.get("trip_budget", {})
            plans = [active.get("multi_city_plan", {}), active.get("last_successful_multi_city_plan", {})]
            plans.extend(record.get("multi_city_plan", {}) for record in data["history"] if isinstance(record, dict))
            if (
                set(profile) - PROFILE_FIELDS
                or any(type(profile.get(key)) is not int or profile[key] <= 0 for key in ("max_flight_price_usd", "max_hotel_price_usd_per_night") if key in profile)
                or any(profile.get(key) not in allowed for key, allowed in (("cabin_class", {"economy", "premium_economy", "business", "first"}), ("room_type", {"standard", "deluxe", "suite", "family"})) if key in profile)
                or ("home_airport" in profile and (not isinstance(profile["home_airport"], str) or len(profile["home_airport"]) != 3 or not profile["home_airport"].isascii() or not profile["home_airport"].isalpha()))
                or not isinstance(active.get("travel_params", {}), dict)
                or not isinstance(active.get("multi_city_plan", {}), dict)
                or not isinstance(active.get("last_successful_multi_city_plan", {}), dict)
                or not isinstance(active.get("last_completed_params", {}), dict)
                or not isinstance(active.get("pending_clarifications", []), list)
                or any(not isinstance(value, str) for value in active.get("pending_clarifications", []))
                or not isinstance(limits, dict)
                or any(key not in {"max_flight_price_usd", "max_hotel_price_usd_per_night"} or type(value) is not int or value <= 0 for key, value in limits.items())
                or not isinstance(turns, list)
                or any(not isinstance(turn, dict) or turn.get("role") not in {"user", "assistant"} or not isinstance(turn.get("content"), str) for turn in turns)
                or any(not isinstance(record, dict) or not isinstance(record.get("id"), str) or not isinstance(record.get("saved_at"), str) or not isinstance(record.get("decision"), str) or not isinstance(record.get("feedback"), str) or not isinstance(record.get("travel_params", {}), dict) or not isinstance(record.get("multi_city_plan", {}), dict) for record in data["history"])
                or any(not isinstance(plan, dict) or ("cities" in plan and (not isinstance(plan["cities"], list) or any(not isinstance(city, str) for city in plan["cities"]))) for plan in plans)
            ):
                raise MemoryStoreError("Local memory has an invalid saved trip or conversation.")
            return data

    def _write(self, data: Dict[str, Any]) -> None:
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix="memory-", suffix=".tmp", delete=False,
            ) as handle:
                temporary = Path(handle.name)
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except (OSError, TypeError, ValueError) as exc:
            raise MemoryStoreError(f"Cannot save local memory: {exc}") from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def save_profile(self, profile: Dict[str, Any]) -> None:
        if not isinstance(profile, dict) or set(profile) - PROFILE_FIELDS:
            raise ValueError("Unknown profile field.")
        for key in ("max_flight_price_usd", "max_hotel_price_usd_per_night"):
            value = profile.get(key)
            if value is not None and (type(value) is not int or value <= 0):
                raise ValueError(f"{key} must be a positive whole number.")
        for key, allowed in (("cabin_class", {"economy", "premium_economy", "business", "first"}), ("room_type", {"standard", "deluxe", "suite", "family"})):
            if profile.get(key) not in (None, "") and profile[key] not in allowed:
                raise ValueError(f"Invalid {key}.")
        airport = profile.get("home_airport")
        if airport not in (None, "") and (not isinstance(airport, str) or len(airport) != 3 or not airport.isascii() or not airport.isalpha()):
            raise ValueError("Home airport must be a three-letter code.")
        if isinstance(airport, str):
            profile = {**profile, "home_airport": airport.upper()}
        with self._lock:
            data = self.load()
            data["profile"] = {key: val for key, val in profile.items() if val not in (None, "")}
            self._write(data)

    def save_active(self, state: Dict[str, Any]) -> None:
        try:
            snapshot = active_snapshot(state)
        except (TypeError, ValueError) as exc:
            raise MemoryStoreError(f"Cannot serialize planner state: {exc}") from exc
        with self._lock:
            data = self.load()
            data["active"] = snapshot
            self._write(data)

    def clear_active(self) -> None:
        with self._lock:
            data = self.load()
            data["active"] = {}
            self._write(data)

    def archive_plan(self, state: Dict[str, Any], decision: str = "", feedback: str = "") -> Dict[str, Any]:
        params = _travel_params(state.get("travel_params"))
        plan = state.get("multi_city_plan", {})
        if not (params.get("destination") or (isinstance(plan, dict) and plan.get("cities"))):
            raise ValueError("Create a travel route before saving a plan.")
        record = {
            "id": str(uuid4()),
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "travel_params": params,
            "multi_city_plan": plan if isinstance(plan, dict) else {},
            "decision": decision.strip()[:500],
            "feedback": feedback.strip()[:500],
        }
        with self._lock:
            data = self.load()
            data["history"].insert(0, record)
            self._write(data)
        return record

    def clear_all(self) -> None:
        """Explicit user action may remove even a corrupt memory file."""
        with self._lock:
            try:
                self.path.unlink(missing_ok=True)
            except OSError as exc:
                raise MemoryStoreError(f"Cannot clear local memory: {exc}") from exc
