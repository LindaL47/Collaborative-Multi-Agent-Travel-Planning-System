"""Friendly Assistant orchestrator implemented as a LangGraph StateGraph.

The orchestrator is the only user-facing agent. It manages conversation state,
extracts/merges travel parameters, asks clarifying questions, delegates via the
A2A protocol, and formats a single friendly response.
"""

from __future__ import annotations

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from agents.flight_agent.agent import FlightBookingAgent
from agents.flight_agent.schemas import CabinClass, FlightSearchParameters, FlightTaskRequest, FlightTaskResponse
from agents.hotel_agent.agent import HotelBookingAgent
from agents.hotel_agent.schemas import HotelSearchParameters, HotelTaskRequest, HotelTaskResponse, RoomType
from orchestrator.prompts import GENERAL_TRAVEL_SYSTEM_PROMPT, INTENT_EXTRACTION_SYSTEM_PROMPT


Route = Literal["respond", "general", "flight", "hotel", "both", "multi_city"]


CITY_ALIASES: Dict[str, Dict[str, str]] = {
    "singapore": {"code": "SIN", "city": "Singapore"},
    "sin": {"code": "SIN", "city": "Singapore"},
    "tokyo": {"code": "TYO", "city": "Tokyo"},
    "tyo": {"code": "TYO", "city": "Tokyo"},
    "dubai": {"code": "DXB", "city": "Dubai"},
    "dxb": {"code": "DXB", "city": "Dubai"},
    "london": {"code": "LON", "city": "London"},
    "lon": {"code": "LON", "city": "London"},
    "paris": {"code": "PAR", "city": "Paris"},
    "par": {"code": "PAR", "city": "Paris"},
    "sydney": {"code": "SYD", "city": "Sydney"},
    "syd": {"code": "SYD", "city": "Sydney"},
    "bangkok": {"code": "BKK", "city": "Bangkok"},
    "bkk": {"code": "BKK", "city": "Bangkok"},
    "hong kong": {"code": "HKG", "city": "Hong Kong"},
    "hkg": {"code": "HKG", "city": "Hong Kong"},
    "seoul": {"code": "SEL", "city": "Seoul"},
    "sel": {"code": "SEL", "city": "Seoul"},
    "kuala lumpur": {"code": "KUL", "city": "Kuala Lumpur"},
    "kul": {"code": "KUL", "city": "Kuala Lumpur"},
    "bengaluru": {"code": "BLR", "city": "Bengaluru"},
    "bangalore": {"code": "BLR", "city": "Bengaluru"},
    "blr": {"code": "BLR", "city": "Bengaluru"},
    "delhi": {"code": "DEL", "city": "Delhi"},
    "new delhi": {"code": "DEL", "city": "Delhi"},
    "del": {"code": "DEL", "city": "Delhi"},
    "mumbai": {"code": "BOM", "city": "Mumbai"},
    "bombay": {"code": "BOM", "city": "Mumbai"},
    "bom": {"code": "BOM", "city": "Mumbai"},
    "bali": {"code": "DPS", "city": "Bali"},
    "denpasar": {"code": "DPS", "city": "Bali"},
    "dps": {"code": "DPS", "city": "Bali"},
    "zurich": {"code": "ZRH", "city": "Zurich"},
    "zrh": {"code": "ZRH", "city": "Zurich"},
    "rome": {"code": "ROM", "city": "Rome"},
    "rom": {"code": "ROM", "city": "Rome"},
    "barcelona": {"code": "BCN", "city": "Barcelona"},
    "bcn": {"code": "BCN", "city": "Barcelona"},
    "san francisco": {"code": "SFO", "city": "San Francisco"},
    "sfo": {"code": "SFO", "city": "San Francisco"},
    "toronto": {"code": "YYZ", "city": "Toronto"},
    "yyz": {"code": "YYZ", "city": "Toronto"},
    "new york": {"code": "NYC", "city": "New York"},
    "nyc": {"code": "NYC", "city": "New York"},
    "reykjavik": {"code": "KEF", "city": "Reykjavik"},
    "mexico city": {"code": "MEX", "city": "Mexico City"},
    "chennai": {"code": "MAA", "city": "Chennai"},
    "madras": {"code": "MAA", "city": "Chennai"},
    "maa": {"code": "MAA", "city": "Chennai"},
    "guwahati": {"code": "GAU", "city": "Guwahati"},
    "gau": {"code": "GAU", "city": "Guwahati"},
}
MOCK_AVAILABLE_CITY_CODES = {
    "SIN", "TYO", "PAR", "DXB", "LON", "SYD", "BKK", "HKG", "SEL", "KUL",
    "BLR", "DEL", "BOM", "DPS", "ZRH", "ROM", "BCN", "SFO", "YYZ", "NYC", "MEX",
}
MOCK_DIRECT_UNAVAILABLE_CITY_CODES = {"MAA", "GAU"}
MOCK_CITY_SUGGESTIONS = "Singapore, Tokyo, Paris, Bengaluru, Delhi, Mumbai, Dubai, London, Sydney, Bangkok"
LOCATION_CAPTURE_STOP_WORDS = {
    "to", "from", "on", "for", "starting", "returning", "return", "back", "with",
    "and", "then", "give", "need", "want", "please", "check", "stay", "staying",
    "after", "before", "by", "arriving", "arrival", "leaving", "departure",
    "flight", "flights", "hotel", "hotels", "both", "economy", "business", "first",
    "class", "near", "around", "about", "during", "until", "till", "visit", "visiting",
    "travel", "travelling", "traveling", "go", "going", "fly", "flying", "book",
    "booking", "plan", "planning", "change", "update", "replace", "show", "search",
    "add", "the", "a", "an", "my", "your", "our", "this", "that", "each",
    "multiple", "through", "last", "date", "dates", "journey", "place", "places",
    "cities", "cites",
}
NON_LOCATION_TERMS = {
    "travel", "trip", "plan", "planning", "book", "booking", "fly", "flying", "go",
    "going", "help", "search", "show", "add", "change", "update", "replace", "me",
    "us", "you", "there", "here", "it", "them", "home", "origin", "destination",
    "somewhere", "something", "details", "information", "hello", "hi", "hey",
    "thanks", "thank", "okay", "ok", "yes", "no", "can", "assist", "night",
    "nights", "traveller", "travellers", "traveler", "travelers", "guest", "guests",
    "the", "a", "an", "my", "your", "our", "this", "that", "date", "dates",
    "journey", "place", "places", "each", "multiple", "through", "last", "city",
    "cities", "cites",
}
KNOWN_AREA_PREFERENCES = {
    "shinjuku", "ginza", "asakusa", "marina bay", "orchard", "downtown",
    "city centre", "city center", "mg road", "whitefield", "indiranagar",
    "connaught place", "bandra", "semiyak", "klcc", "westminster", "shoreditch",
}
COUNTRY_ALIASES: Dict[str, str] = {
    "japan": "Japan",
    "france": "France",
    "india": "India",
    "united states": "United States",
    "usa": "United States",
    "uk": "United Kingdom",
    "uae": "United Arab Emirates",
}


def _known_city_pattern() -> str:
    """Regex alternation of known city aliases, longest first for stable parsing."""
    aliases = sorted((re.escape(alias) for alias in CITY_ALIASES), key=len, reverse=True)
    return r"(?:" + "|".join(aliases) + r")"


