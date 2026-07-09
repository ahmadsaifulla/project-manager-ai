from pydantic import BaseModel

class QCRequest(BaseModel):
    project_id: str
    task_id: str
    repo_url: str
    branch_name: str
