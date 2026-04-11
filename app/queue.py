import uuid

from redis import Redis
from rq import Queue

from app.config import settings


def get_redis_conn() -> Redis:
    return Redis.from_url(settings.redis_url)


def get_queue() -> Queue:
    return Queue("proofread", connection=get_redis_conn())


def enqueue_proofread_task(task_id: str, owner_id: str | None = None, attempt: int | None = None) -> None:
    queue = get_queue()
    job_suffix = attempt if attempt is not None else uuid.uuid4().hex[:8]
    queue.enqueue(
        "app.worker_tasks.process_proofread_task",
        task_id,
        owner_id,
        job_id=f"{task_id}:{job_suffix}",
        job_timeout=settings.effective_rq_job_timeout_sec,
        result_ttl=settings.rq_result_ttl_sec,
    )
