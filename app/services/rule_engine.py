import re


TERM_MAP = {
    "OA系统": "OA 平台",
    "登陆": "登录",
}

SENSITIVE_PATTERNS = [
    (r"\b1[3-9]\d{9}\b", "疑似手机号，建议脱敏"),
]


def check_rules(text: str) -> list[dict]:
    issues = []

    for wrong, right in TERM_MAP.items():
        for _ in re.finditer(re.escape(wrong), text):
            issues.append(
                {
                    "severity": "P1",
                    "category": "terminology",
                    "title": "公司术语不一致",
                    "original_text": wrong,
                    "suggested_text": right,
                    "reason": "与公司术语库冲突",
                    "evidence": "rule_pack:corp_terms_v1",
                    "confidence": 0.98,
                    "source": "rule_engine",
                }
            )

    for pattern, msg in SENSITIVE_PATTERNS:
        for m in re.finditer(pattern, text):
            hit = m.group(0)
            issues.append(
                {
                    "severity": "P0",
                    "category": "compliance",
                    "title": "疑似敏感信息",
                    "original_text": hit,
                    "suggested_text": f"{hit[:3]}****{hit[-4:]}",
                    "reason": msg,
                    "evidence": "rule_pack:compliance_v1",
                    "confidence": 0.99,
                    "source": "rule_engine",
                }
            )

    return issues
