# 5. Command-Driven CQRS State Reconciliation

Date: 2026-07-06

## Status
Accepted

## Context
Our AI Project Manager previously relied on a "Regenerative State" pattern. When a user updated project requirements, the LLM was asked to generate the complete task list from scratch. We attempted to use instruction-based persistence ("preserve IDs") and local backend diffing ("Smart Merge") to protect existing task states (like `IN_PROGRESS`). However, because the LLM inherently generates a complete snapshot rather than targeted updates, it frequently fails to correctly echo existing UUIDs under heavy context load, leading to data loss, overwritten states, and duplicated tasks.

To solve this fundamentally, we must shift to a Command-Driven (CQRS) pattern. The LLM will stop acting as a state generator and instead act as an Event Emitter. The backend will act as the Command Executor, safely processing atomic `CREATE`, `UPDATE`, and `DELETE` commands against the PostgreSQL database.

## Decision
We are adopting a strict Command-Driven (CQRS) pattern for all LLM task generation and state reconciliation.

**CONSTRAINT LOCK:**
The LLM is strictly forbidden from outputting full Task objects for persistence. All state changes MUST be routed through the ProjectPlanCommand schema, ensuring UUIDs remain immutable and IN_PROGRESS states are preserved.

## Consequences
- **Positive:** Task identities (UUIDs) and runtime statuses are absolutely guaranteed to be preserved, as they are only modified via targeted LLM commands rather than full state overwrites.
- **Positive:** Token optimization. The LLM only needs to emit deltas (commands for what changed) instead of hallucinating the entire project task list on every update.
- **Negative:** Increased prompt complexity required to teach the LLM how to emit valid structured commands instead of plain objects.
- **Action Required:** The current planner node and Pydantic schemas must be refactored to implement the Command Executor.
