# Implementation Plan: Dual-Core AI Project Manager Chatbot (v2)

This document serves as our finalized, exhaustive implementation plan for building the AI Project Manager defined in `project-manager-core.md` and `ARCHITECTURE.md`. We have systematically applied the `/requirements-elicitation` and `/grill-with-docs` skills to evaluate the existing architectural contracts and highlight any remaining gaps for implementation.

## 1. System Overview & Core Objective
We are building a production-grade multi-agent project management system. 
The system operates on a **Dual-Core Processing Loop**:
1. **Architect (Hidden)**: Evaluates user prompts against `architecture/` layer files to safeguard boundaries, writing technical notes to `TEMP_ARCHITECT.md`.
2. **Product Manager (Public)**: Ingests `TEMP_ARCHITECT.md` to translate technical constraints into accessible conversations, extracting user requirements into `DRAFT_USER_STORIES.md`.

## 2. Exhaustive Implementation Plan (What IS Specified)

### A. Environment & Workspace Initialization
- **Action**: Build an initializer service that creates the active workspace structure on project startup if it does not exist:
  ```text
  ├── DRAFT_USER_STORIES.md
  ├── TEMP_ARCHITECT.md
  └── architecture/
      ├── DB_LAYER.md
      ├── API_LAYER.md
      ├── SERVICES_LAYER.md
      └── FRONTEND_LAYER.md
  ```

### B. Database Layer (PostgreSQL)
- **Action**: Set up the PostgreSQL schema as defined in `ARCHITECTURE.md`.
- **Tables to Implement**:
  - `users`: (id, name, email, avatar_url, created_at)
  - `tasks`: (id, project_id, title, description, status [todo, in_progress, done], assignee, priority [low, medium, high, critical], estimated_effort)
  - `task_dependencies`: Junction table (task_id, depends_on_id) with `chk_no_self_dependency` constraint.

### C. Services & AI Layer (LangGraph)
- **Action**: Implement the `ProjectState` using Python's `TypedDict`.
- **Fields**: `messages`, `project_id`, `project_goals`, `goals_approved`, `elicitation_phase`, `tasks`, `clarification_questions`, `detected_gaps`, `current_focus`.
- **Nodes & AI Processing**:
  - **Node 1 (`elicit_goals`)**: Execute the Dual-Core Processing Loop.
    - *Sub-Step 1*: Calculate blast radius and read specific `architecture/` layer files to minimize tokens.
    - *Sub-Step 2*: Invoke LLM for hidden Architect Pass -> output to `TEMP_ARCHITECT.md`.
    - *Sub-Step 3*: Invoke LLM for PM pass -> output user message, append to `DRAFT_USER_STORIES.md`.
  - **Node 2 (`plan_tasks`)**: Triggers after `goals_approved == True`. Executes DFS cycle-check (`validate_no_cycles`) to generate the task DAG.
- **State Checkpointing**: Integrate LangGraph's persistent Checkpointer (e.g., PostgreSQL Checkpointer) to resume conversations across API calls.

### D. API Layer (FastAPI)
- **Action**: Implement the following route contracts:
  - `POST /api/projects/:project_id/messages` - Send user message and invoke graph.
  - `POST /api/projects/:project_id/approve-goals` - Set `goals_approved = True`, trigger task planning.
  - `POST /api/projects/:project_id/reject-goals` - Set `goals_approved = False`, fallback to eliciting.
  - `POST /api/projects/:project_id/finish-sharing` - Transition phase to `stress_testing`.
  - `POST /api/projects/:project_id/unlock-requirements` - Reset back to `listening`.

### E. Frontend Layer (React/Vite)
- **Action**: Build the UI as specified:
  - **ChatConsole**: Chat interface. Welcome prompt on empty state. Renders "Begin Analysis" button if `elicitation_phase == "listening"`. Locks input if `goals_approved == True`.
  - **SidePanel**: Minimally rendered when listening. Expands during `stress_testing` with buttons for "Approve" or "Modify". Displays DAG/Task viewer when requirements are approved.

## 3. Finalized Requirements (Resolved)

> [!TIP]
> All requirements have been elicited and approved. The architecture is locked in for the sandbox build.

### Language & Framework Choices
- **Backend**: FastAPI with Python 3.11+.
- **Frontend**: Vite + React + Tailwind CSS.
- **ORM**: SQLModel / SQLAlchemy for standard integration with FastAPI.
- **Database**: PostgreSQL.

### AI Model Provider
- **Provider**: Groq.
- **Model**: `llama-3.3-70b-versatile`
- **Rationale**: Highly cost-effective, high speed/throughput, huge context limits, and already mocked out in our backend code.

### DAG Visualization Library
- **Library/Format**: Standard Kanban Board.
- **Rationale**: A Kanban board (To Do, In Progress, Done) is a more natural fit for project management tasks compared to complex node graphs, giving users immediate familiarity.

### Authentication Mechanism
- **Auth**: None (Single-user sandbox).
- **Rationale**: To speed up development, we are ignoring login screens. The `users` table can be mocked with a single default developer user for now.

## 4. Execution Workflow

We will execute the build in the following sequence:
1. **Phase 1**: Initialize Vite React frontend & FastAPI backend structure.
2. **Phase 2**: Set up PostgreSQL and SQLModel models (skipping Auth).
3. **Phase 3**: Implement LangGraph `ProjectState`, nodes, and connect to **Groq**.
4. **Phase 4**: Wire FastAPI routes to mutate LangGraph states.
5. **Phase 5**: Build the React `ChatConsole` and the Kanban Board in the `SidePanel`.

---
**Status**: Ready for Execution.
