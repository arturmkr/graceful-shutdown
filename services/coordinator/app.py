import asyncio
import logging
import os
import signal
from fastapi import FastAPI, HTTPException
from typing import Dict
import httpx

from models import TaskRequest, TaskResult

app = FastAPI(title="coordinator")
logger = logging.getLogger("coordinator")
logging.basicConfig(level=logging.INFO)

WORKER_URL = os.getenv("WORKER_URL", "http://localhost:8001")
shutdown_event = asyncio.Event()
task_store: Dict[str, TaskResult] = {}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/sync-task")
async def sync_task(req: TaskRequest):
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(f"{WORKER_URL}/sync-task", json=req.dict())
        data = response.json()
        result = TaskResult(**data)
        task_store[result.task_id] = result
        logger.info(f"[SYNC] Task {result.task_id} complete")
        return result

@app.post("/async-task")
async def async_task(req: TaskRequest):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{WORKER_URL}/async-task", json=req.dict())
        task_id = response.json()["task_id"]
        logger.info(f"[ASYNC] Task {task_id} created")
        return {"task_id": task_id}

@app.post("/results")
async def receive_results(result: TaskResult):
    task_store[result.task_id] = result
    logger.info(f"[ASYNC] Results received for task {result.task_id}")
    return {"status": "received"}

@app.get("/task/{task_id}")
def get_task(task_id: str):
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_store[task_id]

def handle_shutdown():
    logger.info("Shutdown requested.")
    shutdown_event.set()

def setup_signals():
    signal.signal(signal.SIGINT, lambda *_: handle_shutdown())
    signal.signal(signal.SIGTERM, lambda *_: handle_shutdown())

if __name__ == "__main__":
    import uvicorn
    setup_signals()
    uvicorn.run("app:app", host="0.0.0.0", port=8000)