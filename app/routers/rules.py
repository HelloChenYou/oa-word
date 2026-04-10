import uuid

from fastapi import APIRouter, HTTPException, Query

from app.domain.rules import KnowledgeRule
from app.schemas import CreateRuleReq, RuleOut
from app.services.rule_repository import create_rule, delete_rule, list_rules


router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


@router.get("", response_model=list[RuleOut])
def get_rules(
    scope: str | None = Query(default=None),
    owner_id: str | None = Query(default=None),
):
    rows = list_rules(scope=scope, owner_id=owner_id)
    return [
        RuleOut(
            rule_id=row.rule_id,
            scope=row.scope,
            owner_id=row.owner_id,
            kind=row.kind,
            title=row.title,
            severity=row.severity,
            category=row.category,
            pattern=row.pattern,
            replacement=row.replacement,
            reason=row.reason,
            evidence=row.evidence,
            enabled=row.enabled,
        )
        for row in rows
    ]


@router.post("", response_model=RuleOut)
def post_rule(req: CreateRuleReq):
    rule = KnowledgeRule(
        rule_id=f"rule_{uuid.uuid4().hex[:12]}",
        scope=req.scope,
        kind=req.kind,
        title=req.title,
        severity=req.severity,
        category=req.category,
        pattern=req.pattern,
        replacement=req.replacement,
        reason=req.reason,
        evidence=req.evidence,
        enabled=req.enabled,
    )
    record = create_rule(rule=rule, owner_id=req.owner_id)
    return RuleOut(
        rule_id=record.rule_id,
        scope=record.scope,
        owner_id=record.owner_id,
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


@router.delete("/{rule_id}")
def remove_rule(rule_id: str, owner_id: str | None = Query(default=None)):
    deleted = delete_rule(rule_id=rule_id, owner_id=owner_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="rule not found")
    return {"ok": True}
