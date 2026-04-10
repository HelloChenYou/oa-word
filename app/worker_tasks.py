from datetime import datetime

from sqlalchemy import delete

from app.db import SessionLocal
from app.models import ProofreadIssue, ProofreadTask, Template
from app.services.orchestrator import run_proofread_sync, run_proofread_with_template_sync


def process_proofread_task(task_id: str) -> None:
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
            )
        else:
            issues = run_proofread_sync(task.source_text, mode=task.mode, scene=task.scene)

        for issue in issues:
            db.add(ProofreadIssue(task_id=task_id, **issue))

        task.status = "success"
        task.finished_at = datetime.utcnow()
        db.commit()
    except Exception as exc:
        task = db.get(ProofreadTask, task_id)
        if task:
            task.status = "failed"
            task.error_msg = repr(exc)
            task.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
