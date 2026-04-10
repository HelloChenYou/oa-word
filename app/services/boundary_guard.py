from fastapi import HTTPException
from redis import Redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from typing import TypeVar

from app.config import settings

T = TypeVar("T")


def ensure_text_within_limit(text: str) -> None:
    if len(text) > settings.max_task_text_chars:
        raise HTTPException(
            status_code=400,
            detail=f"text too long: max {settings.max_task_text_chars} characters",
        )


def ensure_template_file_within_limit(file_size: int) -> None:
    if file_size > settings.max_template_file_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"template file too large: max {settings.max_template_file_bytes} bytes",
        )


def ensure_template_text_within_limit(text: str) -> None:
    if len(text) > settings.max_template_text_chars:
        raise HTTPException(
            status_code=400,
            detail=f"template text too long: max {settings.max_template_text_chars} characters",
        )


def ensure_active_tasks_within_limit(db: Session) -> None:
    from app.models import ProofreadTask

    active_tasks = db.scalar(
        select(func.count()).select_from(ProofreadTask).where(ProofreadTask.status.in_(("queued", "running")))
    )
    if active_tasks is not None and active_tasks >= settings.max_active_tasks:
        raise HTTPException(
            status_code=429,
            detail=f"too many active tasks: max {settings.max_active_tasks}",
        )


def ensure_submit_rate_limit(redis_conn: Redis, client_key: str) -> None:
    redis_key = f"rate:proofread:create:{client_key}"
    current_count = redis_conn.incr(redis_key)
    if current_count == 1:
        redis_conn.expire(redis_key, settings.submit_rate_limit_window_sec)
    if current_count > settings.submit_rate_limit_max_requests:
        raise HTTPException(
            status_code=429,
            detail=(
                "submit rate limit exceeded: "
                f"max {settings.submit_rate_limit_max_requests} requests in "
                f"{settings.submit_rate_limit_window_sec} seconds"
            ),
        )


def clamp_issues(issues: list[T]) -> list[T]:
    return issues[: settings.max_issues_per_task]


def clamp_error_message(message: str) -> str:
    if len(message) <= settings.max_error_msg_chars:
        return message
    return f"{message[:settings.max_error_msg_chars]}...(truncated)"
