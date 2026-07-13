import sys
import os
# Force the root Project-Manager directory into the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import logging
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel, Field
from typing import List, Optional

from services.shared.naming_utils import generate_branch_name

class ProjectCreateRequest(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str = "listening"
    sprint: Optional[str] = None
    progress: int = 0
    due_date: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    accent_color: str = "#5B4EFF"

class TaskUpdateRequest(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None

# Initialize the Master Orchestrator API Gateway
app = FastAPI(title="Master Orchestrator API Gateway")

# Step C: CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup basic logging
logging.basicConfig(level=logging.INFO)

from .config_manager import get_config, save_config

@app.get("/")
def get_status():
    """Health check and global state endpoint."""
    return {
        "status": "Master Orchestrator Online",
        "state": get_config()
    }

# Step A: Global State Management Endpoints
@app.get("/api/config")
def get_global_config():
    """Returns the current global project state."""
    return get_config()

@app.post("/api/config")
async def update_global_config(request: Request):
    """Updates the global project state with the provided JSON payload."""
    try:
        payload = await request.json()
        current = get_config()
        current.update(payload)
        save_config(current)
        return {"status": "success", "state": current}
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": f"Invalid payload: {str(e)}"})

# Existing QC Proxy
@app.post("/api/qc/evaluate")
async def proxy_qc_evaluation(request: Request):
    """
    Reverse proxy to forward QA requests directly to the developer_node.
    Automatically injects the globally stored 'repo_name' to simplify frontend payloads.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}
        
    # Inject global state if not provided
    if "repo_url" not in payload:
        payload["repo_url"] = get_config().get("repo_name", "")
    
    # Inject branch_name using the single source of truth
    if "branch_name" not in payload and "project_id" in payload and "task_id" in payload:
        payload["branch_name"] = generate_branch_name(payload["task_id"])
        
    target_url = f"{get_config()['developer_node_url']}/api/qc/evaluate"
    
    try:
        async with httpx.AsyncClient() as client:
            # Forward the request to the developer_node
            response = await client.post(target_url, json=payload, timeout=30.0)
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        logging.error(f"Failed to reach Developer Node at {target_url}: {e}")
        return JSONResponse(
            status_code=502, 
            content={"detail": "Bad Gateway - Developer Node offline or unreachable."}
        )

# Step B: Chatbot Node Proxy
@app.get("/api/projects")
async def proxy_list_projects():
    """Proxy to list all projects."""
    target_url = f"{get_config()['chatbot_node_url']}/api/projects"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(target_url, timeout=30.0)
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"detail": f"Bad Gateway: {e}"})

@app.post("/api/projects")
async def proxy_create_project(project: ProjectCreateRequest):
    """Proxy to create a new project."""
    payload = project.model_dump(exclude_unset=True)
    target_url = f"{get_config()['chatbot_node_url']}/api/projects"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, json=payload, timeout=30.0)
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"detail": f"Bad Gateway: {e}"})

@app.get("/api/projects/{project_id}")
async def proxy_get_project(project_id: str):
    """Proxy to get project state."""
    target_url = f"{get_config()['chatbot_node_url']}/api/projects/{project_id}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(target_url, timeout=30.0)
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"detail": f"Bad Gateway: {e}"})

@app.delete("/api/projects/{project_id}")
async def proxy_delete_project(project_id: str):
    """Proxy to delete a project."""
    target_url = f"{get_config()['chatbot_node_url']}/api/projects/{project_id}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(target_url, timeout=30.0)
            try:
                content = response.json()
            except Exception:
                content = {}
            return JSONResponse(status_code=response.status_code, content=content)
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"detail": f"Bad Gateway: {e}"})

@app.post("/api/projects/{project_id}/messages")
async def proxy_post_message(project_id: str, request: Request):
    """Proxy chat messages."""
    payload = await request.json()
    target_url = f"{get_config()['chatbot_node_url']}/api/projects/{project_id}/messages"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, json=payload, timeout=60.0)
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"detail": f"Bad Gateway: {e}"})

@app.post("/api/projects/{project_id}/{action}")
async def proxy_project_action(project_id: str, action: str):
    """Proxy state transition actions."""
    target_url = f"{get_config()['chatbot_node_url']}/api/projects/{project_id}/{action}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, timeout=60.0)
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"detail": f"Bad Gateway: {e}"})

@app.get("/api/projects/{project_id}/tasks")
async def proxy_get_tasks(project_id: str):
    """Proxy fetching project tasks."""
    target_url = f"{get_config()['chatbot_node_url']}/api/projects/{project_id}/tasks"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(target_url, timeout=30.0)
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"detail": f"Bad Gateway: {e}"})

async def trigger_qc_node(project_id: str, task_id: str):
    """Background webhook to trigger the Developer Node QC evaluation."""
    target_url = "http://127.0.0.1:8002/api/qc/evaluate"
    
    repo_url = get_config().get("repo_name", "facebook/react")
    branch_name = generate_branch_name(task_id)

    payload = {
        "project_id": project_id,
        "task_id": task_id,
        "repo_url": repo_url,
        "branch_name": branch_name
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, json=payload, timeout=60.0)
            response.raise_for_status()
            logging.info(f"Successfully triggered QC node for Task {task_id}")
    except Exception as e:
        logging.error(f"Failed to trigger QC evaluation for Task {task_id}: {e}")

@app.patch("/api/projects/{project_id}/tasks/{task_id}")
async def proxy_update_task(project_id: str, task_id: str, update: TaskUpdateRequest, background_tasks: BackgroundTasks):
    """Proxy task updates."""
    payload = update.model_dump(exclude_unset=True)
    target_url = f"{get_config()['chatbot_node_url']}/api/projects/{project_id}/tasks/{task_id}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(target_url, json=payload, timeout=30.0)
            
            # If the patch was successful and status is moved to IN QC, trigger the background evaluation
            if response.status_code == 200 and update.status == "in_qc":
                background_tasks.add_task(trigger_qc_node, project_id, task_id)
                
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"detail": f"Bad Gateway: {e}"})
