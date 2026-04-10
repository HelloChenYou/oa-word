from typing import TYPE_CHECKING

from app.domain.issues import LlmIssuesResp, RuleIssue, StoredIssue

if TYPE_CHECKING:
    from app.models import ProofreadIssue


def validate_llm_response(content: str) -> list[StoredIssue]:
    """Validate and normalize raw LLM JSON into canonical stored issues."""
    parsed = LlmIssuesResp.model_validate_json(content)
    return [StoredIssue.model_validate(issue.model_dump()) for issue in parsed.issues]


def validate_rule_issue(payload: dict) -> StoredIssue:
    """Normalize rule-engine output into the canonical issue model."""
    rule_issue = RuleIssue.model_validate(payload)
    return StoredIssue.model_validate(rule_issue.model_dump())


def to_issue_record(task_id: str, issue: StoredIssue):
    """Convert canonical issue model into a SQLAlchemy row."""
    from app.models import ProofreadIssue

    return ProofreadIssue(task_id=task_id, **issue.model_dump())


def from_issue_record(row) -> StoredIssue:
    """Convert a SQLAlchemy row back into the canonical issue model."""
    return StoredIssue(
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
