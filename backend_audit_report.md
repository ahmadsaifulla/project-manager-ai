# Backend Architecture & Code Audit Report

This document contains a comprehensive review of the Python/FastAPI backend codebase against `ARCHITECTURE.md` and `implementation_plan.md`. In accordance with the emergency constraint, low-level anomalies have been ignored, and only P0/P1 issues capable of crashing or severely compromising the multi-agent system have been flagged.

## 1. Global Shared Workspace Corruption
**Location:** `services/chatbot/app/graph.py` (Lines 35-38, 195) and `services/chatbot/app/main.py` (Lines 270-280)
**Type:** Architectural Violation & Critical Bug (P0)
**Description:** The system uses a hardcoded, global `BASE_DIR` (`services/`) to initialize workspaces, store `TEMP_ARCHITECT.md`, `DRAFT_USER_STORIES.md`, and the `architecture/` directory for ALL projects. Meanwhile, `main.py`'s `create_project` endpoint initializes these files in `workspaces/<project_id>/.planning`.
**Impact:** **P0.** Catastrophic cross-project state corruption. Any simultaneous project creation or elicitation will overwrite the global shared files, mixing context between projects. This will cause the LLM Planner to generate invalid, hallucinated tasks based on overwritten architecture documents from other projects.
**Suggested Fix:** Pass `project_id` into the LangGraph state and dynamically compute the workspace path (`workspaces/<project_id>/.planning/`) inside the graph nodes. Update `initialize_workspace` and `calculate_blast_radius` to use this dynamic, project-isolated path.

## 2. Missing PostgreSQL LangGraph Persistence
**Location:** `services/chatbot/app/graph.py` (Line 520) and `services/chatbot/app/database.py` (Line 26)
**Type:** Missing Implementation (P0)
**Description:** The LangGraph state persistence is missing the PostgreSQL Checkpointer. `app_graph` is currently compiled using `MemorySaver()` instead of a robust persistent checkpointer. Additionally, `database.py` defaults to SQLite, defying the `ARCHITECTURE.md` requirement for PostgreSQL.
**Impact:** **P0.** Thread states are strictly in-memory and volatile. If the FastAPI server restarts, or if API requests are load-balanced across multiple worker processes, all conversation history, project goals, and phase statuses are instantly lost. This effectively crashes the multi-agent orchestration state machine.
**Suggested Fix:** Implement LangGraph's Postgres checkpointer (e.g., `AsyncPostgresSaver`) connected to a PostgreSQL database, as mandated by the architecture. Force the `DATABASE_URL` to require PostgreSQL.

## 3. Incorrect Programmatic State Modification (API Layer)
**Location:** `services/chatbot/app/main.py` (Endpoints: `approve-goals`, `reject-goals`, `finish-sharing`)
**Type:** Logic Bug / Architectural Violation (P1)
**Description:** The API layer uses `await app_graph.ainvoke(...)` with forced state dictionaries instead of `await app_graph.update_state(...)` as explicitly documented in `ARCHITECTURE.md`.
**Impact:** **P1.** Using `ainvoke` forces the graph to run the entry point (`elicit_goals_node`) from the beginning. For `reject-goals` and `finish-sharing`, this erroneously triggers full LLM execution passes (Architect and PM agents) on the *previous* user message without any new input. This not only wastes significant tokens and introduces major latency but can also cause the LLM to hallucinate state changes or overwrite gaps dynamically.
**Suggested Fix:** Replace `ainvoke` with `app_graph.update_state(config, {...}, as_node="elicit_goals")` and then resume execution cleanly with `await app_graph.ainvoke(None, config)` exactly as defined in the architectural specification.

## 4. Missing Database Integrity Constraint
**Location:** `services/chatbot/app/database.py` (Lines 38-53)
**Type:** Database Schema Constraint Violation (P1)
**Description:** The `task_dependencies_association` Table does not implement the self-dependency constraint defined in `ARCHITECTURE.md` (`CONSTRAINT chk_no_self_dependency CHECK (task_id <> depends_on_id)`).
**Impact:** **P1.** The database layer fails to prevent tasks from depending on themselves. If the application-level DFS cycle checker is bypassed or fails, circular dependencies will be persisted into the database, causing infinite loops when downstream execution engines attempt to read the DAG.
**Suggested Fix:** Add a `CheckConstraint('task_id <> depends_on_id', name='chk_no_self_dependency')` to the association table in SQLAlchemy.

---
*Note: Request/response schemas, JSON fields, cycle detection DFS logic, and route structure have been verified as compliant with the architecture. Only the P0/P1 constraints listed above represent critical failure points.*
