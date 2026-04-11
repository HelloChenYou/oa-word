from types import SimpleNamespace

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.routers import rules as rules_router_module
from app.routers.rules import router as rules_router
from app.security import require_admin


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(rules_router, dependencies=[Depends(require_admin)])
    return TestClient(app)


def _rule_row(**overrides):
    payload = {
        "rule_id": "rule_existing",
        "scope": "public",
        "owner_id": None,
        "kind": "term_replace",
        "title": "Existing",
        "severity": "P1",
        "category": "terminology",
        "pattern": "login",
        "replacement": "log in",
        "reason": "existing",
        "evidence": "public_rule:rule_existing",
        "enabled": True,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_create_rule_rejects_unsafe_regex(monkeypatch):
    monkeypatch.setattr("app.config.settings.admin_api_token", "secret-token")
    monkeypatch.setattr(rules_router_module, "list_rules", lambda scope=None, owner_id=None, keyword=None: [])
    client = build_client()

    response = client.post(
        "/api/v1/rules",
        headers={"X-Admin-Token": "secret-token"},
        json={
            "scope": "public",
            "kind": "regex_mask",
            "title": "Unsafe regex",
            "severity": "P1",
            "category": "compliance",
            "pattern": "(a+)+$",
            "replacement": "",
            "reason": "unsafe",
            "enabled": True,
        },
    )

    assert response.status_code == 400
    assert "unsafe" in response.json()["detail"]


def test_create_rule_rejects_conflicting_rule(monkeypatch):
    monkeypatch.setattr("app.config.settings.admin_api_token", "secret-token")
    monkeypatch.setattr(
        rules_router_module,
        "list_rules",
        lambda scope=None, owner_id=None, keyword=None: [_rule_row()],
    )
    client = build_client()

    response = client.post(
        "/api/v1/rules",
        headers={"X-Admin-Token": "secret-token"},
        json={
            "scope": "public",
            "kind": "term_replace",
            "title": "Conflicting",
            "severity": "P1",
            "category": "terminology",
            "pattern": "login",
            "replacement": "sign in",
            "reason": "conflict",
            "enabled": True,
        },
    )

    assert response.status_code == 409
    assert "conflicts" in response.json()["detail"]
