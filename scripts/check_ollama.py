"""Quick local health check for Ollama before running the Streamlit demo."""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

try:
    with urllib.request.urlopen(f"{base_url}/api/tags", timeout=5) as response:  # nosec: local dev endpoint
        tags = json.loads(response.read().decode("utf-8"))
except Exception as exc:  # pragma: no cover - utility script
    raise SystemExit(f"Ollama is not reachable at {base_url}. Start it first. Error: {exc}")

models = [item.get("name", "") for item in tags.get("models", [])]
print(f"Ollama is reachable at {base_url}")
print("Installed models:", models)
if not any(name.startswith(model) for name in models):
    raise SystemExit(f"Model {model!r} was not found. Run: ollama pull {model}")
print(f"Model {model!r} is available.")
