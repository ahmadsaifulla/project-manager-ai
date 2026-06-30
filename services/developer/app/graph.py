import os
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from openai import OpenAI
from app.github_client import get_branch_diff
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define the State Schema for the QC Agent
class QCState(TypedDict):
    task_id: str
    repo_name: str
    branch_name: str
    git_diff: Optional[str]
    verdict: Optional[bool]
    feedback: Optional[str]

def retrieve_code(state: QCState) -> dict:
    """
    Pulls the raw git diff into the state using the github_client.
    """
    diff = get_branch_diff(state["repo_name"], state["branch_name"])
    return {"git_diff": diff}

def static_evaluation(state: QCState) -> dict:
    """
    Loads ARCHITECTURE.md, passes it with the diff to Groq via OpenAI client,
    and performs a strict text-based alignment audit.
    """
    # Load root workspace rules
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
    arch_path = os.path.join(workspace_root, "ARCHITECTURE.md")
    
    rules = "No explicit architecture rules found."
    if os.path.exists(arch_path):
        with open(arch_path, "r", encoding="utf-8") as f:
            rules = f.read()

    prompt = f"""
You are a strict Quality Control AI for a software project.
Here are the architecture rules:
{rules}

Here is the git diff for the current task:
{state['git_diff']}

Perform a strict text-based alignment audit against the rules.
First, provide corrective feedback in a markdown list. 
Then, on the very last line, output exactly "VERDICT: APPROVED" or "VERDICT: REJECTED".
"""

    # Initialize OpenAI client pointing to Groq
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is not set in the environment.")
        
    client = OpenAI(
        api_key=groq_api_key,
        base_url="https://api.groq.com/openai/v1"
    )

    response = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    
    result_text = response.choices[0].message.content or ""
    
    # Parse verdict
    if "VERDICT: APPROVED" in result_text.upper():
        verdict = True
    else:
        verdict = False
        
    return {"verdict": verdict, "feedback": result_text}

def handoff_to_qa(state: QCState) -> dict:
    """
    Prepares a success payload intended for Node 3 (Quality Assurance).
    """
    # For now, we simply pass through the state to signify handoff is complete.
    return {}

def route_after_eval(state: QCState) -> str:
    """
    Routes to the handoff node if approved, else ends the graph (rejection flow).
    """
    if state.get("verdict"):
        return "handoff_to_qa"
    return END

# Build the QC State Graph
workflow = StateGraph(QCState)

# Add nodes
workflow.add_node("retrieve_code", retrieve_code)
workflow.add_node("static_evaluation", static_evaluation)
workflow.add_node("handoff_to_qa", handoff_to_qa)

# Add edges and routing
workflow.set_entry_point("retrieve_code")
workflow.add_edge("retrieve_code", "static_evaluation")
workflow.add_conditional_edges("static_evaluation", route_after_eval)
workflow.add_edge("handoff_to_qa", END)

# Compile the graph
qc_graph = workflow.compile()
