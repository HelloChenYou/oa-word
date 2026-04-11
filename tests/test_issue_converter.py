import json

import pytest
from pydantic import ValidationError

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
                "position_start": 1,
                "position_end": 3,
            }
        ]
    }
    issues = validate_llm_response(json.dumps(payload, ensure_ascii=False))
    assert len(issues) == 1
    assert issues[0].source == "llm"
    assert issues[0].category == "grammar"
    assert issues[0].position_start == 1
    assert issues[0].position_end == 3


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
            "position_start": 0,
            "position_end": 11,
        }
    )
    assert issue.source == "rule_engine"
    assert issue.severity == "P0"
    assert issue.position_start == 0
    assert issue.position_end == 11


def test_validate_llm_response_rejects_missing_positions():
    payload = {
        "issues": [
            {
                "severity": "P2",
                "category": "style",
                "title": "style issue",
                "original_text": "old",
                "suggested_text": "new",
                "reason": "reason",
                "evidence": "evidence",
                "confidence": 0.8,
                "source": "llm",
            }
        ]
    }
    with pytest.raises(ValidationError):
        validate_llm_response(json.dumps(payload, ensure_ascii=False))


def test_validate_llm_response_accepts_required_null_positions():
    payload = {
        "issues": [
            {
                "severity": "P2",
                "category": "style",
                "title": "style issue",
                "original_text": "old",
                "suggested_text": "new",
                "reason": "reason",
                "evidence": "evidence",
                "confidence": 0.8,
                "source": "llm",
                "position_start": None,
                "position_end": None,
            }
        ]
    }
    issues = validate_llm_response(json.dumps(payload, ensure_ascii=False))
    assert issues[0].position_start is None
    assert issues[0].position_end is None
