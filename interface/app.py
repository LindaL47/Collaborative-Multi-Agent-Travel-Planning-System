"""Streamlit chat interface for SyncTrip."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=True)

from orchestrator.agent import FriendlyAssistantOrchestrator  # noqa: E402
from orchestrator.memory_store import MemoryStore, MemoryStoreError, repeat_route_state  # noqa: E402

st.set_page_config(page_title="SyncTrip", page_icon="ST", layout="centered")

st.title("SyncTrip")
st.caption("Your travel planner for mock flights, hotels, budget estimates, and explained recommendations.")


@st.cache_resource
def get_memory_store() -> MemoryStore:
    return MemoryStore()


@st.cache_resource
def get_assistant() -> FriendlyAssistantOrchestrator:
    """Create one orchestrator instance per Streamlit process."""
    return FriendlyAssistantOrchestrator(memory_store=get_memory_store())


assistant = get_assistant()
store = get_memory_store()

FULL_PROMPT_EXAMPLE = (
    "Book flight and hotel from Singapore to Tokyo on 2026-07-25 returning 2026-07-30 "
    "for 2 travellers, economy cabin, standard room near Shinjuku."
)


def greeting() -> list[dict[str, str]]:
    return [{"role": "assistant", "content": f"Hi! I can help search mock flights, hotels, or both. Example: `{FULL_PROMPT_EXAMPLE}`"}]


memory_error = ""
try:
    memory_data = store.load()
except MemoryStoreError as exc:
    memory_data = {"profile": {}, "active": {}, "history": []}
    memory_error = str(exc)

if memory_error:
    st.warning(f"Local memory is unavailable: {memory_error}. Chat still works; the file will not be overwritten.")

if "agent_state" not in st.session_state:
    st.session_state.agent_state = None
if "messages" not in st.session_state:
    restored = memory_data["active"].get("conversation_history", [])
    st.session_state.messages = restored if restored else greeting()

with st.sidebar:
    st.header("Memory")
    st.caption("Local single-user demo. Saved plans are not bookings.")
    profile = memory_data["profile"]
    cabin_options = ["", "economy", "premium_economy", "business", "first"]
    room_options = ["", "standard", "deluxe", "suite", "family"]

    with st.expander("Core profile"):
        with st.form("profile_form"):
            home_airport = st.text_input("Home airport (3-letter code)", value=profile.get("home_airport", ""), max_chars=3)
            cabin_value = profile.get("cabin_class", "")
            room_value = profile.get("room_type", "")
            cabin_class = st.selectbox("Preferred cabin", cabin_options, index=cabin_options.index(cabin_value) if cabin_value in cabin_options else 0)
            room_type = st.selectbox("Preferred hotel room", room_options, index=room_options.index(room_value) if room_value in room_options else 0)
            flight_budget = st.number_input("Max flight price (USD / ticket; 0 = no limit)", min_value=0, value=int(profile.get("max_flight_price_usd") or 0), step=10)
            hotel_budget = st.number_input("Max hotel price (USD / night; 0 = no limit)", min_value=0, value=int(profile.get("max_hotel_price_usd_per_night") or 0), step=10)
            save_profile = st.form_submit_button("Save profile")
        if save_profile:
            try:
                store.save_profile({
                    "home_airport": home_airport.strip().upper(),
                    "cabin_class": cabin_class,
                    "room_type": room_type,
                    "max_flight_price_usd": int(flight_budget) or None,
                    "max_hotel_price_usd_per_night": int(hotel_budget) or None,
                })
                st.rerun()
            except (ValueError, MemoryStoreError) as exc:
                st.error(str(exc))

    with st.expander("Save current plan"):
        with st.form("archive_form"):
            decision = st.text_input("Decision (optional)", placeholder="e.g. Prefer the morning flight")
            feedback = st.text_area("Feedback (optional)", max_chars=500)
            archive = st.form_submit_button("Save plan to history")
        if archive:
            try:
                current = st.session_state.agent_state or memory_data["active"]
                store.archive_plan(current, decision, feedback)
                st.rerun()
            except (ValueError, MemoryStoreError) as exc:
                st.error(str(exc))

    history = memory_data["history"]
    with st.expander(f"Saved plans ({len(history)})"):
        if history:
            by_id = {record["id"]: record for record in history if isinstance(record, dict) and record.get("id")}
            if by_id:
                def history_label(record_id: str) -> str:
                    record = by_id[record_id]
                    plan = record.get("multi_city_plan", {})
                    params = record.get("travel_params", {})
                    route = " → ".join(plan.get("cities", [])) if isinstance(plan, dict) and plan.get("cities") else f"{params.get('origin', '?')} → {params.get('destination', '?')}"
                    return f"{record.get('saved_at', '')[:10]} · {route}"

                selected_id = st.selectbox("Plan", list(by_id), format_func=history_label)
                selected = by_id[selected_id]
                st.write("Decision:", selected.get("decision") or "—")
                st.write("Feedback:", selected.get("feedback") or "—")
                st.caption("Repeating a route starts a new draft and asks for new dates.")
                if st.button("Use saved route"):
                    try:
                        repeated = repeat_route_state(selected)
                        store.save_active(repeated)
                        st.session_state.agent_state = repeated
                        st.session_state.messages = repeated["conversation_history"]
                        st.rerun()
                    except MemoryStoreError as exc:
                        st.error(str(exc))
        else:
            st.caption("No saved plans yet.")

    st.header("Demo settings")
    st.write("Configured LLM provider:", os.getenv("FRIENDLY_ASSISTANT_LLM_PROVIDER", "auto"))
    st.write("Ollama model:", os.getenv("OLLAMA_MODEL", "llama3.1:8b"))
    show_debug = st.toggle("Show LangGraph trace", value=False)

    if st.session_state.agent_state and show_debug:
        state = st.session_state.agent_state
        st.subheader("Last graph run")
        st.write(" -> ".join(state.get("debug_trace", [])) or "No graph run yet")
        st.write("Route:", state.get("route", "not set"))
        st.write("Pending:", state.get("pending_clarifications", []))
        st.write("LLM diagnostics:", state.get("llm_diagnostics", {}))
        st.write("Active A2A task ids:", state.get("active_task_ids", []))
        st.write("Decision strategy:", state.get("decision_strategy", "balanced"))
        if state.get("budget_assessment"):
            st.write("Budget assessment:", state["budget_assessment"].model_dump(mode="json"))
        if state.get("recommendation"):
            st.write("Recommendation:", state["recommendation"].model_dump(mode="json"))
        st.code(FriendlyAssistantOrchestrator.mermaid_diagram(), language="mermaid")

    if st.button("Reset conversation"):
        st.session_state.agent_state = None
        st.session_state.messages = greeting()
        try:
            store.clear_active()
            st.rerun()
        except MemoryStoreError as exc:
            st.error(str(exc))

    confirm_clear = st.checkbox("I want to clear all local memory")
    if st.button("Clear all memory", disabled=not confirm_clear):
        try:
            store.clear_all()
            st.session_state.agent_state = None
            st.session_state.messages = greeting()
            st.rerun()
        except MemoryStoreError as exc:
            st.error(str(exc))

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Tell me your travel plan...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        state = assistant.chat(prompt, st.session_state.agent_state)
        st.session_state.agent_state = state
        response = state.get("message_to_show_user", "I'm sorry, I could not prepare a response. Please try again.")
        if state.get("memory_warning"):
            st.warning(f"Local memory was not saved: {state['memory_warning']}")
    except Exception:
        response = "Sorry, I hit a temporary issue while planning that. Please rephrase the request and I'll try again."

    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)
