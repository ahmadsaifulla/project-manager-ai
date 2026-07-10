"""
FastAPI application for the AI Project Manager.
Implements all route contracts defined in ARCHITECTURE.md.
"""
import os
import re
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)
from datetime import datetime, UTC
from typing import List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Body, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage

from dotenv import load_dotenv
load_dotenv()

from .database import init_db, get_db, TaskDb, UserDb, ProjectDb, task_dependencies_association, engine, DATABASE_URL, SessionLocal
from .schemas import Task, TaskStatus, TaskPriority, Project
from .graph import workflow, ProjectState, get_llm_model, invoke_llm, get_workspace_dir
from psycopg_pool import AsyncConnectionPool
from langchain_groq import ChatGroq
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import httpx
from pydantic import BaseModel
import httpx
from pydantic import BaseModel

app_graph = None


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
        logger.error(f"[Snapshot] Error compiling timeline: {e}")
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
    base_dir = get_workspace_dir(project_id)

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
    """Initialize Postgres checkpointer, DB schemas, and seed sample users on startup."""
    global app_graph
    pool = AsyncConnectionPool(DATABASE_URL, kwargs={"autocommit": True}, open=False)
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    app_graph = workflow.compile(checkpointer=checkpointer)

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
    
    try:
        yield
    finally:
        await pool.close()


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
        "tasks": [task if isinstance(task, dict) else task.model_dump() for task in state.get("tasks", [])],
    }


async def get_project_state(project_id: str) -> Dict[str, Any]:
    """Fetch or initialize the LangGraph thread state for a project."""
    config = {"configurable": {"thread_id": project_id, "project_id": project_id}}
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


def parse_title_from_text(text: str) -> str:
    """Extract a concise title from the first line of the requirements text."""
    if not text or not text.strip():
        return "New Project"
    first_line = text.strip().split('\n')[0]
    return first_line.replace('#', '').strip()[:50]

# ─── Project Routes ────────────────────────────────────────────────────────

@app.get("/api/projects", response_model=List[Project])
async def list_projects(db: Session = Depends(get_db)):
    """List all projects in the database."""
    projects = db.query(ProjectDb).all()
    return projects


