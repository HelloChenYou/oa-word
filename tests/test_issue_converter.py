import json

from app.services.issue_converter import validate_llm_response, validate_rule_issue


def test_validate_llm_response_accepts_strict_schema():
    payload = {
        "issues": [
            {
                "severity": "P1",
                "category": "grammar",
                "title": "语法问题",
                "original_text": "原文",
                "suggested_text": "建议",
                "reason": "原因",
                "evidence": "依据",
                "confidence": 0.9,
                "source": "llm",
            }
        ]
    }
    issues = validate_llm_response(json.dumps(payload, ensure_ascii=False))
    assert len(issues) == 1
    assert issues[0].source == "llm"
    assert issues[0].category == "grammar"


def test_validate_rule_issue_accepts_rule_engine_payload():
    issue = validate_rule_issue(
        {
            "severity": "P0",
            "category": "compliance",
            "title": "敏感信息",
            "original_text": "13800138000",
            "suggested_text": "138****8000",
            "reason": "疑似手机号",
            "evidence": "rule_pack:compliance_v1",
            "confidence": 0.99,
            "source": "rule_engine",
        }
    )
    assert issue.source == "rule_engine"
    assert issue.severity == "P0"

