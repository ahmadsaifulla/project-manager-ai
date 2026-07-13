def generate_task_id(project_id: str, index: int) -> str:
    """Generate a deterministic task ID based on the project ID and index."""
    return f"{project_id}-tsk-{index:03d}"

def generate_branch_name(task_id: str) -> str:
    """Generate a deterministic branch name strictly following feature/{task_id}."""
    return f"feature/{task_id}"
