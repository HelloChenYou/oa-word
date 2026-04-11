import json
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import or_, select

from app.db import SessionLocal
from app.domain.rules import KnowledgeRule

if TYPE_CHECKING:
    from app.models import KnowledgeRuleRecord


KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"
PUBLIC_RULES_PATH = KNOWLEDGE_DIR / "public_rules.json"
PRIVATE_RULES_DIR = KNOWLEDGE_DIR / "private_rules"


def _load_seed_file(path: Path) -> list[KnowledgeRule]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [KnowledgeRule.model_validate(item) for item in data]


def _record_to_rule(record) -> KnowledgeRule:
    return KnowledgeRule(
        rule_id=record.rule_id,
        scope=record.scope,
        kind=record.kind,
        title=record.title,
        severity=record.severity,
        category=record.category,
        pattern=record.pattern,
        replacement=record.replacement,
        reason=record.reason,
        evidence=record.evidence,
        enabled=record.enabled,
    )


def seed_builtin_rules() -> None:
    """Seed built-in public/private rules into the database if they are missing."""
    seed_rules = _load_seed_file(PUBLIC_RULES_PATH)
    for seed_file in PRIVATE_RULES_DIR.glob("*.json"):
        seed_rules.extend(_load_seed_file(seed_file))

    if not seed_rules:
        return

    db = SessionLocal()
    try:
        from app.models import KnowledgeRuleRecord

        existing_rule_ids = {
            row[0] for row in db.execute(select(KnowledgeRuleRecord.rule_id)).all()
        }
        existing_rules = {
            row.rule_id: row for row in db.execute(select(KnowledgeRuleRecord)).scalars().all()
        }
        for rule in seed_rules:
            if rule.rule_id in existing_rule_ids:
                record = existing_rules[rule.rule_id]
                if record.evidence.startswith("knowledge:"):
                    record.scope = rule.scope
                    record.kind = rule.kind
                    record.title = rule.title
                    record.severity = rule.severity
                    record.category = rule.category
                    record.pattern = rule.pattern
                    record.replacement = rule.replacement
                    record.reason = rule.reason
                    record.evidence = rule.evidence
                continue
            owner_id = None
            if rule.scope == "private":
                owner_id = rule.evidence.split("/")[1].split(".")[0] if "private_rules/" in rule.evidence else None
            db.add(
                KnowledgeRuleRecord(
                    rule_id=rule.rule_id,
                    scope=rule.scope,
                    owner_id=owner_id,
                    kind=rule.kind,
                    title=rule.title,
                    severity=rule.severity,
                    category=rule.category,
                    pattern=rule.pattern,
                    replacement=rule.replacement,
                    reason=rule.reason,
                    evidence=rule.evidence,
                    enabled=rule.enabled,
                )
            )
        db.commit()
    finally:
        db.close()


def load_public_rules() -> list[KnowledgeRule]:
    db = SessionLocal()
    try:
        from app.models import KnowledgeRuleRecord

        rows = db.execute(
            select(KnowledgeRuleRecord).where(
                KnowledgeRuleRecord.scope == "public",
                KnowledgeRuleRecord.enabled.is_(True),
            )
        ).scalars().all()
        return [_record_to_rule(row) for row in rows]
    finally:
        db.close()


def load_private_rules(owner_id: str | None) -> list[KnowledgeRule]:
    if not owner_id:
        return []
    db = SessionLocal()
    try:
        from app.models import KnowledgeRuleRecord

        rows = db.execute(
            select(KnowledgeRuleRecord).where(
                KnowledgeRuleRecord.scope == "private",
                KnowledgeRuleRecord.owner_id == owner_id,
                KnowledgeRuleRecord.enabled.is_(True),
            )
        ).scalars().all()
        return [_record_to_rule(row) for row in rows]
    finally:
        db.close()


