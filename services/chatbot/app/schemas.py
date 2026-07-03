"""
Pydantic models, enums, and LangGraph state definition for the AI Project Manager.
Fully generic — no hardcoded domains.
"""
from enum import Enum
from typing import List, Optional, Annotated
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


# ─── Domain Enums ───────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_QC = "in_qc"
    IN_QA = "in_qa"
    DONE = "done"
    REJECTED = "rejected"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# ─── Data Models ──────────────────────────────────────────────────────────

class Project(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str = "listening"
    sprint: Optional[str] = None
    progress: int = 0
    due_date: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    accent_color: str = "#5B4EFF"


# ─── Task Model (Used in both LangGraph state and DB persistence) ───────────

class Task(BaseModel):
    id: str = Field(description="Unique task identifier, e.g., 'TSK-001'")
    title: str = Field(description="Brief title of the task")
    description: str = Field(description="Detailed scope of the work")
    status: TaskStatus = Field(default=TaskStatus.TODO)
    assignee: Optional[str] = Field(default=None, description="User ID of the assigned human developer")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    estimated_effort: str = Field(description="Estimated effort (e.g. '3 hours', 'Medium')")
    dependencies: List[str] = Field(default_factory=list, description="IDs of tasks that must complete first")
    evaluation_feedback: Optional[str] = Field(default=None, description="Feedback from QC/QA")


# ─── LLM Structured Output Schemas ─────────────────────────────────────────

class BlastRadiusOutput(BaseModel):
    """Determines which architecture layers are affected by a user request."""
    affected_layers: List[str] = Field(
        default_factory=list,
        description="List of affected layer filenames from: 'DB_LAYER.md', 'API_LAYER.md', 'SERVICES_LAYER.md', 'FRONTEND_LAYER.md'. Return empty list if the request is general or doesn't target any specific architectural component."
    )


class PMOutput(BaseModel):
    """Structured output from the Product Manager agent."""
    detected_gaps: List[str] = Field(
        default_factory=list,
        description="Remaining gaps across: Core Intent, Data Scope, User Journey, Constraints. Empty if all gaps are fully resolved or in listening phase."
    )
    next_question: str = Field(
        default="",
        description="Layman-friendly response to the user. MUST NOT repeat previous greetings. Acknowledge their latest input, provide insights, and ask exactly ONE relevant follow-up question to move the project forward. Do not say 'Welcome' if you have already said it."
    )
    project_goals: str = Field(
        default="None",
        description="Compiled goals summary formatted strictly under exactly three headers: '### What We Have Done / Finalized', '### What Needs to Be Done / Next Steps', and '### What to Update'. Use the value 'None' if a heading has no content."
    )
    updated_draft_user_stories: str = Field(
        default="",
        description="Complete, updated text of DRAFT_USER_STORIES.md, appending newly confirmed requirements systematically."
    )


class TaskModel(BaseModel):
    """Individual task output from the task planner LLM."""
    id: Optional[str] = Field(default=None, description="The existing UUID of this task if it already exists in the database. Use the EXACT UUID provided in the existing tasks list. Set to null ONLY for brand-new tasks.")
    ref_id: int = Field(description="A unique temporary integer for this task (e.g., 1, 2, 3). Used only for dependency mapping.")
    title: str = Field(default="Untitled Task", description="Brief title of the task")
    description: str = Field(default="", description="Detailed scope of the work")
    priority: str = Field(default="medium", description="low, medium, high, or critical")
    estimated_effort: str = Field(default="TBD", description="Estimated effort, e.g. '6 hours', '3 days'")
    dependencies: List[int] = Field(default_factory=list, description="List of ref_id integers this task depends on. Must form an acyclic graph.")


class PlanTasksOutput(BaseModel):
    """Structured output from the task planner agent."""
    prd: str = Field(default="", description="The formalized Product Requirements Document in markdown format.")
    technical_spec: str = Field(default="", description="The formal Technical Specification document in markdown format.")
    tasks: List[TaskModel] = Field(default_factory=list, description="Structured developer tasks mapping to the approved requirements summary.")


# ─── LangGraph State Definition ────────────────────────────────────────────

class ProjectState(TypedDict):
    """Central state schema for the LangGraph coordinator agent."""
    # LangGraph standard message history
    messages: Annotated[List[BaseMessage], add_messages]

    # Project Context
    project_id: str
    project_goals: str
    goals_approved: bool  # Explicit flag to check if the user has confirmed goals
    elicitation_phase: str  # "listening" | "stress_testing" | "goals_approved"

    # Structured data computed by agents
    tasks: List[Task]

    # Elicitation state
    clarification_questions: List[str]
    detected_gaps: List[str]  # Dynamic list of outstanding requirements gaps
    current_focus: Optional[str]  # e.g., "eliciting_goals", "planning_tasks", "idle"
