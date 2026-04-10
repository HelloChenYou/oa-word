from fastapi import HTTPException

from app.config import settings
from app.services.boundary_guard import (
    clamp_error_message,
    clamp_issues,
    ensure_template_file_within_limit,
    ensure_template_text_within_limit,
    ensure_text_within_limit,
)


def test_ensure_text_within_limit_accepts_short_text():
    ensure_text_within_limit("short text")


def test_ensure_text_within_limit_rejects_long_text():
    long_text = "a" * (settings.max_task_text_chars + 1)
    try:
        ensure_text_within_limit(long_text)
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "text too long" in str(exc.detail)


def test_ensure_template_file_within_limit_rejects_large_file():
    try:
        ensure_template_file_within_limit(settings.max_template_file_bytes + 1)
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "template file too large" in str(exc.detail)


def test_ensure_template_text_within_limit_rejects_long_template_text():
    try:
        ensure_template_text_within_limit("a" * (settings.max_template_text_chars + 1))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "template text too long" in str(exc.detail)


def test_clamp_issues_applies_max_limit():
    issues = list(range(settings.max_issues_per_task + 10))
    clamped = clamp_issues(issues)
    assert len(clamped) == settings.max_issues_per_task


def test_clamp_error_message_truncates_long_message():
    raw = "x" * (settings.max_error_msg_chars + 10)
    clamped = clamp_error_message(raw)
    assert len(clamped) > 0
    assert clamped.endswith("...(truncated)")
