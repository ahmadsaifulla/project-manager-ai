# Kanban Phase Updates (Version 2)
This document outlines the exhaustive technical upgrades achieved during the Kanban sprint stabilization phase.

## Frontend Shielding: React Error Boundaries
* **Terminology - Error Boundary:** A React component that acts as a secure container, catching JavaScript rendering errors anywhere in its child component tree to prevent the entire application UI from crashing.
* **The Upgrade:** We implemented robust error handling flows utilizing Error Boundaries coupled with Toast notifications (non-intrusive pop-up alerts) across the user interface.
* **The Mechanics:** When the backend LangGraph engine suffers a fatal crash (e.g., a 500 Internal Server Error), the React frontend previously absorbed the corrupt state and unmounted the UI, resulting in a "White Screen of Death." The Error Boundary now intercepts this cascading failure, halts the UI unmount, and triggers a Toast notification.
* **The Why:** To ensure ultimate session stability. The user can seamlessly recover from backend infrastructure failures without losing their chat history or session data.

## Backend Architecture: LangGraph DAG Transactional Execution
* **Terminology - DAG (Directed Acyclic Graph):** A unidirectional flow chart used to map out the logical, step-by-step execution path of an AI agent.
* **Terminology - Transactional Execution:** An all-or-nothing database operation that ensures data is only saved if the entire multi-step process succeeds without throwing an exception.
* **The Upgrade:** We completely restructured the API routing (specifically approve_goals) to enforce strict transactional execution. The ainvoke(LLM generation) command must now execute and succeed entirely beforeaupdate_state (Database Checkpointing) is permitted to run.
* **The Mechanics:** Previously, the system updated the project state to "Approved" in the database before the AI generated the tasks. If the AI timed out or crashed, the database permanently locked the project in an approved state without any tasks existing, returning permanent 400 Bad Request errors to the user.
* **The Why:** To eliminate state-machine race conditions and prevent database corruption. Shielding the Postgres checkpointer behind a try/except block guarantees that failed LLM generations are cleanly discarded without polluting the application state.

## Database Architecture: PostgreSQL ENUM Expansion
* **Terminology - ENUM (Enumerated Type):** A strict database data type containing a static, predefined set of allowed values, used to enforce data integrity.
* **Terminology - Autocommit:** A database mode that executes commands instantly outside of a bundled transaction block, required for specific structural schema changes.
* **The Upgrade:** We added an evaluation_feedbackcolumn to the tasks table and expanded thetaskstatus ENUM.
* **The Mechanics:** The React UI was updated to support "IN_QC" and "IN_QA" Kanban columns. However, dragging a task triggered a backend crash (psycopg2.errors.InvalidTextRepresentation) because PostgreSQL's strict typing rejected the new string. We wrote a temporary SQLAlchemy script utilizing autocommit=Trueto execute rawALTER TYPE SQL commands, injecting the new states into the database registry.
* **The Why:** To natively support the Quality Control and Quality Assurance pipelines within the database schema, ensuring smooth, crash-free data flow across the Kanban board.
