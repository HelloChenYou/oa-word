from fastapi import APIRouter
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import ProofreadTask
from app.queue import get_queue, get_redis_conn


router = APIRouter(prefix="/api/v1/ops", tags=["ops"])


@router.get("/metrics")
def get_metrics():
    db = SessionLocal()
    try:
        queue = get_queue()
        redis_conn = get_redis_conn()
        status_rows = db.execute(
            select(ProofreadTask.status, func.count()).group_by(ProofreadTask.status)
        ).all()
        task_counts = {status: count for status, count in status_rows}
        return {
            "queue": {
                "name": queue.name,
                "queued_jobs": len(queue),
                "redis_ping": bool(redis_conn.ping()),
            },
            "tasks": {
                "total": sum(task_counts.values()),
                "by_status": task_counts,
            },
        }
    finally:
        db.close()
