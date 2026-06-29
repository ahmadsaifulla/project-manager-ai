"""
FastAPI application for the AI Project Manager.
Implements all route contracts defined in ARCHITECTURE.md.
"""
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from typing import List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage

from dotenv import load_dotenv
load_dotenv()

from .database import init_db, get_db, TaskDb, UserDb, task_dependencies_association, engine
from .schemas import Task, TaskStatus, TaskPriority
from .graph import app_graph, ProjectState, get_llm_model, invoke_llm, BASE_DIR


# ─── State Finalization Helpers ────────────────────────────────────────────

def get_next_snapshot_filename(base_dir: str) -> str:
    """Determine the next sequential snapshot filename (R[Index][DDMMYY].md)."""
    today_str = datetime.now().strftime("%d%m%y")
    files = os.listdir(base_dir) if os.path.isdir(base_dir) else []
    max_index = 0
    pattern = re.compile(r"^R(\d+)\d{6}\.md$")
    for f in files:
        m = pattern.match(f)
        if m:
            try:
                idx = int(m.group(1))
                if idx > max_index:
                    max_index = idx
            except ValueError:
                pass
    next_index = max_index + 1
    return f"R{next_index}{today_str}.md"


def compile_snapshot_timeline(messages: List[Dict[str, Any]]) -> str:
    """Use LLM to extract a timeline of key design decisions from the conversation."""
    messages_history_str = ""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        messages_history_str += f"{role.upper()}: {content}\n\n"

    prompt = f"""You are a technical project manager.
Analyze the following conversation history of a project planning session and extract a timeline of key design decisions made during this session.
Format your response as a numbered markdown list.

Here is the conversation history:
{messages_history_str}

Please generate the timeline of design decisions."""

    try:
        model = get_llm_model()
        response = invoke_llm(model, prompt)
        return response.content
    except Exception as e:
        print(f"[Snapshot] Error compiling timeline: {e}")
        return "1. **Requirements finalized**: The user approved the project requirements."


