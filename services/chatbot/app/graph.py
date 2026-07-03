"""
Dual-Core Processing Loop — LangGraph Coordinator Agent.

This module implements the fully generic (domain-agnostic) LangGraph workflow
for the AI Project Manager. It contains:
  1. LLM initialization (Groq via langchain-groq)
  2. Generic system prompts for Architect, PM, and Planner agents
  3. Workspace initialization and blast radius calculation
  4. Graph nodes: elicit_goals and plan_tasks
  5. Conditional routing and graph compilation
"""
import os
import time
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage

from .schemas import (
    ProjectState,
    Task,
    TaskStatus,
    TaskPriority,
    BlastRadiusOutput,
    PMOutput,
    TaskModel,
    PlanTasksOutput,
)


# ─── Configuration ─────────────────────────────────────────────────────────

# Rate-limit delay (seconds) to avoid free-tier throttling on Gemini
LLM_THROTTLE_SECONDS = float(os.getenv("LLM_THROTTLE_SECONDS", "2.0"))

def get_workspace_dir(project_id: str) -> str:
    """Resolve the project-specific workspace directory."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if os.path.basename(root_dir) == "services":
        root_dir = os.path.dirname(root_dir)
    planning_dir = os.path.join(root_dir, "workspaces", project_id, ".planning")
    os.makedirs(planning_dir, exist_ok=True)
    return planning_dir


# ─── LLM Initialization ───────────────────────────────────────────────────

def get_llm_model():
    """
    Returns the ChatOpenAI model initialized with the API key from .env.
    Requires OPENROUTER_API_KEY env var.
    """
    from langchain_openai import ChatOpenAI
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No API key found. Set OPENROUTER_API_KEY environment variable."
        )

    return ChatOpenAI(
        model="meta-llama/llama-3.1-8b-instruct:free",
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.1,
        max_retries=2,
    )


def invoke_llm(model, prompt_input, throttle: bool = True):
    """
    Invoke the LLM with optional throttling for free-tier rate limits.
    """
    if throttle and LLM_THROTTLE_SECONDS > 0:
        time.sleep(LLM_THROTTLE_SECONDS)
    return model.invoke(prompt_input)


# ─── System Prompts (Fully Generic — No Hardcoded Domains) ─────────────────

SYSTEM_ARCHITECT = """You are the hidden technical Architect agent running Step 1 of the Dual-Core Processing Loop.
Your core objective is to evaluate the user's request against the current architecture layer files and silently safeguard system architecture boundaries.

If there is no architecture present (layer files are empty or contain only default headings), treat this as a NEW project and client. There are no constraints to enforce yet.
If there IS an existing architecture, you must defend it from breaking changes. You can allow minor alterations to accommodate the client, but if the request fundamentally breaks the architecture, you MUST produce a strict Friction Stance.

Current Architecture Layers:
=== DB_LAYER.md ===
{db_layer}

=== API_LAYER.md ===
{api_layer}

=== SERVICES_LAYER.md ===
{services_layer}

=== FRONTEND_LAYER.md ===
{frontend_layer}

User Request: {user_request}

Evaluate the request for structural breaking points, data circularity, parameter drift, API contract mismatches, or layout tree violations.
Write your raw, technical, engineering-grade assessment notes directly. Document:
- Your Friction Stance: (Approved, Minor Alteration, or Rejected — Breaking Change)
- Affected layers
- Potential technical frictions, parameter drift, database constraint violations, or API drift
- Structural recommendations

CRITICAL GUARDRAIL: Do NOT output this engineering jargon to the user. This output is purely for background analysis and for the PM agent to read. Keep your output technical and concise.
CRITICAL: You must return valid JSON matching the exact schema.
"""

SYSTEM_PM = """You are the public-facing Product Manager agent running Step 2 of the Dual-Core Processing Loop.
You are a perfect requirements engineer with over 30 years of experience. Your client is a "layman" who knows what they want but does NOT understand technical buzzwords, jargon, or terminologies.

Your role is to read the Architect's technical Friction Stance from TEMP_ARCHITECT.md and translate complex engineering problems into clean product trade-offs (understandable by a 10-year-old).
You are completely generic and neutral — you handle ANY type of project the user describes (web apps, mobile apps, games, data pipelines, IoT systems, anything). You are NOT hardcoded to any specific domain.

