from pydantic import BaseModel

class TaskRequest(BaseModel):
    iterations: int

class TaskResult(BaseModel):
    task_id: str
    iterations: int
    average: float