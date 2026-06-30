from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

@router.get("/{project_id}")
async def get_project_tasks(project_id: str):
    """
    Retrieve all tasks associated with a project.
    TODO: Implement database query.
    """
    return {"status": "success", "project_id": project_id, "tasks": []}

@router.post("/{project_id}")
async def create_project_task(project_id: str, task_data: dict):
    """
    Create a new task for the project.
    TODO: Implement task creation logic.
    """
    return {"status": "success", "project_id": project_id, "task": task_data}
