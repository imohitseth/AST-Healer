import os
import uuid
import asyncio
from fastapi import FastAPI, HTTPException, status

from schemas import IssuePayload
from main import heal_code, auto_heal_code

app = FastAPI(
    title="AST-Healer Service",
    description="Production-grade API for self-healing buggy Python functions using google.antigravity SDK.",
    version="1.0.0"
)

# In-memory storage for tracking task status
tasks_db = {}

async def run_healer_task(task_id: str, payload: IssuePayload):
    """Worker function executed in the background using asyncio.create_task."""
    tasks_db[task_id]["status"] = "RUNNING"
    try:
        success = await heal_code(payload)
        if success:
            tasks_db[task_id]["status"] = "SUCCESS"
            tasks_db[task_id]["result"] = "Function healed and validated successfully."
        else:
            tasks_db[task_id]["status"] = "FAILED"
            tasks_db[task_id]["error"] = "Failed to heal the code after max attempts."
    except Exception as e:
        tasks_db[task_id]["status"] = "FAILED"
        tasks_db[task_id]["error"] = f"Unexpected error: {str(e)}"

async def run_auto_healer_task(task_id: str, run_target: str, run_mode: str):
    """Worker function for auto-healing tasks executing script/pytest in the background."""
    tasks_db[task_id]["status"] = "RUNNING"
    try:
        success = await auto_heal_code(run_target, mode=run_mode)
        if success:
            tasks_db[task_id]["status"] = "SUCCESS"
            tasks_db[task_id]["result"] = f"Code executed, bug auto-detected, and code healed successfully in {run_mode} mode."
        else:
            tasks_db[task_id]["status"] = "FAILED"
            tasks_db[task_id]["error"] = "Auto-healing was unsuccessful."
    except Exception as e:
        tasks_db[task_id]["status"] = "FAILED"
        tasks_db[task_id]["error"] = f"Unexpected error: {str(e)}"

@app.post(
    "/heal",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger the self-healing agent loop manually",
    response_description="Returns the task ID immediately so you can poll for status."
)
async def heal(payload: IssuePayload):
    """
    Triggers the self-healing loop manually with a pre-defined error payload.
    This endpoint is non-blocking and processes the request in the background.
    """
    if not os.path.exists(payload.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target file not found at path: {payload.file_path}"
        )
        
    task_id = uuid.uuid4().hex
    tasks_db[task_id] = {
        "status": "PENDING",
        "result": None,
        "error": None
    }
    asyncio.create_task(run_healer_task(task_id, payload))
    return {
        "task_id": task_id,
        "status": "PENDING",
        "message": "Healing task started in background."
    }

@app.post(
    "/heal/auto",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger automated traceback detection and healing",
    response_description="Returns the task ID immediately so you can poll for status."
)
async def heal_auto(mode: str = "script", file_path: str = None):
    """
    Automatically runs the target script or pytest file, detects crashes/tracebacks,
    parses exception details, and runs the self-healing loop in the background.
    """
    if mode not in ["script", "pytest"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mode. Must be 'script' or 'pytest'."
        )
        
    if not file_path:
        if mode == "pytest":
            file_path = "tests/test_mock_code.py"
        else:
            file_path = "tests/mock_run.py"
            
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target file not found at path: {file_path}"
        )
        
    task_id = uuid.uuid4().hex
    tasks_db[task_id] = {
        "status": "PENDING",
        "result": None,
        "error": None
    }
    asyncio.create_task(run_auto_healer_task(task_id, file_path, mode))
    return {
        "task_id": task_id,
        "status": "PENDING",
        "message": f"Auto-healing task ({mode} mode) started in background for target: {file_path}"
    }

@app.get(
    "/tasks/{task_id}",
    summary="Get status of a healing task",
    response_description="Returns the execution status, results, or errors."
)
async def get_task_status(task_id: str):
    """Retrieves the status of a scheduled healing task."""
    if task_id not in tasks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task ID not found."
        )
    return {
        "task_id": task_id,
        **tasks_db[task_id]
    }

@app.get("/", summary="Health check endpoint")
async def health_check():
    """Simple check to ensure service is alive."""
    return {"status": "healthy", "service": "AST-Healer API"}
