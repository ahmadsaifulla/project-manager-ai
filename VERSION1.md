# MVP System Architecture - Version 1.0

## System Overview
The AI Project Manager implements a decoupled client-server architecture designed to handle long-running, agentic AI workflows. The system separates the user interface from the backend processing engine, allowing asynchronous task execution, persistent chat sessions, and modular scalability.

## Frontend Architecture
* **Stack**: Built with Vite and React (TypeScript).
* **Routing**: Managed via React Router for navigating between the project dashboard, chat interface, and Kanban task boards.
* **Environment Configuration**: Uses `VITE_API_URL` to point to the backend Orchestrator API Gateway.
* **Deployment**: Configured for seamless edge deployment on Vercel (managed via `vercel.json`).

## Backend Microservices
The backend operates as a unified cluster composed of three distinct FastAPI nodes:
* **Orchestrator API Gateway (Port 8000)**: The public-facing entry point (bound to `0.0.0.0:$PORT`). It routes incoming client requests to the appropriate internal nodes and manages the overall project state.
* **Chatbot Node (Internal Port 8001)**: Handles real-time conversational logic, prompt elicitation, and human-in-the-loop interactions.
* **Developer Node (Internal Port 8002)**: Executes background technical tasks, repository analysis, and integration logic.

## AI & Agentic Logic
* **Framework**: Built on LangGraph to manage complex, multi-step agent workflows (e.g., Elicit Goals -> Check Approval -> Plan Tasks).
* **LLM Engine**: Powered by Groq LLM for ultra-fast, low-latency inference, utilizing a multi-persona strategy (Product Manager, Technical Architect, Planner Agent).
* **State Management**: LangGraph maintains persistent thread states (tracking message history, `goals_approved`, `elicitation_phase`, and generated tasks) ensuring continuity across user sessions.

## Database Layer
* **Engine**: Uses a live PostgreSQL database (migrated from local SQLite).
* **ORM & Drivers**: Implements SQLAlchemy for object-relational mapping and `psycopg2-binary` as the robust connection driver.
* **Schema**: Relational tables include `users`, `tasks`, and a `task_dependencies` junction table to handle complex Directed Acyclic Graph (DAG) relationships for task planning.

## Deployment Infrastructure
* **Containerization**: A unified Docker strategy (`Dockerfile`) packages all backend microservices into a single container (based on `python:3.11-slim`).
* **Multiplexing**: The `start.sh` script orchestrates the boot sequence—starting the Chatbot and Developer nodes in the background on localhost, while binding the Orchestrator to the public port provided by the host.
* **Hosting**: Deployed on Railway, leveraging its environment variables and persistent volume mounts to retain state.

## Workspace Management
* **Directories**: The `workspace/` and `workspaces/` directories act as persistent storage locations for AI-generated artifacts (e.g., `DRAFT_USER_STORIES.md`, `ARCHITECTURE.md`).
* **Protection**: The `.gitignore` file strictly whitelists `.gitkeep` files to preserve the folder structure while excluding runtime clutter and local databases, preventing backend crashes when saving new operational files.
