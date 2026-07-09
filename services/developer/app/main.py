import sys
import os
# Force the root Project-Manager directory into the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

print(f"DEBUG: Current Working Directory: {os.getcwd()}")
print(f"DEBUG: PATH to .env: {os.path.join(os.getcwd(), '.env')}")
print(f"DEBUG: GITHUB_TOKEN exists in env? {'GITHUB_TOKEN' in os.environ}")

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

token = os.getenv("GITHUB_TOKEN")
if not token:
    print("WARNING: GITHUB_TOKEN not found in environment. QC evaluations will fail.")

import json
import logging
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

app = FastAPI(title="Developer Node API")

# Setup basic logging
logging.basicConfig(level=logging.INFO)

from services.shared.schemas import QCRequest

@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"status": "ok"}

async def fetch_github_diff(repo_url: str, branch_name: str) -> str:
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise ValueError("GITHUB_TOKEN is not set")
    
    url = f"https://api.github.com/repos/{repo_url}/compare/main...{branch_name}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3.diff"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"GitHub API Error: {response.text}")
        return response.text

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def call_groq_api(prompt: str) -> str:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is not set")
        
    groq_url = "https://api.groq.com/openai/v1/chat/completions"
    groq_headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
    groq_payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }
    
    async with httpx.AsyncClient() as client:
        groq_resp = await client.post(groq_url, headers=groq_headers, json=groq_payload, timeout=60.0)
        
        # Raise an exception for HTTP errors so tenacity can retry
        groq_resp.raise_for_status()
        
        groq_data = groq_resp.json()
        return groq_data["choices"][0]["message"]["content"]

@app.post("/api/qc/evaluate")
async def evaluate_qc(request: QCRequest):
    """
    Triggers the QC evaluation of the diff using Groq.
    """
    try:
        # Step A: Fetch task details from Chatbot service
        chatbot_url = f"http://127.0.0.1:8001/api/projects/{request.project_id}/tasks"
        async with httpx.AsyncClient() as client:
            task_resp = await client.get(chatbot_url)
            if task_resp.status_code != 200:
                raise HTTPException(status_code=task_resp.status_code, detail="Failed to fetch task details")
            
            tasks = task_resp.json()
            task_data = next((t for t in tasks if t["id"] == request.task_id), None)
            
            if not task_data:
                raise HTTPException(status_code=404, detail="Task not found in project")
                
            task_title = task_data.get("title", "Unknown Task")
            task_description = task_data.get("description", "No description")

        # Step B: Call fetch_github_diff
        diff = await fetch_github_diff(request.repo_url, request.branch_name)

        # Step C: Construct prompt for Groq
        QC_PROMPT = f"""
        You are a Senior Software Engineer performing a PR code review.
        Evaluate this code diff for:
        1. Correctness (Does it meet task requirements?)
        2. Security (Are there leaks or bad practices?)
        3. Efficiency (Is the code clean?)
        
        TASK REQUIREMENTS:
        {task_title} - {task_description}

        CODE DIFF:
        {diff}

        Output format (JSON):
        {{
            "passed": boolean,
            "feedback": "string (detailed review comments)",
            "suggested_changes": "string (or None)"
        }}
        """
        
        # This function handles its own retries internally
        result_text = await call_groq_api(QC_PROMPT)
            
        # Step D: Parse the Groq response
        import re
        try:
            clean_json = re.sub(r'^```json\s*|\s*```$', '', result_text.strip())
            parsed_result = json.loads(clean_json)
            passed = parsed_result.get("passed", False)
            feedback = parsed_result.get("feedback", "")
            suggested_changes = parsed_result.get("suggested_changes")
            if suggested_changes and suggested_changes != "None":
                feedback += f"\n\nSuggested Changes:\n{suggested_changes}"
        except json.JSONDecodeError:
            passed = False
            feedback = "Failed to parse JSON response from Groq."
            
        new_status = "in_qa" if passed else "rejected"
        
        # Patch the Task Status
        patch_url = f"http://127.0.0.1:8001/api/projects/{request.project_id}/tasks/{request.task_id}"
        patch_payload = {
            "status": new_status,
            "evaluation_feedback": feedback
        }
        
        async with httpx.AsyncClient() as client:
            patch_resp = await client.patch(patch_url, json=patch_payload)
            if patch_resp.status_code not in (200, 204):
                logging.warning(f"Failed to patch task status: {patch_resp.text}")
                
        return {
            "task_id": request.task_id,
            "verdict": passed,
            "feedback": feedback,
            "new_status": new_status
        }
        
    except Exception as e:
        logging.error(f"QC Evaluation Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
