from app.domain.issues import StoredIssue
from app.services.merger import dedup_issues


def make_issue(title: str, reason: str) -> StoredIssue:
    return StoredIssue(
        severity="P1",
        category="grammar",
        title=title,
        original_text="原文",
        suggested_text="建议",
        reason=reason,
        evidence="依据",
        confidence=0.9,
        source="llm",
    )


def test_dedup_issues_removes_duplicates_by_business_key():
    issue_a = make_issue("问题A", "原因A")
    issue_b = make_issue("问题B", "原因A")
    deduped = dedup_issues([issue_a, issue_b])
    assert len(deduped) == 1
