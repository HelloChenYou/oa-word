import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.domain.rules import KnowledgeRule
from app.schemas import CreateRuleReq, RuleOut, UpdateRuleReq
from app.security import require_authenticated
from app.services.rule_engine import validate_regex_pattern
from app.services.rule_repository import create_rule, delete_rule, list_rules, update_rule


router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


def _is_admin(user: dict) -> bool:
    return user.get("role") == "admin"


def _assert_can_write_rule(scope: str, owner_id: str | None, current_user: dict) -> str | None:
    if scope == "public":
        if not _is_admin(current_user):
            raise HTTPException(status_code=403, detail="public rules can only be modified by admin")
        return None

    if _is_admin(current_user):
        return owner_id or current_user["username"]

    if owner_id and owner_id != current_user["username"]:
        raise HTTPException(status_code=403, detail="cannot modify another user's private rules")
    return current_user["username"]


def _build_rule_evidence(scope: str, owner_id: str | None, rule_id: str) -> str:
    if scope == "public":
        return f"public_rule:{rule_id}"
    return f"private_rule:{owner_id or 'unknown'}:{rule_id}"


def _assert_safe_rule(kind: str, pattern: str) -> None:
    if kind != "regex_mask":
        return
    try:
        validate_regex_pattern(pattern)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _assert_no_rule_conflict(
    *,
    scope: str,
    owner_id: str | None,
    kind: str,
    pattern: str,
    replacement: str,
    current_rule_id: str | None = None,
) -> None:
    for row in list_rules(scope=scope, owner_id=owner_id):
        if current_rule_id and row.rule_id == current_rule_id:
            continue
        if not row.enabled or row.kind != kind or row.pattern != pattern:
            continue
        if row.replacement != replacement:
            raise HTTPException(
                status_code=409,
                detail=f"rule conflicts with existing rule: {row.rule_id}",
            )


@router.get("", response_model=list[RuleOut])
def get_rules(
    scope: str | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    current_user: dict = Depends(require_authenticated),
):
    effective_scope = scope
    effective_owner_id = owner_id
    if not _is_admin(current_user):
        if scope == "public":
            effective_owner_id = None
        else:
            effective_scope = "private"
            effective_owner_id = current_user["username"]

    rows = list_rules(scope=effective_scope, owner_id=effective_owner_id, keyword=keyword)
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
def post_rule(req: CreateRuleReq, current_user: dict = Depends(require_authenticated)):
    owner_id = _assert_can_write_rule(req.scope, req.owner_id, current_user)
    _assert_safe_rule(req.kind, req.pattern)
    _assert_no_rule_conflict(
        scope=req.scope,
        owner_id=owner_id,
        kind=req.kind,
        pattern=req.pattern,
        replacement=req.replacement,
    )
    rule_id = f"rule_{uuid.uuid4().hex[:12]}"
    rule = KnowledgeRule(
        rule_id=rule_id,
        scope=req.scope,
        kind=req.kind,
        title=req.title,
        severity=req.severity,
        category=req.category,
        pattern=req.pattern,
        replacement=req.replacement,
        reason=req.reason,
        evidence=_build_rule_evidence(req.scope, owner_id, rule_id),
        enabled=req.enabled,
    )
    record = create_rule(rule=rule, owner_id=owner_id)
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


@router.patch("/{rule_id}", response_model=RuleOut)
def patch_rule(
    rule_id: str,
    req: UpdateRuleReq,
    owner_id: str | None = Query(default=None),
    current_user: dict = Depends(require_authenticated),
):
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="no updates provided")
    updates.pop("evidence", None)

    lookup_owner_id = owner_id if _is_admin(current_user) else current_user["username"]
    existing = list_rules(owner_id=lookup_owner_id, keyword=rule_id)
    existing = [rule for rule in existing if rule.rule_id == rule_id]
    if not existing:
        raise HTTPException(status_code=404, detail="rule not found")
    current_scope = existing[0].scope
    existing_rule = existing[0]
    effective_scope = updates.get("scope", current_scope)
    effective_owner_id = _assert_can_write_rule(effective_scope, lookup_owner_id, current_user)
    effective_kind = updates.get("kind", existing_rule.kind)
    effective_pattern = updates.get("pattern", existing_rule.pattern)
    effective_replacement = updates.get("replacement", existing_rule.replacement)
    _assert_safe_rule(effective_kind, effective_pattern)
    if updates.get("enabled", existing_rule.enabled):
        _assert_no_rule_conflict(
            scope=effective_scope,
            owner_id=effective_owner_id,
            kind=effective_kind,
            pattern=effective_pattern,
            replacement=effective_replacement,
            current_rule_id=rule_id,
        )

    record = update_rule(rule_id=rule_id, owner_id=lookup_owner_id, **updates)
    if record is None:
        raise HTTPException(status_code=404, detail="rule not found")

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
def remove_rule(
    rule_id: str,
    owner_id: str | None = Query(default=None),
    current_user: dict = Depends(require_authenticated),
):
    lookup_owner_id = owner_id if _is_admin(current_user) else current_user["username"]
    existing = list_rules(owner_id=lookup_owner_id, keyword=rule_id)
    existing = [rule for rule in existing if rule.rule_id == rule_id]
    if not existing:
        raise HTTPException(status_code=404, detail="rule not found")
    _assert_can_write_rule(existing[0].scope, lookup_owner_id, current_user)

    deleted = delete_rule(rule_id=rule_id, owner_id=lookup_owner_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="rule not found")
    return {"ok": True}
