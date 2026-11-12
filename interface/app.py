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

st.set_page_config(page_title="SyncTrip", page_icon="ST", layout="centered")

st.title("SyncTrip")
st.caption("Your travel planner for mock flights, hotels, and itinerary changes.")


@st.cache_resource
def get_assistant() -> FriendlyAssistantOrchestrator:
    """Create one orchestrator instance per Streamlit process."""
    return FriendlyAssistantOrchestrator()


assistant = get_assistant()

FULL_PROMPT_EXAMPLE = (
    "Book flight and hotel from Singapore to Tokyo on 2026-07-25 returning 2026-07-30 "
    "for 2 travellers, economy cabin, standard room near Shinjuku."
)

if "agent_state" not in st.session_state:
    st.session_state.agent_state = None
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hi! I can help search mock flights, hotels, or both. "
                f"Example: `{FULL_PROMPT_EXAMPLE}`"
            ),
        }
    ]

with st.sidebar:
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
        st.code(FriendlyAssistantOrchestrator.mermaid_diagram(), language="mermaid")

    if st.button("Reset conversation"):
        st.session_state.agent_state = None
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Conversation reset. Where would you like to travel? "
                    f"Example: `{FULL_PROMPT_EXAMPLE}`"
                ),
            }
        ]
        st.rerun()

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
    except Exception:
        response = "Sorry, I hit a temporary issue while planning that. Please rephrase the request and I'll try again."

    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)
