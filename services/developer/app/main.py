import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import json
import logging
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

app = FastAPI(title="Developer Node API")

# Setup basic logging
logging.basicConfig(level=logging.INFO)

class QCEvaluationRequest(BaseModel):
    project_id: str
    task_id: str
    repo_name: str

@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"status": "ok"}

async def fetch_github_diff(repo_name: str) -> str:
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise ValueError("GITHUB_TOKEN is not set")
    
    url = f"https://api.github.com/repos/{repo_name}/commits/main"
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
async def evaluate_qc(request: QCEvaluationRequest):
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
        diff = await fetch_github_diff(request.repo_name)

        # Step C: Construct prompt for Groq
        prompt = (
            f"You are a strict QA Engineer. Does this code diff satisfy this task requirement? "
            f"Task: {task_title} - {task_description}. "
            f"Code Diff: {diff}. "
            f"Output strictly JSON with boolean 'pass' and string 'feedback'."
        )
        
        # This function handles its own retries internally
        result_text = await call_groq_api(prompt)
            
        # Step D: Parse the Groq response
        try:
            parsed_result = json.loads(result_text)
            passed = parsed_result.get("pass", False)
            feedback = parsed_result.get("feedback", "")
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
