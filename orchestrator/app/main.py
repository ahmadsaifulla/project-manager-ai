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
@app.post("/api/chat/message")
async def proxy_chat_message(request: Request):
    """
    Reverse proxy to forward conversational traffic directly to the chatbot_node.
    Translates payload from frontend format to chatbot_v2 format.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}
        
    user_message = payload.get("message", "")
    chatbot_payload = {"content": user_message}
    project_id = "test-002" # Hardcoded default for now
    
    target_url = f"{project_state['chatbot_node_url']}/api/projects/{project_id}/messages"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, json=chatbot_payload, timeout=60.0)
            
            if response.status_code == 200:
                data = response.json()
                # Find the last assistant message
                messages = data.get("messages", [])
                ai_reply = "No response received."
                for msg in reversed(messages):
                    if msg.get("role") == "assistant":
                        ai_reply = msg.get("content")
                        break
                return JSONResponse(status_code=200, content={"reply": ai_reply, "raw_state": data})
                
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        logging.error(f"Failed to reach Chatbot Node at {target_url}: {e}")
        return JSONResponse(
            status_code=502, 
            content={"detail": "Bad Gateway - Chatbot Node offline or unreachable."}
        )

@app.post("/api/chat/{action}")
async def proxy_chat_action(action: str, request: Request):
    """
    Reverse proxy to forward state transition actions to the chatbot_node.
    Supported actions: finish-sharing, approve-goals, reject-goals, unlock-requirements
    """
    project_id = "test-002" # Hardcoded default for now
    target_url = f"{project_state['chatbot_node_url']}/api/projects/{project_id}/{action}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, timeout=60.0)
            return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.RequestError as e:
        logging.error(f"Failed to reach Chatbot Node at {target_url}: {e}")
        return JSONResponse(
            status_code=502, 
            content={"detail": "Bad Gateway - Chatbot Node offline or unreachable."}
        )