def _normalize_city_fragment(fragment: str) -> Optional[str]:
    """Return a known IATA code from a free-text city fragment."""
    cleaned = re.sub(r"[^a-z\s]", " ", fragment.lower()).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if cleaned in CITY_ALIASES:
        return CITY_ALIASES[cleaned]["code"]
    # Prefer exact alias occurrence, longest first, so "new york" wins over "york" if added later.
    for alias, value in sorted(CITY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", cleaned):
            return value["code"]
    return None

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

OUT_OF_SCOPE_MESSAGE = (
    "I am focused on travel planning, mock flights, hotels, itineraries, and travel advice. "
    "I do not have reliable knowledge for that topic, so I should not answer it here. "
    "Share a destination, route, or travel date and I can help with the trip."
)


class OrchestratorState(TypedDict, total=False):
    """State carried through the Friendly Assistant StateGraph."""

    session_id: str
    current_message: str
    conversation_history: List[Dict[str, str]]
    extracted: Dict[str, Any]
    travel_params: Dict[str, Any]
    user_intent: str
    pending_clarifications: List[str]
    active_task_ids: List[str]
    last_task_ids: List[str]
    a2a_messages: List[Dict[str, Any]]
    flight_response: Optional[FlightTaskResponse]
    hotel_response: Optional[HotelTaskResponse]
    final_aggregated_options: Dict[str, Any]
    hotel_dates_inferred: bool
    destination_changed: bool
    constraints_changed: bool
    message_to_show_user: str
    route: Route
    should_delegate_flight: bool
    should_delegate_hotel: bool
    awaiting_hotel_offer: bool
    general_question: bool
    last_completed_params: Dict[str, Any]
    conversation_focus: str
    debug_trace: List[str]
    multi_city_plan: Dict[str, Any]
    last_successful_multi_city_plan: Dict[str, Any]
    planner_snapshot: Dict[str, Any]
    planner_revision: int
    planner_confidence: float
    planner_decision: str
    llm_diagnostics: Dict[str, Any]


@dataclass(frozen=True)
class ExtractedIntent:
    """Normalized extraction object returned by the local or optional LLM parser."""

    intent: str
    entities: Dict[str, Any]
    general_question: bool = False
    destination_changed: bool = False
    raw_text: str = ""


class OptionalOllamaClient:
    """Small Ollama adapter used for local Llama semantic extraction.

    The previous implementation only made it obvious when the LLM succeeded.
    This version records availability/errors so the UI can show whether Ollama
    was actually contacted, fell back, or was disabled by configuration.
    """

    def __init__(self) -> None:
        self.model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.last_error: Optional[str] = None

    def is_available(self, timeout_seconds: int = 2) -> bool:
        request = Request(url=f"{self.base_url.rstrip('/')}/api/tags", method="GET")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # nosec: local optional dev endpoint
                response.read()
            self.last_error = None
            return True
        except (URLError, TimeoutError, OSError) as exc:
            self.last_error = str(exc)
            return False

    def generate(self, system_prompt: str, user_prompt: str, timeout_seconds: int = 20) -> Optional[str]:
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\nUser/context: {user_prompt}\nAssistant:",
            "stream": False,
            "options": {"temperature": 0.1},
        }
        request = Request(
            url=f"{self.base_url.rstrip('/')}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # nosec: local optional dev endpoint
                body = json.loads(response.read().decode("utf-8"))
                self.last_error = None
                return str(body.get("response", "")).strip() or None
        except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            self.last_error = str(exc)
            return None

    def generate_json(self, system_prompt: str, user_prompt: str, timeout_seconds: int = 25) -> Optional[Dict[str, Any]]:
        """Call Ollama using structured JSON mode and return a parsed object.

        v11 used free-form text generation and then tried to scrape a JSON
        object out of the answer. That made the LLM advisory layer fragile: the
        model could add prose, produce partial JSON, or miss important fields.
        v12 uses Ollama's structured-output `format` parameter so the model is
        constrained to emit a JSON object that matches the planner schema.
        """
        schema: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "intent": {"type": ["string", "null"]},
                "origin": {"type": ["string", "null"]},
                "destination": {"type": ["string", "null"]},
                "departure_date": {"type": ["string", "null"]},
                "return_date": {"type": ["string", "null"]},
                "start_date": {"type": ["string", "null"]},
                "return_destination": {"type": ["string", "null"]},
                "passengers": {"type": ["integer", "null"]},
                "cabin_class": {"type": ["string", "null"]},
                "needs_flight": {"type": ["boolean", "null"]},
                "needs_hotel": {"type": ["boolean", "null"]},
                "guests": {"type": ["integer", "null"]},
                "room_type": {"type": ["string", "null"]},
                "location_preference": {"type": ["string", "null"]},
                "check_in_date": {"type": ["string", "null"]},
                "check_out_date": {"type": ["string", "null"]},
                "general_question": {"type": ["boolean", "null"]},
                "destination_changed": {"type": ["boolean", "null"]},
                "cancel_hotel": {"type": ["boolean", "null"]},
                "stay_duration_days": {"type": ["integer", "null"]},
                "route_cities": {
                    "type": ["array", "null"],
                    "items": {"type": "string"}
                },
                "planner_action": {"type": ["string", "null"]},
                "scope": {"type": ["string", "null"]},
                "clarification_question": {"type": ["string", "null"]},
                "answer_topic": {"type": ["string", "null"]},
                "multi_city_segments": {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "properties": {
                            "origin": {"type": ["string", "null"]},
                            "destination": {"type": ["string", "null"]},
                            "departure_date": {"type": ["string", "null"]},
                            "hotel_destination": {"type": ["string", "null"]},
                            "hotel_check_in": {"type": ["string", "null"]},
                            "hotel_check_out": {"type": ["string", "null"]},
                        },
                    },
                },
            },
        }
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\nJSON_SCHEMA: {json.dumps(schema)}\n\nUser/context: {user_prompt}\nAssistant:",
            "stream": False,
            "format": schema,
            "options": {"temperature": 0.0},
        }
        request = Request(
            url=f"{self.base_url.rstrip('/')}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # nosec: local optional dev endpoint
                body = json.loads(response.read().decode("utf-8"))
            raw = str(body.get("response", "")).strip()
            parsed = json.loads(raw)
            self.last_error = None
            return parsed if isinstance(parsed, dict) else None
        except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            self.last_error = f"Ollama structured JSON call failed: {exc}"
            return None

class TravelNLU:
    """Hybrid NLU layer: deterministic extraction with optional local LLM support."""

    def __init__(self) -> None:
        configured = os.getenv("FRIENDLY_ASSISTANT_LLM_PROVIDER", "auto").strip().lower()
        if os.getenv("FRIENDLY_ASSISTANT_DISABLE_LLM", "false").strip().lower() in {"1", "true", "yes"}:
            configured = "heuristic"
        self.configured_provider = configured
        self.provider = configured
        self.ollama: Optional[OptionalOllamaClient] = None
        self.ollama_available = False
        if configured in {"ollama", "auto"}:
            client = OptionalOllamaClient()
            self.ollama_available = client.is_available()
            if self.ollama_available:
                self.ollama = client
                self.provider = "ollama"
            elif configured == "auto":
                self.provider = "heuristic"
            else:
                self.provider = "ollama_unavailable"

    def extract(self, message: str, state: OrchestratorState) -> ExtractedIntent:
        """Extract intent and entities from a user utterance.

        The orchestrator always performs deterministic extraction first. When
        Ollama is enabled and healthy, the LLM is called as a semantic planner
        that proposes structured JSON. The deterministic planner validates and
        normalizes the LLM output before any A2A task is created.
        """
        heuristic = self._heuristic_extract(message=message, state=state)
        if heuristic.intent == "out_of_scope":
            heuristic.entities.setdefault("_llm_used", False)
            heuristic.entities.setdefault("_llm_called", False)
            heuristic.entities.setdefault("_llm_provider", self.provider)
            return heuristic
        if not self.ollama:
            heuristic.entities.setdefault("_llm_used", False)
            heuristic.entities.setdefault("_llm_called", False)
            heuristic.entities.setdefault("_llm_provider", self.provider)
            if self.provider == "ollama_unavailable":
                heuristic.entities.setdefault("_llm_error", "Ollama is configured but http://localhost:11434 is not reachable")
            return heuristic

        started = time.perf_counter()
        llm_payload = self._llm_extract(message=message, state=state)
        latency_ms = int((time.perf_counter() - started) * 1000)
        if not llm_payload:
            heuristic.entities.update({
                "_llm_used": False,
                "_llm_called": True,
                "_llm_provider": "ollama_fallback",
                "_llm_latency_ms": latency_ms,
                "_llm_error": self.ollama.last_error or "Ollama returned no usable JSON",
            })
            return heuristic

        merged = self._merge_llm_entities(heuristic=heuristic, llm_payload=llm_payload, state=state)
        merged.entities.update({"_llm_used": True, "_llm_called": True, "_llm_provider": "ollama", "_llm_latency_ms": latency_ms})
        return merged

    def _llm_extract(self, message: str, state: OrchestratorState) -> Optional[Dict[str, Any]]:
        """Ask local Llama/Ollama for semantic extraction JSON.

        The prompt includes the current travel frame so the model can interpret
        repairs like "same as earlier" or "only flights" without guessing.
        """
        if not self.ollama:
            return None
        prior = {k: v for k, v in state.get("travel_params", {}).items() if v is not None}
        pending = state.get("pending_clarifications", [])
        active_plan = state.get("multi_city_plan", {}) if isinstance(state.get("multi_city_plan"), dict) else {}
        recent_history = state.get("conversation_history", [])[-8:]
        system = INTENT_EXTRACTION_SYSTEM_PROMPT + """

You are the PRIMARY TRAVEL PLANNER for a multi-agent travel assistant.
Return JSON only. Do not use markdown. Use these exact keys when applicable:
intent, origin, destination, departure_date, return_date, return_destination,
passengers, cabin_class, needs_flight, needs_hotel, guests, room_type,
location_preference, check_in_date, check_out_date, general_question,
destination_changed, cancel_hotel, start_date, stay_duration_days, route_cities,
multi_city_segments, planner_action, scope, clarification_question, answer_topic.

Planning contract:
- Read CURRENT_TRAVEL_FRAME, CURRENT_MULTI_CITY_PLAN, RECENT_CONVERSATION and USER_MESSAGE together.
- For a new trip, return the complete canonical plan.
- For an edit, return the complete UPDATED canonical plan, not just the changed field.
- For multi-city trips, prefer route_cities + start_date + stay_duration_days when possible, and ALSO return multi_city_segments when you can compute exact legs/stays.
- multi_city_segments must be ordered objects with origin, destination, departure_date, hotel_destination, hotel_check_in, hotel_check_out.
- If user says "replace Paris with BLR", update every affected leg and stay in the active plan.
- If user says "change date for BLR to SIN from 2026-08-04 to 2026-08-08", update that leg departure date and the previous hotel stay checkout.
- If user says "give flight details", set scope="flights_only" and keep the current route/date memory.
- If user says "give hotel details", set scope="hotels_only" and keep the current route/date memory.
- If user asks a general question about the current itinerary, set general_question true and answer_topic to the requested topic.
- Never invent a date. If no start date/date points are available, leave missing values null and provide clarification_question.
"""
        prompt = json.dumps(
            {
                "CURRENT_TRAVEL_FRAME": prior,
                "CURRENT_MULTI_CITY_PLAN": active_plan,
                "PENDING_CLARIFICATIONS": pending,
                "RECENT_CONVERSATION": recent_history,
                "USER_MESSAGE": message,
            },
            ensure_ascii=False,
        )
        return self.ollama.generate_json(system, prompt)

    def _merge_llm_entities(self, heuristic: ExtractedIntent, llm_payload: Dict[str, Any], state: Optional[OrchestratorState] = None) -> ExtractedIntent:
        """Merge LLM extraction with deterministic extraction under guardrails.

        The local LLM is used as a semantic advisor, not as the source of truth.
        This prevents an unpredictable model response from breaking tested graph
        routing, swapping origin/destination, or classifying a bare destination
        like "Tokyo" as a general question. Deterministic extraction wins for
        fields it already understood; the LLM fills gaps and contributes complex
        multi-city plans when the heuristic did not already produce one.
        """
        if heuristic.intent == "out_of_scope":
            return heuristic

        entities = dict(heuristic.entities)
        if entities.get("_force_hotel_followup"):
            return ExtractedIntent(
                intent=heuristic.intent,
                entities=entities,
                general_question=heuristic.general_question,
                destination_changed=heuristic.destination_changed,
                raw_text=heuristic.raw_text,
            )

        # LLM-assisted TravelPlan: deterministic current-turn evidence wins.
        # Ollama may fill gaps, but it cannot replace a complete executable
        # plan that was extracted from the latest user message.
        existing_plan = (state or {}).get("multi_city_plan", {}) if isinstance((state or {}).get("multi_city_plan"), dict) else {}
        user_text = heuristic.raw_text.lower()
        explicit_scope_words = bool(
            re.search(
                r"\b(only flights?|flight[s]? only|only hotels?|hotel[s]? only|both|package|flight[s]? and hotel[s]?|hotel[s]? and flight[s]?|book|search|give.*details)\b",
                user_text,
            )
        )
        allow_llm_scope = explicit_scope_words or heuristic.intent in {"multi_city_package"}
        scope_value = str(llm_payload.get("scope") or "").strip().lower()
        if allow_llm_scope and scope_value in {"flights_only", "flight_only", "only_flights"}:
            entities["_multi_city_scope"] = "flights_only"
            entities["needs_flight"] = True
            entities["needs_hotel"] = False
            entities["_explicit_needs_flight"] = True
        elif allow_llm_scope and scope_value in {"hotels_only", "hotel_only", "only_hotels"}:
            entities["_multi_city_scope"] = "hotels_only"
            entities["needs_flight"] = False
            entities["needs_hotel"] = True
            entities["_explicit_needs_hotel"] = True
        elif allow_llm_scope and scope_value in {"both", "package", "flights_and_hotels"}:
            entities["_multi_city_scope"] = "both"
            entities["needs_flight"] = True
            entities["needs_hotel"] = True
            entities["_explicit_needs_flight"] = True
            entities["_explicit_needs_hotel"] = True

        def llm_segments_to_plan(segments: Any) -> Optional[Dict[str, Any]]:
            if not isinstance(segments, list):
                return None
            legs: List[Dict[str, Any]] = []
            stays: List[Dict[str, Any]] = []
            cities: List[str] = []
            date_points: List[str] = []
            for segment in segments:
                if not isinstance(segment, dict):
                    continue
                origin = self._city_code(str(segment.get("origin", "")))
                destination = self._city_code(str(segment.get("destination", "")))
                departure = str(segment.get("departure_date") or "")
                if origin and destination and re.fullmatch(r"20\d{2}-\d{2}-\d{2}", departure):
                    legs.append({"origin": origin, "destination": destination, "departure_date": departure})
                    if not cities:
                        cities.append(origin)
                    cities.append(destination)
                    date_points.append(departure)
                hotel_destination = self._city_code(str(segment.get("hotel_destination") or ""))
                check_in = str(segment.get("hotel_check_in") or "")
                check_out = str(segment.get("hotel_check_out") or "")
                if hotel_destination and re.fullmatch(r"20\d{2}-\d{2}-\d{2}", check_in) and re.fullmatch(r"20\d{2}-\d{2}-\d{2}", check_out):
                    stays.append({"destination": hotel_destination, "check_in_date": check_in, "check_out_date": check_out})
            if not legs:
                return None
            if len(date_points) < len(cities):
                last_checkout = None
                for stay in reversed(stays):
                    if stay.get("destination") == cities[-2] and stay.get("check_out_date"):
                        last_checkout = stay["check_out_date"]
                        break
                if last_checkout:
                    date_points.append(last_checkout)
            plan = {"cities": cities, "date_points": date_points, "legs": legs, "stays": stays}
            if entities.get("_multi_city_scope"):
                plan["scope"] = entities["_multi_city_scope"]
            return plan

        llm_plan = llm_segments_to_plan(llm_payload.get("multi_city_segments"))
        heuristic_plan = entities.get("multi_city_plan") if isinstance(entities.get("multi_city_plan"), dict) else {}
        heuristic_leg_count = len((heuristic_plan or {}).get("legs", []))
        llm_leg_count = len((llm_plan or {}).get("legs", [])) if llm_plan else 0
        heuristic_has_complete_plan = bool(heuristic_leg_count >= 2 and not (heuristic_plan or {}).get("missing"))
        llm_is_richer_than_heuristic = bool(
            llm_plan
            and not heuristic_has_complete_plan
            and llm_leg_count >= 2
            and (
                not heuristic_leg_count
                or llm_leg_count >= heuristic_leg_count
            )
        )
        semantic_edit_or_new_plan = bool(
            llm_plan
            and llm_is_richer_than_heuristic
            and (
                not entities.get("multi_city_plan")
                or llm_leg_count >= heuristic_leg_count
                or re.search(r"\b(change|replace|instead|directly|remove|dont want|don't want|give flight|flight details|hotel details|new plan|start over)\b", user_text)
                or existing_plan
            )
        )
        if semantic_edit_or_new_plan:
            entities["multi_city_plan"] = llm_plan
            if entities.get("_multi_city_scope") == "flights_only":
                entities["needs_flight"] = True
                entities["needs_hotel"] = False
            elif entities.get("_multi_city_scope") == "hotels_only":
                entities["needs_flight"] = False
                entities["needs_hotel"] = True
            else:
                entities["needs_flight"] = True
                entities["needs_hotel"] = True
                entities["_explicit_needs_hotel"] = True
            entities["_explicit_needs_flight"] = True

        if not entities.get("multi_city_plan") and isinstance(llm_payload.get("route_cities"), list):
            route_cities = [self._city_code(str(city)) for city in (llm_payload.get("route_cities") or [])]
            route_cities = [city for city in route_cities if city]
            start_value = str(llm_payload.get("start_date") or llm_payload.get("departure_date") or "")
            duration_value = llm_payload.get("stay_duration_days")
            try:
                start_dt = date.fromisoformat(start_value) if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", start_value) else None
                duration_days = int(duration_value) if duration_value not in (None, "", []) else None
            except (TypeError, ValueError):
                start_dt = None
                duration_days = None
            if len(route_cities) >= 3 and start_dt and duration_days:
                date_points = [start_dt + timedelta(days=duration_days * idx) for idx in range(len(route_cities))]
                plan = self._build_multi_city_plan_from_cities(cities=route_cities, date_points=date_points)
                if entities.get("_multi_city_scope"):
                    plan["scope"] = entities["_multi_city_scope"]
                entities["multi_city_plan"] = plan
                entities["needs_flight"] = entities.get("_multi_city_scope") != "hotels_only"
                entities["needs_hotel"] = entities.get("_multi_city_scope") != "flights_only"
                entities["_explicit_needs_flight"] = entities["needs_flight"]
                entities["_explicit_needs_hotel"] = entities["needs_hotel"]

        prior_params = (state or {}).get("travel_params", {}) if isinstance((state or {}).get("travel_params"), dict) else {}
        has_executable_flight = bool(entities.get("needs_flight") and entities.get("origin") and entities.get("destination") and entities.get("departure_date"))
        has_contextual_flight = bool(
            prior_params.get("needs_flight")
            and (entities.get("origin") or prior_params.get("origin"))
            and (entities.get("destination") or prior_params.get("destination"))
            and (entities.get("departure_date") or prior_params.get("departure_date"))
            and (entities.get("passengers") or prior_params.get("passengers"))
        )
        has_executable_hotel = bool(entities.get("needs_hotel") and entities.get("destination") and entities.get("check_in_date") and entities.get("check_out_date"))
        has_complete_current_task = bool(
            ((entities.get("needs_flight") or entities.get("needs_hotel")) and (not entities.get("needs_flight") or has_executable_flight)
            and (not entities.get("needs_hotel") or has_executable_hotel)
            )
            or has_contextual_flight
        )
        if (
            not entities.get("_planner_message")
            and not entities.get("_force_hotel_followup")
            and llm_payload.get("clarification_question")
            and not has_complete_current_task
        ):
            q = str(llm_payload.get("clarification_question") or "").strip()
            if q and not entities.get("multi_city_plan"):
                entities["_planner_message"] = q

        # Only fill missing scalar fields from the LLM. Do not allow the LLM to
        # overwrite explicit regex matches like "from Singapore to Tokyo".
        city_fields = {"origin", "destination", "return_destination", "hotel_city"}
        date_fields = {"departure_date", "return_date", "check_in_date", "check_out_date"}
        numeric_fields = {"passengers", "guests"}
        other_fields = {"cabin_class", "room_type", "location_preference"}

        for key in city_fields:
            if key not in entities and llm_payload.get(key) not in (None, "", []):
                code = self._city_code(str(llm_payload[key]))
                if code:
                    entities[key] = code
        for key in date_fields:
            if key not in entities and llm_payload.get(key) not in (None, "", []):
                value = str(llm_payload[key])
                if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", value):
                    if not re.search(r"\b20\d{2}\b", user_text):
                        try:
                            if date.fromisoformat(value) < date.today():
                                continue
                        except ValueError:
                            continue
                    entities[key] = value
        for key in numeric_fields:
            if key not in entities and llm_payload.get(key) not in (None, "", []):
                try:
                    entities[key] = int(llm_payload[key])
                except (TypeError, ValueError):
                    pass
        for key in other_fields:
            if key not in entities and llm_payload.get(key) not in (None, "", []):
                entities[key] = llm_payload[key]

        # Scope changes are accepted only when the user explicitly requested a
        # booking/search scope or the heuristic already detected a booking-ish intent.
        bookingish = heuristic.intent in {"flight_search", "hotel_search", "package_search", "change_dates", "multi_city_package"}
        if llm_payload.get("cancel_hotel") is True or entities.get("_cancel_hotel"):
            entities.update({"needs_flight": True, "needs_hotel": False, "_cancel_hotel": True, "_explicit_needs_flight": True})
        elif bookingish or explicit_scope_words:
            if llm_payload.get("needs_flight") is True and "needs_flight" not in entities:
                entities["needs_flight"] = True
                entities["_explicit_needs_flight"] = True
            allow_llm_hotel = explicit_scope_words or heuristic.intent in {"hotel_search", "package_search", "multi_city_package"}
            if llm_payload.get("needs_hotel") is True and "needs_hotel" not in entities and allow_llm_hotel:
                entities["needs_hotel"] = True
                entities["_explicit_needs_hotel"] = True
            if llm_payload.get("needs_hotel") is False and explicit_scope_words and "needs_hotel" not in entities:
                entities["needs_hotel"] = False

        # Never let the LLM turn a bare destination or ambiguous planning ask
        # into a general advice answer. It may only confirm general_question if
        # deterministic logic already classified it as general.
        intent = heuristic.intent
        general_question = heuristic.general_question
        if heuristic.general_question and llm_payload.get("general_question") is True:
            intent = "general_question"
            general_question = True
        elif entities.get("multi_city_plan"):
            intent = "multi_city_package"
        elif entities.get("needs_flight") and entities.get("needs_hotel"):
            intent = "package_search"
        elif entities.get("needs_flight") and not entities.get("needs_hotel"):
            intent = "flight_search"
        elif entities.get("needs_hotel") and not entities.get("needs_flight"):
            intent = "hotel_search"

        return ExtractedIntent(
            intent=intent,
            entities=entities,
            general_question=general_question,
            destination_changed=heuristic.destination_changed or bool(llm_payload.get("destination_changed")),
            raw_text=heuristic.raw_text,
        )

    def answer_general_question(self, message: str, state: Optional[OrchestratorState] = None) -> str:
        """Answer a general travel question directly without sub-agent delegation.

        The prompt includes recent conversation context so follow-ups like
        "what places can I visit there?" resolve "there" to the latest city.
        """
        context_city = self._context_city_for_general_answer(message, state or {})
        itinerary_answer = self._answer_itinerary_comparison(message, state or {})
        if itinerary_answer:
            return itinerary_answer
        deterministic = self._deterministic_general_answer(message, context_city=context_city)

        # Known travel-advice cases are intentionally deterministic so the demo
        # remains factual, short, and testable. The LLM is still called during
        # extraction when enabled, which is visible in diagnostics.
        lower = message.lower()
        known_case = any(marker in lower for marker in [
            "mock data", "available data", "places", "attractions", "reputed", "higly", "highly",
            "good time", "best time", "june", "july", "singapore", "tokyo", "japan", "paris"
        ])
        if known_case:
            return deterministic

        if self.ollama:
            prompt = json.dumps(
                {
                    "latest_user_message": message,
                    "context_city": context_city,
                    "recent_conversation": (state or {}).get("conversation_history", [])[-6:],
                    "instruction": "Answer the user directly. If they use pronouns like there, resolve them from context_city.",
                },
                ensure_ascii=False,
            )
            answer = self.ollama.generate(GENERAL_TRAVEL_SYSTEM_PROMPT, prompt)
            if answer:
                return answer
        return deterministic

    def _heuristic_extract(self, message: str, state: OrchestratorState) -> ExtractedIntent:
        text = message.strip()
        lower = text.lower()
        # Normalize common chat typos such as "5i want both" so the
        # extractor behaves more like a human travel agent in multi-turn flows.
        lower = re.sub(r"(?<=\d)(?=[a-z])", " ", lower)
        lower = re.sub(r"(?<=[a-z])(?=\d)", " ", lower)
        lower = re.sub(r"\b(\d{1,2})\s+(st|nd|rd|th)\b", r"\1\2", lower)
        entities: Dict[str, Any] = {}

        if self._is_out_of_scope_request(lower):
            return ExtractedIntent(intent="out_of_scope", entities=entities, raw_text=text)
        if re.search(r"\b(new plan|new trip|planning a new trip|plan a new trip|start over|fresh trip|fresh plan)\b", lower):
            entities["_fresh_plan"] = True
        unsupported_locations = self._extract_explicit_unsupported_locations(text)
        if unsupported_locations:
            entities["_unsupported_locations"] = unsupported_locations
            return ExtractedIntent(intent="unsupported_location", entities=entities, raw_text=text)

        # Function-toolbelt planner repairs run before normal slot filling.
        # These are deliberately small functions: one detects unsafe city replacement,
        # one handles duration-only itinerary edits, one handles explicit dated legs,
        # and the normal extractor handles fresh route chains/lists.
        # Planner kernel operations run before slot filling. These are not
        # prompt-specific fixes; they are typed edit/search operations that
        # transform messy natural language into a canonical TravelPlan before
        # any A2A agent receives a task.
        replacement_clarification = self._extract_replacement_clarification(lower, state)
        if replacement_clarification:
            return ExtractedIntent(intent="planner_clarification", entities={"_planner_message": replacement_clarification}, raw_text=text)

        active_multi_city_plan = state.get("multi_city_plan", {}) if isinstance(state.get("multi_city_plan"), dict) else {}
        has_new_route_language = bool(re.search(r"\b(from|frm|to|through|cities?|cites|route|itinerary|starting from|book|plan|travel(?:ling)? through)\b", lower))
        asks_both = bool(re.search(r"\b(flights?\s+and\s+hotels?|hotels?\s+and\s+flights?|both|package)\b", lower))
        short_scope_followup = len(lower.split()) <= 8 or bool(re.search(r"\b(what about|show only|only|just)\b", lower))
        if active_multi_city_plan.get("legs") and short_scope_followup and not has_new_route_language and not asks_both and "hotel" not in lower and re.search(r"\bflights?\b|\bflights?\s+details\b", lower):
            plan = dict(active_multi_city_plan)
            plan["scope"] = "flights_only"
            return ExtractedIntent(intent="multi_city_package", entities={"multi_city_plan": plan, "needs_flight": True, "needs_hotel": False, "_explicit_needs_flight": True, "_multi_city_scope": "flights_only"}, raw_text=text)
        if active_multi_city_plan.get("stays") and short_scope_followup and not has_new_route_language and not asks_both and "flight" not in lower and re.search(r"\bhotels?\b|\bhotels?\s+details\b", lower):
            plan = dict(active_multi_city_plan)
            plan["scope"] = "hotels_only"
            return ExtractedIntent(intent="multi_city_package", entities={"multi_city_plan": plan, "needs_flight": False, "needs_hotel": True, "_explicit_needs_hotel": True, "_multi_city_scope": "hotels_only"}, raw_text=text)

        multi_city_plan = self._extract_leg_date_update_plan(lower, state)
        if not multi_city_plan:
            multi_city_plan = self._extract_itinerary_edit_plan(lower, state)
        if not multi_city_plan:
            multi_city_plan = self._extract_multi_city_duration_update(lower, state)
        if not multi_city_plan:
            multi_city_plan = self._extract_explicit_leg_dates_plan(lower)
        if not multi_city_plan:
            multi_city_plan = self._extract_multi_city_plan(lower, state=state)
        pending_multi_city_plan = state.get("multi_city_plan", {}) if isinstance(state.get("multi_city_plan"), dict) else {}
        if not multi_city_plan and ("multi_city_dates" in state.get("pending_clarifications", []) or pending_multi_city_plan.get("missing")):
            multi_city_plan = self._complete_pending_multi_city_plan(lower, pending_multi_city_plan)
        if multi_city_plan:
            entities["multi_city_plan"] = multi_city_plan
            scope = str((multi_city_plan or {}).get("scope") or entities.get("_multi_city_scope") or "both").lower()
            if scope in {"flights_only", "flight_only", "only_flights"}:
                entities["needs_flight"] = True
                entities["needs_hotel"] = False
                entities["_explicit_needs_flight"] = True
                entities["_multi_city_scope"] = "flights_only"
            elif scope in {"hotels_only", "hotel_only", "only_hotels"}:
                entities["needs_flight"] = False
                entities["needs_hotel"] = True
                entities["_explicit_needs_hotel"] = True
                entities["_multi_city_scope"] = "hotels_only"
            else:
                entities["needs_flight"] = True
                entities["needs_hotel"] = True
                entities["_explicit_needs_flight"] = True
                entities["_explicit_needs_hotel"] = True

        # Conversational repair for general advice: if the assistant answered
        # June but the user says "I said July", answer the corrected travel
        # question instead of falling back to booking clarification.
        month_repair = re.search(r"\b(?:i\s+said|no[, ]*i\s+said)\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b", lower)
        if month_repair:
            last_destination = None
            for turn in reversed(state.get("conversation_history", [])):
                content = turn.get("content", "").lower()
                for alias, value in sorted(CITY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
                    if re.search(rf"\b{re.escape(alias)}\b", content):
                        last_destination = value["city"]
                        break
                if last_destination:
                    break
            if last_destination:
                month_name = month_repair.group(1)
                entities["_general_question_override"] = f"Is {month_name} a good time to visit {last_destination}?"
                return ExtractedIntent(intent="general_question", entities=entities, general_question=True, raw_text=text)

        bare_destination_only = self._is_bare_destination_only(lower)
        if bare_destination_only:
            entities["_bare_destination_only"] = True

        # Natural modification intent. A user may say "change the return date
        # to 2026-07-28" in one turn. Do not short-circuit before entity
        # extraction; first observe all new facts, then the policy node decides
        # whether to ask, update, or delegate.
        date_change_requested = bool(
            re.search(r"\b(change|modify|update|shift|move|reschedule)\b.*\b(date|dates|travel date|return date|check[- ]?out|check[- ]?in)\b", lower)
            or re.search(r"\b(date|dates)\b.*\b(change|modify|update)\b", lower)
            or "departure date is same" in lower
        )
        if date_change_requested:
            entities["_change_dates"] = True

        awaiting_hotel_offer = state.get("awaiting_hotel_offer", False)
        force_hotel_followup = False
        if awaiting_hotel_offer and re.match(r"\s*(yes|yeah|yep|sure|please|add hotel|hotel)\b", lower):
            force_hotel_followup = True
        if awaiting_hotel_offer and re.fullmatch(r"\s*(no|nope|not now|no thanks)\s*[.!]?\s*", lower):
            return ExtractedIntent(intent="decline_hotel", entities={"needs_hotel": False}, raw_text=text)

        previous_params = state.get("travel_params", {})
        origin, destination = self._extract_route(lower)
        if not origin and not destination:
            origin, destination = self._extract_city_pair_route(lower)
        if origin:
            entities["origin"] = origin
        if destination:
            entities["destination"] = destination

        origin_only = self._extract_origin_only(lower)
        if origin_only and "origin" not in entities:
            entities["origin"] = origin_only

        back_to_origin = self._extract_back_to_origin(lower)
        if back_to_origin and "origin" not in entities:
            entities["origin"] = back_to_origin

        return_destination = self._extract_return_destination(lower)
        if return_destination:
            entities["return_destination"] = return_destination

        # In travel-agent language, "checkout 2026-07-30 back to Tokyo" means
        # return to the departure city; it should not overwrite an existing
        # destination such as Singapore.
        loose_destination = self._extract_loose_destination(lower, existing_destination=destination)
        if origin_only and loose_destination == origin_only:
            # Example: "tokyo 25 july 2026 frm singapore". The generic city
            # scanner may see Singapore first because it is longer, but the
            # explicit "frm/from" phrase already consumed Singapore as origin.
            # Pick another mentioned city as destination.
            for alias, value in sorted(CITY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
                code = value["code"]
                if code != origin_only and re.search(rf"\b{re.escape(alias)}\b", lower):
                    loose_destination = code
                    break
        if loose_destination and previous_params.get("destination") and re.search(r"\b(back|return|returning)\s+to\b", lower):
            if loose_destination == previous_params.get("origin") or back_to_origin == loose_destination:
                loose_destination = None
        if loose_destination and previous_params.get("destination") and loose_destination == entities.get("origin"):
            loose_destination = None

        # Contextual date-change flow: if the user previously asked to change
        # dates, short replies such as "Singapore, 2026-07-28" should not
        # accidentally replace Tokyo with Singapore. If the city matches the
        # existing origin or destination, keep it in that slot and use the dates.
        waiting_for_date_change = "date_change" in state.get("pending_clarifications", [])
        if waiting_for_date_change and loose_destination:
            previous_params = state.get("travel_params", {})
            if loose_destination == previous_params.get("origin") and "origin" not in entities:
                entities["origin"] = loose_destination
                loose_destination = None
            elif loose_destination == previous_params.get("destination"):
                entities["destination"] = loose_destination
                loose_destination = None
            elif not any(word in lower for word in ["change", "switch", "instead", "actually", "make it", "to "]):
                # Unknown city in a date-change reply is ambiguous; do not
                # overwrite destination without an explicit destination change.
                loose_destination = None

        # Contextual slot filling: if the previous assistant explicitly asked
        # for origin, a short answer like "Singapore" should fill origin, not
        # overwrite destination. This is the key multi-turn behaviour users
        # expect from a conversational assistant.
        waiting_for_origin = "origin" in state.get("pending_clarifications", [])
        if waiting_for_origin and loose_destination and "origin" not in entities:
            is_destination_change = any(word in lower for word in ["change", "switch", "instead", "actually", "make it", "to "])
            if not is_destination_change:
                entities["origin"] = loose_destination
                loose_destination = None

        if loose_destination and "destination" not in entities:
            entities["destination"] = loose_destination

        departure_date, return_date = self._extract_dates(lower)
        labeled_departure, labeled_return, labeled_check_in, labeled_check_out = self._extract_labeled_dates(lower)
        if self._contains_yearless_date(lower):
            entities["_date_year_missing"] = True
        if departure_date and re.search(r"\b(?:around|about|approximately|approx|roughly|near|circa)\b.{0,45}(?:\d{1,2}|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)", lower):
            entities["_date_is_approximate"] = True
        if departure_date and re.search(r"\barriv(?:e|ing|al)\b", lower):
            entities["_arrival_date_requested"] = True

        # Follow-up after an open-jaw response: if we told the user "share
        # Paris hotel dates" and the next turn is just two dates, treat it as
        # a hotel-only search for the onward city, not as a new ambiguous trip.
        if "onward_hotel_dates" in state.get("pending_clarifications", []) and departure_date and return_date:
            onward_city = previous_params.get("return_destination")
            if onward_city:
                entities["destination"] = onward_city
                entities["check_in_date"] = departure_date.isoformat()
                entities["check_out_date"] = return_date.isoformat()
                entities["needs_hotel"] = True
                entities["needs_flight"] = False
                entities["_explicit_needs_hotel"] = True
                entities["_onward_hotel_followup"] = True

        pending_slots = state.get("pending_clarifications", [])
        existing_params = state.get("travel_params", {})
        pending_hotel_dates = "hotel_dates" in pending_slots
        hotel_date_phrase = bool(re.search(r"\b(check\s*in|check-in|check\s*out|check-out|hotel dates?|stay dates?)\b", lower))
        single_date_as_hotel_checkout = (
            pending_hotel_dates
            and departure_date is not None
            and return_date is None
            and bool(existing_params.get("departure_date"))
            and not re.search(r"\b(depart|departure|leave|leaving|fly|flight)\b", lower)
        )

        if date_change_requested:
            # Non-linear correction policy: a date-change turn may provide only
            # the return date, only the departure date, or a complete date pair.
            # Preserve prior trip context unless the user explicitly replaces it.
            if "departure date is same" in lower and existing_params.get("departure_date"):
                entities["departure_date"] = existing_params["departure_date"]
                if existing_params.get("needs_hotel"):
                    entities["check_in_date"] = existing_params["departure_date"]

            if labeled_departure and "departure date is same" not in lower:
                entities["departure_date"] = labeled_departure.isoformat()
                if existing_params.get("needs_hotel"):
                    entities["check_in_date"] = labeled_departure.isoformat()
            if labeled_return:
                entities["return_date"] = labeled_return.isoformat()
                if existing_params.get("needs_hotel"):
                    entities["check_out_date"] = labeled_return.isoformat()
            if labeled_check_in:
                entities["check_in_date"] = labeled_check_in.isoformat()
                if existing_params.get("needs_flight"):
                    entities.setdefault("departure_date", labeled_check_in.isoformat())
            if labeled_check_out:
                entities["check_out_date"] = labeled_check_out.isoformat()
                if existing_params.get("needs_flight"):
                    entities["return_date"] = labeled_check_out.isoformat()

            labelled_any = any([labeled_departure, labeled_return, labeled_check_in, labeled_check_out])
            if not labelled_any and departure_date and return_date:
                entities["departure_date"] = departure_date.isoformat()
                entities["return_date"] = return_date.isoformat()
                if existing_params.get("needs_hotel"):
                    entities["check_in_date"] = departure_date.isoformat()
                    entities["check_out_date"] = return_date.isoformat()
            elif not labelled_any and departure_date:
                if re.search(r"\b(return|returning|return date|check[- ]?out|checkout)\b", lower):
                    entities["return_date"] = departure_date.isoformat()
                    if existing_params.get("needs_hotel"):
                        entities["check_out_date"] = departure_date.isoformat()
                elif re.search(r"\b(depart|departure|leave|leaving|check[- ]?in|checkin)\b", lower):
                    entities["departure_date"] = departure_date.isoformat()
                    if existing_params.get("needs_hotel"):
                        entities["check_in_date"] = departure_date.isoformat()
                else:
                    entities["departure_date"] = departure_date.isoformat()

        elif pending_hotel_dates and departure_date and return_date and (hotel_date_phrase or bool(existing_params.get("needs_hotel"))):
            # A reply like "check in 2026-07-31 check out 2026-08-05" or a
            # shorthand reply after we asked for hotel dates supplies hotel
            # dates. In package mode the second date can also be the flight
            # return date, but accepting a hotel after a one-way flight should
            # not silently convert the trip into a round trip.
            entities["check_in_date"] = departure_date.isoformat()
            entities["check_out_date"] = return_date.isoformat()
            should_align_return = bool(existing_params.get("return_date")) or bool(
                re.search(r"\b(return|returning|round trip|round-trip|back)\b", lower)
            )
            if existing_params.get("needs_flight") and not existing_params.get("_hotel_add_on_after_one_way"):
                should_align_return = True
            if existing_params.get("needs_flight") and should_align_return:
                entities["return_date"] = return_date.isoformat()
        elif single_date_as_hotel_checkout:
            # In a package flow, a single follow-up date after "origin + hotel dates"
            # is naturally both the flight return date and hotel check-out date,
            # even if the user simply says "Singapore, 2026-07-31".
            existing_wants_flight = bool(existing_params.get("needs_flight"))
            existing_wants_hotel = bool(existing_params.get("needs_hotel"))
            if existing_wants_flight and existing_wants_hotel and not existing_params.get("_hotel_add_on_after_one_way"):
                entities["return_date"] = departure_date.isoformat()
            elif re.search(r"\b(return|returning|round trip|round-trip)\b", lower):
                entities["return_date"] = departure_date.isoformat()
            entities["check_in_date"] = existing_params.get("departure_date")
            entities["check_out_date"] = departure_date.isoformat()
        else:
            if departure_date:
                entities["departure_date"] = departure_date.isoformat()
            if return_date:
                entities["return_date"] = return_date.isoformat()

        if not date_change_requested:
            if labeled_departure:
                entities["departure_date"] = labeled_departure.isoformat()
            if labeled_return:
                entities["return_date"] = labeled_return.isoformat()
            if labeled_check_in:
                entities["check_in_date"] = labeled_check_in.isoformat()
            if labeled_check_out:
                entities["check_out_date"] = labeled_check_out.isoformat()

        nights = self._extract_nights(lower)
        if nights and pending_hotel_dates and not departure_date and existing_params.get("check_in_date"):
            try:
                inferred_checkin = date.fromisoformat(str(existing_params["check_in_date"]))
                entities["check_in_date"] = inferred_checkin.isoformat()
                entities["check_out_date"] = (inferred_checkin + timedelta(days=nights)).isoformat()
                entities["stay_duration_days"] = nights
            except (TypeError, ValueError):
                pass
        elif nights and departure_date and not return_date:
            inferred_checkout = departure_date + timedelta(days=nights)
            entities["check_in_date"] = departure_date.isoformat()
            entities["check_out_date"] = inferred_checkout.isoformat()
            entities["stay_duration_days"] = nights

        passengers = self._extract_count(lower, ["passenger", "passengers", "traveller", "travellers", "traveler", "travelers", "person", "people", "ppl", "adult", "adults"])
        if passengers is None and (
            any(key in state.get("pending_clarifications", []) for key in ["travellers", "travelers", "travel_dates", "booking_scope"])
            or "both" in lower
        ):
            passengers = self._extract_contextual_passenger_count(lower)
        if passengers is not None:
            entities["passengers"] = passengers
            entities["guests"] = passengers

        guests = self._extract_count(lower, ["guest", "guests", "person", "people", "ppl", "adult", "adults"])
        if guests is not None:
            entities["guests"] = guests

        cabin_class = self._extract_cabin_class(lower)
        if cabin_class:
            entities["cabin_class"] = cabin_class

        room_type = self._extract_room_type(lower)
        if room_type:
            entities["room_type"] = room_type

        location_preference = self._extract_location_preference(lower)
        if location_preference:
            entities["location_preference"] = location_preference

        if "one way" in lower or "one-way" in lower:
            entities["return_date"] = None
            entities["one_way"] = True

        if re.search(r"\b(no|don'?t have|not sure).{0,25}(check[- ]?out|return).{0,20}(yet|now|details)?\b", lower):
            entities.pop("return_date", None)
            entities.pop("check_out_date", None)
            entities["_missing_return_or_checkout"] = True

        cancel_hotel = bool(re.search(r"\b(?:don'?t|do not|no)\s+(?:show|need|want|include).*hotel|\bonly\s+flights?\b|\bflight[s]?\s+only\b", lower))
        if cancel_hotel:
            entities["needs_flight"] = True
            entities["needs_hotel"] = False
            entities["_explicit_needs_flight"] = True
            entities["_cancel_hotel"] = True

        passenger_change_only = bool(
            re.search(r"\b(?:make it|change|update|instead)\s+\d+\s*(?:travellers|travelers|passengers|people|ppl)\b", lower)
            or re.search(r"\b\d+\s*(?:travellers|travelers|passengers|people|ppl)\s+instead\b", lower)
        )
        if passenger_change_only:
            entities["_change_passengers"] = True

        scope_pending = any(key in state.get("pending_clarifications", []) for key in ["booking_scope", "travel_scope"])
        both_requested = bool(re.search(r"\b(both|flight[s]?\s*(and|&)\s*hotel[s]?|hotel[s]?\s*(and|&)\s*flight[s]?)\b", lower))
        hotel_only = bool(re.search(r"\b(?:only\s+hotels?|hotel[s]?\s+only|show\s+only\s+hotels?)\b", lower))
        city_pair_visible = bool(origin and destination)
        needs_flight = any(token in lower for token in ["flight", "flights", "fly", "flying", "airline", "ticket"]) or city_pair_visible
        needs_hotel = any(token in lower for token in ["hotel", "hotels", "stay", "room", "accommodation", "nights", "check-in", "check in"])
        if both_requested:
            needs_flight = True
            needs_hotel = True
        if hotel_only:
            needs_flight = False
            needs_hotel = True
            entities["_hotel_only"] = True
        if cancel_hotel:
            needs_flight = True
            needs_hotel = False
        if force_hotel_followup:
            needs_hotel = True
        if needs_hotel and not needs_flight and departure_date and return_date:
            entities["check_in_date"] = departure_date.isoformat()
            entities["check_out_date"] = return_date.isoformat()
        if (
            entities.get("_date_year_missing")
            and not date_change_requested
            and "origin" in entities
            and "destination" in entities
            and entities.get("departure_date")
            and (needs_flight or needs_hotel)
            and not state.get("pending_clarifications")
        ):
            entities["_year_inferred"] = True
            entities.pop("_date_year_missing", None)

        # Keep explicit scope separate from durable state. This prevents stale
        # package-search scope from making a later short message re-run old searches.
        if needs_flight:
            entities["needs_flight"] = True
            entities["_explicit_needs_flight"] = True
        if needs_hotel:
            entities["needs_hotel"] = True
            entities["_explicit_needs_hotel"] = True
        if force_hotel_followup:
            entities["_force_hotel_followup"] = True

        general_question = self._is_general_question(lower, needs_flight=needs_flight, needs_hotel=needs_hotel)
        destination_changed = self._detect_destination_change(lower, entities, state)

        has_date_update = any(key in entities for key in ["departure_date", "return_date", "check_in_date", "check_out_date"])
        previous_needs_flight = bool(previous_params.get("needs_flight"))
        previous_needs_hotel = bool(previous_params.get("needs_hotel"))

        if general_question:
            intent = "general_question"
        elif entities.get("multi_city_plan"):
            intent = "multi_city_package"
        elif entities.get("_cancel_hotel"):
            intent = "flight_search"
        elif entities.get("_change_passengers") and previous_needs_flight and previous_needs_hotel:
            intent = "package_search"
            entities.setdefault("needs_flight", True)
            entities.setdefault("needs_hotel", True)
        elif entities.get("_change_passengers") and previous_needs_flight:
            intent = "flight_search"
            entities.setdefault("needs_flight", True)
        elif entities.get("_change_passengers") and previous_needs_hotel:
            intent = "hotel_search"
            entities.setdefault("needs_hotel", True)
        elif date_change_requested and not has_date_update:
            intent = "change_dates"
        elif date_change_requested and needs_flight and not needs_hotel:
            intent = "flight_search"
        elif date_change_requested and needs_hotel and not needs_flight:
            intent = "hotel_search"
        elif date_change_requested and (needs_flight and needs_hotel or previous_needs_flight and previous_needs_hotel):
            intent = "package_search"
            entities.setdefault("needs_flight", True)
            entities.setdefault("needs_hotel", True)
        elif date_change_requested and previous_needs_flight:
            intent = "flight_search"
            entities.setdefault("needs_flight", True)
        elif force_hotel_followup:
            intent = "hotel_search"
        elif needs_flight and needs_hotel:
            intent = "package_search"
        elif needs_flight:
            intent = "flight_search"
        elif needs_hotel:
            intent = "hotel_search"
        elif "destination" in entities:
            intent = "travel_planning"
        else:
            intent = "ambiguous"

        return ExtractedIntent(
            intent=intent,
            entities=entities,
            general_question=general_question,
            destination_changed=destination_changed,
            raw_text=text,
        )

    def _extract_leg_date_update_plan(self, lower: str, state: OrchestratorState) -> Optional[Dict[str, Any]]:
        """Update a specific leg date in the active multi-city plan.

        Natural travel edits often arrive as: "replace the date for BLR to SIN
        from 2026-08-04 to 2026-08-08". Earlier versions treated this as a
        hotel-only request because two dates were visible. This function treats
        it as an itinerary edit: update the matching flight leg and adjust the
        neighbouring hotel checkout/check-in dates.
        """
        if not re.search(r"\b(change|replace|update|move|shift|reschedule)\b.*\b(date|leg|flight|route)\b|\bdate\s+for\b", lower):
            return None
        active = state.get("multi_city_plan", {}) if isinstance(state.get("multi_city_plan"), dict) else {}
        if not active.get("legs"):
            return None
        city_pattern = _known_city_pattern()
        leg_match = re.search(rf"\b(?:for|leg|flight|route)?\s*({city_pattern})\s+to\s+({city_pattern})\b", lower)
        if not leg_match:
            return None
        dates = self._extract_all_dates(lower)
        if not dates:
            return None
        origin = _normalize_city_fragment(leg_match.group(1))
        destination = _normalize_city_fragment(leg_match.group(2))
        if not origin or not destination:
            return None
        old_date = dates[0].isoformat() if len(dates) >= 2 else None
        new_date = dates[-1].isoformat()
        legs = [dict(leg) for leg in active.get("legs", []) if isinstance(leg, dict)]
        stays = [dict(stay) for stay in active.get("stays", []) if isinstance(stay, dict)]
        changed_idx: Optional[int] = None
        for idx, leg in enumerate(legs):
            if leg.get("origin") == origin and leg.get("destination") == destination:
                if old_date and leg.get("departure_date") != old_date:
                    # If the user says "from old to new" but the old date does
                    # not match the active plan, still allow the edit when the
                    # route is unambiguous. The model should be helpful and not
                    # get blocked by stale wording.
                    pass
                leg["departure_date"] = new_date
                changed_idx = idx
                break
        if changed_idx is None:
            return None

        # Reconstruct city/date points from legs.
        cities: List[str] = []
        for leg in legs:
            if not cities:
                cities.append(str(leg.get("origin")))
            cities.append(str(leg.get("destination")))
        date_points = [str(leg.get("departure_date")) for leg in legs]
        # Final date point can be the checkout of the last non-home stay if known.
        if len(date_points) < len(cities):
            final_checkout = None
            for stay in reversed(stays):
                if stay.get("check_out_date"):
                    final_checkout = str(stay["check_out_date"])
                    break
            date_points.append(final_checkout or date_points[-1])

        # Adjust stay boundaries. For a leg A->B on date D, the hotel in A (if
        # any) checks out on D, and the hotel in B (if any) checks in on D.
        for stay in stays:
            if stay.get("destination") == origin:
                # This is the stay before the edited leg.
                stay["check_out_date"] = new_date
            if stay.get("destination") == destination and not (changed_idx == len(legs) - 1 and destination == cities[0]):
                # This is the stay after the edited leg, if the destination is not final home.
                stay["check_in_date"] = new_date

        return {"cities": cities, "date_points": date_points, "legs": legs, "stays": stays, "scope": "both", "edit_summary": "leg_date_update"}

    def _extract_itinerary_edit_plan(self, lower: str, state: OrchestratorState) -> Optional[Dict[str, Any]]:
        """Interpret natural edits against the active multi-city itinerary.

        Real users often edit an itinerary without restating every date:
        - "I don't want to go Paris. From Singapore directly go to Tokyo."
        - "Remove Paris and keep the rest same."
        - "Skip Tokyo; go from Singapore to Paris instead."

        Earlier versions treated those turns as fresh single-flight searches and
        reused stale dates. This function treats them as TravelPlan edit actions:
        first identify the old plan, then remove/replace cities, then rebuild
        flight legs and hotel stays using the existing date points.
        """
        plan = state.get("multi_city_plan", {}) if isinstance(state.get("multi_city_plan"), dict) else {}
        cities = plan.get("cities") or []
        raw_points = plan.get("date_points") or []
        if not isinstance(cities, list) or len(cities) < 3 or not raw_points:
            return None
        try:
            old_points = [date.fromisoformat(str(value)) for value in raw_points]
        except ValueError:
            return None

        city_pattern = _known_city_pattern()
        editish = bool(re.search(r"\b(change|changed|edit|modify|update|remove|skip|drop|dont|don't|do not|directly|instead|replace)\b", lower))
        if not editish:
            return None
        duration_adjustments = self._extract_named_duration_adjustments(lower)
        duration_overrides = self._extract_named_duration_overrides(lower)
        for adjusted_city in duration_adjustments:
            duration_overrides.pop(adjusted_city, None)
        generic_duration_adjustment = self._extract_generic_duration_adjustment(lower)

        # Ambiguous replacement: "replace with Paris" does not tell us which
        # city to replace. Do not guess; ask one focused clarification.
        ambiguous_replace = re.search(rf"\breplace\s+with\s+({city_pattern})\b", lower)
        if ambiguous_replace:
            new_city = _normalize_city_fragment(ambiguous_replace.group(1))
            if new_city:
                labels = ", ".join(_city_label(code) for code in cities)
                return {"missing": "replacement_target", "planner_message": f"I can update the itinerary, but please tell me which city should be replaced with {_city_label(new_city)}. Your current route is: {labels}."}

        # Case: "I don't want to go Paris" / "skip Paris" / "remove Paris".
        remove_codes: List[str] = []
        for match in re.finditer(rf"\b(?:dont|don't|do\s+not|not|skip|remove|drop)\s+(?:want\s+to\s+)?(?:go\s+to\s+|visit\s+)?({city_pattern})\b", lower):
            code = _normalize_city_fragment(match.group(1))
            if code and code not in remove_codes:
                remove_codes.append(code)

        # Case: "from Singapore directly go to Tokyo" says how to reconnect
        # after removing an intermediate stop.
        direct_match = re.search(rf"\bfrom\s+({city_pattern})\s+(?:i\s+will\s+)?(?:directly\s+)?(?:go|fly|travel)?\s*(?:to|towards)\s+({city_pattern})\b", lower)
        direct_origin = _normalize_city_fragment(direct_match.group(1)) if direct_match else None
        direct_destination = _normalize_city_fragment(direct_match.group(2)) if direct_match else None

        # Case: "skip Tokyo; go from Singapore to Paris instead".
        if direct_origin and direct_destination and direct_origin in cities and direct_destination in cities:
            start_idx = cities.index(direct_origin)
            end_idx = len(cities) - 1 - list(reversed(cities)).index(direct_destination)
            if start_idx < end_idx:
                # Keep the prefix through direct_origin, jump to direct_destination,
                # and then keep any suffix after direct_destination. This removes
                # the skipped middle cities without losing the return home.
                new_cities = cities[: start_idx + 1] + cities[end_idx:]
                if remove_codes:
                    first = new_cities[0]
                    last = new_cities[-1]
                    new_cities = [code for i, code in enumerate(new_cities) if code not in remove_codes or i in {0, len(new_cities) - 1}]
                    if new_cities[0] != first:
                        new_cities.insert(0, first)
                    if new_cities[-1] != last:
                        new_cities.append(last)
                return self._rebuild_plan_for_edited_cities(
                    old_cities=cities,
                    old_points=old_points,
                    new_cities=new_cities,
                    duration_overrides=duration_overrides,
                    duration_adjustments=duration_adjustments,
                )

        if remove_codes:
            # Remove only intermediate occurrences by default. If the user names
            # the home city, avoid deleting the origin/final return without a
            # stronger instruction.
            new_cities: List[str] = []
            for idx, code in enumerate(cities):
                is_home_endpoint = idx == 0 or idx == len(cities) - 1
                if code in remove_codes and not is_home_endpoint:
                    continue
                if not new_cities or new_cities[-1] != code:
                    new_cities.append(code)
            if len(new_cities) >= 2 and new_cities != cities:
                return self._rebuild_plan_for_edited_cities(
                    old_cities=cities,
                    old_points=old_points,
                    new_cities=new_cities,
                    duration_overrides=duration_overrides,
                    duration_adjustments=duration_adjustments,
                )

        # Explicit replacement "replace Tokyo with Paris" when it does not
        # create consecutive duplicates. Consecutive duplicates are handled by
        # _extract_replacement_clarification before this function.
        replace_match = re.search(rf"\breplace\s+({city_pattern})\s+with\s+({city_pattern})\b", lower)
        if replace_match:
            old_code = _normalize_city_fragment(replace_match.group(1))
            new_code = _normalize_city_fragment(replace_match.group(2))
            if old_code and new_code and old_code in cities:
                new_cities = [new_code if code == old_code else code for code in cities]
                if any(new_cities[idx] == new_cities[idx + 1] for idx in range(len(new_cities) - 1)):
                    return None
                if generic_duration_adjustment and new_code not in duration_adjustments:
                    duration_adjustments[new_code] = generic_duration_adjustment
                    duration_overrides.pop(new_code, None)
                return self._rebuild_plan_for_edited_cities(
                    old_cities=cities,
                    old_points=old_points,
                    new_cities=new_cities,
                    duration_overrides=duration_overrides,
                    duration_adjustments=duration_adjustments,
                )

        return None

    def _rebuild_plan_for_edited_cities(
        self,
        old_cities: List[str],
        old_points: List[date],
        new_cities: List[str],
        duration_overrides: Optional[Dict[str, int]] = None,
        duration_adjustments: Optional[Dict[str, int]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Recalculate date points after an itinerary edit.

        The first departure date is preserved. Durations are preserved by
        destination city when possible. If a city was removed, the preceding stay
        duration is reused for the next direct leg instead of borrowing unrelated
        stale return dates.
        """
        if len(new_cities) < 2:
            return None
        duration_overrides = duration_overrides or {}
        duration_adjustments = duration_adjustments or {}
        durations_by_destination: Dict[str, int] = {}
        sequential_durations: List[int] = []
        for idx in range(len(old_cities) - 1):
            if idx + 1 >= len(old_points):
                break
            gap = max((old_points[idx + 1] - old_points[idx]).days, 0)
            dest = old_cities[idx + 1]
            is_final_return_home = idx == len(old_cities) - 2 and dest == old_cities[0]
            if not is_final_return_home:
                durations_by_destination[dest] = gap
                sequential_durations.append(gap)

        points = [old_points[0]]
        for idx in range(1, len(new_cities)):
            dest = new_cities[idx]
            is_final_return_home = idx == len(new_cities) - 1 and dest == new_cities[0]
            if is_final_return_home:
                # Leave the prior city after its existing/new stay duration.
                duration = 0
            else:
                duration = durations_by_destination.get(dest)
                if duration is None:
                    duration = sequential_durations[min(idx - 1, len(sequential_durations) - 1)] if sequential_durations else 7
                if dest in duration_overrides:
                    duration = duration_overrides[dest]
                if dest in duration_adjustments:
                    duration = int(duration) + duration_adjustments[dest]
            points.append(points[-1] + timedelta(days=int(duration)))
        return self._build_multi_city_plan_from_cities(cities=new_cities, date_points=points)

    def _extract_replacement_clarification(self, lower: str, state: OrchestratorState) -> Optional[str]:
        """Clarify destructive edits that would create nonsense city chains.

        Example: in Paris → Singapore → Tokyo → Paris, the follow-up
        "replace Tokyo with Singapore" produces Paris → Singapore → Singapore → Paris.
        A real travel agent would not blindly search a Singapore → Singapore leg;
        it would ask whether the user wants to extend the Singapore stay or add a
        second Singapore stop.
        """
        if "replace" not in lower or "with" not in lower:
            return None
        plan = state.get("multi_city_plan", {}) if isinstance(state.get("multi_city_plan"), dict) else {}
        cities = plan.get("cities") or []
        if not isinstance(cities, list) or len(cities) < 3:
            return None
        city_pattern = _known_city_pattern()
        # Ambiguous edit: "replace with Paris" gives a new city but not the
        # target city. Ask a clean planner clarification and keep the old plan
        # intact for the next turn.
        ambiguous = re.search(rf"\breplace\s+with\s+({city_pattern})\b", lower)
        if ambiguous:
            new_code = _normalize_city_fragment(ambiguous.group(1))
            if new_code:
                labels = ", ".join(_city_label(code) for code in cities)
                return f"I can update the itinerary, but please tell me which city should be replaced with {_city_label(new_code)}. Your current route is: {labels}."
        match = re.search(rf"\breplace\s+({city_pattern})\s+with\s+({city_pattern})\b", lower)
        if not match:
            return None
        old_code = _normalize_city_fragment(match.group(1))
        new_code = _normalize_city_fragment(match.group(2))
        if not old_code or not new_code:
            return None
        replaced = [new_code if code == old_code else code for code in cities]
        if any(replaced[idx] == replaced[idx + 1] for idx in range(len(replaced) - 1)):
            old_label = _city_label(old_code)
            new_label = _city_label(new_code)
            return (
                f"Replacing {old_label} with {new_label} would create two consecutive {new_label} stops. "
                f"Should I remove {old_label} and extend the {new_label} stay, or keep {new_label} as a separate second stop?"
            )
        date_points = []
        for value in plan.get("date_points") or []:
            try:
                date_points.append(date.fromisoformat(str(value)))
            except ValueError:
                return None
        if len(date_points) >= len(replaced):
            return None
        return None

    def _extract_explicit_leg_dates_plan(self, lower: str) -> Optional[Dict[str, Any]]:
        """Build a canonical plan from explicitly dated leg phrases.

        Handles: "from Singapore to Tokyo on 2026-07-25, then from Tokyo
        to Paris on 2026-07-30. I need hotel in Tokyo too."  Earlier
        versions saw three cities and two dates and incorrectly asked for a
        duration; this function knows the second date is the departure date of
        the second leg and the check-out date for the first destination.
        """
        city_pattern = _known_city_pattern()
        leg_matches = list(re.finditer(rf"\b(?:from|frm)\s+({city_pattern})\s+to\s+({city_pattern})\b", lower))
        if len(leg_matches) < 2:
            return None
        dates = self._extract_all_dates(lower)
        if len(dates) < len(leg_matches):
            return None
        legs: List[Dict[str, Any]] = []
        cities: List[str] = []
        for idx, match in enumerate(leg_matches):
            origin = _normalize_city_fragment(match.group(1))
            destination = _normalize_city_fragment(match.group(2))
            if not origin or not destination:
                return None
            if idx == 0:
                cities.append(origin)
            # Avoid immediate duplicate if the user repeats the shared transfer city.
            if not cities or cities[-1] != destination:
                cities.append(destination)
            legs.append({"origin": origin, "destination": destination, "departure_date": dates[idx].isoformat()})

        stays: List[Dict[str, Any]] = []
        wants_hotel = bool(re.search(r"\b(hotel|hotels|stay|room|accommodation)\b", lower))
        if wants_hotel:
            for idx in range(len(legs) - 1):
                current_leg = legs[idx]
                next_leg = legs[idx + 1]
                if current_leg["destination"] == next_leg["origin"] and dates[idx + 1] > dates[idx]:
                    stays.append({
                        "destination": current_leg["destination"],
                        "check_in_date": dates[idx].isoformat(),
                        "check_out_date": dates[idx + 1].isoformat(),
                    })
        return {
            "cities": cities,
            "date_points": [dt.isoformat() for dt in dates[: len(legs)]],
            "legs": legs,
            "stays": stays,
            "source": "explicit_dated_legs",
        }

    def _extract_multi_city_duration_update(self, lower: str, state: OrchestratorState) -> Optional[Dict[str, Any]]:
        """Update durations on the existing itinerary from a natural repair turn.

        Example: "Make Singapore 7 days instead, keep Paris 5 days." This is
        not a new route, but it must recalculate all downstream leg dates and
        re-run the A2A agents.
        """
        if not re.search(r"\b(make|change|update|keep|instead|extend|increase|add)\b", lower):
            return None
        plan = state.get("multi_city_plan", {}) if isinstance(state.get("multi_city_plan"), dict) else {}
        cities = plan.get("cities") or []
        raw_points = plan.get("date_points") or []
        if not isinstance(cities, list) or len(cities) < 3 or not raw_points:
            return None
        try:
            existing_points = [date.fromisoformat(str(value)) for value in raw_points]
        except ValueError:
            return None
        adjustments = self._extract_named_duration_adjustments(lower)
        overrides = self._extract_named_duration_overrides(lower)
        for adjusted_city in adjustments:
            overrides.pop(adjusted_city, None)
        if not overrides and not adjustments:
            return None

        # Derive previous destination durations from the existing date points.
        destination_durations: Dict[str, int] = {}
        for idx in range(1, min(len(cities), len(existing_points))):
            destination_code = cities[idx]
            is_final_return_home = idx == len(cities) - 1 and destination_code == cities[0]
            if is_final_return_home:
                continue
            previous_point = existing_points[idx - 1]
            current_point = existing_points[idx]
            destination_durations[destination_code] = max((current_point - previous_point).days, 0)
        destination_durations.update(overrides)
        for city_code, adjustment in adjustments.items():
            if city_code in destination_durations:
                destination_durations[city_code] = destination_durations[city_code] + adjustment

        points = [existing_points[0]]
        for idx in range(1, len(cities)):
            destination_code = cities[idx]
            is_final_return_home = idx == len(cities) - 1 and destination_code == cities[0]
            duration = 0 if is_final_return_home else destination_durations.get(destination_code)
            if duration is None:
                # Fallback to the previous gap if available, otherwise keep a safe 7-day default.
                if idx < len(existing_points):
                    duration = max((existing_points[idx] - existing_points[idx - 1]).days, 0)
                else:
                    duration = 7
            points.append(points[-1] + timedelta(days=int(duration)))
        return self._build_multi_city_plan_from_cities(cities=cities, date_points=points)

    def _extract_named_duration_overrides(self, lower: str) -> Dict[str, int]:
        """Return city-specific duration overrides, e.g. Singapore -> 7."""
        overrides: Dict[str, int] = {}
        city_pattern = _known_city_pattern()
        for match in re.finditer(rf"\b({city_pattern})\b[^.\n,;]{{0,50}}?\b(?:(?:for|stay|staying|keep|make(?:\s+it)?)\s*)?(?:(a|one|1)\s+week|(\d{{1,2}})\s*days?)\b", lower):
            code = _normalize_city_fragment(match.group(1))
            if not code:
                continue
            days = 7 if match.group(2) else int(match.group(3))
            overrides[code] = days
        return overrides

    def _extract_named_duration_adjustments(self, lower: str) -> Dict[str, int]:
        """Return additive stay changes, e.g. BLR -> +2 days."""
        adjustments: Dict[str, int] = {}
        city_pattern = _known_city_pattern()
        patterns = [
            rf"\b(?:extend|increase)\b[^.\n,;]{{0,60}}?\b(?:stay|stop|visit)?\s*(?:in|at|for)\s+({city_pattern})\b[^.\n,;]{{0,40}}?\b(?:by|for|with)?\s*(?:(a|one|1)\s+week|(\d{{1,2}})\s*days?)\b",
            rf"\b(?:add|extend|increase)\s+(?:(a|one|1)\s+week|(\d{{1,2}})\s*days?)\b[^.\n,;]{{0,60}}?\b(?:to|in|at)\s+({city_pattern})\b",
            rf"\b(?:extend|increase)\s+({city_pattern})\s+(?:stay|stop|visit)\b[^.\n,;]{{0,40}}?\b(?:by|for)\s+(?:(a|one|1)\s+week|(\d{{1,2}})\s*days?)\b",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, lower):
                groups = match.groups()
                city_text = next((group for group in groups if group and _normalize_city_fragment(group)), None)
                code = _normalize_city_fragment(city_text or "")
                if not code:
                    continue
                days = 7 if any(group in {"a", "one", "1"} for group in groups if group) else None
                if days is None:
                    number = next((group for group in groups if group and group.isdigit()), None)
                    if not number:
                        continue
                    days = int(number)
                adjustments[code] = days
        return adjustments

    @staticmethod
    def _extract_generic_duration_adjustment(lower: str) -> Optional[int]:
        """Return additive stay change without a city, e.g. extend stay by 2 days."""
        match = re.search(
            r"\b(?:extend|increase|add)\b[^.\n,;]{0,40}?\b(?:stay|stop|visit)?\b[^.\n,;]{0,20}?\b(?:by|for|with)\s+(?:(a|one|1)\s+week|(\d{1,2})\s*days?)\b",
            lower,
        )
        if not match:
            return None
        if match.group(1):
            return 7
        return int(match.group(2))

    def _answer_itinerary_comparison(self, message: str, state: OrchestratorState) -> Optional[str]:
        """Answer comparative follow-ups against the active itinerary context."""
        lower = message.lower()
        if not any(token in lower for token in ["better", "food", "nightlife", "these places", "which of these"]):
            return None
        plan = state.get("multi_city_plan", {}) if isinstance(state.get("multi_city_plan"), dict) else {}
        cities = []
        for code in plan.get("cities") or []:
            label = _city_label(code)
            if label != "your destination" and label not in cities:
                cities.append(label)
        if not cities:
            return None
        food_notes = {
            "Tokyo": "Tokyo is strongest for food variety: sushi, ramen, izakayas, department-store food halls, Shinjuku, Shibuya, Tsukiji outer market, and late-night dining.",
            "Singapore": "Singapore is excellent for hawker food, Peranakan cuisine, Little India, Chinatown, Lau Pa Sat, Maxwell Food Centre, and clean city movement.",
            "Paris": "Paris is best for cafés, bakeries, wine bars, bistros, fine dining, food markets, Le Marais, Saint-Germain, and Seine-side evening walks.",
        }
        history_notes = {
            "Tokyo": "For historical travel, Tokyo gives Asakusa/Sensō-ji, Meiji Shrine, Edo-Tokyo style neighbourhoods, Ueno museums, and day trips to Nikko or Kamakura.",
            "Singapore": "For history and culture, Singapore gives Chinatown, Little India, Kampong Glam, National Gallery, Asian Civilisations Museum, Fort Canning, and colonial civic districts.",
            "Paris": "For historical places, Paris is the strongest: Louvre, Notre-Dame area, Sainte-Chapelle, Musée d'Orsay, Panthéon, Montmartre, Arc de Triomphe, and Versailles nearby.",
        }
        nightlife_notes = {
            "Tokyo": "Tokyo has the most energetic nightlife through Shinjuku, Shibuya, Golden Gai, music bars, and late-night food.",
            "Singapore": "Singapore is polished and safe for nightlife: Marina Bay, Clarke Quay, rooftop bars, and waterfront evenings.",
            "Paris": "Paris is better for romantic evenings, wine bars, jazz clubs, cafés, and culture-led nights rather than high-energy nightlife.",
        }
        wants_history = any(token in lower for token in ["history", "historical", "heritage", "culture", "cultural", "monument", "museums", "museum"])
        wants_nightlife = "nightlife" in lower or "night life" in lower
        lines = ["Based on your current itinerary, here is the practical comparison:"]
        for city in cities:
            pieces = [food_notes.get(city, city + " is worth comparing based on your travel style, budget, and season.")]
            if wants_history:
                pieces.append(history_notes.get(city, "It also has local heritage areas worth checking."))
            if wants_nightlife:
                pieces.append(nightlife_notes.get(city, "Nightlife depends on the area and season."))
            lines.append(f"- {' '.join(pieces)}")
        if "food" in lower and wants_history:
            lines.append("For food + historical places together, I would rank them: Paris first for history, Tokyo first for food depth, and Singapore first for easy food access and multicultural neighbourhoods.")
        elif "food" in lower and wants_nightlife:
            lines.append("For pure food + nightlife energy, I would rank them: Tokyo first, Singapore second, Paris third. For romance and culture-heavy evenings, Paris can move to first.")
        return "\n".join(lines)

    def _extract_city_sequence(self, lower: str) -> List[str]:
        """Extract ordered city chains from many natural travel phrasings.

        This is the deterministic safety net behind the LLM planner.  It is
        deliberately pattern-rich because real travellers do not use one fixed
        syntax.  It supports:
        - "from Paris to Singapore to Tokyo to Paris"
        - "from Paris to Singapore then Tokyo then Paris"
        - "travel through the cities as follows: Paris, Singapore, Tokyo, Paris"
        - "route: Paris -> Singapore -> Tokyo -> Paris"
        - "Paris, Singapore, Tokyo, Paris" when the message is clearly asking
          for flight/hotel itinerary details.
        """
        city_pattern = _known_city_pattern()
        pre_context = re.split(
            r"\bstart(?:ing)?\s+date\b|\bjourney\s+on\b|\bi\s+will\s+stay\b|\bstay(?:ing)?\b|\bbased\s+on\b|\bgive\s+me\b|\bfor\s+\d+\s+(?:travellers|travelers|people|ppl)\b",
            lower,
            maxsplit=1,
        )[0]

        candidates: List[str] = []

        # 1) Explicit "cities as follows/list/route".  This catches the user's
        # failing prompt: "travel through the cites as follow: paris, ...".
        list_match = re.search(
            r"\b(?:cities?|cites|route|itinerary|places?)\b[^:;\n]{0,80}(?:as\s+follows?|as\s+follow|list|sequence)?\s*[:\-]?\s*(.+)",
            pre_context,
        )
        if list_match:
            list_part = list_match.group(1)
            for match in re.finditer(rf"\b({city_pattern})\b", list_part):
                code = _normalize_city_fragment(match.group(1))
                if code:
                    candidates.append(code)
            # If the loose list pattern only captured a tail fragment such as
            # "... cites starting from Tokyo ... at last to Tokyo", do not trust
            # the one-city result. Fall back to route-chain extraction below.
            if len(candidates) < 3:
                candidates = []

        # 2) "from X to Y to Z" / "from X to Y then to Z" route chains.
        if not candidates:
            start_match = re.search(rf"\b(?:from|frm)\s+({city_pattern})\b", pre_context)
            if start_match:
                first = _normalize_city_fragment(start_match.group(1))
                if first:
                    candidates.append(first)
                remainder = pre_context[start_match.end():]
                for match in re.finditer(rf"\b(?:to|then\s+to|then|via|through|finally\s+to|finally|lastly\s+to|lastly|back\s+to|and\s+finally|at\s+last\s+to|at\s+the\s+end\s+to)\s+({city_pattern})\b", remainder):
                    code = _normalize_city_fragment(match.group(1))
                    if code:
                        candidates.append(code)

        # 3) Arrow/comma chain where the user says "route" or asks for travel
        # details.  Avoid converting normal single-destination prompts into
        # multi-city just because multiple city names appear in an open-jaw.
        if not candidates:
            chainish = bool(re.search(r"\b(route|itinerary|multi[- ]?city|through|cities?|cites|places?)\b", pre_context))
            bookingish = bool(re.search(r"\b(flights?|hotels?|book|travel|details|journey|trip)\b", lower))
            separators = pre_context.count(",") + pre_context.count("->") + pre_context.count("→") + len(re.findall(r"\s+to\s+", pre_context))
            if chainish or (bookingish and separators >= 2):
                for match in re.finditer(rf"\b({city_pattern})\b", pre_context):
                    code = _normalize_city_fragment(match.group(1))
                    if code:
                        candidates.append(code)

        # Preserve repeated non-consecutive cities, but remove accidental
        # immediate duplicates from phrases like "Tokyo Tokyo".
        cities: List[str] = []
        for code in candidates:
            if code and (not cities or cities[-1] != code):
                cities.append(code)
        return cities

    def _extract_multi_city_plan(self, lower: str, state: Optional[OrchestratorState] = None) -> Optional[Dict[str, Any]]:
        """Extract an ordered multi-city itinerary from natural language.

        The planner is intentionally itinerary-first, not slot-first.  It tries
        to create a complete travel frame from arbitrary phrasing, then the
        LangGraph router decides whether to ask for missing information or fan
        out A2A tasks to specialist agents.
        """
        if re.search(r"\breturn(?:ing)?\s+to\b", lower) and not re.search(r"\b(then|through|cities?|cites|multi|route|itinerary)\b", lower):
            # Open-jaw round trips such as "Singapore to Tokyo returning to Paris"
            # have three cities but are not necessarily multi-city chains.
            return None

        cities = self._extract_city_sequence(lower)
        if len(cities) < 3:
            return None

        # A normal round-trip can be written as
        # "Singapore to Tokyo on DATE and Tokyo to Singapore on DATE".
        # The city scanner sees SIN → TYO → SIN, but that is still a
        # single-destination round trip, not a multi-city itinerary.
        multi_cue = bool(re.search(r"\b(multi[- ]?city|through|cities?|cites|route|itinerary|places?)\b", lower))
        if len(cities) == 3 and cities[0] == cities[-1] and len(set(cities)) == 2 and not multi_cue:
            return None

        dates = self._extract_all_dates(lower)
        duration_days = self._extract_stay_duration_days(lower)
        per_stop_durations = self._extract_per_stop_durations(lower, cities)

        # Natural repairs often omit the start date but clearly replace the route,
        # e.g. after one itinerary: "starting from Tokyo to Singapore for 7 days
        # then to Paris for 5 days then at last to Tokyo".  Reuse the previous
        # itinerary start date only when the new utterance gives a new route but
        # no new date. This is a planner-level memory repair, not a sub-agent job.
        if not dates and state:
            previous_plan = state.get("multi_city_plan", {}) if isinstance(state.get("multi_city_plan"), dict) else {}
            previous_points = previous_plan.get("date_points") or []
            if previous_points:
                try:
                    dates = [date.fromisoformat(str(previous_points[0]))]
                except ValueError:
                    dates = []

        if dates and len(dates) < len(cities):
            if per_stop_durations:
                dates = self._date_points_from_variable_durations(dates[0], cities, per_stop_durations, default_duration_days=duration_days)
            elif duration_days:
                dates = [dates[0] + timedelta(days=int(duration_days) * idx) for idx in range(len(cities))]

        if len(dates) < len(cities):
            return {"cities": cities, "duration_days": duration_days, "per_stop_durations": per_stop_durations, "missing": "date_points"}
        return self._build_multi_city_plan_from_cities(cities=cities, date_points=dates[: len(cities)])

    def _complete_pending_multi_city_plan(self, lower: str, pending_plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Complete a saved multi-city frame from a natural follow-up turn."""
        cities = pending_plan.get("cities") if isinstance(pending_plan, dict) else None
        if not isinstance(cities, list) or len(cities) < 3:
            return None
        dates = self._extract_all_dates(lower)
        duration_days = self._extract_stay_duration_days(lower) or pending_plan.get("duration_days")
        if dates and len(dates) >= len(cities):
            return self._build_multi_city_plan_from_cities(cities=cities, date_points=dates[: len(cities)])
        if dates and duration_days:
            generated_dates = [dates[0] + timedelta(days=int(duration_days) * idx) for idx in range(len(cities))]
            return self._build_multi_city_plan_from_cities(cities=cities, date_points=generated_dates)
        return {"cities": cities, "duration_days": duration_days, "missing": "date_points"}

    @staticmethod
    def _extract_stay_duration_days(lower: str) -> Optional[int]:
        """Extract stay duration from phrases such as 'a week' or '7 days'."""
        if re.search(r"\b(a|one|1)\s+week\b|\bweek\s+(?:everywhere|each|per)\b|\beach\s+(?:city|place|destination).*?\bweek\b|\bweek\s+in\s+each|\bafter\s+(?:a|one|1)\s+week\b", lower):
            return 7
        match = re.search(r"\b(?:stay(?:ing)?(?:\s+in)?(?:\s+each)?(?:\s+city|\s+place|\s+destination)?(?:\s+for)?|for|each|every|after)\s*(\d{1,2})\s*days?\b", lower)
        if match:
            return int(match.group(1))
        match = re.search(r"\b(\d{1,2})\s*days?\s*(?:each|everywhere|in each|per city|per place)?\b", lower)
        if match:
            return int(match.group(1))
        return None

    def _extract_per_stop_durations(self, lower: str, cities: List[str]) -> List[Optional[int]]:
        """Extract variable stay durations attached to each visited city.

        Example: "starting from Tokyo to Singapore for 7 days then to Paris
        for 5 days then at last to Tokyo" becomes [7, 5, None] for the
        destinations Singapore, Paris, Tokyo. The final return-home duration is
        normally unused, but keeping positional alignment makes validation easy.
        """
        if len(cities) < 2:
            return []

        duration_mentions: List[int] = []
        for match in re.finditer(r"\bfor\s+(?:(a|one|1)\s+week|(\d{1,2})\s*days?)\b", lower):
            if match.group(1):
                duration_mentions.append(7)
            elif match.group(2):
                duration_mentions.append(int(match.group(2)))

        # If the user gave one uniform duration, leave this to
        # _extract_stay_duration_days to avoid accidentally applying it only to
        # the first stop. Variable mode starts when at least two durations are
        # visible or the phrase clearly attaches durations to several legs.
        if len(duration_mentions) < 2:
            return []

        aligned: List[Optional[int]] = []
        for idx in range(1, len(cities)):
            aligned.append(duration_mentions[idx - 1] if idx - 1 < len(duration_mentions) else None)
        return aligned

    @staticmethod
    def _date_points_from_variable_durations(
        start_date: date,
        cities: List[str],
        per_stop_durations: List[Optional[int]],
        default_duration_days: Optional[int] = None,
    ) -> List[date]:
        """Build itinerary date points from per-stop durations.

        Date point i is the departure date for leg i.  For the final return
        home, no hotel stay is needed, so its extra date point may equal the
        previous point.
        """
        points = [start_date]
        for idx in range(1, len(cities)):
            is_final_city = idx == len(cities) - 1
            is_final_return_home = is_final_city and cities[idx] == cities[0]
            duration = per_stop_durations[idx - 1] if idx - 1 < len(per_stop_durations) else None
            if duration is None:
                if is_final_return_home:
                    duration = 0
                elif default_duration_days:
                    duration = int(default_duration_days)
                else:
                    duration = 0
            points.append(points[-1] + timedelta(days=int(duration)))
        return points

    @staticmethod
    def _build_multi_city_plan_from_cities(cities: List[str], date_points: List[date]) -> Dict[str, Any]:
        """Create flight legs and hotel stays from a city chain and date points.

        If the trip returns to the origin, hotel stays are created for the
        travelled destinations only, not for the home city after returning.
        """
        legs: List[Dict[str, Any]] = []
        stays: List[Dict[str, Any]] = []
        for idx in range(len(cities) - 1):
            legs.append({
                "origin": cities[idx],
                "destination": cities[idx + 1],
                "departure_date": date_points[idx].isoformat(),
            })
            is_final_return_home = idx == len(cities) - 2 and cities[idx + 1] == cities[0]
            if not is_final_return_home:
                stays.append({
                    "destination": cities[idx + 1],
                    "check_in_date": date_points[idx].isoformat(),
                    "check_out_date": date_points[idx + 1].isoformat(),
                })
        return {"cities": cities, "date_points": [dt.isoformat() for dt in date_points], "legs": legs, "stays": stays}

    def _extract_all_dates(self, lower: str) -> List[date]:
        """Return all dates in mention order, borrowing year from prior date."""
        events: List[tuple[int, date, bool]] = []
        for match in re.finditer(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", lower):
            events.append((match.start(), date(int(match.group(1)), int(match.group(2)), int(match.group(3))), True))
        month_pattern = "|".join(sorted((re.escape(month) for month in MONTHS), key=len, reverse=True))
        for match in re.finditer(rf"\b({month_pattern})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s*(20\d{{2}}))?\b", lower):
            month = MONTHS[match.group(1)]
            year = int(match.group(3)) if match.group(3) else 0
            events.append((match.start(), date(year or 1900, month, int(match.group(2))), bool(year)))
        for match in re.finditer(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({month_pattern})(?:,?\s*(20\d{{2}}))?\b", lower):
            month = MONTHS[match.group(2)]
            year = int(match.group(3)) if match.group(3) else 0
            events.append((match.start(), date(year or 1900, month, int(match.group(1))), bool(year)))
        events.sort(key=lambda item: item[0])
        resolved: List[date] = []
        context_year: Optional[int] = None
        for _, parsed, has_year in events:
            if has_year:
                context_year = parsed.year
                resolved.append(parsed)
            else:
                resolved.append(self._resolve_yearless_date(parsed.month, parsed.day, context_year))
        ordered: List[date] = []
        for dt in resolved:
            if dt not in ordered:
                ordered.append(dt)
        return ordered

    def _extract_route(self, lower: str) -> tuple[Optional[str], Optional[str]]:
        """Extract explicit directional route language.

        Handles both formal input ("from Singapore to Tokyo") and natural
        input ("travelling to Singapore from Tokyo"). This node deliberately
        avoids guessing when direction is not explicit.
        """
        origin = None
        destination = None
        city_pattern = _known_city_pattern()

        # from X to Y
        route_match = re.search(
            rf"\bfrom\s+({city_pattern})\s+to\s+({city_pattern})\b", lower
        )
        if route_match:
            origin = _normalize_city_fragment(route_match.group(1))
            destination = _normalize_city_fragment(route_match.group(2))

        # travelling/going/flying to Y from X
        reverse_phrase = re.search(
            rf"\b(?:travelling|traveling|going|go|flying|fly)\s+to\s+({city_pattern})\s+from\s+({city_pattern})\b",
            lower,
        )
        if reverse_phrase:
            destination = _normalize_city_fragment(reverse_phrase.group(1))
            origin = _normalize_city_fragment(reverse_phrase.group(2))

        compact_route = re.search(r"\b([a-z]{3})\s*[-→>]\s*([a-z]{3})\b", lower)
        if compact_route:
            origin = self._city_code(compact_route.group(1))
            destination = self._city_code(compact_route.group(2))

        return origin, destination

    def _extract_city_pair_route(self, lower: str) -> tuple[Optional[str], Optional[str]]:
        """Extract route expressions without the word 'from'.

        Users often say: "Singapore to Tokyo on 2026-07-25 and Tokyo to
        Singapore on 2026-07-30". That is still a precise round-trip route.
        """
        city_pattern = _known_city_pattern()
        match = re.search(rf"\b({city_pattern})\s+to\s+({city_pattern})\b", lower)
        if not match:
            return None, None
        return _normalize_city_fragment(match.group(1)), _normalize_city_fragment(match.group(2))

    def _extract_back_to_origin(self, lower: str) -> Optional[str]:
        """Extract return-origin hints such as 'back to Tokyo'."""
        city_pattern = _known_city_pattern()
        match = re.search(rf"\b(?:back|return|returning)\s+to\s+({city_pattern})\b", lower)
        if match:
            return _normalize_city_fragment(match.group(1))
        return None

    def _extract_return_destination(self, lower: str) -> Optional[str]:
        """Extract an explicit return/onward destination.

        Examples:
        - "returning to Paris 2025-06-20" -> PAR
        - "back to Tokyo" -> TYO

        This extends the mandated A2A schema without breaking it and lets the
        flight agent model open-jaw routes like SIN → TYO, then TYO → PAR.
        """
        city_pattern = _known_city_pattern()
        match = re.search(rf"\b(?:returning|return|back)\s+to\s+({city_pattern})\b", lower)
        if match:
            return _normalize_city_fragment(match.group(1))
        return None

    def _extract_origin_only(self, lower: str) -> Optional[str]:
        """Extract origin from phrases like 'from Singapore' without a destination."""
        city_pattern = _known_city_pattern()
        patterns = [
            rf"\b(?:from|frm)\s+({city_pattern})\b",
            rf"\bdeparture\s+(?:(?:from|frm)\s+)?({city_pattern})\b",
            rf"\bflying\s+(?:from|frm)\s+({city_pattern})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                return _normalize_city_fragment(match.group(1))
        return None

    def _extract_loose_destination(self, lower: str, existing_destination: Optional[str]) -> Optional[str]:
        if existing_destination:
            return existing_destination

        destination_patterns = [
            r"(?:change|switch|make it|instead|actually).*?\bto\s+([a-z\s]+?)(?:\s+on|\s+for|\s+with|,|\.|$)",
            r"\b(?:to|in|visit|for)\s+([a-z\s]+?)(?:\s+on|\s+for|\s+with|\s+in\s+|,|\.|$)",
            r"destination\s+(?:is|as)\s+([a-z\s]+?)(?:,|\.|$)",
        ]
        for pattern in destination_patterns:
            match = re.search(pattern, lower)
            if match:
                code = self._city_code(match.group(1))
                if code:
                    return code

        for alias, value in sorted(CITY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(rf"\b{re.escape(alias)}\b", lower):
                return value["code"]
        return None

    def _extract_dates(self, lower: str) -> tuple[Optional[date], Optional[date]]:
        """Extract the first two travel dates in text order.

        The previous implementation sorted natural-language dates. That broke
        realistic inputs such as "25 July 2026 ... checkout 30 July" because
        the second date had no year and defaulted to 2025. This version keeps
        mention order and borrows the explicit year from the first dated mention
        when a later date omits the year.
        """
        events: List[tuple[int, date, bool]] = []
        for match in re.finditer(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})(?!\d)", lower):
            try:
                events.append((match.start(), date(int(match.group(1)), int(match.group(2)), int(match.group(3))), True))
            except ValueError:
                continue

        month_pattern = "|".join(sorted((re.escape(month) for month in MONTHS), key=len, reverse=True))
        for match in re.finditer(rf"\b({month_pattern})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s*(20\d{{2}}))?\b", lower):
            month = MONTHS[match.group(1)]
            year = int(match.group(3)) if match.group(3) else 0
            events.append((match.start(), date(year or 1900, month, int(match.group(2))), bool(year)))
        for match in re.finditer(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({month_pattern})(?:,?\s*(20\d{{2}}))?\b", lower):
            month = MONTHS[match.group(2)]
            year = int(match.group(3)) if match.group(3) else 0
            events.append((match.start(), date(year or 1900, month, int(match.group(1))), bool(year)))

        events.sort(key=lambda item: item[0])
        resolved: List[date] = []
        context_year: Optional[int] = None
        for _, parsed, has_year in events:
            if has_year:
                context_year = parsed.year
                resolved.append(parsed)
            else:
                resolved.append(self._resolve_yearless_date(parsed.month, parsed.day, context_year))

        # Deduplicate while preserving text order.
        ordered: List[date] = []
        for dt in resolved:
            if dt not in ordered:
                ordered.append(dt)
        if len(ordered) >= 2:
            return ordered[0], ordered[1]
        if ordered:
            return ordered[0], None
        return None, None

    @staticmethod
    def _resolve_yearless_date(month: int, day: int, context_year: Optional[int] = None) -> date:
        """Resolve natural dates without a year to a safe future date."""
        if context_year:
            return date(context_year, month, day)
        today = date.today()
        candidate = date(today.year, month, day)
        if candidate < today:
            candidate = date(today.year + 1, month, day)
        return candidate

    @staticmethod
    def _extract_labeled_dates(lower: str) -> tuple[Optional[date], Optional[date], Optional[date], Optional[date]]:
        """Extract dates attached to semantic labels.

        Returns departure_date, return_date, check_in_date, check_out_date.
        This is stronger than positional parsing and fixes turns like
        "change the return date to 2026-07-28" where a single date should not
        become a new departure date.
        """
        def find_after(label_pattern: str) -> Optional[date]:
            match = re.search(label_pattern + r"[^0-9]*(20\d{2})-(\d{1,2})-(\d{1,2})", lower)
            if match:
                try:
                    return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                except ValueError:
                    return None
            return None

        departure = find_after(r"\b(?:depart(?:ure)?(?:\s+date)?|leave|leaving|outbound)\b")
        return_dt = find_after(r"\b(?:return(?:ing)?(?:\s+date)?|inbound|back)\b")
        check_in = find_after(r"\b(?:check[- ]?in|checkin)\b")
        check_out = find_after(r"\b(?:check[- ]?out|checkout)\b")
        return departure, return_dt, check_in, check_out

    @staticmethod
    def _extract_nights(lower: str) -> Optional[int]:
        match = re.search(r"\b(\d+)\s+nights?\b", lower)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _extract_count(lower: str, nouns: List[str]) -> Optional[int]:
        noun_pattern = "|".join(re.escape(noun) for noun in nouns)
        match = re.search(rf"\b(\d+)\s*(?:{noun_pattern})\b", lower)
        if match:
            return int(match.group(1))
        word_numbers = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
        for word, number in word_numbers.items():
            if re.search(rf"\b{word}\s*(?:{noun_pattern})\b", lower):
                return number
        return None

    @staticmethod
    def _extract_contextual_passenger_count(lower: str) -> Optional[int]:
        """Read shorthand traveller counts such as '26 July, 5, both'."""
        patterns = [
            r"(?:^|[,;])\s*([1-9]\d?)\s*(?:[,;.]|\b)\s*(?:both|flight|flights|hotel|hotels)?",
            r"\b([1-9]\d?)\s*(?:i\s*)?(?:want\s*)?(?:both|flight|flights|hotel|hotels)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _extract_cabin_class(lower: str) -> Optional[str]:
        if "premium economy" in lower:
            return CabinClass.PREMIUM_ECONOMY.value
        if "business" in lower:
            return CabinClass.BUSINESS.value
        if "first class" in lower or re.search(r"\bfirst\b", lower):
            return CabinClass.FIRST.value
        if "economy" in lower:
            return CabinClass.ECONOMY.value
        return None

    @staticmethod
    def _extract_room_type(lower: str) -> Optional[str]:
        if "suite" in lower:
            return RoomType.SUITE.value
        if "family" in lower:
            return RoomType.FAMILY.value
        if "deluxe" in lower:
            return RoomType.DELUXE.value
        if "standard" in lower:
            return RoomType.STANDARD.value
        return None

    @staticmethod
    def _extract_location_preference(lower: str) -> Optional[str]:
        patterns = [
            r"near\s+([a-z0-9\s-]+?)(?:\s+for|\s+with|\s+from|,|\.|$)",
            r"around\s+([a-z0-9\s-]+?)(?:\s+for|\s+with|\s+from|,|\.|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                cleaned = match.group(1).strip()
                if re.search(r"\b20\d{2}-\d{2}-\d{2}\b|\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)\b", cleaned):
                    continue
                if cleaned and cleaned not in {"the", "a"}:
                    return cleaned.title()
        if "city centre" in lower or "city center" in lower:
            return "City Centre"
        return None

    @staticmethod
    def _is_general_question(lower: str, needs_flight: bool, needs_hotel: bool) -> bool:
        question_style = "?" in lower or any(
            lower.startswith(prefix)
            for prefix in ["is ", "are ", "what ", "when ", "where ", "how ", "should ", "can "]
        )
        general_markers = [
            "good time",
            "best time",
            "weather",
            "safe",
            "visa",
            "things to do",
            "places",
            "attractions",
            "where to visit",
            "worth visiting",
            "season",
            "local events",
            "travel rules",
            "mock data",
            "available data",
        ]
        asks_for_advice = any(phrase in lower for phrase in ["tell me", "can you tell", "suggest", "recommend", "what places", "places in"])
        general_command = (lower.startswith(("check ", "tell me ", "explain ")) or asks_for_advice) and any(
            marker in lower for marker in general_markers
        )
        return (question_style or general_command) and any(marker in lower for marker in general_markers) and not (
            "book" in lower or "search" in lower or needs_flight or needs_hotel
        )

    @staticmethod
    def _is_out_of_scope_request(lower: str) -> bool:
        """Return True for clear non-travel knowledge requests.

        The assignment scope is a travel booking assistant. This guard prevents
        stale travel state from being reused when the user asks an unrelated
        educational or technical question.
        """
        cleaned = lower.strip()
        if not cleaned:
            return False

        for alias in list(CITY_ALIASES) + list(COUNTRY_ALIASES):
            if re.search(rf"\b{re.escape(alias)}\b", cleaned):
                return False

        travel_markers = [
            "flight",
            "flights",
            "fly",
            "flying",
            "airline",
            "airport",
            "hotel",
            "hotels",
            "room",
            "stay",
            "accommodation",
            "trip",
            "travel",
            "travelling",
            "traveler",
            "traveller",
            "itinerary",
            "route",
            "destination",
            "booking",
            "book",
            "visa",
            "weather",
            "places",
            "attractions",
            "food",
            "nightlife",
            "historical",
            "history",
            "sightseeing",
            "mock data",
            "good time",
            "best time",
        ]
        if any(re.search(rf"\b{re.escape(marker)}\b", cleaned) for marker in travel_markers):
            return False

        asks_for_knowledge = (
            "?" in cleaned
            or cleaned.startswith(("tell me", "explain", "what ", "why ", "how ", "define", "teach", "can you tell"))
        )
        if not asks_for_knowledge:
            return False

        non_travel_topics = [
            "calculus",
            "probability",
            "statistics",
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "neural network",
            "algebra",
            "geometry",
            "physics",
            "chemistry",
            "biology",
            "programming",
            "coding",
            "history homework",
            "essay",
            "stock market",
            "medical",
            "legal",
        ]
        if any(re.search(rf"\b{re.escape(topic)}\b", cleaned) for topic in non_travel_topics):
            return True
        return bool(re.search(r"\bai\b", cleaned))

    @staticmethod
    def _detect_destination_change(lower: str, entities: Dict[str, Any], state: OrchestratorState) -> bool:
        existing_destination = state.get("travel_params", {}).get("destination")
        new_destination = entities.get("destination")
        change_words = any(word in lower for word in ["change", "switch", "instead", "actually", "make it", "no i want"] )
        explicit_new_trip = any(key in entities for key in ["departure_date", "return_date", "needs_flight", "needs_hotel"])
        return bool(existing_destination and new_destination and existing_destination != new_destination and (change_words or explicit_new_trip))


    @staticmethod
    def _contains_yearless_date(lower: str) -> bool:
        """Return True only when a natural-language date omits the year."""
        if re.search(r"\b20\d{2}(?:-\d{2}-\d{2})?\b", lower):
            return False
        month_pattern = "|".join(sorted((re.escape(month) for month in MONTHS), key=len, reverse=True))
        for match in re.finditer(rf"\b(?:{month_pattern})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s*(20\d{{2}}))?\b", lower):
            if not match.group(1):
                return True
        for match in re.finditer(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:{month_pattern})(?:,?\s*(20\d{{2}}))?\b", lower):
            if not match.group(1):
                return True
        return False

    @staticmethod
    def _is_bare_destination_only(lower: str) -> bool:
        cleaned = re.sub(r"[^a-z\s]", " ", lower).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned in CITY_ALIASES

    @staticmethod
    def _city_code(fragment: str) -> Optional[str]:
        cleaned = re.sub(r"[^a-z\s]", " ", fragment.lower()).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if cleaned in CITY_ALIASES:
            return CITY_ALIASES[cleaned]["code"]
        tokens = cleaned.split()
        for length in range(min(3, len(tokens)), 0, -1):
            candidate = " ".join(tokens[:length])
            if candidate in CITY_ALIASES:
                return CITY_ALIASES[candidate]["code"]
        return None

    @staticmethod
    def _extract_explicit_unsupported_locations(message: str) -> List[str]:
        """Find explicit travel locations that are outside the mock-data catalog."""
        lower = message.lower().replace("->", " to ").replace("→", " to ")
        stop_pattern = "|".join(sorted((re.escape(word) for word in LOCATION_CAPTURE_STOP_WORDS), key=len, reverse=True))
        location_word = rf"(?!(?:{stop_pattern})\b)[a-z][a-z'-]*"
        location_phrase = rf"{location_word}(?:\s+{location_word}){{0,2}}"
        patterns = [
            rf"\bfrom\s+({location_phrase})",
            rf"\bto\s+({location_phrase})",
            rf"\b(?:visit|visiting)\s+({location_phrase})",
            rf"\b(?:destination(?:\s+is|\s+to|:)|hotels?\s+(?:in|at)|stay(?:ing)?\s+in|places?\s+in)\s+({location_phrase})",
        ]

        candidates: List[str] = []
        for pattern in patterns:
            candidates.extend(match.group(1) for match in re.finditer(pattern, lower))
        for match in re.finditer(rf"\bbetween\s+({location_phrase})\s+and\s+({location_phrase})", lower):
            candidates.extend([match.group(1), match.group(2)])
        for match in re.finditer(
            r"\b(?:cities?|cites|route|itinerary)\s*(?:as\s+follows?|as\s+follow|:)\s*:?\s*"
            r"([a-z\s,'-]+?)(?=\bon\b|\bstarting\b|\bfor\b|[.;]|\d|$)",
            lower,
        ):
            candidates.extend(
                part.strip()
                for part in re.split(r"\s*(?:,|\bto\b|\bthen\b)\s*", match.group(1))
                if part.strip()
            )

        bare = re.sub(r"[^a-zA-Z\s'-]", " ", message).strip()
        bare = re.sub(r"\s+", " ", bare)
        if bare and not re.search(r"\d", message) and len(bare.split()) == 1 and not any(word in lower for word in ["?", "flight", "hotel", "travel", "trip", "plan", "book"]):
            candidates.append(bare)

        unsupported: List[str] = []
        country_names = set(COUNTRY_ALIASES)
        for candidate in candidates:
            cleaned = re.sub(r"[^a-z\s'-]", " ", candidate.lower()).strip()
            cleaned = re.sub(r"\s+", " ", cleaned)
            raw_code = TravelNLU._city_code(cleaned)
            if raw_code in MOCK_AVAILABLE_CITY_CODES:
                continue
            words = cleaned.split()
            while words and words[-1] in LOCATION_CAPTURE_STOP_WORDS | NON_LOCATION_TERMS:
                words.pop()
            while words and words[0] in NON_LOCATION_TERMS:
                words.pop(0)
            cleaned = " ".join(words)
            if not cleaned or cleaned in NON_LOCATION_TERMS or cleaned in country_names or cleaned in KNOWN_AREA_PREFERENCES:
                continue

            code = TravelNLU._city_code(cleaned)
            if code in MOCK_AVAILABLE_CITY_CODES:
                continue
            if code and code not in MOCK_DIRECT_UNAVAILABLE_CITY_CODES:
                continue
            label = _city_label(code) if code else " ".join(word.capitalize() for word in cleaned.split())
            if label and label not in unsupported:
                unsupported.append(label)
        return unsupported

    @staticmethod
    def _context_city_for_general_answer(message: str, state: OrchestratorState) -> Optional[str]:
        """Resolve pronouns such as "there" from current message and recent history."""
        lower = message.lower()
        for alias, country in sorted(COUNTRY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(rf"\b{re.escape(alias)}\b", lower):
                return country
        for alias, value in sorted(CITY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(rf"\b{re.escape(alias)}\b", lower):
                return value["city"]

        params = state.get("travel_params", {}) if state else {}
        destination_code = params.get("destination") or params.get("hotel_city")
        if destination_code:
            return _city_label(destination_code)

        # Fall back to the most recent user-mentioned city/country. This makes
        # follow-ups like "tell me places there" work after "tell me about Singapore".
        for turn in reversed((state or {}).get("conversation_history", [])):
            if turn.get("role") != "user":
                continue
            content = turn.get("content", "").lower()
            for alias, country in sorted(COUNTRY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
                if re.search(rf"\b{re.escape(alias)}\b", content):
                    return country
            for alias, value in sorted(CITY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
                if re.search(rf"\b{re.escape(alias)}\b", content):
                    return value["city"]
        return None

    @staticmethod
    def _deterministic_general_answer(message: str, context_city: Optional[str] = None) -> str:
        lower = message.lower()
        destination = context_city or "your destination"
        for alias, country in sorted(COUNTRY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(rf"\b{re.escape(alias)}\b", lower):
                destination = country
                break
        if destination == "your destination":
            for alias, value in sorted(CITY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
                if re.search(rf"\b{re.escape(alias)}\b", lower):
                    destination = value["city"]
                    break

        wants_places = any(marker in lower for marker in ["places", "things to do", "attractions", "reputed", "higly", "highly", "famous", "must see", "must-see", "where to visit"])
        if wants_places:
            if destination == "Singapore":
                return (
                    "For Singapore, highly reputed places include Marina Bay Sands and the SkyPark area, Gardens by the Bay, Sentosa Island, "
                    "Jewel Changi Airport, Merlion Park, Singapore Botanic Gardens, Clarke Quay, Chinatown, Little India, Kampong Glam, "
                    "and the National Gallery Singapore. For a balanced first trip, combine Marina Bay + Gardens by the Bay on one day, "
                    "Sentosa on another, and heritage neighbourhoods with food streets in the evening."
                )
            if destination in {"Japan", "Tokyo"}:
                return (
                    "For Japan, strong first-trip places include Tokyo for food, shopping, and city energy; Kyoto for temples and traditional streets; "
                    "Osaka for nightlife and street food; Nara for heritage sites and deer parks; Hakone or Mount Fuji for scenery; and Hiroshima for history. "
                    "If you focus on Tokyo, add Shinjuku, Shibuya, Asakusa, Ueno, Ginza, teamLab, and a day trip to Hakone or Nikko."
                )
            if destination == "Paris":
                return (
                    "For Paris, highly reputed places include the Eiffel Tower, Louvre Museum, Musée d'Orsay, Notre-Dame area, Sainte-Chapelle, "
                    "Montmartre, Sacré-Cœur, Champs-Élysées, Arc de Triomphe, Le Marais, Luxembourg Gardens, and a Versailles day trip."
                )

        if "mock data" in lower or "available data" in lower:
            if "tokyo" in lower or "japan" in lower:
                return (
                    "Yes — the demo has Tokyo mock data. The richest routes are Singapore → Tokyo on 2025-06-15, "
                    "Singapore → Tokyo on 2026-07-25 or 2026-07-26, and Tokyo → Singapore on 2025-06-20 or 2026-07-31. "
                    "If you share one of those route/date combinations, I can show the flight and hotel options together."
                )
            return "Yes, the project uses stable mock flight and hotel data. Availability depends on the exact city pair and date in the demo dataset."

        asked_month = None
        for month_name in sorted(MONTHS, key=len, reverse=True):
            if re.search(rf"\b{re.escape(month_name)}\b", lower):
                asked_month = month_name
                break

        if destination == "Tokyo":
            if asked_month in {"jul", "july"}:
                return (
                    "July can be a good time to visit Tokyo if you are prepared for hot, humid summer weather. "
                    "It is better for festivals, shopping, food, museums, and evening city walks than for long midday outdoor plans. "
                    "Carry light clothes, sunscreen, water, and plan indoor breaks during peak heat."
                )
            if asked_month in {"jun", "june"}:
                return (
                    "June can be a lovely time to visit Tokyo if you are comfortable with warm, humid weather. "
                    "It is usually less peak than cherry blossom season, and it is good for food, shopping, museums, and city walks. "
                    "Pack a light rain jacket because early summer showers are possible."
                )
            return (
                "Tokyo is a strong year-round city destination. The best experience depends on whether you prefer cherry blossoms, festivals, autumn colours, or cooler weather. "
                "Share your month and travel style and I can narrow it down."
            )

        city_notes = {
            "Singapore": (
                "Singapore is usually warm and humid year-round, so it works well for city breaks, food, shopping, and business travel. "
                "Plan indoor breaks during the hottest hours, keep a compact umbrella handy, and check local events or public holidays before locking dates."
            ),
            "Dubai": (
                "Dubai is best when the weather is milder, especially for outdoor sightseeing. "
                "For summer travel, plan more indoor activities and check event calendars before booking."
            ),
            "Paris": (
                "Paris is great for museums, food, neighbourhood walks, and culture-heavy trips. "
                "Check school holidays, major events, and accommodation demand before finalising dates."
            ),
        }
        if destination in city_notes:
            return city_notes[destination]

        return (
            f"For {destination}, I would check four things before finalising: the season and expected weather, local events or holidays, "
            "visa or entry rules, and hotel demand around your dates. Once those look good, share your departure city and dates and I can search mock options."
        )


def _city_label(code: Optional[str]) -> str:
    if not code:
        return "your destination"
    for value in CITY_ALIASES.values():
        if value["code"] == code:
            return value["city"]
    return code


def _ensure_session(state: OrchestratorState) -> str:
    session_id = state.get("session_id")
    if session_id:
        return session_id
    return str(uuid4())


def _enum_value(value: Any) -> Any:
    """Return the raw value for enum-like fields used in A2A metadata."""
    return getattr(value, "value", value)


def _a2a_message(
    *,
    direction: str,
    node: str,
    agent_id: str,
    task_id: str,
    task_type: str,
    trace_id: str,
    payload: Any,
) -> Dict[str, Any]:
    """Create a serializable A2A audit entry for orchestrator state."""
    body = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
    return {
        "direction": direction,
        "node": node,
        "agent_id": agent_id,
        "task_id": task_id,
        "task_type": task_type,
        "trace_id": trace_id,
        "payload": body,
    }


def _append_a2a_exchange(
    state: OrchestratorState,
    request: FlightTaskRequest | HotelTaskRequest,
    response: FlightTaskResponse | HotelTaskResponse,
    node: str,
) -> List[Dict[str, Any]]:
    """Append one request/response A2A pair to the conversation audit trail."""
    messages = list(state.get("a2a_messages", []))
    request_task_type = str(_enum_value(request.task_type))
    response_task_type = request_task_type
    trace_id = request.metadata.trace_id
    messages.append(
        _a2a_message(
            direction="orchestrator_to_sub_agent",
            node=node,
            agent_id=request.metadata.receiver_agent_id,
            task_id=request.task_id,
            task_type=request_task_type,
            trace_id=trace_id,
            payload=request,
        )
    )
    messages.append(
        _a2a_message(
            direction="sub_agent_to_orchestrator",
            node=node,
            agent_id=response.metadata.agent_id,
            task_id=response.task_id,
            task_type=response_task_type,
            trace_id=response.metadata.trace_id,
            payload=response,
        )
    )
    return messages


def _merge_new_a2a_messages(base: List[Dict[str, Any]], candidates: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Merge child graph A2A logs without duplicating the shared base prefix."""
    merged = list(base)
    seen = {
        (
            item.get("direction"),
            item.get("task_id"),
            item.get("trace_id"),
            item.get("agent_id"),
        )
        for item in merged
    }
    for messages in candidates:
        for item in messages[len(base):]:
            key = (
                item.get("direction"),
                item.get("task_id"),
                item.get("trace_id"),
                item.get("agent_id"),
            )
            if key not in seen:
                merged.append(item)
                seen.add(key)
    return merged


class FriendlyAssistantOrchestrator:
    """User-facing conversational orchestrator for travel planning."""

    def __init__(self, flight_agent: Optional[FlightBookingAgent] = None, hotel_agent: Optional[HotelBookingAgent] = None) -> None:
        self.flight_agent = flight_agent or FlightBookingAgent()
        self.hotel_agent = hotel_agent or HotelBookingAgent()
        self.nlu = TravelNLU()
        self.graph = self._build_graph()

    def chat(self, message: str, state: Optional[OrchestratorState] = None) -> OrchestratorState:
        """Process one user turn and return the updated conversation state."""
        initial_state: OrchestratorState = state.copy() if state else {}
        initial_state["current_message"] = message
        initial_state.setdefault("conversation_history", [])
        initial_state.setdefault("travel_params", {})
        initial_state.setdefault("pending_clarifications", [])
        initial_state["active_task_ids"] = []
        initial_state["debug_trace"] = []
        initial_state.setdefault("last_task_ids", [])
        initial_state.setdefault("a2a_messages", [])
        initial_state.setdefault("final_aggregated_options", {})
        initial_state.setdefault("hotel_dates_inferred", False)
        initial_state.setdefault("destination_changed", False)
        initial_state.setdefault("constraints_changed", False)
        initial_state.setdefault("awaiting_hotel_offer", False)
        initial_state.setdefault("last_completed_params", {})
        initial_state.setdefault("conversation_focus", "")
        initial_state.setdefault("multi_city_plan", {})
        initial_state.setdefault("last_successful_multi_city_plan", {})
        initial_state.setdefault("planner_snapshot", {})
        initial_state.setdefault("planner_revision", 0)
        initial_state.setdefault("planner_confidence", 0.0)
        initial_state.setdefault("planner_decision", "not_started")
        initial_state.setdefault("llm_diagnostics", {})
        initial_state["session_id"] = _ensure_session(initial_state)
        return self.graph.invoke(initial_state)

    def _build_graph(self):
        graph = StateGraph(OrchestratorState)
        graph.add_node("input_understanding", self._input_understanding_node)
        graph.add_node("state_update", self._state_update_node)
        graph.add_node("clarification", self._clarification_node)
        graph.add_node("flight_delegation", self._flight_delegation_node)
        graph.add_node("hotel_delegation", self._hotel_delegation_node)
        graph.add_node("parallel_a2a_delegation", self._parallel_a2a_delegation_node)
        graph.add_node("multi_city_delegation", self._multi_city_delegation_node)
        graph.add_node("aggregation", self._aggregation_node)
        graph.add_node("user_response_formatting", self._user_response_formatting_node)

        graph.add_edge(START, "input_understanding")
        graph.add_edge("input_understanding", "state_update")
        graph.add_edge("state_update", "clarification")
        graph.add_conditional_edges(
            "clarification",
            self._route_after_clarification,
            {
                "respond": "user_response_formatting",
                "general": "user_response_formatting",
                "flight": "flight_delegation",
                "hotel": "hotel_delegation",
                "both": "parallel_a2a_delegation",
                "multi_city": "multi_city_delegation",
            },
        )
        graph.add_conditional_edges(
            "flight_delegation",
            self._route_after_flight,
            {"hotel": "hotel_delegation", "aggregate": "aggregation"},
        )
        graph.add_edge("hotel_delegation", "aggregation")
        graph.add_edge("parallel_a2a_delegation", "aggregation")
        graph.add_edge("multi_city_delegation", "user_response_formatting")
        graph.add_edge("aggregation", "user_response_formatting")
        graph.add_edge("user_response_formatting", END)
        return graph.compile()

    def _input_understanding_node(self, state: OrchestratorState) -> OrchestratorState:
        message = state.get("current_message", "")
        extracted = self.nlu.extract(message, state)
        history = list(state.get("conversation_history", []))
        history.append({"role": "user", "content": message})
        return {
            **state,
            "debug_trace": list(state.get("debug_trace", [])) + ["input_understanding"],
            "conversation_history": history,
            "extracted": {"intent": extracted.intent, **extracted.entities},
            "planner_snapshot": {
                "intent": extracted.intent,
                "entities": {k: v for k, v in extracted.entities.items() if not k.startswith("_")},
                "source": extracted.entities.get("_llm_provider", "heuristic"),
                "raw_text": extracted.raw_text,
            },
            "planner_decision": extracted.intent,
            "llm_diagnostics": {
                "provider": extracted.entities.get("_llm_provider", "heuristic"),
                "used": bool(extracted.entities.get("_llm_used", False)),
                "latency_ms": extracted.entities.get("_llm_latency_ms", 0),
                "called": bool(extracted.entities.get("_llm_called", False)),
                "error": extracted.entities.get("_llm_error"),
            },
            "user_intent": extracted.intent,
            "general_question": extracted.general_question,
            "destination_changed": extracted.destination_changed,
            "message_to_show_user": "",
        }

    def _state_update_node(self, state: OrchestratorState) -> OrchestratorState:
        extracted = state.get("extracted", {})

        # General travel questions should not mutate the booking context. This
        # avoids a question like "Is June good for Singapore?" changing a Tokyo
        # itinerary that the user was building.
        if state.get("general_question"):
            return {
                **state,
                "debug_trace": list(state.get("debug_trace", [])) + ["state_update"],
                "constraints_changed": False,
            }

        if state.get("user_intent") == "out_of_scope":
            return {
                **state,
                "debug_trace": list(state.get("debug_trace", [])) + ["state_update"],
                "constraints_changed": False,
            }

        previous_params = dict(state.get("travel_params", {}))
        params = dict(previous_params)
        destination_changed = bool(state.get("destination_changed", False))
        constraints_changed = False
        pending_before = bool(state.get("pending_clarifications"))
        intent = state.get("user_intent", "ambiguous")

        explicit_flight = bool(extracted.get("_explicit_needs_flight"))
        explicit_hotel = bool(extracted.get("_explicit_needs_hotel"))
        bare_destination_only = bool(extracted.get("_bare_destination_only"))
        force_hotel_followup = bool(extracted.get("_force_hotel_followup"))

        updates: OrchestratorState = {}

        if extracted.get("_fresh_plan"):
            params = {
                "cabin_class": previous_params.get("cabin_class", CabinClass.ECONOMY.value),
                "room_type": previous_params.get("room_type", RoomType.STANDARD.value),
            }
            updates.update({
                "flight_response": None,
                "hotel_response": None,
                "final_aggregated_options": {},
                "hotel_dates_inferred": False,
                "awaiting_hotel_offer": False,
                "multi_city_plan": {},
                "last_successful_multi_city_plan": {},
            })
            pending_before = False
            constraints_changed = True

        if extracted.get("multi_city_plan"):
            updates.update({
                "multi_city_plan": extracted["multi_city_plan"],
                "planner_revision": int(state.get("planner_revision", 0)) + 1,
                "planner_confidence": 0.95 if extracted.get("_llm_used") else 0.85,
                "planner_decision": "multi_city_plan_ready",
                "flight_response": None,
                "hotel_response": None,
                "final_aggregated_options": {},
                "hotel_dates_inferred": False,
            })
            constraints_changed = True

        if intent == "change_dates":
            # Keep the current travel frame intact. A later reply like
            # "departure is same, change return date to 2026-07-28" needs the
            # old departure date. Clear only stale rendered results.
            updates.update({"flight_response": None, "hotel_response": None, "final_aggregated_options": {}, "hotel_dates_inferred": False})
            constraints_changed = True

        if destination_changed:
            previous_needs_flight = previous_params.get("needs_flight")
            previous_needs_hotel = previous_params.get("needs_hotel")
            for key in ["destination", "check_in_date", "check_out_date", "location_preference"]:
                params.pop(key, None)
            if previous_needs_flight:
                params["needs_flight"] = previous_needs_flight
            if previous_needs_hotel:
                params["needs_hotel"] = previous_needs_hotel
            updates.update({"flight_response": None, "hotel_response": None, "final_aggregated_options": {}, "hotel_dates_inferred": False})

        # A single city name outside an active clarification should start a fresh
        # planning question, not re-run stale searches from the previous turn.
        if bare_destination_only and not pending_before and not destination_changed:
            params = {
                "destination": extracted.get("destination"),
                "cabin_class": previous_params.get("cabin_class", CabinClass.ECONOMY.value),
                "room_type": previous_params.get("room_type", RoomType.STANDARD.value),
            }
            updates.update({"flight_response": None, "hotel_response": None, "final_aggregated_options": {}, "hotel_dates_inferred": False})
            constraints_changed = True
        else:
            merge_keys = [
                "origin",
                "destination",
                "departure_date",
                "return_date",
                "passengers",
                "cabin_class",
                "guests",
                "room_type",
                "location_preference",
                "check_in_date",
                "check_out_date",
                "stay_duration_days",
                "one_way",
                "return_destination",
            ]
            old_departure = previous_params.get("departure_date")
            for key in merge_keys:
                if key in extracted:
                    old_value = params.get(key)
                    new_value = extracted[key]
                    if old_value != new_value:
                        constraints_changed = True
                    if new_value is None:
                        params.pop(key, None)
                    else:
                        params[key] = new_value

            # A new explicit city-pair normally means a normal round trip back
            # to origin unless the user says "returning/back to <third city>".
            # This prevents stale open-jaw memory from contaminating later trips.
            if ("origin" in extracted or "destination" in extracted) and "return_destination" not in extracted:
                params.pop("return_destination", None)
            if "return_date" in extracted:
                params.pop("_hotel_add_on_after_one_way", None)

            # If the user supplies a new departure date without a new return/check-out
            # date, do not keep stale return/hotel dates from an older trip.
            if (
                "departure_date" in extracted
                and extracted.get("departure_date") != old_departure
                and "return_date" not in extracted
                and "check_out_date" not in extracted
            ):
                stale_keys = ["return_date", "check_out_date"]
                if "check_in_date" not in extracted:
                    stale_keys.append("check_in_date")
                for stale_key in stale_keys:
                    params.pop(stale_key, None)
                updates.update({"hotel_response": None, "final_aggregated_options": {}, "hotel_dates_inferred": False})

            if (
                "departure_date" in extracted
                and params.get("stay_duration_days")
                and params.get("needs_hotel")
                and ("date_precision" in state.get("pending_clarifications", []) or not params.get("check_out_date"))
            ):
                try:
                    exact_check_in = date.fromisoformat(params["departure_date"])
                    exact_check_out = exact_check_in + timedelta(days=int(params["stay_duration_days"]))
                    params["check_in_date"] = exact_check_in.isoformat()
                    params["check_out_date"] = exact_check_out.isoformat()
                    updates["hotel_dates_inferred"] = False
                except (TypeError, ValueError):
                    pass

            if explicit_flight and explicit_hotel:
                params["needs_flight"] = True
                params["needs_hotel"] = True
                if not params.get("departure_date") and params.get("check_in_date"):
                    params["departure_date"] = params["check_in_date"]
                    constraints_changed = True
                if "check_in_date" not in extracted:
                    params.pop("check_in_date", None)
                    params.pop("check_out_date", None)
                updates.update({"flight_response": None, "hotel_response": None, "final_aggregated_options": {}, "hotel_dates_inferred": False})
            elif explicit_flight and not explicit_hotel:
                params["needs_flight"] = True
                # A direct new flight request should clear stale hotel scope,
                # but a follow-up like "what about flight?" during an active
                # package conversation should not destroy the package context.
                followup_flight_question = bool(re.search(r"\b(what about|flight details|show.*flight|where.*flight)\b", state.get("current_message", "").lower()))
                if not (pending_before and previous_params.get("needs_hotel") and followup_flight_question):
                    params.pop("needs_hotel", None)
                    params.pop("check_in_date", None)
                    params.pop("check_out_date", None)
                    updates.update({"hotel_response": None, "final_aggregated_options": {}, "hotel_dates_inferred": False})
            elif explicit_hotel and not explicit_flight:
                params["needs_hotel"] = True
                if extracted.get("_onward_hotel_followup"):
                    params.pop("needs_flight", None)
                    params.pop("origin", None)
                    params.pop("return_date", None)
                    params.pop("return_destination", None)
                    updates.update({"flight_response": None, "final_aggregated_options": {}, "hotel_dates_inferred": False})
                if force_hotel_followup:
                    updates.update({"flight_response": None, "final_aggregated_options": {}})
                    if not previous_params.get("return_date"):
                        params["_hotel_add_on_after_one_way"] = True
                        if params.get("departure_date") and not params.get("check_in_date"):
                            params["check_in_date"] = params["departure_date"]
                            updates["hotel_dates_inferred"] = False
                # Critical multi-turn rule: when the assistant previously asked
                # for hotel dates in a package request, a reply such as
                # "check in ... check out ..." supplies only the missing hotel
                # slot. It must not remove the already-requested flight search.
                keep_existing_flight_scope = bool(
                    previous_params.get("needs_flight")
                    and not extracted.get("_onward_hotel_followup")
                    and not extracted.get("_hotel_only")
                    and (pending_before or "origin" in params or "departure_date" in params)
                )
                if keep_existing_flight_scope:
                    params["needs_flight"] = True
                else:
                    params.pop("needs_flight", None)
                    params.pop("_hotel_add_on_after_one_way", None)
                    if not force_hotel_followup:
                        updates.update({"flight_response": None, "final_aggregated_options": {}})
            elif intent == "travel_planning" and not pending_before and not destination_changed:
                params.pop("needs_flight", None)
                params.pop("needs_hotel", None)
                updates.update({"flight_response": None, "hotel_response": None, "final_aggregated_options": {}, "hotel_dates_inferred": False})

        if params.get("origin") and params.get("destination") and params.get("origin") == params.get("destination"):
            # When destination changes to the old origin, the previous origin is no longer valid.
            # Clear it and ask naturally instead of creating an invalid A2A request.
            params.pop("origin", None)
            constraints_changed = True

        if "check_in_date" in extracted or "check_out_date" in extracted:
            updates["hotel_dates_inferred"] = False

        if params.get("passengers") and (not params.get("guests") or extracted.get("_change_passengers")):
            params["guests"] = params["passengers"]
        params.setdefault("cabin_class", CabinClass.ECONOMY.value)
        params.setdefault("room_type", RoomType.STANDARD.value)

        # Critical reset rule: a fresh normal flight/hotel request must not be
        # hijacked by an old multi-city plan. Earlier versions kept
        # state["multi_city_plan"] forever, and clarification_node routed every
        # later request back to multi_city.
        if (
            not extracted.get("multi_city_plan")
            and intent in {"flight_search", "hotel_search", "package_search", "travel_planning"}
            and ("origin" in extracted or "destination" in extracted or "departure_date" in extracted or explicit_flight or explicit_hotel)
        ):
            updates["multi_city_plan"] = {}

        if constraints_changed and not updates.get("final_aggregated_options"):
            updates.setdefault("final_aggregated_options", {})

        return {
            **state,
            **updates,
            "debug_trace": list(state.get("debug_trace", [])) + ["state_update"],
            "travel_params": params,
            "constraints_changed": constraints_changed,
        }

    def _clarification_node(self, state: OrchestratorState) -> OrchestratorState:
        intent = state.get("user_intent", "ambiguous")
        params = state.get("travel_params", {})
        extracted = state.get("extracted", {})
        pending: List[str] = []
        trace = list(state.get("debug_trace", [])) + ["clarification"]

        if extracted.get("_planner_message"):
            return {
                **state,
                "debug_trace": trace,
                "route": "respond",
                "message_to_show_user": extracted["_planner_message"],
                "pending_clarifications": ["itinerary_confirmation"],
            }

        unsupported_locations = extracted.get("_unsupported_locations") or []
        if unsupported_locations:
            return {
                **state,
                "debug_trace": trace,
                "route": "respond",
                "message_to_show_user": self._unsupported_location_message(unsupported_locations),
                "pending_clarifications": [],
                "awaiting_hotel_offer": False,
                "flight_response": None,
                "hotel_response": None,
                "final_aggregated_options": {},
            }

        if state.get("general_question"):
            answer_prompt = extracted.get("_general_question_override") or state.get("current_message", "")
            answer = self.nlu.answer_general_question(answer_prompt, state)
            return {**state, "debug_trace": trace, "route": "general", "message_to_show_user": answer, "pending_clarifications": []}

        if intent == "out_of_scope":
            return {
                **state,
                "debug_trace": trace,
                "route": "respond",
                "message_to_show_user": OUT_OF_SCOPE_MESSAGE,
                "pending_clarifications": [],
                "awaiting_hotel_offer": False,
            }

        if intent == "decline_hotel":
            return {
                **state,
                "debug_trace": trace,
                "route": "respond",
                "awaiting_hotel_offer": False,
                "message_to_show_user": "No problem — I’ll keep it to flights for now. Tell me whenever you want to add a hotel.",
            }

        if intent == "multi_city_package" or state.get("multi_city_plan"):
            plan = state.get("multi_city_plan", {})
            if plan.get("planner_message"):
                return {
                    **state,
                    "debug_trace": trace,
                    "route": "respond",
                    "pending_clarifications": [plan.get("missing", "planner_confirmation")],
                    "message_to_show_user": plan["planner_message"],
                }
            if plan.get("missing") == "date_points" or not plan.get("legs"):
                return {
                    **state,
                    "debug_trace": trace,
                    "route": "respond",
                    "pending_clarifications": ["multi_city_dates"],
                    "message_to_show_user": "I understand this as a multi-city trip. Please share the travel date for each leg, or tell me the start date and how long you want to stay in each city.",
                }
            return {
                **state,
                "debug_trace": trace,
                "route": "multi_city",
                "pending_clarifications": [],
            }

        if intent == "change_dates":
            destination_label = _city_label(params.get("destination"))
            origin_label = _city_label(params.get("origin"))
            scope = "flights and hotels" if params.get("needs_flight") and params.get("needs_hotel") else "the search"
            return {
                **state,
                "debug_trace": trace,
                "route": "respond",
                "message_to_show_user": (
                    f"Sure — I’ll keep {origin_label} to {destination_label} for {int(params.get('passengers', params.get('guests', 1)))} traveller(s) "
                    f"and update the dates for {scope}. What new departure date and return/check-out date should I use?"
                ),
                "pending_clarifications": ["date_change"],
            }

        needs_flight = bool(params.get("needs_flight")) or intent in {"flight_search", "package_search"}
        needs_hotel = bool(params.get("needs_hotel")) or intent in {"hotel_search", "package_search"}

        unavailable_message = self._mock_data_unavailable_message(params, needs_flight=needs_flight, needs_hotel=needs_hotel)
        if unavailable_message:
            return {
                **state,
                "debug_trace": trace,
                "route": "respond",
                "message_to_show_user": unavailable_message,
                "pending_clarifications": [],
                "awaiting_hotel_offer": False,
                "flight_response": None,
                "hotel_response": None,
                "final_aggregated_options": {},
            }

        if "date_precision" in state.get("pending_clarifications", []):
            lower_message = state.get("current_message", "").lower()
            date_confirmed = "departure_date" in extracted or bool(
                re.search(r"\b(?:yes|yep|yeah|correct|confirm|confirmed|use it|that works|same date)\b", lower_message)
            )
            if not date_confirmed:
                pending.append("date_precision")

        if (
            "travellers" in state.get("pending_clarifications", [])
            and (needs_flight or needs_hotel)
            and not params.get("passengers")
            and not params.get("guests")
        ):
            pending.append("travellers")

        invalid_date_message = self._validate_date_order(params)
        if invalid_date_message:
            return {
                **state,
                "debug_trace": trace,
                "route": "respond",
                "message_to_show_user": invalid_date_message,
                "pending_clarifications": ["date_order"],
            }

        if extracted.get("_date_year_missing"):
            missing_bits: List[str] = []
            if needs_flight and not params.get("origin"):
                missing_bits.append("departure city")
            if needs_hotel and not params.get("return_date") and not params.get("check_out_date"):
                missing_bits.append("return/check-out date")
            extra = f" Also share the {', '.join(missing_bits)}." if missing_bits else ""
            return {
                **state,
                "debug_trace": trace,
                "route": "respond",
                "message_to_show_user": "Please confirm the full date with year in YYYY-MM-DD format so I do not search the wrong trip." + extra,
                "pending_clarifications": ["date_year"] + missing_bits,
            }

        if extracted.get("_date_is_approximate") and (needs_flight or needs_hotel):
            pending_precision = ["date_precision"]
            if not params.get("passengers") and not params.get("guests"):
                pending_precision.append("travellers")
            tentative_date = params.get("departure_date") or params.get("check_in_date")
            tentative_text = f" I interpreted the date as {tentative_date}." if tentative_date else ""
            traveller_text = " Also tell me how many travellers/guests to use." if "travellers" in pending_precision else ""
            return {
                **state,
                "debug_trace": trace,
                "route": "respond",
                "message_to_show_user": (
                    "I can help with the flight and hotel, but because you said the date is around that time, "
                    "please confirm the exact flight date and hotel check-in date in YYYY-MM-DD format."
                    f"{tentative_text}{traveller_text}"
                ),
                "pending_clarifications": pending_precision,
                "awaiting_hotel_offer": False,
            }

        continuing_pending_flow = bool(state.get("pending_clarifications")) and (
            bool(params.get("destination")) or bool(params.get("origin")) or bool(params.get("departure_date"))
        )
        if intent == "ambiguous" and not continuing_pending_flow:
            return {
                **state,
                "debug_trace": trace,
                "route": "respond",
                "message_to_show_user": "I can help with flights, hotels, or both. Where are you travelling, and what dates should I use?",
                "pending_clarifications": ["travel_scope", "destination", "dates"],
            }

        if intent == "travel_planning" and not needs_flight and not needs_hotel:
            message = self._build_planning_clarification(params=params, extracted=extracted)
            return {
                **state,
                "debug_trace": trace,
                "route": "respond",
                "message_to_show_user": message,
                "pending_clarifications": ["travel_dates", "travellers", "booking_scope"],
            }

        if needs_flight:
            if not params.get("origin"):
                pending.append("origin")
            if not params.get("destination"):
                pending.append("destination")
            if not params.get("departure_date"):
                pending.append("departure_date")
            if not params.get("passengers") and "travellers" not in pending:
                pending.append("travellers")

        if needs_hotel:
            if not params.get("destination"):
                pending.append("destination")
            allow_hotel_date_inference = bool(params.get("needs_flight")) or bool(state.get("awaiting_hotel_offer")) or intent == "package_search"
            self._infer_hotel_dates_if_possible(state, allow_existing_flight_dates=allow_hotel_date_inference)
            params = state.get("travel_params", {})
            if not params.get("check_in_date") or not params.get("check_out_date"):
                pending.append("hotel_dates")
            if not params.get("guests") and not params.get("passengers") and "travellers" not in pending:
                pending.append("travellers")
            if not params.get("guests") and "travellers" not in pending:
                params["guests"] = params.get("passengers", 1)

        if pending:
            return {
                **state,
                "debug_trace": trace,
                "route": "respond",
                "pending_clarifications": pending,
                "message_to_show_user": self._build_clarification_message(pending, params, needs_flight, needs_hotel),
            }

        route: Route
        if needs_flight and needs_hotel:
            route = "both"
        elif needs_flight:
            route = "flight"
        elif needs_hotel:
            route = "hotel"
        else:
            route = "respond"

        return {
            **state,
            "debug_trace": trace,
            "route": route,
            "should_delegate_flight": route in {"flight", "both"},
            "should_delegate_hotel": route in {"hotel", "both"},
            "pending_clarifications": [],
        }

    @staticmethod
    def _mock_data_unavailable_message(params: Dict[str, Any], needs_flight: bool, needs_hotel: bool) -> Optional[str]:
        """Return a friendly no-mock-data message for recognized unsupported cities."""
        unavailable: List[str] = []
        if needs_flight:
            for key in ["origin", "destination"]:
                code = params.get(key)
                if code in MOCK_DIRECT_UNAVAILABLE_CITY_CODES and code not in unavailable:
                    unavailable.append(code)
        if needs_hotel:
            code = params.get("destination")
            if code in MOCK_DIRECT_UNAVAILABLE_CITY_CODES and code not in unavailable:
                unavailable.append(code)
        if not unavailable:
            return None

        labels = [_city_label(code) for code in unavailable]
        if len(labels) == 1:
            unavailable_text = labels[0]
        else:
            unavailable_text = ", ".join(labels[:-1]) + f" and {labels[-1]}"
        service_bits = []
        if needs_flight:
            service_bits.append("flights")
        if needs_hotel:
            service_bits.append("hotels")
        service_text = " and ".join(service_bits) if service_bits else "travel searches"
        return (
            f"I don't have mock data for {unavailable_text}, so I can't search {service_text} for that destination in this demo. "
            f"Try with {MOCK_CITY_SUGGESTIONS} or another city from the mock data."
        )

    @staticmethod
    def _unsupported_location_message(locations: List[str]) -> str:
        """Format a deterministic unsupported-location response."""
        unique_locations = list(dict.fromkeys(str(location) for location in locations if location))
        if len(unique_locations) == 1:
            location_text = unique_locations[0]
        else:
            location_text = ", ".join(unique_locations[:-1]) + f" and {unique_locations[-1]}"
        return (
            f"I don't have mock data for {location_text}, so I can't search that location in this demo. "
            f"Try with {MOCK_CITY_SUGGESTIONS} or another city from the mock data."
        )

    @staticmethod
    def _validate_date_order(params: Dict[str, Any]) -> Optional[str]:
        """Block impossible date ranges before calling sub-agents."""
        try:
            dep = date.fromisoformat(params["departure_date"]) if params.get("departure_date") else None
            ret = date.fromisoformat(params["return_date"]) if params.get("return_date") else None
            check_in = date.fromisoformat(params["check_in_date"]) if params.get("check_in_date") else None
            check_out = date.fromisoformat(params["check_out_date"]) if params.get("check_out_date") else None
        except (TypeError, ValueError):
            return "One of the dates looks invalid. Please share dates in YYYY-MM-DD format."
        if dep and ret and ret < dep:
            return "The return date is before the departure date. Please confirm the correct return date so I can search the trip safely."
        if check_in and check_out and check_out <= check_in:
            return "The hotel check-out date must be after the check-in date. Please confirm the correct hotel dates."
        return None

    def _infer_hotel_dates_if_possible(self, state: OrchestratorState, allow_existing_flight_dates: bool = True) -> None:
        params = state.get("travel_params", {})
        if params.get("check_in_date") and params.get("check_out_date"):
            return
        if not allow_existing_flight_dates:
            return
        if params.get("departure_date") and params.get("return_date"):
            params["check_in_date"] = params["departure_date"]
            params["check_out_date"] = params["return_date"]
            state["hotel_dates_inferred"] = True

    @staticmethod
    def _build_planning_clarification(params: Dict[str, Any], extracted: Dict[str, Any]) -> str:
        destination_label = _city_label(params.get("destination"))
        if extracted.get("_date_year_missing"):
            missing = ["the full date with year"]
            if not params.get("passengers") and not params.get("guests"):
                missing.append("how many travellers are going")
            if not params.get("needs_flight") and not params.get("needs_hotel"):
                missing.append("whether you want flights, hotels, or both")
            return f"I have {destination_label} and a date. Please confirm " + ", ".join(missing) + "."
        if params.get("destination") and not params.get("origin") and not params.get("departure_date"):
            return (
                f"Great choice — {destination_label}! What travel dates should I use, "
                "how many travellers are going, and would you like flights, hotels, or both?"
            )
        return (
            f"I have {destination_label} so far. Please tell me the departure city, full travel dates, "
            "number of travellers, and whether you want flights, hotels, or both."
        )

    @staticmethod
    def _build_clarification_message(pending: List[str], params: Dict[str, Any], needs_flight: bool, needs_hotel: bool) -> str:
        destination_label = _city_label(params.get("destination"))
        if "date_precision" in pending:
            tentative = params.get("departure_date") or params.get("check_in_date")
            tentative_text = f" I currently have {tentative}." if tentative else ""
            if "travellers" in pending:
                return (
                    "Please confirm the exact flight/check-in date in YYYY-MM-DD format and tell me how many "
                    f"travellers/guests to use.{tentative_text}"
                )
            return f"Please confirm the exact flight/check-in date in YYYY-MM-DD format.{tentative_text}"
        if pending == ["travel_dates", "travellers", "booking_scope"] or set(pending) >= {"travel_dates", "travellers"}:
            return f"Great choice — {destination_label}! What travel dates should I use, how many travellers are going, and do you need flights, hotels, or both?"
        if "departure_date" in pending and "travellers" in pending and "origin" in pending:
            return f"Where will you be flying from, what departure date should I search for {destination_label}, and how many travellers are going?"
        if "departure_date" in pending and "travellers" in pending:
            return "What departure date should I use, and how many travellers are going? Please share the date in YYYY-MM-DD format if possible."
        if "hotel_dates" in pending and "travellers" in pending:
            if params.get("check_in_date") or params.get("departure_date"):
                check_in = params.get("check_in_date") or params.get("departure_date")
                return f"I can use {check_in} as the hotel check-in date. What check-out date or number of nights should I use, and how many travellers/guests are going?"
            return "What check-in and check-out dates should I use for the hotel, and how many travellers/guests are going?"
        if "origin" in pending and "travellers" in pending:
            return "Which city will you be flying from, and how many travellers are going?"
        if "travellers" in pending:
            return "How many travellers/guests should I use for this trip?"
        if "origin" in pending and "departure_date" in pending:
            return f"Sure — I can help with that. Where will you be flying from, and what date should I search for {destination_label}?"
        if "origin" in pending and "hotel_dates" in pending:
            return "Which city will you be flying from, and what return/check-out date should I use for the hotel?"
        if "origin" in pending:
            return "Which city will you be flying from?"
        if "destination" in pending:
            return "Which destination should I use for the search?"
        if "departure_date" in pending:
            return "What departure date should I use? Please share it in YYYY-MM-DD format if possible."
        if "hotel_dates" in pending:
            if params.get("check_in_date"):
                return f"I can use {params['check_in_date']} as the hotel check-in date from your flight. What check-out date or number of nights should I use?"
            return "What check-in and check-out dates should I use for the hotel?"
        if needs_hotel and not needs_flight:
            return "I can search hotels for you. What city and dates should I use?"
        return "Could you share the missing travel details so I can search the best options?"

    def _route_after_clarification(self, state: OrchestratorState) -> Route:
        return state.get("route", "respond")

    def _flight_delegation_node(self, state: OrchestratorState) -> OrchestratorState:
        params = state.get("travel_params", {})
        task_ids = list(state.get("active_task_ids", []))
        try:
            request = FlightTaskRequest(
                session_id=state["session_id"],
                parameters=FlightSearchParameters(
                    origin=params["origin"],
                    destination=params["destination"],
                    departure_date=params["departure_date"],
                    return_date=params.get("return_date"),
                    return_destination=params.get("return_destination"),
                    passengers=int(params.get("passengers", 1)),
                    cabin_class=params.get("cabin_class", CabinClass.ECONOMY.value),
                ),
            )
            task_ids.append(request.task_id)
            response = self.flight_agent.invoke(request)
            a2a_messages = _append_a2a_exchange(state, request, response, "flight_delegation")
            return {
                **state,
                "debug_trace": list(state.get("debug_trace", [])) + ["flight_delegation"],
                "flight_response": response,
                "active_task_ids": task_ids,
                "last_task_ids": task_ids,
                "a2a_messages": a2a_messages,
            }
        except (ValidationError, KeyError, ValueError) as exc:
            safe_response = FlightTaskResponse.failed(task_id=str(uuid4()), error=f"Flight search could not be completed: {exc}")
            return {**state, "debug_trace": list(state.get("debug_trace", [])) + ["flight_delegation"], "flight_response": safe_response}

    def _route_after_flight(self, state: OrchestratorState) -> Literal["hotel", "aggregate"]:
        return "hotel" if state.get("should_delegate_hotel") else "aggregate"

    def _hotel_delegation_node(self, state: OrchestratorState) -> OrchestratorState:
        # Date inference happens in the clarification/readiness node, where the
        # orchestrator knows whether this is a package search or a hotel follow-up.
        params = state.get("travel_params", {})
        task_ids = list(state.get("active_task_ids", []))
        try:
            request = HotelTaskRequest(
                session_id=state["session_id"],
                parameters=HotelSearchParameters(
                    destination=params["destination"],
                    check_in_date=params["check_in_date"],
                    check_out_date=params["check_out_date"],
                    guests=int(params.get("guests", params.get("passengers", 1))),
                    room_type=params.get("room_type", RoomType.STANDARD.value),
                    location_preference=params.get("location_preference"),
                ),
            )
            task_ids.append(request.task_id)
            response = self.hotel_agent.invoke(request)
            a2a_messages = _append_a2a_exchange(state, request, response, "hotel_delegation")
            return {
                **state,
                "debug_trace": list(state.get("debug_trace", [])) + ["hotel_delegation"],
                "hotel_response": response,
                "active_task_ids": task_ids,
                "last_task_ids": task_ids,
                "a2a_messages": a2a_messages,
            }
        except (ValidationError, KeyError, ValueError) as exc:
            safe_response = HotelTaskResponse.failed(task_id=str(uuid4()), error=f"Hotel search could not be completed: {exc}")
            return {**state, "debug_trace": list(state.get("debug_trace", [])) + ["hotel_delegation"], "hotel_response": safe_response}

    def _parallel_a2a_delegation_node(self, state: OrchestratorState) -> OrchestratorState:
        """Run flight and hotel A2A tasks concurrently for package requests.

        The graph remains explicit and inspectable, while package searches avoid
        artificial sequential dependence. Sub-agents are stateless, so parallel
        execution is safe and deterministic.
        """
        base_a2a_messages = list(state.get("a2a_messages", []))
        base_state = {**state, "active_task_ids": list(state.get("active_task_ids", [])), "a2a_messages": base_a2a_messages}
        with ThreadPoolExecutor(max_workers=2) as executor:
            flight_future = executor.submit(self._flight_delegation_node, base_state)
            hotel_future = executor.submit(self._hotel_delegation_node, base_state)
            flight_state = flight_future.result()
            hotel_state = hotel_future.result()

        task_ids = []
        for candidate in [flight_state, hotel_state]:
            for task_id in candidate.get("active_task_ids", []):
                if task_id not in task_ids:
                    task_ids.append(task_id)

        return {
            **state,
            "debug_trace": list(state.get("debug_trace", [])) + ["parallel_a2a_delegation", "flight_delegation", "hotel_delegation"],
            "flight_response": flight_state.get("flight_response"),
            "hotel_response": hotel_state.get("hotel_response"),
            "active_task_ids": task_ids,
            "last_task_ids": task_ids,
            "a2a_messages": _merge_new_a2a_messages(
                base_a2a_messages,
                [flight_state.get("a2a_messages", []), hotel_state.get("a2a_messages", [])],
            ),
        }

    def _multi_city_delegation_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute a multi-city itinerary as several A2A tasks.

        This keeps the assignment contract intact: every specialist search is
        still an A2A request to a stateless sub-agent. The orchestrator simply
        manages a dynamic itinerary plan instead of forcing everything into one
        round-trip frame.
        """
        plan = state.get("multi_city_plan", {})
        scope = str(plan.get("scope") or state.get("extracted", {}).get("_multi_city_scope") or "both").lower()
        include_flights = scope not in {"hotels_only", "hotel_only", "only_hotels"}
        include_hotels = scope not in {"flights_only", "flight_only", "only_flights"}
        task_ids: List[str] = []
        a2a_messages = list(state.get("a2a_messages", []))
        flight_segments: List[Dict[str, Any]] = []
        hotel_segments: List[Dict[str, Any]] = []
        errors: List[str] = []
        passengers = int(state.get("travel_params", {}).get("passengers", 1))
        cabin = state.get("travel_params", {}).get("cabin_class", CabinClass.ECONOMY.value)
        room_type = state.get("travel_params", {}).get("room_type", RoomType.STANDARD.value)

        for leg in (plan.get("legs", []) if include_flights else []):
            try:
                request = FlightTaskRequest(
                    session_id=state["session_id"],
                    parameters=FlightSearchParameters(
                        origin=leg["origin"],
                        destination=leg["destination"],
                        departure_date=leg["departure_date"],
                        return_date=None,
                        passengers=passengers,
                        cabin_class=cabin,
                    ),
                )
                task_ids.append(request.task_id)
                response = self.flight_agent.invoke(request)
                a2a_messages = _append_a2a_exchange({"a2a_messages": a2a_messages}, request, response, "multi_city_delegation")
                if response.status in {"success", "partial"}:
                    flight_segments.append({**leg, "options": response.results[:2]})
                else:
                    errors.append(response.error or response.clarification_needed or "A flight segment could not be searched.")
            except (ValidationError, KeyError, ValueError) as exc:
                errors.append(f"A flight segment could not be completed: {exc}")

        for stay in (plan.get("stays", []) if include_hotels else []):
            try:
                request = HotelTaskRequest(
                    session_id=state["session_id"],
                    parameters=HotelSearchParameters(
                        destination=stay["destination"],
                        check_in_date=stay["check_in_date"],
                        check_out_date=stay["check_out_date"],
                        guests=int(state.get("travel_params", {}).get("guests", passengers)),
                        room_type=room_type,
                        location_preference=state.get("travel_params", {}).get("location_preference"),
                    ),
                )
                task_ids.append(request.task_id)
                response = self.hotel_agent.invoke(request)
                a2a_messages = _append_a2a_exchange({"a2a_messages": a2a_messages}, request, response, "multi_city_delegation")
                if response.status in {"success", "partial"}:
                    hotel_segments.append({**stay, "options": response.results[:2]})
                else:
                    errors.append(response.error or response.clarification_needed or "A hotel stay could not be searched.")
            except (ValidationError, KeyError, ValueError) as exc:
                errors.append(f"A hotel stay could not be completed: {exc}")

        return {
            **state,
            "debug_trace": list(state.get("debug_trace", [])) + ["multi_city_delegation"],
            "active_task_ids": task_ids,
            "last_task_ids": task_ids,
            "a2a_messages": a2a_messages,
            "final_aggregated_options": {
                "multi_city": {"flights": flight_segments, "hotels": hotel_segments},
                "errors": errors,
            },
            "conversation_focus": "multi_city_results",
            "last_successful_multi_city_plan": plan if (flight_segments or hotel_segments) else state.get("last_successful_multi_city_plan", {}),
        }

    def _aggregation_node(self, state: OrchestratorState) -> OrchestratorState:
        aggregated: Dict[str, Any] = {"flights": [], "hotels": [], "errors": [], "partials": []}
        flight_response = state.get("flight_response")
        hotel_response = state.get("hotel_response")

        if flight_response:
            if flight_response.status == "success":
                aggregated["flights"] = flight_response.results
            elif flight_response.status == "partial":
                aggregated["flights"] = flight_response.results
                aggregated["partials"].append(flight_response.clarification_needed)
            elif flight_response.status == "needs_clarification":
                aggregated["partials"].append(flight_response.clarification_needed)
            elif flight_response.status == "failed":
                aggregated["errors"].append(flight_response.error)

        if hotel_response:
            if hotel_response.status == "success":
                aggregated["hotels"] = hotel_response.results
            elif hotel_response.status == "needs_clarification":
                aggregated["partials"].append(hotel_response.clarification_needed)
            elif hotel_response.status == "failed":
                aggregated["errors"].append(hotel_response.error)

        completed_params = dict(state.get("travel_params", {})) if aggregated.get("flights") or aggregated.get("hotels") else state.get("last_completed_params", {})
        pending_after = list(state.get("pending_clarifications", []))
        params = state.get("travel_params", {})
        if (
            aggregated.get("hotels")
            and params.get("return_destination")
            and params.get("return_destination") != params.get("origin")
        ):
            pending_after = ["onward_hotel_dates"]

        return {
            **state,
            "debug_trace": list(state.get("debug_trace", [])) + ["aggregation"],
            "final_aggregated_options": aggregated,
            "last_completed_params": completed_params,
            "conversation_focus": "results" if aggregated.get("flights") or aggregated.get("hotels") else state.get("conversation_focus", ""),
            "pending_clarifications": pending_after,
        }

    def _user_response_formatting_node(self, state: OrchestratorState) -> OrchestratorState:
        if state.get("message_to_show_user"):
            message = state["message_to_show_user"]
        else:
            message = self._format_aggregated_response(state)

        history = list(state.get("conversation_history", []))
        history.append({"role": "assistant", "content": message})
        return {**state, "debug_trace": list(state.get("debug_trace", [])) + ["user_response_formatting"], "conversation_history": history, "message_to_show_user": message}

    def _format_aggregated_response(self, state: OrchestratorState) -> str:
        aggregated = state.get("final_aggregated_options", {})
        if aggregated.get("multi_city"):
            return self._format_multi_city_response(state)
        params = state.get("travel_params", {})
        flights = aggregated.get("flights", [])
        hotels = aggregated.get("hotels", [])
        errors = [error for error in aggregated.get("errors", []) if error]
        partials = [partial for partial in aggregated.get("partials", []) if partial]

        lines: List[str] = []
        destination = _city_label(params.get("destination"))

        if flights or hotels:
            lines.append(f"Here are the best mock options I found for {destination}:")

        if flights:
            lines.append("\n**Flight options**")
            for option in flights[:4]:
                leg = "Outbound" if option.trip_leg == "outbound" else ("Return" if option.destination == params.get("origin") else "Return / onward")
                lines.append(
                    f"- {leg}: {option.airline} {option.flight_number} — {option.origin} → {option.destination}, "
                    f"{option.departure_date.isoformat()} {option.departure_time} to {option.arrival_time}, "
                    f"{option.duration}, ${option.price_usd}, {option.baggage_note}."
                )

        if hotels:
            inferred = " I used your flight dates for the hotel stay." if state.get("hotel_dates_inferred") else ""
            stay = ""
            if params.get("check_in_date") and params.get("check_out_date"):
                stay = f" Stay: {params['check_in_date']} to {params['check_out_date']}."
            lines.append(f"\n**Hotel options**{inferred}{stay}")
            for hotel in hotels[:3]:
                lines.append(
                    f"- {hotel.hotel_name} — {hotel.star_rating}★ in {hotel.area}, "
                    f"${hotel.price_per_night_usd}/night, {hotel.distance_from_landmark}. "
                    f"Amenities: {', '.join(hotel.amenities[:3])}."
                )
            if params.get("return_destination") and params.get("return_destination") != params.get("origin"):
                onward_label = _city_label(params.get("return_destination"))
                primary_label = _city_label(params.get("destination"))
                lines.append(
                    f"Note: I showed hotels for {primary_label}, because that is the stay between your outbound and onward flight. "
                    f"If you also need hotels in {onward_label}, share the check-in and check-out dates for that city."
                )

        if errors and not flights and not hotels:
            lines.append("I don't have matching mock data for that route and date, so I could not find matching availability.")
            lines.append("Try a nearby destination, a different date, or economy cabin for the demo data.")
        elif errors:
            lines.append("\nA quick note: one part of the search had limited availability, so I showed what I could find.")

        if partials:
            lines.append("\n" + " ".join(partials))

        if flights and not hotels and not params.get("needs_hotel"):
            lines.append("\nWould you like me to add hotel options for the same trip?")
            state["awaiting_hotel_offer"] = True
        else:
            state["awaiting_hotel_offer"] = False

        if not lines:
            lines.append("I’m ready to help. Share your destination, dates, and whether you need flights, hotels, or both.")

        return "\n".join(lines)

    def _format_multi_city_response(self, state: OrchestratorState) -> str:
        aggregated = state.get("final_aggregated_options", {})
        itinerary = aggregated.get("multi_city", {})
        plan = state.get("multi_city_plan", {}) if isinstance(state.get("multi_city_plan"), dict) else {}
        route_labels = [_city_label(city) for city in plan.get("cities", [])] if plan.get("cities") else []
        lines: List[str] = ["Here is a multi-city mock itinerary based on your travel plan:"]
        if route_labels:
            lines.append(f"\n**Interpreted route:** {' → '.join(route_labels)}")

        flight_segments = itinerary.get("flights", [])
        if flight_segments:
            lines.append("\n**Flight segments**")
            for idx, segment in enumerate(flight_segments, start=1):
                origin = _city_label(segment.get("origin"))
                destination = _city_label(segment.get("destination"))
                lines.append(f"\n**Leg {idx}: {origin} → {destination} on {segment.get('departure_date')}**")
                for option in segment.get("options", [])[:2]:
                    lines.append(
                        f"- {option.airline} {option.flight_number} — {option.origin} → {option.destination}, "
                        f"{option.departure_date.isoformat()} {option.departure_time} to {option.arrival_time}, "
                        f"{option.duration}, ${option.price_usd}, {option.baggage_note}."
                    )

        hotel_segments = itinerary.get("hotels", [])
        if hotel_segments:
            lines.append("\n**Hotel stays**")
            for segment in hotel_segments:
                city = _city_label(segment.get("destination"))
                lines.append(f"\n**{city}: {segment.get('check_in_date')} to {segment.get('check_out_date')}**")
                for hotel in segment.get("options", [])[:2]:
                    lines.append(
                        f"- {hotel.hotel_name} — {hotel.star_rating}★ in {hotel.area}, "
                        f"${hotel.price_per_night_usd}/night, {hotel.distance_from_landmark}. "
                        f"Amenities: {', '.join(hotel.amenities[:3])}."
                    )

        errors = [error for error in aggregated.get("errors", []) if error]
        if errors:
            lines.append("\nA quick note: one or more legs had limited mock availability, so I showed what I could find.")
        return "\n".join(lines).strip()

    @staticmethod
    def mermaid_diagram() -> str:
        """Return an accurate Mermaid diagram for documentation."""
        return """flowchart TD
    START([START]) --> input_understanding[Input understanding: evidence-first TravelPlan extraction]
    input_understanding --> state_update[State update: canonical memory merge]
    state_update --> clarification[Clarification and plan readiness check]
    clarification --> route{Conditional routing}
    route -->|general or needs info| user_response_formatting[User response formatting]
    route -->|flight only| flight_delegation[Build FlightTaskRequest + log A2A exchange]
    route -->|hotel only| hotel_delegation[Build HotelTaskRequest + log A2A exchange]
    route -->|both / package| parallel_a2a_delegation[Parallel A2A fan-out + merge audit log]
    route -->|multi-city| multi_city_delegation[Dynamic multi-city A2A fan-out]
    flight_delegation --> after_flight{Need hotel too?}
    after_flight -->|yes| hotel_delegation
    after_flight -->|no| aggregation[Aggregation]
    parallel_a2a_delegation --> aggregation
    multi_city_delegation --> user_response_formatting
    hotel_delegation --> aggregation
    aggregation --> user_response_formatting
    user_response_formatting --> END([END])"""


def create_orchestrator() -> FriendlyAssistantOrchestrator:
    """Factory used by Streamlit and tests."""
    return FriendlyAssistantOrchestrator()
