# FULL SYSTEM ARCHITECTURE & VULNERABILITY AUDIT

## Current System Architecture
The system employs a multi-tenant, three-node microservices design communicating via HTTP proxies.
- **Frontend (React)**: Communicates exclusively with the Orchestrator via REST (`/api/*`).
- **Orchestrator Node (Port 8000)**: Serves as the API Gateway. It maintains an in-memory global `project_state` dictionary and reverse-proxies requests to either the Chatbot Node or the Developer Node.
- **Chatbot Node (Port 8001)**: The core state machine and database owner. It uses `LangGraph` for a Dual-Core Processing Loop (Architect + PM LLM passes) and handles PostgreSQL persistence (projects, tasks, requirements).
- **Developer Node (Port 8002)**: The Quality Control (QC) evaluator. Currently implemented as a synchronous LangGraph executor that takes task details and evaluates code diffs.

## Successes
- **CQRS Kanban State**: The Chatbot's planner agent efficiently uses a Command Query Responsibility Segregation (CQRS) pattern. The `ProjectPlanCommand` schema allows the LLM to emit atomic, idempotent `CREATE`, `UPDATE`, and `DELETE` commands, which reliably handle state mutations.
- **Proxy Routing**: The Orchestrator's reverse proxy successfully encapsulates the microservices, presenting a unified `/api/` surface to the frontend, preventing CORS nightmares across multiple ports.
- **Graph Separation**: LangGraph state is cleanly managed with a well-defined `ProjectState` schema, separating the conversational (listening) phase from the task execution (planning) phase.

## Breaking Points & Leakages
- **Event Loop Blocking (Performance Leak)**: The Chatbot Node uses synchronous SQLAlchemy (`db.query()`) inside `async def` route handlers (e.g., `list_projects`, `create_project`). This blocks the entire ASGI event loop during database I/O, completely breaking FastAPI's concurrency model.
- **Unhandled Exceptions**: In `orchestrator/app/main.py`, `await request.json()` is called without error handling in routes like `proxy_post_message`. An empty body will throw a `JSONDecodeError`, crashing the request ungracefully.
- **Unvalidated Pydantic Models**: The Developer node lacks validation on its `QCRequest`, and the Chatbot's `TaskUpdateRequest` relies on basic strings instead of Enums for `status`, which could trigger 500 errors on database flushes instead of a clean 422 HTTP error.
- **Insecure Data Passing**: The `X-Tenant-ID` is passed as a plain text header without any cryptographic validation.

## Pain Points & Challenges
- **Hardcoded Values & Tight Coupling**:
  - The Chatbot node explicitly hardcodes `http://127.0.0.1:8000/api/qc/evaluate` (Line 623) to trigger the QC node, creating a circular dependency back to the gateway.
  - The QC trigger passes hardcoded `"mock-repo"` and `"mock-branch"`.
  - The Orchestrator's `project_state` hardcodes `http://127.0.0.1:8001` and `8002`.
- **Ephemeral Global State**: The Orchestrator relies on an in-memory python dictionary (`project_state`) to store the routing config. This state is wiped every time the server restarts.
- **Context Window Leak**: The LangGraph state continuously appends messages without truncation or summarization. Long conversations will inevitably exceed the LLM context window limits and crash the graph pipeline.

## Absences
- **JWT Authentication**: There is absolutely no authentication mechanism. The `X-Tenant-ID` acts as a naive multitenancy gate, but there are no signed tokens, session states, or OAuth flows.
- **User Mapping**: The RBAC `require_role` dependency (Chatbot `main.py:345`) is entirely faked: `user = db.query(UserDb).filter(UserDb.id == "usr_default").first()`. Any request automatically receives "MANAGER" privileges regardless of the actual user identity.
- **QC Node Background Tasks**: The Developer Node executes `qc_graph.invoke(initial_state)` synchronously on the API route. LLM chains can take minutes; this will definitively cause HTTP timeouts. It must be refactored into a `BackgroundTask` or Celery queue.
- **GitHub Context Ingestion**: The system demands a `repo_name` and `branch_name` but lacks the infrastructure (Webhooks, GitHub App integration) to actually clone code, read commits, or generate the `git_diff` required for the QC state.
