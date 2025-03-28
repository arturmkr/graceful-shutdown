import asyncio
import logging
import random
import signal
import uuid
import os
from fastapi import FastAPI, HTTPException
from typing import Dict
import httpx

from services.worker.models import TaskResult, TaskRequest

app = FastAPI(title="worker")
logger = logging.getLogger("worker")
logging.basicConfig(level=logging.INFO)
COORDINATOR_URL = os.getenv("COORDINATOR_URL", "http://localhost:8000")
shutdown_event = asyncio.Event()
task_store: Dict[str, TaskResult] = {}
running_tasks: Dict[str, asyncio.Task] = {}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/sync-task")
async def sync_task(req: TaskRequest):
    task_id = str(uuid.uuid4())
    result = await run_task(task_id, req.iterations)
    task_store[task_id] = result
    return result

@app.post("/async-task")
async def async_task(req: TaskRequest):
    task_id = str(uuid.uuid4())
    task = asyncio.create_task(run_and_callback(task_id, req.iterations))
    running_tasks[task_id] = task
    return {"task_id": task_id}

@app.get("/task/{task_id}")
def get_task(task_id: str):
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_store[task_id]

async def run_task(task_id: str, iterations: int) -> TaskResult:
    numbers = []
    for i in range(iterations):
        if shutdown_event.is_set():
            logger.info(f"[{task_id}] Shutdown in progress. Interrupting.")
            break
        number = random.randint(1, 100)
        numbers.append(number)
        logger.info(f"[{task_id}] Iteration {i + 1}: {number}")
        await asyncio.sleep(1)
    average = sum(numbers) / len(numbers) if numbers else 0
    return TaskResult(task_id=task_id, iterations=len(numbers), average=average)

async def run_and_callback(task_id: str, iterations: int):
    result = await run_task(task_id, iterations)
    task_store[task_id] = result
    try:
        callback_url = f"{COORDINATOR_URL}/results"
        async with httpx.AsyncClient() as client:
            await client.post(callback_url, json=result.dict())
        logger.info(f"[{task_id}] Async result sent to coordinator.")
    except Exception as e:
        logger.error(f"[{task_id}] Failed to callback coordinator: {e}")

def handle_shutdown():
    logger.info("Shutdown requested. Waiting for tasks to finish...")
    shutdown_event.set()

def setup_signals():
    signal.signal(signal.SIGINT, lambda *_: handle_shutdown())
    signal.signal(signal.SIGTERM, lambda *_: handle_shutdown())

if __name__ == "__main__":
    import uvicorn
    setup_signals()
    uvicorn.run(app, host="0.0.0.0", port=8001)