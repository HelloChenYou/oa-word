import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import ProofreadIssue, ProofreadTask, Template
from app.queue import get_queue
from app.schemas import (
    CreateTaskReq,
    CreateTaskResp,
    IssueOut,
    TaskResultResp,
    TaskStatusResp,
)

router = APIRouter(prefix="/api/v1/proofread", tags=["proofread"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/tasks", response_model=CreateTaskResp)
async def create_task(req: CreateTaskReq, db: Session = Depends(get_db)):
    if req.template_id:
        template = db.get(Template, req.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="template not found")

    task_id = f"t_{uuid.uuid4().hex[:16]}"
    task = ProofreadTask(
        id=task_id,
        mode=req.mode,
        scene=req.scene,
        template_id=req.template_id,
        status="queued",
        source_text=req.text,
    )
    db.add(task)
    db.commit()
    queue = get_queue()
    queue.enqueue("app.worker_tasks.process_proofread_task", task_id, job_id=task_id)
    return CreateTaskResp(task_id=task_id, status="queued")


@router.get("/tasks/{task_id}", response_model=TaskStatusResp)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(ProofreadTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskStatusResp(task_id=task_id, status=task.status)


@router.get("/tasks/{task_id}/result", response_model=TaskResultResp)
def get_result(task_id: str, db: Session = Depends(get_db)):
    task = db.get(ProofreadTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    rows = db.execute(select(ProofreadIssue).where(ProofreadIssue.task_id == task_id)).scalars().all()
    issues = [
        IssueOut(
            severity=row.severity,
            category=row.category,
            title=row.title,
            original_text=row.original_text,
            suggested_text=row.suggested_text,
            reason=row.reason,
            evidence=row.evidence,
            confidence=row.confidence,
            source=row.source,
        )
        for row in rows
    ]

    summary = {
        "total_issues": len(issues),
        "p0": len([x for x in issues if x.severity == "P0"]),
        "p1": len([x for x in issues if x.severity == "P1"]),
        "p2": len([x for x in issues if x.severity == "P2"]),
    }
    return TaskResultResp(task_id=task_id, status=task.status, summary=summary, issues=issues)