We are currently in the "{elicitation_phase}" phase.

### Phase Control Rules:
#### PHASE A: "listening"
- Do NOT say "Welcome" or repeat greetings if there is already a conversation history.
- Read the conversation history. Acknowledge the user's latest input naturally.
- Ask ONE relevant follow-up question to draw out more details about their project.
- Extract high-level requirements and append them systematically to DRAFT_USER_STORIES.md.
- Do NOT populate detected_gaps or clarification_questions.
- Conclude your response by asking if they have anything else to add or if we should begin the architectural analysis.

#### PHASE B: "stress_testing"
- Ingest the technical frictions and warnings from the Architect Notes. If the Architect's Friction Stance rejects a feature because it breaks the architecture:
  1. Translate the rejection into simple, layman-friendly concepts (NO JARGON).
  2. Collaboratively propose a "better solution" with the client that satisfies both their needs and the Architect's constraints.
- Analyze the user request against 4 vectors: Core Intent, Data Scope, User Journey, Constraints.
- Identify requirements gaps and list them in detected_gaps.
- Ask exactly ONE clear question at a time to prevent cognitive overload.
- When all gaps are resolved, set detected_gaps to empty, and format the project goals summary under exactly three headers:
   ### What We Have Done / Finalized
   ### What Needs to Be Done / Next Steps
   ### What to Update

Architect Notes (TEMP_ARCHITECT.md):
{architect_notes}

Current DRAFT_USER_STORIES.md:
{draft_user_stories}

CRITICAL: You must return valid JSON matching the exact schema."""

SYSTEM_PLANNER = """You are the final translation and packaging agent.
Your role is to read the approved project goals and generate a complete "Translation Package" for handoff.
This package must include:
1. A formalized Layman PRD (Product Requirements Document) understandable by the client.
2. A formal Technical Specification document for the engineering team.
3. A structured, cycle-free list of developer tasks (Directed Acyclic Graph) representing an ordered build plan.

Each task must contain:
- ref_id: A unique temporary integer starting from 1 (e.g., 1, 2, 3). This is ONLY for dependency mapping.
- title, description, priority (low/medium/high/critical), estimated_effort
- dependencies: A list of ref_id integers that this task depends on. Must form a valid DAG (no circular dependencies).

Do NOT generate string IDs like TSK-001. Use ONLY integer ref_ids.

You are completely generic — generate tasks appropriate for whatever project the user described.

Approved Project Goals:
{project_goals}

