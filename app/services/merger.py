from app.domain.issues import StoredIssue


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def _semantic_key(issue: StoredIssue) -> tuple[str, str, str]:
    return (
        issue.category,
        _normalize_text(issue.original_text),
        _normalize_text(issue.suggested_text),
    )


def _rule_match_key(issue: StoredIssue) -> tuple[str, str]:
    return (
        issue.category,
        _normalize_text(issue.original_text),
    )


def _positions_overlap(left: StoredIssue, right: StoredIssue) -> bool:
    if (
        left.position_start is None
        or left.position_end is None
        or right.position_start is None
        or right.position_end is None
    ):
        return False
    return left.position_start < right.position_end and right.position_start < left.position_end


def _is_covered_by_rule(issue: StoredIssue, rule_issues: list[StoredIssue]) -> bool:
    issue_original = _normalize_text(issue.original_text)
    for rule_issue in rule_issues:
        if issue.category != rule_issue.category:
            continue
        rule_original = _normalize_text(rule_issue.original_text)
        if not rule_original:
            continue
        if _positions_overlap(issue, rule_issue):
            return True
        if rule_original in issue_original or issue_original in rule_original:
            return True
    return False


def _exact_key(issue: StoredIssue) -> tuple[str, str, str, str]:
    return (
        issue.category,
        _normalize_text(issue.original_text),
        _normalize_text(issue.suggested_text),
        _normalize_text(issue.reason),
    )


def dedup_issues(issues: list[StoredIssue]) -> list[StoredIssue]:
    rule_issues = [issue for issue in issues if issue.source == "rule_engine"]
    rule_keys = {_semantic_key(issue) for issue in rule_issues}
    rule_match_keys = {_rule_match_key(issue) for issue in rule_issues}
    seen_exact = set()
    seen_semantic = set()
    result: list[StoredIssue] = []
    for issue in issues:
        semantic_key = _semantic_key(issue)
        rule_match_key = _rule_match_key(issue)
        exact_key = _exact_key(issue)
        if issue.source == "llm" and (
            semantic_key in rule_keys
            or rule_match_key in rule_match_keys
            or _is_covered_by_rule(issue, rule_issues)
        ):
            continue
        if issue.source == "rule_engine" and semantic_key in seen_semantic:
            continue
        if exact_key in seen_exact:
            continue
        seen_exact.add(exact_key)
        if issue.source == "rule_engine":
            seen_semantic.add(semantic_key)
        result.append(issue)
    return result
