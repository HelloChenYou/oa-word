from datetime import datetime

from sqlalchemy import delete

from app.db import SessionLocal
from app.logging_utils import configure_logging, elapsed_ms, get_logger, log_exception, log_info, now_perf
from app.models import ProofreadIssue, ProofreadTask, Template
from app.queue import enqueue_proofread_task
from app.services.boundary_guard import clamp_error_message
from app.services.issue_converter import to_issue_record
from app.services.orchestrator import run_proofread_sync, run_proofread_with_template_sync
from app.services.task_recovery import classify_task_error, should_retry_task

configure_logging()
logger = get_logger(__name__)

def process_proofread_task(task_id: str, owner_id: str | None = None) -> None:
    started_at = now_perf()
    db = SessionLocal()
    try:
        task = db.get(ProofreadTask, task_id)
        if not task:
            log_info(logger, "task_missing", task_id=task_id)
            return

        log_info(
            logger,
            "task_started",
            task_id=task_id,
            owner_id=owner_id,
            mode=task.mode,
            scene=task.scene,
            template_id=task.template_id,
        )
        task.status = "running"
        task.error_msg = ""
        task.failure_reason = ""
        task.finished_at = None
        db.execute(delete(ProofreadIssue).where(ProofreadIssue.task_id == task_id))
        db.commit()

        template_rule_pack = "{}"
        if task.template_id:
            template = db.get(Template, task.template_id)
            if template:
                template_rule_pack = template.parsed_json

        if template_rule_pack != "{}":
            issues = run_proofread_with_template_sync(
                task.source_text,
                mode=task.mode,
                scene=task.scene,
                template_rule_pack=template_rule_pack,
                owner_id=owner_id,
            )
        else:
            issues = run_proofread_sync(task.source_text, mode=task.mode, scene=task.scene, owner_id=owner_id)

        for issue in issues:
            db.add(to_issue_record(task_id=task_id, issue=issue))

        task.status = "success"
        task.error_msg = ""
        task.failure_reason = ""
        task.finished_at = datetime.utcnow()
        db.commit()
        log_info(
            logger,
            "task_success",
            task_id=task_id,
            issue_count=len(issues),
            duration_ms=elapsed_ms(started_at),
        )
    except Exception as exc:
        failure_reason = classify_task_error(exc)
        log_exception(
            logger,
            "task_failed",
            task_id=task_id,
            owner_id=owner_id,
            failure_reason=failure_reason,
            duration_ms=elapsed_ms(started_at),
        )
        task = db.get(ProofreadTask, task_id)
        if task:
            task.error_msg = clamp_error_message(repr(exc))
            task.failure_reason = failure_reason
            task.last_error_at = datetime.utcnow()
            if should_retry_task(task.retry_count, task.max_retries, failure_reason):
                task.retry_count += 1
                task.status = "retrying"
            else:
                task.status = "failed"
            task.finished_at = datetime.utcnow() if task.status == "failed" else None
            db.commit()
            if task.status == "retrying":
                enqueue_proofread_task(task.id, task.owner_id, attempt=task.retry_count)
                log_info(
                    logger,
                    "task_requeued",
                    task_id=task.id,
                    retry_count=task.retry_count,
                    max_retries=task.max_retries,
                    failure_reason=failure_reason,
                )
    finally:
        db.close()
