import re

with open("services/orchestrator/app/main.py", "r") as f:
    content = f.read()

# 1. Add imports and remove project_state definition
content = content.replace(
"""# Light persistence layout to store global project metadata
# This allows the React frontend to fetch/update these values globally.
project_state = {
    "repo_name": "facebook/react",
    "developer_node_url": "http://127.0.0.1:8002",
    "chatbot_node_url": "http://127.0.0.1:8001"
}""",
"""from .config_manager import get_config, save_config"""
)

# 2. Fix get_status
content = content.replace(
"""    return {
        "status": "Master Orchestrator Online",
        "state": project_state
    }""",
"""    return {
        "status": "Master Orchestrator Online",
        "state": get_config()
    }"""
)

# 3. Fix /api/config
content = content.replace(
"""@app.get("/api/config")
def get_config():
    \"\"\"Returns the current global project state.\"\"\"
    return project_state

@app.post("/api/config")
async def update_config(request: Request):
    \"\"\"Updates the global project state with the provided JSON payload.\"\"\"
    try:
        payload = await request.json()
        for key, value in payload.items():
            if key in project_state:
                project_state[key] = value
        return {"status": "success", "state": project_state}
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": f"Invalid payload: {str(e)}"})""",
"""@app.get("/api/config")
def get_global_config():
    \"\"\"Returns the current global project state.\"\"\"
    return get_config()

@app.post("/api/config")
async def update_global_config(request: Request):
    \"\"\"Updates the global project state with the provided JSON payload.\"\"\"
    try:
        payload = await request.json()
        current = get_config()
        current.update(payload)
        save_config(current)
        return {"status": "success", "state": current}
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": f"Invalid payload: {str(e)}"})"""
)

# 4. Replace global project_state dictionary lookups
content = content.replace("project_state['developer_node_url']", "get_config()['developer_node_url']")
content = content.replace("project_state['chatbot_node_url']", "get_config()['chatbot_node_url']")
content = content.replace("project_state[\"repo_name\"]", "get_config()[\"repo_name\"]")
content = content.replace("project_state.get(\"repo_name\"", "get_config().get(\"repo_name\"")

with open("services/orchestrator/app/main.py", "w") as f:
    f.write(content)
