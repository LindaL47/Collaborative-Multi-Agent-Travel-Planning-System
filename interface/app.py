"""SyncTrip dashboard for the existing conversational travel planner."""
from __future__ import annotations

import base64
import html
import logging
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=True)
from orchestrator.agent import FriendlyAssistantOrchestrator  # noqa: E402
from orchestrator.memory_store import MemoryStore, MemoryStoreError, repeat_route_state  # noqa: E402
from orchestrator.response_localization import render_response  # noqa: E402
from interface.i18n import LANGUAGE_NAMES, translate  # noqa: E402

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
logger = logging.getLogger(__name__)
st.set_page_config(page_title="SyncTrip | Travel Dashboard", page_icon="✈️", layout="wide")


@st.cache_resource
def memory_store() -> MemoryStore:
    return MemoryStore()


@st.cache_resource
def assistant() -> FriendlyAssistantOrchestrator:
    return FriendlyAssistantOrchestrator(memory_store=memory_store())


def initial_messages() -> list[dict[str, str]]:
    return [{"role": "assistant", "content": "", "kind": "welcome"}]


try:
    memory_data = memory_store().load()
    memory_error = ""
except MemoryStoreError as exc:
    memory_data = {"profile": {}, "active": {}, "history": []}
    memory_error = str(exc)

restored = memory_data["active"]
restored_messages = restored.get("conversation_history") or initial_messages()
for key, default in {"agent_state": restored or None, "messages": restored_messages, "selected_flights": {},
                     "selected_hotel": None, "budget_usd": float(restored.get("trip_budget", {}).get("total_budget_usd") or 0), "ui_error": "", "ui_language": "zh"}.items():
    if key not in st.session_state:
        st.session_state[key] = default

language = st.session_state.ui_language


def t(key: str, **values: object) -> str:
    return translate(language, key, **values)


