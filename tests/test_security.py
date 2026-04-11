import pytest
from fastapi import HTTPException

from app.config import settings, validate_runtime_settings
from app.security import (
    _extract_bearer_token,
    create_access_token,
    decode_access_token,
    hash_password,
    require_admin,
    verify_password,
)


def test_extract_bearer_token():
    assert _extract_bearer_token("Bearer abc123") == "abc123"
    assert _extract_bearer_token("bearer xyz") == "xyz"
    assert _extract_bearer_token("Basic abc") is None
    assert _extract_bearer_token(None) is None


def test_password_hash_roundtrip():
    password_hash = hash_password("secret-pass")
    assert verify_password("secret-pass", password_hash) is True
    assert verify_password("wrong-pass", password_hash) is False


def test_access_token_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret_key", "unit-test-secret")
    token = create_access_token("alice", "admin", True)
    payload = decode_access_token(token)
    assert payload["sub"] == "alice"
    assert payload["role"] == "admin"
    assert payload["must_change_password"] is True


def test_require_admin_accepts_admin_role():
    user = require_admin(current_user={"username": "alice", "role": "admin"})
    assert user["username"] == "alice"


def test_require_admin_rejects_non_admin_role():
    with pytest.raises(HTTPException) as exc:
        require_admin(current_user={"username": "bob", "role": "operator"})
    assert exc.value.status_code == 403


def test_validate_runtime_settings_requires_secure_auth_secret_in_prod(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "admin_api_token", None)
    monkeypatch.setattr(settings, "auth_secret_key", "change-me-in-prod")
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
