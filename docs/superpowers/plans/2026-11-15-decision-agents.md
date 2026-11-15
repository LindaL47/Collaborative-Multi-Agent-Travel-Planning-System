# Travel Decision Agents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Add budget assessment and explainable recommendation agents to the existing travel workflow and push a feature branch.

**Architecture:** Two deterministic LangGraph agents consume typed groups of flight/hotel options. The orchestrator runs both after existing price filtering, records A2A exchanges, and formats their decisions for chat.

**Tech Stack:** Existing Python 3.10+, LangGraph, Pydantic, pytest, Streamlit.

**Spec:** `docs/superpowers/specs/2026-11-15-decision-agents-design.md`

## Global Constraints

- Use existing dependencies; no live inventory service or model is required.
- Push only `feat/decision-agents`; keep the shared default branch untouched.
- Costs cover all passengers and one room per stay; incomplete plans show subtotals.
- Preserve existing search contracts and price filtering.

## Review Focus

- Round trips must count both legs and multiply flight costs by passengers.
- Multi-city failed or filtered-out components must remain visible as missing groups.
- Total budget must override a more expensive recommendation when a complete cheaper plan fits.
- A fresh trip or a general/clarification turn must not show stale decisions.
- Location preference and caller-owned option ordering must survive recommendation scoring.

### Task 1: Implement the two decision agents

**Files:** Create `agents/decision_schemas.py`, `agents/budget_agent/agent.py`, `agents/recommendation_agent/agent.py`, and `tests/test_decision_agents.py`.

**Interfaces:** `BudgetDecisionAgent.invoke(BudgetTaskRequest | dict) -> BudgetTaskResponse`; `RecommendationAgent.invoke(RecommendationTaskRequest | dict) -> RecommendationTaskResponse`. Shared `DecisionParameters` contains flight/hotel groups, passengers, strategy, location preference, and optional total budget. Each result records completeness and missing groups.

- [x] Write tests for hand-calculated group costs, budget feasibility, incomplete groups, strategy-dependent choices, location matching, total-budget priority, and trace correlation.
- [x] Run `.venv/bin/python -m pytest tests/test_decision_agents.py -q`; confirm new behavior is missing.
- [x] Implement typed contracts and independent graphs using cost and normalized quality scores.
- [x] Run the new tests and existing `tests` suite; expect all passing.
- [x] Commit the two agents and tests.

### Task 2: Connect decisions to conversational planning

**Files:** Create `orchestrator/decision_support.py` and `tests/test_decision_integration.py`; modify `orchestrator/agent.py` and existing protocol task-count assertions.

**Interfaces:** `build_decision_parameters(state: dict) -> DecisionParameters`; graph nodes `budget_assessment` and `option_recommendation` consume Task 1 contracts. Store typed results in `budget_assessment` and `recommendation`, and their exchanges in `a2a_messages`.

- [x] Write integration tests for round trips, multi-city plans, per-option filtering, total budget, preference changes, and stale-result clearing.
- [x] Run the integration tests; confirm the decision fields/nodes are absent.
- [x] Implement parameter grouping, chat preference extraction, graph nodes, A2A logging, and concise user-facing decision sections.
- [x] Update search-only task-count assertions to account for the two decision tasks while retaining request/response contract checks.
- [x] Run `.venv/bin/python -m pytest tests -q`; expect all passing.
- [x] Commit the integrated workflow and tests.

### Task 3: Document and verify the deliverable

**Files:** Modify `README.md`, `scripts/export_graphs.py`, graph sources, and Streamlit's optional trace display.

**Interfaces:** Each new agent exposes `mermaid_diagram() -> str`; `scripts/export_graphs.py` exports all five workflows.

- [x] Add setup/demo documentation, scoring/cost assumptions, and examples.
- [x] Export graphs; run the full application test suite and a Streamlit smoke check.
- [x] Review the full diff, resolve substantive findings with reproducing tests, and commit.
- [ ] Push `feat/decision-agents` and verify that the remote commit matches local HEAD.
