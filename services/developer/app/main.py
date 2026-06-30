import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.graph import qc_graph, QCState

app = FastAPI(title="Developer Node API")

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# Step A: Define the Request Schema
class QCRequest(BaseModel):
    task_id: str
    repo_name: str
    branch_name: str

@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"status": "ok"}

# Step B: Build the Evaluation Endpoint
@app.post("/api/qc/evaluate")
def evaluate_code(request: QCRequest):
    """
    Triggers the QC LangGraph engine to evaluate the diff of the specified branch.
    """
    # Step C: Error Isolation
    try:
        # Initialize the starting state
        initial_state: QCState = {
            "task_id": request.task_id,
            "repo_name": request.repo_name,
            "branch_name": request.branch_name,
            "git_diff": None,
            "verdict": None,
            "feedback": None
        }
        
        # Run the compiled graph
        final_state = qc_graph.invoke(initial_state)
        
        # Extract the final verdict and feedback
        verdict = final_state.get("verdict", False)
        feedback = final_state.get("feedback", "No feedback was generated.")
        
        # Return clean JSON response
        return {
            "task_id": request.task_id,
            "verdict": verdict,
            "feedback": feedback
        }
        
    except Exception as e:
        logging.error(f"QC Evaluation Failed: {str(e)}")
        # Catch unexpected errors (GitHub auth, Groq timeouts, etc.) and return HTTP 500
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
