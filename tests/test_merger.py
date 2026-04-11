from app.domain.issues import StoredIssue
from app.services.merger import dedup_issues


def make_issue(
    title: str,
    reason: str,
    source: str = "llm",
    original_text: str = "old text",
    suggested_text: str = "new text",
    category: str = "grammar",
    position_start: int | None = None,
    position_end: int | None = None,
) -> StoredIssue:
    return StoredIssue(
        severity="P1",
        category=category,
        title=title,
        original_text=original_text,
        suggested_text=suggested_text,
        reason=reason,
        evidence="evidence",
        confidence=0.9,
        source=source,
        position_start=position_start,
        position_end=position_end,
    )


def test_dedup_issues_removes_exact_duplicates():
    issue_a = make_issue("Issue A", "same reason")
    issue_b = make_issue("Issue B", "same reason")
    deduped = dedup_issues([issue_a, issue_b])
    assert len(deduped) == 1


def test_dedup_issues_keeps_distinct_llm_reasons_without_rule_match():
    issue_a = make_issue("Issue A", "reason A")
    issue_b = make_issue("Issue B", "reason B")
    deduped = dedup_issues([issue_a, issue_b])
    assert len(deduped) == 2


def test_dedup_issues_drops_llm_duplicate_when_rule_engine_matches_semantic_key():
    rule_issue = make_issue("Rule issue", "rule reason", source="rule_engine")
    llm_issue = make_issue("LLM issue", "different llm reason", source="llm")

    deduped = dedup_issues([rule_issue, llm_issue])

    assert deduped == [rule_issue]


def test_dedup_issues_prefers_rule_engine_even_if_llm_appears_first():
    llm_issue = make_issue("LLM issue", "different llm reason", source="llm")
    rule_issue = make_issue("Rule issue", "rule reason", source="rule_engine")

    deduped = dedup_issues([llm_issue, rule_issue])

    assert deduped == [rule_issue]


def test_dedup_issues_normalizes_whitespace_for_rule_priority():
    rule_issue = make_issue("Rule issue", "rule reason", source="rule_engine", original_text="old text")
    llm_issue = make_issue("LLM issue", "llm reason", source="llm", original_text=" old   text ")

    deduped = dedup_issues([rule_issue, llm_issue])

    assert deduped == [rule_issue]


def test_dedup_issues_drops_llm_when_same_category_and_original_text_match_rule():
    rule_issue = make_issue("Rule issue", "rule reason", source="rule_engine", original_text="OA系统", suggested_text="OA平台")
    llm_issue = make_issue(
        "LLM issue",
        "llm reason",
        source="llm",
        original_text="OA系统",
        suggested_text="请各部门登录OA平台，并上报员工手机号码13800138000。",
    )

    deduped = dedup_issues([rule_issue, llm_issue])

    assert deduped == [rule_issue]


def test_dedup_issues_drops_llm_sentence_when_it_contains_rule_original_text():
    rule_issue = make_issue(
        "Rule issue",
        "rule reason",
        source="rule_engine",
        category="terminology",
        original_text="OA系统",
        suggested_text="OA平台",
        position_start=6,
        position_end=10,
    )
    llm_issue = make_issue(
        "LLM issue",
        "llm reason",
        source="llm",
        category="terminology",
        original_text="请各部门登录OA系统，并上报员工手机号13800138000。",
        suggested_text="请各部门登录OA平台，并上报员工手机号码13800138000。",
        position_start=0,
        position_end=31,
    )

    deduped = dedup_issues([rule_issue, llm_issue])

    assert deduped == [rule_issue]


def test_dedup_issues_drops_llm_sentence_when_it_overlaps_rule_position():
    rule_issue = make_issue(
        "Rule issue",
        "rule reason",
        source="rule_engine",
        category="compliance",
        original_text="13800138000",
        suggested_text="138****8000",
        position_start=19,
        position_end=30,
    )
    llm_issue = make_issue(
        "LLM issue",
        "llm reason",
        source="llm",
        category="compliance",
        original_text="请各部门登录OA系统，并上报员工手机号13800138000。",
        suggested_text="请各部门登录OA平台，并上报员工手机号码13800138000，请注意，该号码已进行脱敏处理。",
        position_start=0,
        position_end=31,
    )

    deduped = dedup_issues([rule_issue, llm_issue])

    assert deduped == [rule_issue]