def consolidate_architecture(base_dir: str):
    """Consolidate architecture/ layer files into a single ARCHITECTURE.md."""
    arch_dir = os.path.join(base_dir, "architecture")
    layers = ["DB_LAYER.md", "API_LAYER.md", "SERVICES_LAYER.md", "FRONTEND_LAYER.md"]

    combined_content = """# AI Project Manager Architecture Specification

This document consolidates the layered architecture specifications for the AI Project Manager chatbot system. It serves as an immutable handoff for downstream developer agents.

---
"""

    layer_titles = {
        "DB_LAYER.md": "1. Database Layer",
        "API_LAYER.md": "2. API Layer",
        "SERVICES_LAYER.md": "3. Services Layer",
        "FRONTEND_LAYER.md": "4. Frontend Layer",
    }

    for layer in layers:
        layer_path = os.path.join(arch_dir, layer)
        if os.path.exists(layer_path):
            with open(layer_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            title = layer_titles.get(layer, layer)

            # Strip the first heading if it duplicates the layer title
            lines = content.splitlines()
            if lines and (lines[0].startswith("# ") or lines[0].startswith("## ")):
                content = "\n".join(lines[1:]).strip()

            combined_content += f"\n## {title}\n\n{content}\n\n---\n"

    dest_path = os.path.join(base_dir, "ARCHITECTURE.md")
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(combined_content.rstrip("\n-") + "\n")


def execute_state_finalization(project_id: str, state: Dict[str, Any]):
    """
    State Finalization Contract (project-manager-core.md Section 6):
    1. Compile snapshot log R[Index][DDMMYY].md
    2. Consolidate architecture/ into ARCHITECTURE.md
    """
    base_dir = BASE_DIR

    # 1. Create snapshot file
    filename = get_next_snapshot_filename(base_dir)
    filepath = os.path.join(base_dir, filename)

    m = re.match(r"^R(\d+)(\d{6})\.md$", filename)
    session_index = m.group(1) if m else "1"
    date_str = datetime.now().strftime("%B %d, %Y")

    # Build messages list for timeline compilation
    messages = []
    for msg in state.get("messages", []):
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        messages.append({"role": role, "content": msg.content})
    if not messages:
        messages = state.get("messages", [])

    timeline = compile_snapshot_timeline(messages)

    snapshot_content = f"""# Session Snapshot Log: {filename.replace('.md', '')}

* **Date**: {date_str}
* **Session Index**: {session_index}
* **Project**: {project_id}

## 1. Timeline of Design Decisions

{timeline}

## 2. File State References
* DRAFT_USER_STORIES.md - Confirmed requirements.
* TEMP_ARCHITECT.md - Active technical assessments.
* architecture/DB_LAYER.md - SQL schemas.
* architecture/API_LAYER.md - HTTP REST endpoints.
* architecture/SERVICES_LAYER.md - Service logic, state, and rules.
* architecture/FRONTEND_LAYER.md - UI design and components.
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(snapshot_content)

    # 2. Consolidate architecture
    consolidate_architecture(base_dir)


# ─── Lifespan ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize DB schemas and seed sample users on startup."""
    init_db()
    db = next(get_db())
    try:
        if db.query(UserDb).count() == 0:
            sample_users = [
                UserDb(
                    id="usr_default",
                    name="Developer",
                    email="dev@localhost",
                    avatar_url=None,
                ),
            ]
            db.add_all(sample_users)
            db.commit()
    finally:
        db.close()
    yield


# ─── FastAPI Application ──────────────────────────────────────────────────

app = FastAPI(title="AI Project Manager API", version="2.0.0", lifespan=lifespan)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helper Functions ─────────────────────────────────────────────────────

def format_graph_state(state: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    """Convert LangGraph state into API-friendly JSON response."""
    messages_list = []
    for msg in state.get("messages", []):
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        messages_list.append({"role": role, "content": msg.content})

    return {
        "project_id": project_id,
        "elicitation_phase": state.get("elicitation_phase", "listening"),
        "goals_approved": state.get("goals_approved", False),
        "project_goals": state.get("project_goals", ""),
        "detected_gaps": state.get("detected_gaps", []),
        "clarification_questions": state.get("clarification_questions", []),
        "messages": messages_list,
        "current_focus": state.get("current_focus", "idle"),
        "tasks": [task.model_dump() for task in state.get("tasks", [])],
    }


async def get_project_state(project_id: str) -> Dict[str, Any]:
    """Fetch or initialize the LangGraph thread state for a project."""
    config = {"configurable": {"thread_id": project_id}}
    state_snap = await app_graph.aget_state(config)
    if not state_snap.values:
        init_values = {
            "messages": [],
            "project_id": project_id,
            "project_goals": "",
            "goals_approved": False,
            "elicitation_phase": "listening",
            "tasks": [],
            "clarification_questions": [],
            "detected_gaps": [],
            "current_focus": "idle",
        }
        await app_graph.aupdate_state(config, init_values)
        return init_values
    return state_snap.values


# ─── API Endpoints ────────────────────────────────────────────────────────

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Fetch the current project state."""
    state = await get_project_state(project_id)
    return format_graph_state(state, project_id)


@app.post("/api/projects/{project_id}/messages")
async def post_message(project_id: str, payload: Dict[str, str] = Body(...)):
    """Send a user message and invoke the LangGraph flow."""
    user_content = payload.get("content", "").strip()
    if not user_content:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    config = {"configurable": {"thread_id": project_id}}
    await get_project_state(project_id)  # Ensure state exists

    human_msg = HumanMessage(content=user_content)
    updated_state_snap = await app_graph.ainvoke({"messages": [human_msg]}, config)

    return format_graph_state(updated_state_snap, project_id)


@app.post("/api/projects/{project_id}/finish-sharing")
async def finish_sharing(project_id: str):
    """Transition from listening phase to stress_testing phase."""
    config = {"configurable": {"thread_id": project_id}}
    state = await get_project_state(project_id)

    if state.get("elicitation_phase") != "listening":
        raise HTTPException(status_code=400, detail="Project is not in listening phase")

    updated_state_snap = await app_graph.ainvoke(
        {"elicitation_phase": "stress_testing", "current_focus": "eliciting_goals"},
        config,
    )
    return format_graph_state(updated_state_snap, project_id)


@app.post("/api/projects/{project_id}/approve-goals")
async def approve_goals(project_id: str, db: Session = Depends(get_db)):
    """Approve goals, trigger task generation, and persist tasks to the database."""
    config = {"configurable": {"thread_id": project_id}}
    state = await get_project_state(project_id)

    if state.get("goals_approved"):
        raise HTTPException(status_code=400, detail="Goals are already approved")

    if state.get("elicitation_phase") != "stress_testing" or state.get("detected_gaps"):
        raise HTTPException(
            status_code=400, detail="Cannot approve goals with unresolved gaps"
        )

    # Trigger goal approval and task generation
    concluding_msg = AIMessage(content="Got it! Starting your project now...")
    updated_state_snap = await app_graph.ainvoke(
        {
            "goals_approved": True,
            "elicitation_phase": "goals_approved",
            "messages": [concluding_msg],
        },
        config,
    )

    # Persist generated tasks to SQL database
    generated_tasks: List[Task] = updated_state_snap.get("tasks", [])

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
    for t in generated_tasks:
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
    for t in generated_tasks:
        if t.dependencies:
            db_t = db.query(TaskDb).filter(TaskDb.id == t.id).first()
            if db_t:
                for dep_id in t.dependencies:
                    dep_task = db.query(TaskDb).filter(TaskDb.id == dep_id).first()
                    if dep_task:
                        db_t.dependencies.append(dep_task)
    db.commit()

    # State finalization (snapshot log + architecture consolidation)
    try:
        execute_state_finalization(project_id, updated_state_snap)
    except Exception as e:
        print(f"[Finalization] Error: {e}")

    return format_graph_state(updated_state_snap, project_id)


@app.post("/api/projects/{project_id}/reject-goals")
async def reject_goals(project_id: str):
    """Reject goals and loop back to the elicitation conversation."""
    config = {"configurable": {"thread_id": project_id}}
    state = await get_project_state(project_id)

    if state.get("goals_approved"):
        raise HTTPException(
            status_code=400, detail="Cannot reject already approved requirements"
        )

    updated_state_snap = await app_graph.ainvoke(
        {
            "goals_approved": False,
            "elicitation_phase": "stress_testing",
            "current_focus": "eliciting_goals",
            "detected_gaps": [
                "Modify: What specific changes or additions would you like to make to the project goals?"
            ],
        },
        config,
    )
    return format_graph_state(updated_state_snap, project_id)


@app.post("/api/projects/{project_id}/unlock-requirements")
async def unlock_requirements(project_id: str, db: Session = Depends(get_db)):
    """Reset back to listening phase, allowing the user to add more requirements."""
    config = {"configurable": {"thread_id": project_id}}
    await get_project_state(project_id)

    # Remove persisted tasks for this project
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

    # Revert to listening phase
    updated_state_snap = await app_graph.ainvoke(
        {
            "goals_approved": False,
            "elicitation_phase": "listening",
            "current_focus": "idle",
            "tasks": [],
            "detected_gaps": [],
            "clarification_questions": [],
        },
        config,
    )
    return format_graph_state(updated_state_snap, project_id)


@app.get("/api/projects/{project_id}/tasks")
async def get_project_tasks(project_id: str, db: Session = Depends(get_db)):
    """Fetch persisted tasks for a project from the database."""
    tasks = db.query(TaskDb).filter(TaskDb.project_id == project_id).all()
    results = []
    for t in tasks:
        results.append(
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "status": t.status.value,
                "assignee": t.assignee,
                "priority": t.priority.value,
                "estimated_effort": t.estimated_effort,
                "dependencies": [dep.id for dep in t.dependencies],
            }
        )
    return results


@app.get("/api/users")
def get_users(db: Session = Depends(get_db)):
    """Fetch all registered users."""
    users = db.query(UserDb).all()
    return [
        {"id": u.id, "name": u.name, "email": u.email, "avatar_url": u.avatar_url}
        for u in users
    ]
