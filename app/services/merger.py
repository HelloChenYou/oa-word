def dedup_issues(issues: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for issue in issues:
        key = (
            issue.get("category", ""),
            issue.get("original_text", ""),
            issue.get("suggested_text", ""),
            issue.get("reason", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(issue)
    return result
