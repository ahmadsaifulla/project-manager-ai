import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

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

# Light persistence layout to store global project metadata
# This allows the React frontend to fetch/update these values globally.
project_state = {
    "repo_name": "facebook/react",
    "developer_node_url": "http://127.0.0.1:8002",
    "chatbot_node_url": "http://127.0.0.1:8001"
}

@app.get("/")
def get_status():
    """Health check and global state endpoint."""
    return {
        "status": "Master Orchestrator Online",
        "state": project_state
    }

# Step A: Global State Management Endpoints
@app.get("/api/config")
def get_config():
    """Returns the current global project state."""
    return project_state

@app.post("/api/config")
async def update_config(request: Request):
    """Updates the global project state with the provided JSON payload."""
    try:
        payload = await request.json()
        for key, value in payload.items():
            if key in project_state:
                project_state[key] = value
        return {"status": "success", "state": project_state}
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
    if "repo_name" not in payload:
        payload["repo_name"] = project_state["repo_name"]
        
    target_url = f"{project_state['developer_node_url']}/api/qc/evaluate"
    
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
    target_url = f"{project_state['chatbot_node_url']}/api/projects"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(target_url, timeout=30.0)
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"detail": f"Bad Gateway: {e}"})

@app.post("/api/projects")
async def proxy_create_project(request: Request):
    """Proxy to create a new project."""
    payload = await request.json()
    target_url = f"{project_state['chatbot_node_url']}/api/projects"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, json=payload, timeout=30.0)
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"detail": f"Bad Gateway: {e}"})

@app.get("/api/projects/{project_id}")
async def proxy_get_project(project_id: str):
    """Proxy to get project state."""
    target_url = f"{project_state['chatbot_node_url']}/api/projects/{project_id}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(target_url, timeout=30.0)
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"detail": f"Bad Gateway: {e}"})

@app.post("/api/projects/{project_id}/messages")
async def proxy_post_message(project_id: str, request: Request):
    """Proxy chat messages."""
    payload = await request.json()
    target_url = f"{project_state['chatbot_node_url']}/api/projects/{project_id}/messages"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, json=payload, timeout=60.0)
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"detail": f"Bad Gateway: {e}"})

@app.post("/api/projects/{project_id}/{action}")
async def proxy_project_action(project_id: str, action: str):
    """Proxy state transition actions."""
    target_url = f"{project_state['chatbot_node_url']}/api/projects/{project_id}/{action}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, timeout=60.0)
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"detail": f"Bad Gateway: {e}"})
