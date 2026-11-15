"""Export accurate Mermaid graph files from the compiled graph wrappers.

The assignment accepts Mermaid graph visualisations. This script refreshes the
files in graph_visualization/ from the graph helper methods used by the app.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.flight_agent.agent import FlightBookingAgent
from agents.hotel_agent.agent import HotelBookingAgent
from agents.budget_agent.agent import BudgetDecisionAgent
from agents.recommendation_agent.agent import RecommendationAgent
from orchestrator.agent import FriendlyAssistantOrchestrator

OUT = ROOT / "graph_visualization"
OUT.mkdir(exist_ok=True)

FILES = {
    "orchestrator_graph.mmd": FriendlyAssistantOrchestrator.mermaid_diagram(),
    "flight_agent_graph.mmd": FlightBookingAgent.mermaid_diagram(),
    "hotel_agent_graph.mmd": HotelBookingAgent.mermaid_diagram(),
    "budget_agent_graph.mmd": BudgetDecisionAgent.mermaid_diagram(),
    "recommendation_agent_graph.mmd": RecommendationAgent.mermaid_diagram(),
}

for name, content in FILES.items():
    (OUT / name).write_text(content.strip() + "\n", encoding="utf-8")
    print(f"wrote {OUT / name}")
