import pytest
from fastapi import HTTPException

from app.config import settings, validate_runtime_settings
from app.security import _extract_bearer_token, require_admin


def test_extract_bearer_token():
    assert _extract_bearer_token("Bearer abc123") == "abc123"
    assert _extract_bearer_token("bearer xyz") == "xyz"
    assert _extract_bearer_token("Basic abc") is None
    assert _extract_bearer_token(None) is None


def test_require_admin_accepts_matching_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_api_token", "secret-token")
    require_admin(x_admin_token="secret-token")
    require_admin(authorization="Bearer secret-token")


def test_require_admin_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_api_token", "secret-token")
    with pytest.raises(HTTPException) as exc:
        require_admin(x_admin_token="wrong-token")
    assert exc.value.status_code == 401


def test_validate_runtime_settings_requires_token_in_prod(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "admin_api_token", None)
    monkeypatch.setattr(settings, "cors_allow_origins", "http://localhost:5173")
    with pytest.raises(RuntimeError):
        validate_runtime_settings()


def test_validate_runtime_settings_requires_cors_origin(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "dev")
    monkeypatch.setattr(settings, "cors_allow_origins", "")
    with pytest.raises(RuntimeError):
        validate_runtime_settings()


def test_retryable_task_error_types_are_parsed(monkeypatch):
    monkeypatch.setattr(settings, "retryable_task_error_types", "timeout, llm_http_error ,unknown_error")
    assert settings.retryable_task_error_types_set == {
        "timeout",
        "llm_http_error",
        "unknown_error",
    }
