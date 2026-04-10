from datetime import datetime

from sqlalchemy import delete

from app.db import SessionLocal
from app.logging_utils import configure_logging, get_logger
from app.models import ProofreadIssue, ProofreadTask, Template
from app.services.boundary_guard import clamp_error_message
from app.services.issue_converter import to_issue_record
from app.services.orchestrator import run_proofread_sync, run_proofread_with_template_sync

configure_logging()
logger = get_logger(__name__)


def process_proofread_task(task_id: str, owner_id: str | None = None) -> None:
    db = SessionLocal()
    try:
        task = db.get(ProofreadTask, task_id)
        if not task:
            return

        task.status = "running"
        task.error_msg = ""
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
        task.finished_at = datetime.utcnow()
        db.commit()
        logger.info("[TASK_SUCCESS] task_id=%s issue_count=%s", task_id, len(issues))
    except Exception as exc:
        logger.exception("[TASK_FAILED] task_id=%s", task_id)
        task = db.get(ProofreadTask, task_id)
        if task:
            task.status = "failed"
            task.error_msg = clamp_error_message(repr(exc))
            task.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