def submit_request(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.ui_error = ""
    try:
        planning_state = st.session_state.agent_state
        if st.session_state.budget_usd > 0:
            planning_state = dict(planning_state or {})
            trip_budget = dict(planning_state.get("trip_budget", {}))
            trip_budget["total_budget_usd"] = int(st.session_state.budget_usd)
            planning_state["trip_budget"] = trip_budget
        result = assistant().chat(prompt, planning_state, language=language)
        st.session_state.agent_state = result
        if result.get("memory_warning"):
            st.session_state.ui_error = f'{t("memory_save_error")}: {result["memory_warning"]}'
        st.session_state.messages.append({"role": "assistant", "content": result.get("message_to_show_user", t("no_response"))})
        st.session_state.selected_flights = {}
        st.session_state.selected_hotel = None
    except Exception:
        logger.exception("Travel planning request failed")
        st.session_state.ui_error = t("planner_error")
        st.session_state.messages.append({"role": "assistant", "content": st.session_state.ui_error})


def parsed_date(value: object, default: date) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return default


def stay_nights(params: dict) -> int:
    start = params.get("check_in_date") or params.get("departure_date")
    end = params.get("check_out_date") or params.get("return_date")
    try:
        return max(0, (date.fromisoformat(str(end)) - date.fromisoformat(str(start))).days)
    except (TypeError, ValueError):
        return 0


def side_row(label: str, value: object) -> None:
    st.markdown(f'<div class="side-row"><span>{html.escape(str(label))}</span><strong>{html.escape(str(value))}</strong></div>', unsafe_allow_html=True)


def display_message(value: str) -> str:
    """Keep presentation copy free of backend dataset qualifiers."""
    value = re.sub(r"\bdemo (?:data|dataset)\b", "available data", value, flags=re.IGNORECASE)
    value = re.sub(r"\b(?:this|the) demo\b", "the planner", value, flags=re.IGNORECASE)
    value = re.sub(r"\bmock[- ]*", "", value, flags=re.IGNORECASE)
    return re.sub(r"\bdemo\b", "", value, flags=re.IGNORECASE)


hero = base64.b64encode((ASSETS / "hero-lake.webp").read_bytes()).decode("ascii")
st.html(
    f'<style>{(HERE / "styles.css").read_text(encoding="utf-8")}'
    f'.hero{{background-image:linear-gradient(90deg,rgba(12,39,56,.66),rgba(16,48,60,.38)),url("data:image/webp;base64,{hero}");}}</style>'
)

state = st.session_state.agent_state or {}
profile = memory_data["profile"]
params = {target: profile[source] for target, source in (("origin", "home_airport"), ("cabin_class", "cabin_class"), ("room_type", "room_type")) if profile.get(source)}
params.update(state.get("travel_params", {}))
options = state.get("final_aggregated_options", {})
flights, hotels = options.get("flights", []), options.get("hotels", [])
nights = stay_nights(params)
travellers = int(params.get("passengers") or params.get("guests") or 1)

with st.sidebar:
    if memory_error:
        st.warning(f'{t("memory_load_error")}: {memory_error}')
    st.markdown(f'<div class="side-heading">{t("Trip Summary")}</div>', unsafe_allow_html=True)
    with st.container(border=True):
        side_row(t("Route"), f"{params.get('origin', '—')} → {params.get('destination', '—')}")
        side_row(t("Departure"), params.get("departure_date") or params.get("check_in_date") or "—")
        side_row(t("Return / check-out"), params.get("return_date") or params.get("check_out_date") or "—")
        side_row(t("Travellers"), travellers if params else "—")
        side_row(t("Stay"), t("nights", count=nights) if nights else "—")
        side_row(t("Cabin / room"), f"{t(params.get('cabin_class', '—'))} / {t(params.get('room_type', '—'))}")
    st.markdown(f'#### {t("Budget Breakdown")}')
    st.number_input(t("Your budget (USD)"), min_value=0.0, step=100.0, key="budget_usd")
    chosen_flights = st.session_state.selected_flights
    chosen_hotel = st.session_state.selected_hotel
    flight_cost = sum(item["price_usd"] for item in chosen_flights.values()) * travellers
    hotel_cost = chosen_hotel["price_per_night_usd"] * nights if chosen_hotel else 0
    total = flight_cost + hotel_cost
    with st.container(border=True):
        side_row(t("Flights"), f"${flight_cost:,}" if chosen_flights else t("Choose a flight"))
        side_row(t("Hotel"), f"${hotel_cost:,}" if chosen_hotel and nights else t("Choose a hotel"))
        side_row(t("Estimated total"), f"${total:,}" if total else "—")
        if st.session_state.budget_usd and total:
            side_row(t("Remaining"), f"${st.session_state.budget_usd - total:,.0f}")
        st.caption(t("budget_note"))
    st.markdown(f'#### {t("Travel Plan")}')
    with st.container(border=True):
        st.markdown(display_message(render_response(state, language, state["message_to_show_user"])) if state.get("message_to_show_user") else t("plan_empty"))
    if st.button(t("Reset conversation"), width="stretch"):
        try:
            memory_store().clear_active()
            for key in ("agent_state", "messages", "selected_flights", "selected_hotel", "budget_usd", "ui_error"):
                st.session_state.pop(key, None)
            st.rerun()
        except MemoryStoreError as exc:
            st.error(str(exc))
    with st.expander(t("Memory")):
        st.markdown(f'**{t("Profile")}**')
        with st.form("memory_profile"):
            home_airport = st.text_input(t("Home airport"), value=profile.get("home_airport", ""), max_chars=3)
            cabin_options = ["", "economy", "premium_economy", "business", "first"]
            room_options = ["", "standard", "deluxe", "suite", "family"]
            preferred_cabin = st.selectbox(t("Preferred cabin"), cabin_options, index=cabin_options.index(profile.get("cabin_class", "")) if profile.get("cabin_class", "") in cabin_options else 0, format_func=lambda value: t(value) if value else "—")
            preferred_room = st.selectbox(t("Preferred room"), room_options, index=room_options.index(profile.get("room_type", "")) if profile.get("room_type", "") in room_options else 0, format_func=lambda value: t(value) if value else "—")
            flight_limit = st.number_input(t("Flight price limit"), min_value=0, value=int(profile.get("max_flight_price_usd") or 0), step=10)
            hotel_limit = st.number_input(t("Hotel price limit"), min_value=0, value=int(profile.get("max_hotel_price_usd_per_night") or 0), step=10)
            save_profile = st.form_submit_button(t("Save profile"), width="stretch")
        if save_profile:
            try:
                memory_store().save_profile({"home_airport": home_airport.strip().upper(), "cabin_class": preferred_cabin, "room_type": preferred_room, "max_flight_price_usd": flight_limit or None, "max_hotel_price_usd_per_night": hotel_limit or None})
                st.rerun()
            except (ValueError, MemoryStoreError) as exc:
                st.error(str(exc))
        st.markdown(f'**{t("Saved plans")} ({len(memory_data["history"])})**')
        with st.form("archive_plan"):
            decision = st.text_input(t("Decision optional"))
            feedback = st.text_area(t("Feedback optional"), max_chars=500)
            save_plan = st.form_submit_button(t("Save plan"), width="stretch")
        if save_plan:
            try:
                memory_store().archive_plan(state, decision, feedback)
                st.rerun()
            except (ValueError, MemoryStoreError) as exc:
                st.error(str(exc))
        history = {item["id"]: item for item in memory_data["history"] if isinstance(item, dict) and item.get("id")}
        if history:
            def plan_label(plan_id: str) -> str:
                item = history[plan_id]
                cities = item.get("multi_city_plan", {}).get("cities", [])
                route = " → ".join(cities) if cities else f'{item.get("travel_params", {}).get("origin", "?")} → {item.get("travel_params", {}).get("destination", "?")}'
                return f'{item.get("saved_at", "")[:10]} · {route}'

            selected_id = st.selectbox(t("Saved route"), list(history), format_func=plan_label)
            selected_plan = history[selected_id]
            st.caption(f'{t("Decision optional")}: {selected_plan.get("decision") or "—"}')
            st.caption(f'{t("Feedback optional")}: {selected_plan.get("feedback") or "—"}')
            if st.button(t("Use saved route"), width="stretch"):
                try:
                    repeated = repeat_route_state(selected_plan)
                    repeated["conversation_history"] = [{"role": "assistant", "content": t("route_restored")}]
                    memory_store().save_active(repeated)
                    st.session_state.agent_state = repeated
                    st.session_state.messages = repeated["conversation_history"]
                    st.session_state.selected_flights = {}
                    st.session_state.selected_hotel = None
                    st.rerun()
                except MemoryStoreError as exc:
                    st.error(str(exc))
        confirm_clear = st.checkbox(t("Confirm clear memory"))
        if st.button(t("Clear all memory"), disabled=not confirm_clear, width="stretch"):
            try:
                memory_store().clear_all()
                for key in ("agent_state", "messages", "selected_flights", "selected_hotel", "budget_usd", "ui_error"):
                    st.session_state.pop(key, None)
                st.rerun()
            except MemoryStoreError as exc:
                st.error(str(exc))
    with st.expander(t("Agent diagnostics")):
        st.write(t("LLM provider:"), os.getenv("FRIENDLY_ASSISTANT_LLM_PROVIDER", "auto"))
        st.write(t("Graph route:"), state.get("route", "—"))
        st.write(t("Trace:"), " → ".join(state.get("debug_trace", [])) or "—")
        st.write(t("Decision strategy:"), t(state.get("decision_strategy", "balanced")))
        if state.get("budget_assessment"):
            st.write(t("Budget assessment:"), state["budget_assessment"].model_dump(mode="json"))
        if state.get("recommendation"):
            st.write(t("Recommendation:"), state["recommendation"].model_dump(mode="json"))

top_left, top_right = st.columns([8, 2], vertical_alignment="center")
with top_right:
    with st.popover(f"🌐 {LANGUAGE_NAMES[language]}", width="stretch"):
        for code, name in LANGUAGE_NAMES.items():
            if st.button(name, key=f"language-{code}", width="stretch", type="primary" if code == language else "secondary"):
                st.session_state.ui_language = code
                st.rerun()

st.markdown(f'<div class="hero"><div class="eyebrow">{t("hero_eyebrow")}</div><h1>{t("hero_title")}</h1><p>{t("hero_subtitle")}</p></div>', unsafe_allow_html=True)
if st.session_state.ui_error:
    st.error(st.session_state.ui_error)

flight_tab, hotel_tab, trip_tab = st.tabs([t("Flights tab"), t("Hotels tab"), t("Trips tab")])
with flight_tab:
    st.markdown(f'### {t("Find flights")}')
    with st.form("flight_search"):
        c1, c2, c3, c4 = st.columns([1.2, 1.2, 1, 1])
        with c1: origin = st.text_input(t("From"), value=params.get("origin") or "Singapore")
        with c2: destination = st.text_input(t("To"), value=params.get("destination") or "Tokyo")
        with c3: departure = st.date_input(t("Departure"), value=parsed_date(params.get("departure_date"), date.today() + timedelta(days=30)))
        with c4: returning = st.date_input(t("Return date"), value=parsed_date(params.get("return_date"), date.today() + timedelta(days=35)))
        c5, c6, c7 = st.columns(3)
        with c5: passengers = st.number_input(t("Travellers input"), min_value=1, max_value=12, value=travellers)
        with c6:
            cabins = ["economy", "premium_economy", "business", "first"]
            cabin = st.selectbox(t("Cabin"), cabins, index=cabins.index(params.get("cabin_class")) if params.get("cabin_class") in cabins else 0, format_func=t)
        with c7: round_trip = st.checkbox(t("Round trip"), value=bool(params.get("return_date")))
        flight_submit = st.form_submit_button(t("Search flights"), type="primary", width="stretch")
    if flight_submit:
        if not origin.strip() or not destination.strip() or (round_trip and returning <= departure):
            st.error(t("flight_validation"))
        else:
            return_phrase = f" returning {returning.isoformat()}" if round_trip else " one way"
            submit_request(f"Find flights from {origin.strip()} to {destination.strip()} departing {departure.isoformat()}{return_phrase} for {passengers} travellers, {cabin.replace('_', ' ')} cabin.")
            st.rerun()
    st.markdown(f'### {t("Flight Results")} · {t("option_count", count=len(flights))}')
    if not flights: st.info(t("flight_empty"))
    for index, option in enumerate(flights):
        with st.container(border=True):
            route, details, price = st.columns([1, 2.3, .9], vertical_alignment="center")
            with route:
                st.markdown(f"**{option.origin} → {option.destination}**")
                st.caption(f"{t(option.trip_leg)} · {t(option.cabin_class)}")
            with details:
                st.markdown(f"**{option.airline} · {option.flight_number}**")
                st.write(f"{option.departure_date} · {option.departure_time} → {option.arrival_time} · {option.duration}")
                st.caption(f'{t("stop_count", count=option.stops)} · {option.baggage_note}')
            with price:
                st.markdown(f'<div class="price">${option.price_usd:,}</div><div class="micro">{t("per_traveller")}</div>', unsafe_allow_html=True)
                if st.button(t("Add to trip"), key=f"flight-{index}-{option.flight_number}", width="stretch"):
                    st.session_state.selected_flights[option.trip_leg] = option.model_dump(mode="json")
                    st.rerun()

with hotel_tab:
    st.markdown(f'### {t("Find hotels")}')
    with st.form("hotel_search"):
        c1, c2, c3, c4 = st.columns([1.3, 1, 1, .7])
        with c1: city = st.text_input(t("Destination"), value=params.get("destination") or "Tokyo", key="hotel_city")
        with c2: checkin = st.date_input(t("Check-in"), value=parsed_date(params.get("check_in_date"), date.today() + timedelta(days=30)))
        with c3: checkout = st.date_input(t("Check-out"), value=parsed_date(params.get("check_out_date"), date.today() + timedelta(days=35)))
        with c4: guests = st.number_input(t("Guests"), min_value=1, max_value=12, value=int(params.get("guests") or travellers))
        c5, c6 = st.columns([1, 2])
        with c5:
            rooms = ["standard", "deluxe", "suite", "family"]
            room = st.selectbox(t("Room"), rooms, index=rooms.index(params.get("room_type")) if params.get("room_type") in rooms else 0, format_func=t)
        with c6: area = st.text_input(t("Preferred area (optional)"), value=params.get("location_preference") or "")
        hotel_submit = st.form_submit_button(t("Find hotels"), type="primary", width="stretch")
    if hotel_submit:
        if not city.strip() or checkout <= checkin:
            st.error(t("hotel_validation"))
        else:
            area_phrase = f" near {area.strip()}" if area.strip() else ""
            submit_request(f"Find hotels in {city.strip()} checking in {checkin.isoformat()} and checking out {checkout.isoformat()} for {guests} guests, {room} room{area_phrase}.")
            st.rerun()
    st.markdown(f'### {t("Hotel Results")} · {t("option_count", count=len(hotels))}')
    results, map_area = st.columns([1.6, 1], gap="large")
    with results:
        if not hotels: st.info(t("hotel_empty"))
        for index, hotel in enumerate(hotels):
            with st.container(border=True):
                photo, details, price = st.columns([1, 1.5, .8], vertical_alignment="center")
                with photo:
                    image_name = "hotel-lobby.webp" if hotel.illustration_key == "lobby" else "hotel-illustration.webp"
                    st.image(str(ASSETS / image_name), width="stretch")
                with details:
                    st.markdown(f"**{hotel.hotel_name}**")
                    st.caption(f'{hotel.city_name} · {hotel.area} · {hotel.star_rating}★ {t("hotel_class")}')
                    if hotel.review_rating is not None and hotel.review_count is not None:
                        st.write(f'⭐ {hotel.review_rating:.1f} · {t("review_count", count=f"{hotel.review_count:,}")}')
                    st.caption(hotel.distance_from_landmark)
                    st.caption(" · ".join(hotel.amenities[:3]))
                with price:
                    if hotel.original_price_per_night_usd and hotel.original_price_per_night_usd > hotel.price_per_night_usd:
                        pct = round(100 * (1 - hotel.price_per_night_usd / hotel.original_price_per_night_usd))
                        st.markdown(f'<span class="tag">{pct}% {t("offer")}</span><br><span class="old-price">${hotel.original_price_per_night_usd:,}</span>', unsafe_allow_html=True)
                    st.markdown(f'<div class="price">${hotel.price_per_night_usd:,}</div><div class="micro">{t("per_night")}</div>', unsafe_allow_html=True)
                    if st.button(t("Add to trip"), key=f"hotel-{index}-{hotel.destination}", width="stretch"):
                        st.session_state.selected_hotel = hotel.model_dump(mode="json")
                        st.rerun()
    with map_area:
        with st.container(border=True):
            st.markdown(f'**{t("Map")}**')
            points = [{"lat": h.latitude, "lon": h.longitude} for h in hotels if h.latitude is not None and h.longitude is not None]
            if points:
                st.map(pd.DataFrame(points), latitude="lat", longitude="lon", zoom=11, height=380)
                for h in hotels: st.caption(f"📍 {h.hotel_name}")
            else:
                st.info(t("map_empty"))

with trip_tab:
    st.markdown(f'### {t("Your Trip")}')
    with st.container(border=True):
        if params:
            st.write(f'**{t("Route")}:** {params.get("origin", "—")} → {params.get("destination", "—")}')
            st.write(f'**{t("Dates:")}** {params.get("departure_date") or params.get("check_in_date") or "—"} → {params.get("return_date") or params.get("check_out_date") or "—"}')
            st.write(f'**{t("Travellers")}:** {travellers} · **{t("Stay")}:** {t("nights", count=nights) if nights else "—"}')
        else: st.info(t("trip_empty"))
        if chosen_flights:
            st.write(f'**{t("Selected flights:")}** ' + ", ".join(f"{f['airline']} {f['flight_number']} ({t(leg)})" for leg, f in chosen_flights.items()))
        if chosen_hotel: st.write(f'**{t("Selected hotel:")}** {chosen_hotel["hotel_name"]}')
        st.caption(t("selection_note"))
    st.markdown(f'### {t("Conversation")}')
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(t("welcome") if message.get("kind") == "welcome" else display_message(message["content"]))
    with st.form("chat_form", clear_on_submit=True):
        prompt = st.text_input(t("Ask the assistant or change a detail"), placeholder=t("chat_example"))
        send = st.form_submit_button(t("Send to assistant"), type="primary")
    if send and prompt.strip():
        submit_request(prompt.strip())
        st.rerun()
