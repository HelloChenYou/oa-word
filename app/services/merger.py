from app.domain.issues import StoredIssue


def dedup_issues(issues: list[StoredIssue]) -> list[StoredIssue]:
    seen = set()
    result: list[StoredIssue] = []
    for issue in issues:
        key = (
            issue.category,
            issue.original_text,
            issue.suggested_text,
            issue.reason,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(issue)
    return result
