import asyncio
import logging
import os
import random
import signal
import uuid
from typing import Dict

import httpx
from fastapi import FastAPI, HTTPException

from services.worker.models import TaskRequest, TaskResult

app = FastAPI(title="worker")
logger = logging.getLogger("worker")
logging.basicConfig(level=logging.INFO)

COORDINATOR_URL = os.getenv("COORDINATOR_URL", "http://localhost:8000")
shutdown_event = asyncio.Event()
shutdown_complete_event = asyncio.Event()
task_store: Dict[str, TaskResult] = {}
running_tasks: Dict[str, asyncio.Task] = {}

from datetime import datetime, timezone


@app.get("/ping")
async def ping_coordinator(duration: int):
    async with httpx.AsyncClient() as client:
        for _ in range(duration):
            try:
                resp = await client.get(f"{COORDINATOR_URL}/health")
                logger.info(f"[PING] {datetime.now(timezone.utc).isoformat()} - {resp.status_code}")
            except Exception as e:
                logger.error(f"[PING] {datetime.now(timezone.utc).isoformat()} - ERROR: {e}")
            await asyncio.sleep(1)
    return {"status": "done"}


@app.post("/sleep")
async def sleep_background(duration: int):
    task_id = str(uuid.uuid4())
    logger.info(f"[{task_id}] Started sleep task for {duration} seconds")

    async def background_sleep():
        try:
            for i in range(duration):
                logger.info(f"[{task_id}] Sleeping... {i + 1}/{duration}")
                await asyncio.sleep(1)
            logger.info(f"[{task_id}] Sleep complete")
        finally:
            if task_id in running_tasks:
                del running_tasks[task_id]

    task = asyncio.create_task(background_sleep())
    running_tasks[task_id] = task

    return {"task_id": task_id, "status": "sleep started"}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/sync-task")
async def sync_task(req: TaskRequest):
    task_id = str(uuid.uuid4())
    logger.info(f"Started task [{task_id}] with {req.iterations} iterations")
    result = await run_task(task_id, req.iterations)
    task_store[task_id] = result
    return result


@app.post("/async-task")
async def async_task(req: TaskRequest):
    task_id = str(uuid.uuid4())
    logger.info(f"Started task [{task_id}] with {req.iterations} iterations")
    task = asyncio.create_task(run_and_callback(task_id, req.iterations))
    running_tasks[task_id] = task
    return {"task_id": task_id}


@app.get("/task/{task_id}")
def get_task(task_id: str):
    result = task_store.get(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


async def run_task(task_id: str, iterations: int) -> TaskResult:
    numbers = []
    for i in range(iterations):
        number = random.randint(1, 100)
        numbers.append(number)
        logger.info(f"[{task_id}] Iteration {i + 1}: {number}")
        await asyncio.sleep(1)
    average = sum(numbers) / len(numbers)
    return TaskResult(task_id=task_id, iterations=len(numbers), average=average)


async def run_and_callback(task_id: str, iterations: int):
    result = await run_task(task_id, iterations)
    task_store[task_id] = result
    try:
        callback_url = f"{COORDINATOR_URL}/results"
        async with httpx.AsyncClient() as client:
            await client.post(callback_url, json=result.model_dump())
        logger.info(f"[{task_id}] Async result sent to coordinator.")
    except Exception as e:
        logger.error(f"[{task_id}] Failed to callback coordinator: {e}")
    finally:
        running_tasks.pop(task_id, None)


def setup_signals(loop: asyncio.AbstractEventLoop):
    def _handle_signal():
        logger.info("[SHUTDOWN] SIGTERM/SIGINT received. Shutting down gracefully...")
        shutdown_event.set()

        async def wait_and_finish():
            if running_tasks:
                logger.info(f"[SHUTDOWN] Waiting for {len(running_tasks)} async tasks to finish...")
                await asyncio.gather(*running_tasks.values(), return_exceptions=True)
            else:
                logger.info("[SHUTDOWN] No running async tasks.")
            shutdown_complete_event.set()

        loop.create_task(wait_and_finish())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)


if __name__ == "__main__":
    import uvicorn

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    setup_signals(loop)

    config = uvicorn.Config(app, host="0.0.0.0", port=8001, loop="asyncio")
    server = uvicorn.Server(config)


    async def main():
        await server.serve()
        await shutdown_complete_event.wait()


    loop.run_until_complete(main())