CRITICAL: You must return valid JSON matching the exact schema."""


# ─── DAG Validation ───────────────────────────────────────────────────────

def validate_no_cycles(tasks: List[Task]) -> bool:
    """
    Returns True if the task list represents a valid Directed Acyclic Graph (DAG).
    Returns False if a circular dependency is detected.
    """
    adj = {t.id: t.dependencies for t in tasks}
    visited: Dict[str, int] = {}  # 0: Unvisited, 1: Visiting, 2: Visited

    def has_cycle(node_id: str) -> bool:
        if visited.get(node_id) == 1:
            return True  # Found cycle
        if visited.get(node_id) == 2:
            return False

        visited[node_id] = 1
        for dep_id in adj.get(node_id, []):
            # Guard against invalid ID references
            if dep_id not in adj:
                continue
            if has_cycle(dep_id):
                return True

        visited[node_id] = 2
        return False

    for task in tasks:
        if has_cycle(task.id):
            return False
    return True


# ─── Workspace Initialization ─────────────────────────────────────────────

def initialize_workspace(project_id: str):
    """
    Create the workspace directory structure if it does not exist.
    This is Phase 0 from project-manager-core.md.
    """
    base_dir = get_workspace_dir(project_id)
    arch_dir = os.path.join(base_dir, "architecture")
    os.makedirs(arch_dir, exist_ok=True)

    default_layers = {
        "DB_LAYER.md": "# Database Layer\n\nThis document defines database schemas, relational models, and caching strategies.\n",
        "API_LAYER.md": "# API Layer\n\nThis document defines route contracts, endpoint payloads, and authentication.\n",
        "SERVICES_LAYER.md": "# Services Layer\n\nThis document defines business logic handlers, domain boundaries, and workers.\n",
        "FRONTEND_LAYER.md": "# Frontend Layer\n\nThis document defines UI component trees, page routing, and client states.\n",
    }

    for name, content in default_layers.items():
        path = os.path.join(arch_dir, name)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    # Ensure draft user stories file exists
    draft_file = os.getenv("USER_STORIES_FILE", "DRAFT_USER_STORIES.md")
    draft_path = os.path.join(base_dir, draft_file)
    if not os.path.exists(draft_path):
        with open(draft_path, "w", encoding="utf-8") as f:
            f.write(
                "# Draft User Stories\n\n"
                "This document is the active staging ground for user-approved requirements "
                "gathered during the elicitation session.\n\n---\n\n"
                "*No active session. Waiting for client input.*\n"
            )

    # Ensure temp architect scratchpad exists
    arch_file = os.getenv("ARCHITECT_FILE", "TEMP_ARCHITECT.md")
    temp_path = os.path.join(base_dir, arch_file)
    if not os.path.exists(temp_path):
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(
                "# TEMP_ARCHITECT.md — Background Scratchpad\n\n"
                "## Progressive Depth Elicitation (PDE) — Traffic Light Checklist\n\n"
                "| Vector | Status | Notes |\n"
                "|---|---|---|\n"
                "| **Core Intent** | 🔴 | Not yet assessed. |\n"
                "| **Data Scope** | 🔴 | Not yet assessed. |\n"
                "| **User Journey** | 🔴 | Not yet assessed. |\n"
                "| **Constraints** | 🔴 | Not yet assessed. |\n\n"
                "## Architectural Friction Log\n\n- None.\n\n"
                "## Affected Layers\n\n- None.\n"
            )


# ─── Blast Radius Calculation ─────────────────────────────────────────────

def calculate_blast_radius(user_request: str) -> List[str]:
    """
    Use the LLM to determine which architecture layers are affected by the user's message.
    This is the token-optimization step from project-manager-core.md (Section 3).
    """
    prompt = """You are a software architect analyzing a user request to determine the blast radius of affected architecture layers.
Which of the following layers are affected by this request:
1. DB_LAYER.md (database schemas, SQL, cache, tables, relationships)
2. API_LAYER.md (HTTP routes, payloads, API contracts, endpoints, query parameters)
3. SERVICES_LAYER.md (business logic, backend helpers, background tasks, domain rules, state machines)
4. FRONTEND_LAYER.md (UI components, styling, pages, layout, buttons, actions, client state)

If the request is a general greeting, welcome, or doesn't target any specific architectural component, return an empty list.

User Request: {user_request}

