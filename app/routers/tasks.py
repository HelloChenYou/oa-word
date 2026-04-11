import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import ProofreadIssue, ProofreadTask, Template
from app.queue import enqueue_proofread_task, get_redis_conn
from app.schemas import (
    CreateTaskReq,
    CreateTaskResp,
    IssueOut,
    RetryTaskResp,
    TaskResultResp,
    TaskStatusResp,
)
from app.services.boundary_guard import ensure_active_tasks_within_limit, ensure_submit_rate_limit, ensure_text_within_limit
from app.services.issue_converter import from_issue_record

router = APIRouter(prefix="/api/v1/proofread", tags=["proofread"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/tasks", response_model=CreateTaskResp)
async def create_task(req: CreateTaskReq, request: Request, db: Session = Depends(get_db)):
    ensure_text_within_limit(req.text)
    ensure_active_tasks_within_limit(db)
    client_host = request.client.host if request.client and request.client.host else "unknown"
    ensure_submit_rate_limit(get_redis_conn(), client_host)

    if req.template_id:
        template = db.get(Template, req.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="template not found")

    task_id = f"t_{uuid.uuid4().hex[:16]}"
    task = ProofreadTask(
        id=task_id,
        mode=req.mode,
        scene=req.scene,
        owner_id=req.owner_id,
        template_id=req.template_id,
        status="queued",
        source_text=req.text,
        failure_reason="",
        retry_count=0,
        max_retries=settings.task_max_retries,
    )
    db.add(task)
    db.commit()
    enqueue_proofread_task(task_id, req.owner_id, attempt=0)
    return CreateTaskResp(task_id=task_id, status="queued")


@router.get("/tasks/{task_id}", response_model=TaskStatusResp)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(ProofreadTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskStatusResp(
        task_id=task_id,
        status=task.status,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        failure_reason=task.failure_reason or "",
        error_msg=task.error_msg or "",
    )


@router.post("/tasks/{task_id}/retry", response_model=RetryTaskResp)
def retry_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(ProofreadTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    if task.status in {"queued", "running", "retrying"}:
        raise HTTPException(status_code=409, detail="task is already in progress")

    task.status = "queued"
    task.error_msg = ""
    task.failure_reason = ""
    task.finished_at = None
    db.commit()

    enqueue_proofread_task(task_id, task.owner_id, attempt=task.retry_count + 1)
    return RetryTaskResp(
        task_id=task_id,
        status=task.status,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
    )


@router.get("/tasks/{task_id}/result", response_model=TaskResultResp)
def get_result(task_id: str, db: Session = Depends(get_db)):
    task = db.get(ProofreadTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    rows = db.execute(select(ProofreadIssue).where(ProofreadIssue.task_id == task_id)).scalars().all()
    issues = [
        IssueOut.model_validate(from_issue_record(row).model_dump())
        for row in rows
    ]

    summary = {
        "total_issues": len(issues),
        "p0": len([x for x in issues if x.severity == "P0"]),
        "p1": len([x for x in issues if x.severity == "P1"]),
        "p2": len([x for x in issues if x.severity == "P2"]),
    }
    return TaskResultResp(task_id=task_id, status=task.status, summary=summary, issues=issues)
