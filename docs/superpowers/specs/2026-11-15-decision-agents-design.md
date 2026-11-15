# Travel decision agents

## Intent and scope

Add two useful decision agents to SyncTrip's existing Python/LangGraph travel
planner, as requested. Keep the work on `feat/decision-agents` and push that
branch for the shared project's collaborators to review.

## Approaches

- Add more search agents: increases the inventory scope, but does not improve
  decisions about the flight/hotel options already available.
- Add an LLM-only decision prompt: flexible, but needs a model and makes costs
  and recommendations difficult to reproduce.
- Add two deterministic decision graphs after search and budget filtering:
  reuses the existing architecture and runs offline. This is the implementation
  choice within the user's delegated scope.

## Behavior

1. **BudgetDecisionAgent** estimates the cheapest available flight/hotel
   combination, multiplying each flight leg by passenger count and each hotel
   stay by its nights. It reports missing itinerary components, total-budget
   feasibility, and the amount by which an infeasible budget falls short.
2. **RecommendationAgent** selects one option per flight leg and hotel stay
   using `balanced`, `budget`, or `comfort` scoring. Scores use price, flight
   duration/stops, and hotel rating/location/refundability. Explanations name
   the actual properties of each selected option. If preferred choices exceed
   the total budget but the cheapest complete plan fits, choose the cheapest
   plan and explain that budget took priority.
3. Both agents use independent StateGraphs and typed A2A task contracts with
   UUID task/trace identities. Their exchanges join the orchestrator's existing
   audit log and task list. General questions and clarification do not run them.
4. The orchestrator builds groups for every expected leg/stay, including missing
   ones, for single-city and multi-city trips. New chat turns clear previous
   decision results. Preference and total budget persist within a trip and reset
   on a fresh trip. Current-turn preferences override prior ones.
5. Chat output includes recommended options, reasons, estimated cost, and budget
   guidance. Recognize explicit total-budget phrases such as `total budget
   $2500`, and strategy phrases such as `cheapest` or `prioritize comfort`.

## Constraints and assumptions

- Use existing dependencies; no live inventory service or model is required.
- Keep current flight/hotel task contracts, per-ticket/per-night price filters,
  memory system, and planner behavior intact.
- Hotel estimates cover **one room per night**, matching the current mock hotel
  API. Flight estimates cover all travellers. State that meals, local transport,
  and other expenses are excluded. Incomplete estimates are subtotals, never
  presented as complete trip totals.
- New modules live under `agents/budget_agent`, `agents/recommendation_agent`,
  and a shared decision schema file. Group conversion lives in
  `orchestrator/decision_support.py`, keeping the large planner file focused.
- Tests exercise cost calculations, changing recommendations, budget priority,
  incomplete plans, A2A correlation, and conversational integration. Update
  architecture documentation and exportable Mermaid diagrams.
