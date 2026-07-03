# System Architecture
This document details the exhaustive, current state of the Project Manager AI system, tracking the complete tech stack, data flow, and underlying engineering philosophy.

## Frontend Presentation Layer
* **Tech Stack:** React, Vite, Tailwind CSS.
* **Terminology - Vite:** A modern, ultra-fast frontend build tool and local development server.
* **Terminology - Tailwind CSS:** A utility-first styling framework that applies styles directly via class names for rapid UI design without bloated CSS files.
* **The Why:** This stack provides a lightning-fast development environment with modular, reusable components. This allows for the rapid iteration and deployment of a highly responsive, enterprise-grade modern user interface.

## Backend Orchestration Layer
* **Tech Stack:** FastAPI running multiple logical ports internally (Orchestrator API Gateway on 8080/8001, Developer/QC Node on 8002).
* **Terminology - FastAPI:** A high-performance Python web framework built specifically for asynchronous operations and automated data validation.
* **Terminology - Monolithic Architecture:** A unified software design where multiple distinct logical components run within a single shared codebase.
* **The Why:** FastAPI natively handles the heavy asynchronous operations required by LangGraph without blocking the main execution thread. By splitting the internal logic across distinct ports, we have mapped a monolith to behave exactly like a microservice architecture. This guarantees that if production load demands it, we can seamlessly extract the Developer Node to a completely separate remote server without rewriting the application.

## State Management & Data Layer
* **Tech Stack:** LangGraph mapped to a PostgreSQL database via a persistent checkpointer.
* **Terminology - Checkpointer:** A database mechanism that securely saves an AI agent's memory, state, and exact progress at every execution step.
* **The Why:** LangGraph is the industry standard for natively managing complex, cyclical multi-agent workflows (such as our Architect/PM Dual-Core feedback loops). By integrating a PostgreSQL checkpointer, we ensure durable, ACID-compliant transactional state persistence across user sessions. This prevents any data loss during frontend browser reloads or temporary network disconnects.

## AI Inference Engine
* **Tech Stack:** Groq API utilizing the llama-3.3-70b-versatilemodel, orchestrated via LangChain'swith_structured_output parser.
* **Terminology - Pydantic:** A Python library used extensively in FastAPI and LangChain for strict data validation, enforcing exact schema requirements on inputs and outputs.
* **The Why:** Groq offers unmatched inference speed via its proprietary LPU hardware. This raw speed, combined with the comprehensive intelligence of a 70-billion parameter model, guarantees the reasoning depth required to strictly output Pydantic-compliant JSON objects. This architecture is the definitive solution to extracting structured software development tasks without the risk of AI hallucinations or broken parsers.
