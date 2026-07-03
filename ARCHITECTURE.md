# System Architecture

This document details the current state of the Project Manager AI system, tracking the complete tech stack and data flow.

## Current Tech Stack and Data Flow

* **Frontend:** React, Vite, Tailwind CSS.
  * *Why:* Provides a lightning-fast development environment with utility-first styling to deliver a highly responsive, modern UI.
* **Backend Monolith:** FastAPI running multiple logical nodes (Orchestrator on 8080/8001, QC/Developer on 8002).
  * *Why:* FastAPI provides high-performance asynchronous routing. Splitting the logic into distinct ports/nodes internally mimics a microservice architecture, allowing for easy extraction into true microservices if production load demands it later.
* **State Management:** LangGraph with PostgreSQL checkpointer.
  * *Why:* LangGraph natively handles complex, cyclical multi-agent workflows (like the Architect/PM Dual-Core loops). The Postgres checkpointer ensures durable, transactional state persistence across sessions and frontend reloads.
* **LLM Engine:** Groq API utilizing `llama-3.3-70b-versatile` with LangChain's strict `with_structured_output` parser.
  * *Why:* Groq offers unmatched inference speed via LPU hardware. Combining this speed with a massive 70B parameter model guarantees the reasoning depth required to strictly adhere to Pydantic JSON schemas without hallucinating or breaking the parser.