@app.post("/api/projects", response_model=Project)
async def create_project(project: Project, db: Session = Depends(get_db)):
    """Create a new project in the database."""
    project_name = project.name.strip() if project.name and project.name.strip() else "New Project"
    
    db_project = ProjectDb(
        id=project.id,
        name=project_name,
        description=project.description,
        status=project.status,
        sprint=project.sprint,
        progress=project.progress,
        due_date=project.due_date,
        tags=project.tags,
        accent_color=project.accent_color
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    # Create boilerplate files for the developer node
    import os
    workspace_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "workspaces", project.id)
    planning_dir = os.path.join(workspace_dir, ".planning")
    os.makedirs(planning_dir, exist_ok=True)

    with open(os.path.join(planning_dir, "TEMP_ARCHITECTURE.md"), "w") as f:
        f.write(f"# Architecture for {project.name}\n\nDraft architecture document.")

    with open(os.path.join(planning_dir, "DRAFT_USER_STORIES.md"), "w") as f:
        f.write(f"# User Stories for {project.name}\n\nDraft user stories document.")

    return db_project


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str, db: Session = Depends(get_db)):
    """Fetch the current project state, merging DB metadata with LangGraph state."""
    db_project = db.query(ProjectDb).filter(ProjectDb.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    state = await get_project_state(project_id)
    graph_data = format_graph_state(state, project_id)
    
    # Merge DB metadata with Graph state
    response_data = {
        **graph_data,
        "name": db_project.name,
        "description": db_project.description,
        "status": db_project.status,
        "sprint": db_project.sprint,
        "progress": db_project.progress,
        "due_date": db_project.due_date,
        "tags": db_project.tags,
        "accent_color": db_project.accent_color
    }
    return response_data


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project and its associated tasks."""
    db_project = db.query(ProjectDb).filter(ProjectDb.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(db_project)
    db.commit()

    # Flush LangGraph checkpoints to prevent ghost states
    try:
        pool = app_graph.checkpointer.conn
        async with pool.connection() as conn:
            await conn.execute("DELETE FROM checkpoints WHERE thread_id = %s", (project_id,))
            await conn.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (project_id,))
            await conn.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (project_id,))
    except Exception as e:
        print(f"Checkpointer flush on delete ignored or failed: {e}")

    return {"status": "success"}


@app.post("/api/projects/{project_id}/messages")
async def post_message(project_id: str, payload: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    """Send a user message and invoke the LangGraph flow."""
    db_project = db.query(ProjectDb).filter(ProjectDb.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    user_content = payload.get("content", "").strip()
    if not user_content:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    print(f"CURRENT_PROJECT_CONTEXT: {user_content}")

    config = {"configurable": {"thread_id": project_id, "project_id": project_id}}
    state = await get_project_state(project_id)  # Ensure state exists

    if not state.get("messages"):
        # Explicitly clear state and memory for a new interaction
        try:
            pool = app_graph.checkpointer.conn
            async with pool.connection() as conn:
                await conn.execute("DELETE FROM checkpoints WHERE thread_id = %s", (project_id,))
                await conn.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (project_id,))
                await conn.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (project_id,))
        except Exception as e:
            print(f"Checkpointer flush ignored or failed: {e}")
            
        await app_graph.aupdate_state(config, {
            "tasks": [],
            "detected_gaps": [],
            "project_goals": "",
            "clarification_questions": [],
            "elicitation_phase": "listening"
        })

    human_msg = HumanMessage(content=user_content)
    updated_state_snap = await app_graph.ainvoke({"messages": [human_msg]}, config)

    return format_graph_state(updated_state_snap, project_id)


@app.post("/api/projects/{project_id}/finish-sharing")
async def finish_sharing(project_id: str, db: Session = Depends(get_db)):
    """Transition from listening phase to stress_testing phase."""
    db_project = db.query(ProjectDb).filter(ProjectDb.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    config = {"configurable": {"thread_id": project_id, "project_id": project_id}}
    state = await get_project_state(project_id)

    if state.get("elicitation_phase") != "listening":
        raise HTTPException(status_code=400, detail="Project is not in listening phase")

    await app_graph.aupdate_state(
        config,
        {"elicitation_phase": "stress_testing", "current_focus": "eliciting_goals"},
        as_node="elicit_goals",
    )
    updated_state_snap = (await app_graph.aget_state(config)).values
    return format_graph_state(updated_state_snap, project_id)


@app.post("/api/projects/{project_id}/approve-goals")
async def approve_goals(project_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Approve goals, trigger task generation, and persist tasks to the database."""
    db_project = db.query(ProjectDb).filter(ProjectDb.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    config = {"configurable": {"thread_id": project_id, "project_id": project_id}}
    state = await get_project_state(project_id)

    if state.get("goals_approved"):
        raise HTTPException(status_code=400, detail="Goals are already approved")

    if state.get("elicitation_phase") != "stress_testing" or state.get("detected_gaps"):
        raise HTTPException(
            status_code=400, detail="Cannot approve goals with unresolved gaps"
        )

    try:
        concluding_msg = AIMessage(content="Got it! Starting your project now...")
        await app_graph.aupdate_state(
            config,
            {
                "goals_approved": True,
                "elicitation_phase": "goals_approved",
                "messages": [concluding_msg],
                "current_focus": "planning_tasks",
            },
            as_node="elicit_goals",
        )

        db_project.pipeline_status = "in_progress"
        db_project.pipeline_error = None
        db.commit()

        # Trigger analysis in the background
        background_tasks.add_task(run_analysis_pipeline, project_id, config)

    except Exception as e:
        logger.error(f"[ApproveGoals] Failed to launch background pipeline: {e}")
        db_project.pipeline_status = "failed"
        db_project.pipeline_error = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to start analysis pipeline.")

    # ── Auto-Name Generation ──
    try:
        if not db_project.name or db_project.name == "New Project":
            draft_path = os.path.join(get_workspace_dir(project_id), "DRAFT_USER_STORIES.md")
            requirements_text = "No requirements provided."
            if os.path.exists(draft_path):
                with open(draft_path, "r", encoding="utf-8") as f:
                    requirements_text = f.read()
            
            db_project.name = parse_title_from_text(requirements_text)

        db_project.status = "Approved"
        db.commit()
    except Exception as e:
        logger.error(f"[ApproveGoals] Auto-naming failed: {e}")

    updated_state_snap = (await app_graph.aget_state(config)).values

    # State finalization (snapshot log + architecture consolidation)
    try:
        background_tasks.add_task(execute_state_finalization, project_id, updated_state_snap)
    except Exception as e:
        logger.error(f"[Finalization] Error: {e}")

    return format_graph_state(updated_state_snap, project_id)

import traceback

async def run_analysis_pipeline(project_id: str, config: dict):
    db = SessionLocal()
    try:
        _set_pipeline_status(db, project_id, "in_progress")
        db.commit()
    finally:
        db.close()

    try:
        # Run the full LLM graph pipeline
        await app_graph.ainvoke(None, config)

        db = SessionLocal()
        try:
            _set_pipeline_status(db, project_id, "completed")
            db.commit()
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Pipeline failed for project_id={project_id}: {e}\n{traceback.format_exc()}")
        db = SessionLocal()
        try:
            _set_pipeline_status(db, project_id, "failed", error_message=str(e))
            db.commit()
        finally:
            db.close()

def _set_pipeline_status(db, project_id: str, status: str, error_message: str = None):
    project = db.query(ProjectDb).filter(ProjectDb.id == project_id).first()
    if project:
        project.pipeline_status = status
        if error_message is not None:
            project.pipeline_error = error_message

@app.post("/api/projects/{project_id}/reject-goals")
async def reject_goals(project_id: str, db: Session = Depends(get_db)):
    """Reject goals and loop back to the elicitation conversation."""
    db_project = db.query(ProjectDb).filter(ProjectDb.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    config = {"configurable": {"thread_id": project_id, "project_id": project_id}}
    state = await get_project_state(project_id)

    if state.get("goals_approved"):
        raise HTTPException(
            status_code=400, detail="Cannot reject already approved requirements"
        )

    await app_graph.aupdate_state(
        config,
        {
            "goals_approved": False,
            "elicitation_phase": "stress_testing",
            "current_focus": "eliciting_goals",
            "detected_gaps": [
                "Modify: What specific changes or additions would you like to make to the project goals?"
            ],
        },
        as_node="elicit_goals",
    )
    updated_state_snap = (await app_graph.aget_state(config)).values
    return format_graph_state(updated_state_snap, project_id)


@app.post("/api/projects/{project_id}/unlock-requirements")
async def unlock_requirements(project_id: str, db: Session = Depends(get_db)):
    """Reset back to listening phase, allowing the user to add more requirements."""
    db_project = db.query(ProjectDb).filter(ProjectDb.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    config = {"configurable": {"thread_id": project_id, "project_id": project_id}}
    await get_project_state(project_id)

    # Do NOT remove persisted tasks; we will use Smart Merge to upsert/append
    
    # Revert to listening phase but retain historical tasks, gaps, and clarifications
    await app_graph.aupdate_state(
        config,
        {
            "goals_approved": False,
            "elicitation_phase": "listening",
            "current_focus": "idle",
        },
        as_node="elicit_goals",
    )
    updated_state_snap = (await app_graph.aget_state(config)).values
    return format_graph_state(updated_state_snap, project_id)


class TaskUpdateRequest(BaseModel):
    status: str | None = None
    assignee: str | None = None
    evaluation_feedback: str | None = None

async def trigger_qc_node(task_id: str, project_id: str):
    """Proxy QC trigger through the orchestrator, which owns the repo config and branch-name logic."""
    try:
        target_url = "http://127.0.0.1:8000/api/qc/evaluate"
        payload = {
            "task_id": task_id,
            "project_id": project_id,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, json=payload, timeout=60.0)
            if response.status_code == 200:
                result = response.json()
                verdict = result.get("verdict")
                feedback = result.get("feedback")
                
                db = next(get_db())
                db_task = db.query(TaskDb).filter(TaskDb.id == task_id).first()
                if db_task:
                    if verdict:
                        db_task.status = TaskStatus.IN_QA
                    else:
                        db_task.status = TaskStatus.REJECTED
                    db_task.evaluation_feedback = feedback
                    db.commit()
                db.close()
    except Exception as e:
        logger.error(f"Failed to trigger QC node: {e}")


@app.patch("/api/projects/{project_id}/tasks/{task_id}")
async def update_project_task(project_id: str, task_id: str, payload: TaskUpdateRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = db.query(TaskDb).filter(TaskDb.id == task_id, TaskDb.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if payload.status:
        try:
            task.status = TaskStatus(payload.status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    if payload.assignee is not None:
        task.assignee = payload.assignee
    if payload.evaluation_feedback is not None:
        task.evaluation_feedback = payload.evaluation_feedback
        
    db.commit()
    db.refresh(task)
    
    if task.status == TaskStatus.IN_QC:
        background_tasks.add_task(trigger_qc_node, task.id, project_id)
        
    return {"status": "success", "task": {"id": task.id, "status": task.status.value, "evaluation_feedback": task.evaluation_feedback}}


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
                "evaluation_feedback": t.evaluation_feedback,
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