def list_rules(scope: str | None = None, owner_id: str | None = None, keyword: str | None = None):
    db = SessionLocal()
    try:
        from app.models import KnowledgeRuleRecord

        stmt = select(KnowledgeRuleRecord)
        if scope:
            stmt = stmt.where(KnowledgeRuleRecord.scope == scope)
        if owner_id is not None:
            stmt = stmt.where(KnowledgeRuleRecord.owner_id == owner_id)
        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    KnowledgeRuleRecord.rule_id.ilike(pattern),
                    KnowledgeRuleRecord.owner_id.ilike(pattern),
                    KnowledgeRuleRecord.title.ilike(pattern),
                    KnowledgeRuleRecord.pattern.ilike(pattern),
                    KnowledgeRuleRecord.replacement.ilike(pattern),
                    KnowledgeRuleRecord.reason.ilike(pattern),
                    KnowledgeRuleRecord.evidence.ilike(pattern),
                )
            )
        return db.execute(stmt.order_by(KnowledgeRuleRecord.id.asc())).scalars().all()
    finally:
        db.close()


def create_rule(rule: KnowledgeRule, owner_id: str | None = None):
    db = SessionLocal()
    try:
        from app.models import KnowledgeRuleRecord

        record = KnowledgeRuleRecord(
            rule_id=rule.rule_id,
            scope=rule.scope,
            owner_id=owner_id,
            kind=rule.kind,
            title=rule.title,
            severity=rule.severity,
            category=rule.category,
            pattern=rule.pattern,
            replacement=rule.replacement,
            reason=rule.reason,
            evidence=rule.evidence,
            enabled=rule.enabled,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()


def update_rule(rule_id: str, owner_id: str | None = None, **updates):
    db = SessionLocal()
    try:
        from app.models import KnowledgeRuleRecord

        stmt = select(KnowledgeRuleRecord).where(KnowledgeRuleRecord.rule_id == rule_id)
        if owner_id is not None:
            stmt = stmt.where(KnowledgeRuleRecord.owner_id == owner_id)
        record = db.execute(stmt).scalar_one_or_none()
        if record is None:
            return None

        for field, value in updates.items():
            if value is None or not hasattr(record, field):
                continue
            setattr(record, field, value)

        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()


def delete_rule(rule_id: str, owner_id: str | None = None) -> bool:
    db = SessionLocal()
    try:
        from app.models import KnowledgeRuleRecord

        stmt = select(KnowledgeRuleRecord).where(KnowledgeRuleRecord.rule_id == rule_id)
        if owner_id is not None:
            stmt = stmt.where(KnowledgeRuleRecord.owner_id == owner_id)
        record = db.execute(stmt).scalar_one_or_none()
        if record is None:
            return False
        db.delete(record)
        db.commit()
        return True
    finally:
        db.close()


def build_template_rules(template_rule_pack: str) -> list[KnowledgeRule]:
    if not template_rule_pack or template_rule_pack == "{}":
        return []

    try:
        parsed = json.loads(template_rule_pack)
    except json.JSONDecodeError:
        return []

    rules: list[KnowledgeRule] = []
    for index, section in enumerate(parsed.get("required_sections", []), start=1):
        if not isinstance(section, str) or not section.strip():
            continue
        rules.append(
            KnowledgeRule(
                rule_id=f"template_required_section_{index}",
                scope="template",
                kind="required_section",
                title="模板章节缺失",
                severity="P1",
                category="structure",
                pattern=section.strip(),
                replacement="",
                reason=f"模板要求保留章节“{section.strip()}”",
                evidence=f"template_rule_pack.required_sections[{index - 1}]",
            )
        )
    return rules


def build_rule_pack_summary(rules: list[KnowledgeRule]) -> str:
    payload = [
        {
            "rule_id": rule.rule_id,
            "scope": rule.scope,
            "kind": rule.kind,
            "title": rule.title,
            "severity": rule.severity,
            "category": rule.category,
            "pattern": rule.pattern,
            "replacement": rule.replacement,
            "reason": rule.reason,
            "evidence": rule.evidence,
        }
        for rule in rules
    ]
    return json.dumps({"rules": payload}, ensure_ascii=False)