Return a list of filenames that are affected."""

    try:
        model = get_llm_model()
        structured_model = model.with_structured_output(BlastRadiusOutput)
        result = invoke_llm(structured_model, prompt.format(user_request=user_request))
        return result.affected_layers
    except Exception as e:
        logger.error(f"[BlastRadius] Error: {e}. Defaulting to all layers.")
        return ["DB_LAYER.md", "API_LAYER.md", "SERVICES_LAYER.md", "FRONTEND_LAYER.md"]


# ─── Dual-Core Processing Functions ───────────────────────────────────────

def run_hidden_backend_pass(user_request: str, affected_layers: List[str], project_id: str) -> str:
    """
    Step 1: The Hidden Architect Pass.
    Reads targeted architecture layer files, invokes the Architect LLM,
    and writes the assessment to TEMP_ARCHITECT.md.
    """
    initialize_workspace(project_id)
    base_dir = get_workspace_dir(project_id)

    layers = {}
    all_layer_names = ["DB_LAYER.md", "API_LAYER.md", "SERVICES_LAYER.md", "FRONTEND_LAYER.md"]
    for f_name in all_layer_names:
        if not affected_layers or f_name in affected_layers:
            path = os.path.join(base_dir, "architecture", f_name)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    layers[f_name] = f.read()
            else:
                layers[f_name] = "Not initialized yet."
        else:
            layers[f_name] = "(Skipped: Outside the blast radius of the user request)"

    prompt = SYSTEM_ARCHITECT.format(
        db_layer=layers["DB_LAYER.md"],
        api_layer=layers["API_LAYER.md"],
        services_layer=layers["SERVICES_LAYER.md"],
        frontend_layer=layers["FRONTEND_LAYER.md"],
        user_request=user_request or "None (initial check)",
    )

    model = get_llm_model()
    response = invoke_llm(model, prompt)
    assessment = response.content

    # Write assessment to TEMP_ARCHITECT.md (or configured file)
    arch_file = os.getenv("ARCHITECT_FILE", "TEMP_ARCHITECT.md")
    temp_architect_path = os.path.join(base_dir, arch_file)
    with open(temp_architect_path, "w", encoding="utf-8") as f:
        f.write(assessment)

    return assessment


def run_public_conversational_pass(
    messages_history_str: str,
    architect_notes: str,
    elicitation_phase: str,
    project_id: str,
) -> PMOutput:
    """
    Step 2: The Public Product Manager Pass.
    Invokes the PM LLM with structured output, updates DRAFT_USER_STORIES.md.
    """
    base_dir = get_workspace_dir(project_id)
    draft_file = os.getenv("USER_STORIES_FILE", "DRAFT_USER_STORIES.md")
    draft_path = os.path.join(base_dir, draft_file)
    draft_content = ""
    if os.path.exists(draft_path):
        with open(draft_path, "r", encoding="utf-8") as f:
            draft_content = f.read()

    prompt = SYSTEM_PM.format(
        elicitation_phase=elicitation_phase,
        architect_notes=architect_notes,
        draft_user_stories=draft_content,
    )

    model = get_llm_model()
    structured_model = model.with_structured_output(PMOutput)

    llm_input = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                f"Here is the full conversation history:\n{messages_history_str}\n\n"
                "Please analyze, update draft user stories, extract remaining gaps, "
                "and formulate the layman-friendly response."
            ),
        },
    ]

    result = invoke_llm(structured_model, llm_input)

    # Persist updated draft user stories
    if result.updated_draft_user_stories:
        with open(draft_path, "w", encoding="utf-8") as f:
            f.write(result.updated_draft_user_stories)

    return result


# ─── Graph Nodes ───────────────────────────────────────────────────────────

def elicit_goals_node(state: ProjectState) -> Dict[str, Any]:
    """
    The main Dual-Core orchestration node.
    Runs the hidden Architect pass, then the public PM pass, per turn.
    """
    messages = state.get("messages", [])
    phase = state.get("elicitation_phase", "listening")
    goals_approved = state.get("goals_approved", False)

    if goals_approved:
        return {"current_focus": "planning_tasks"}

    # Extract the last human message
    last_human_msg = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            last_human_msg = m.content
            break

    project_id = state.get("project_id")
    if not project_id:
        raise ValueError("Missing project_id in state")

    initialize_workspace(project_id)

    # Handle "Modify" rejection loop
    detected_gaps = state.get("detected_gaps", [])
    if detected_gaps and detected_gaps[0].startswith("Modify:"):
        last_msg = messages[-1] if messages else None
        if not isinstance(last_msg, HumanMessage):
            question = (
                "I understand. Let's adjust the requirements. "
                "What specific changes or additions would you like to make to the project goals?"
            )
            return {
                "detected_gaps": detected_gaps,
                "clarification_questions": [question],
                "messages": [AIMessage(content=question)],
                "current_focus": "eliciting_goals",
            }

    # Step 1: Calculate blast radius (token optimization)
    affected_layers = calculate_blast_radius(last_human_msg) if last_human_msg else []

    # Step 2: Run Hidden Architect Pass
    architect_notes = run_hidden_backend_pass(last_human_msg, affected_layers, project_id)

    # Build conversation history string for PM context
    messages_history_str = ""
    for msg in messages:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        messages_history_str += f"{role}: {msg.content}\n"

    # Step 3: Run Public PM Pass
    pm_result = run_public_conversational_pass(
        messages_history_str, architect_notes, phase, project_id
    )

    out_gaps = pm_result.detected_gaps
    out_questions = [pm_result.next_question] if out_gaps else []

    # In listening phase, suppress gaps — just listen
    if phase == "listening":
        out_gaps = []
        out_questions = []

    return {
        "project_goals": pm_result.project_goals,
        "detected_gaps": out_gaps,
        "clarification_questions": out_questions,
        "messages": [AIMessage(content=pm_result.next_question)],
        "current_focus": "eliciting_goals",
    }


def plan_tasks_node(state: ProjectState) -> Dict[str, Any]:
    """
    Generates structured developer tasks from the approved project goals.
    Maps integer ref_ids to UUIDs, persists to DB, validates DAG integrity.
    """
    import uuid
    from .database import SessionLocal, TaskDb, task_dependencies_association

    goals = state.get("project_goals", "")
    project_id = state.get("project_id", "")
    prompt = SYSTEM_PLANNER.format(project_goals=goals)

    model = get_llm_model()
    structured_model = model.with_structured_output(PlanTasksOutput)
    result = invoke_llm(structured_model, prompt)

    # Build deterministic ref_id -> UUID mapping
    ref_to_uuid: Dict[int, str] = {}
    for t in result.tasks:
        ref_to_uuid[t.ref_id] = f"{project_id[:8]}-{uuid.uuid4().hex[:8]}"

    # Construct Task objects with real UUIDs and mapped dependencies
    tasks: List[Task] = []
    for t in result.tasks:
        priority_val = TaskPriority.MEDIUM
        p_lower = t.priority.lower()
        if "low" in p_lower:
            priority_val = TaskPriority.LOW
        elif "high" in p_lower:
            priority_val = TaskPriority.HIGH
        elif "critical" in p_lower:
            priority_val = TaskPriority.CRITICAL

        mapped_deps = [ref_to_uuid[dep] for dep in t.dependencies if dep in ref_to_uuid]

        tasks.append(
            Task(
                id=ref_to_uuid[t.ref_id],
                title=t.title,
                description=t.description,
                status=TaskStatus.TODO,
                assignee=None,
                priority=priority_val,
                estimated_effort=t.estimated_effort,
                dependencies=mapped_deps,
            )
        )

    # Post-processing: validate DAG integrity
    if not validate_no_cycles(tasks):
        logger.warning("[PlanTasks] WARNING: Circular dependency detected. Clearing all dependencies.")
        for t in tasks:
            t.dependencies = []

    # Persist tasks to the database inside the node
    db = SessionLocal()
    try:
        # Clean previous tasks for this project
        db.execute(
            task_dependencies_association.delete().where(
                task_dependencies_association.c.task_id.in_(
                    db.query(TaskDb.id).filter(TaskDb.project_id == project_id)
                )
            )
        )
        db.commit()
        db.query(TaskDb).filter(TaskDb.project_id == project_id).delete()
        db.commit()

        # Insert new tasks
        for t in tasks:
            db_t = TaskDb(
                id=t.id,
                project_id=project_id,
                title=t.title,
                description=t.description,
                status=t.status,
                assignee=None,
                priority=t.priority,
                estimated_effort=t.estimated_effort,
            )
            db.add(db_t)
        db.commit()

        # Insert dependency relations
        for t in tasks:
            if t.dependencies:
                db_t = db.query(TaskDb).filter(TaskDb.id == t.id).first()
                if db_t:
                    for dep_id in t.dependencies:
                        dep_task = db.query(TaskDb).filter(TaskDb.id == dep_id).first()
                        if dep_task:
                            db_t.dependencies.append(dep_task)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[PlanTasks] DB commit failed: {e}")
        raise RuntimeError(f"Failed to persist tasks to database: {e}")
    finally:
        db.close()

    return {
        "tasks": tasks,
        "current_focus": "idle",
    }


# ─── Conditional Router ───────────────────────────────────────────────────

def route_next_node(state: ProjectState) -> str:
    """Route to plan_tasks if goals are approved, otherwise END (wait for next input)."""
    if state.get("goals_approved", False):
        return "plan_tasks"
    return END


# ─── Graph Compilation ────────────────────────────────────────────────────

workflow = StateGraph(ProjectState)

workflow.add_node("elicit_goals", elicit_goals_node)
workflow.add_node("plan_tasks", plan_tasks_node)

workflow.set_entry_point("elicit_goals")

workflow.add_conditional_edges(
    "elicit_goals",
    route_next_node,
    {
        "plan_tasks": "plan_tasks",
        END: END,
    },
)

workflow.add_edge("plan_tasks", END)

