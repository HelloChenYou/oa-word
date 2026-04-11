from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.routers.users import router as users_router
import app.routers.users as users_router_module
from app.security import require_admin


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(users_router, dependencies=[Depends(require_admin)])
    return TestClient(app)


def test_list_users_endpoint_works_with_admin_dependency_override():
    client = build_client()
    app = client.app
    app.dependency_overrides[require_admin] = lambda: {"username": "admin", "role": "admin", "must_change_password": False}
    import app.routers.users as users_router_module

    class DummyUser:
        def __init__(self):
            self.username = "admin"
            self.role = "admin"
            self.enabled = True
            self.must_change_password = False
            self.created_at = __import__("datetime").datetime(2026, 4, 11, 0, 0, 0)

    users_router_module.list_users = lambda: [DummyUser()]
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    assert response.json()[0]["username"] == "admin"
    app.dependency_overrides.clear()


def test_user_management_endpoints(monkeypatch):
    client = build_client()
    app = client.app
    app.dependency_overrides[require_admin] = lambda: {"username": "admin", "role": "admin", "must_change_password": False}

    class DummyUser:
        def __init__(self, username: str, role: str = "operator", enabled: bool = True, must_change_password: bool = True):
            self.username = username
            self.role = role
            self.enabled = enabled
            self.must_change_password = must_change_password
            self.created_at = __import__("datetime").datetime(2026, 4, 11, 0, 0, 0)

    users = {"operator1": DummyUser("operator1")}

    monkeypatch.setattr(users_router_module, "list_users", lambda: list(users.values()))
    monkeypatch.setattr(
        users_router_module,
        "create_user_account",
        lambda username, password, role, enabled=True, must_change_password=True: users.setdefault(
            username, DummyUser(username, role, enabled, must_change_password)
        ) if username not in users else None,
    )
    monkeypatch.setattr(
        users_router_module,
        "update_user_account",
        lambda username, **updates: (
            None
            if username not in users
            else _apply_updates(users[username], updates)
        ),
    )
    monkeypatch.setattr(
        users_router_module,
        "reset_user_password",
        lambda username, new_password, must_change_password=True: (
            None
            if username not in users
            else _apply_updates(users[username], {"must_change_password": must_change_password})
        ),
    )

    list_resp = client.get("/api/v1/users")
    assert list_resp.status_code == 200
    assert list_resp.json()[0]["username"] == "operator1"

    create_resp = client.post(
        "/api/v1/users",
        json={"username": "operator2", "password": "operator123", "role": "operator"},
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["username"] == "operator2"

    patch_resp = client.patch("/api/v1/users/operator2", json={"enabled": False})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["enabled"] is False

    reset_resp = client.post(
        "/api/v1/users/operator2/reset-password",
        json={"new_password": "new-operator123", "must_change_password": True},
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["must_change_password"] is True

    app.dependency_overrides.clear()


def _apply_updates(user, updates: dict):
    for key, value in updates.items():
        setattr(user, key, value)
    return user
