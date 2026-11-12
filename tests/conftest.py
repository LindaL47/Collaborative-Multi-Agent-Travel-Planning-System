"""Pytest configuration for local package imports."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Unit tests must be deterministic even if the developer has .env set to Ollama.
# The Streamlit app can still use Ollama; pytest exercises graph/state logic.
os.environ["FRIENDLY_ASSISTANT_LLM_PROVIDER"] = "heuristic"
os.environ["FRIENDLY_ASSISTANT_DISABLE_LLM"] = "true"
