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


def test_rules_endpoint_requires_admin_token(monkeypatch):
    monkeypatch.setattr("app.config.settings.admin_api_token", "secret-token")
    client = build_client()
    response = client.get("/api/v1/rules")
    assert response.status_code == 401


def test_list_rules_returns_payload(monkeypatch):
    monkeypatch.setattr("app.config.settings.admin_api_token", "secret-token")
    monkeypatch.setattr(
        rules_router_module,
        "list_rules",
        lambda scope=None, owner_id=None, keyword=None: [
            SimpleNamespace(
                rule_id="rule_1",
                scope="private",
                owner_id="demo_user",
                kind="term_replace",
                title="统一术语",
                severity="P1",
                category="style",
                pattern="登陆",
                replacement="登录",
                reason="术语统一",
                evidence="private_rule:demo_user:login",
                enabled=True,
            )
        ],
    )
    client = build_client()
    response = client.get(
        "/api/v1/rules?scope=private&owner_id=demo_user",
        headers={"X-Admin-Token": "secret-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body[0]["rule_id"] == "rule_1"
    assert body[0]["owner_id"] == "demo_user"


def test_create_rule_returns_created_record(monkeypatch):
    monkeypatch.setattr("app.config.settings.admin_api_token", "secret-token")

    def fake_create_rule(rule, owner_id=None):
        return SimpleNamespace(
            rule_id=rule.rule_id,
            scope=rule.scope,
            owner_id=owner_id,
            kind=rule.kind,
            title=rule.title,
            severity=rule.severity,
            category=rule.category,
            pattern=rule.pattern,
            replacement=rule.replacement,
            reason=rule.reason,
            evidence=rule.evidence,
            enabled=rule.enabled,
        )

    monkeypatch.setattr(rules_router_module, "create_rule", fake_create_rule)
    client = build_client()
    response = client.post(
        "/api/v1/rules",
        headers={"X-Admin-Token": "secret-token"},
        json={
            "owner_id": "demo_user",
            "scope": "private",
            "kind": "term_replace",
            "title": "统一术语",
            "severity": "P1",
            "category": "style",
            "pattern": "登陆",
            "replacement": "登录",
            "reason": "术语统一",
            "enabled": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["owner_id"] == "demo_user"
    assert response.json()["evidence"].startswith("private_rule:demo_user:rule_")


def test_patch_rule_updates_record(monkeypatch):
    monkeypatch.setattr("app.config.settings.admin_api_token", "secret-token")
    monkeypatch.setattr(
        rules_router_module,
        "list_rules",
        lambda scope=None, owner_id=None, keyword=None: [
            SimpleNamespace(
                rule_id="rule_1",
                scope="private",
                owner_id=owner_id,
                kind="term_replace",
                title="缁熶竴鏈",
                severity="P1",
                category="style",
                pattern="鐧婚檰",
                replacement="鐧诲綍",
                reason="鏈缁熶竴",
                evidence="private_rule:demo_user:login",
                enabled=True,
            )
        ],
    )
    monkeypatch.setattr(
        rules_router_module,
        "update_rule",
        lambda rule_id, owner_id=None, **updates: SimpleNamespace(
            rule_id=rule_id,
            scope="private",
            owner_id=owner_id,
            kind="term_replace",
            title="统一术语",
            severity="P1",
            category="style",
            pattern="登陆",
            replacement="登录",
            reason="术语统一",
            evidence="private_rule:demo_user:login",
            enabled=updates.get("enabled", True),
        ),
    )
    client = build_client()
    response = client.patch(
        "/api/v1/rules/rule_1?owner_id=demo_user",
        headers={"X-Admin-Token": "secret-token"},
        json={"enabled": False},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_delete_rule_handles_missing_record(monkeypatch):
    monkeypatch.setattr("app.config.settings.admin_api_token", "secret-token")
    monkeypatch.setattr("app.routers.rules.list_rules", lambda scope=None, owner_id=None, keyword=None: [])
    monkeypatch.setattr(rules_router_module, "delete_rule", lambda rule_id, owner_id=None: False)
    client = build_client()
    response = client.delete(
        "/api/v1/rules/rule_missing",
        headers={"X-Admin-Token": "secret-token"},
    )
    assert response.status_code == 404
