import io
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.db import Base
from app.routers import ops as ops_module
from app.routers import tasks as tasks_module
from app.routers import templates as templates_module
from app.routers.auth import router as auth_router
from app.routers.ops import router as ops_router
from app.routers.rules import router as rules_router
from app.routers.tasks import router as tasks_router
from app.routers.templates import router as templates_router
import app.security as security_module
from app.security import hash_password, require_admin, require_authenticated


def _build_test_client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    test_app = FastAPI()
    test_app.include_router(auth_router)
    test_app.include_router(rules_router, dependencies=[Depends(require_admin)])
    test_app.include_router(tasks_router, dependencies=[Depends(require_authenticated)])
    test_app.include_router(templates_router, dependencies=[Depends(require_admin)])
    test_app.include_router(ops_router, dependencies=[Depends(require_admin)])

    test_app.dependency_overrides[tasks_module.get_db] = override_get_db
    test_app.dependency_overrides[templates_module.get_db] = override_get_db

    monkeypatch.setattr(tasks_module, "ensure_submit_rate_limit", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks_module, "ensure_active_tasks_within_limit", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks_module, "enqueue_proofread_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(ops_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(security_module, "SessionLocal", testing_session_local)

    db = testing_session_local()
    try:
        db.add(
            models.UserAccount(
                username="admin",
                password_hash=hash_password("admin123456"),
                role="admin",
                enabled=True,
            )
        )
        db.add(
            models.UserAccount(
                username="operator1",
                password_hash=hash_password("operator123"),
                role="operator",
                enabled=True,
            )
        )
        db.commit()
    finally:
        db.close()

    client = TestClient(test_app)
    return client, testing_session_local


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_auth_login_and_me(monkeypatch):
    monkeypatch.setattr("app.config.settings.auth_secret_key", "unit-test-secret")
    client, _ = _build_test_client(monkeypatch)

    token = _login(client, "admin", "admin123456")
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "admin"
    assert me_resp.json()["role"] == "admin"
    assert me_resp.json()["must_change_password"] is False


def test_bootstrap_password_change_flow(monkeypatch):
    monkeypatch.setattr("app.config.settings.auth_secret_key", "unit-test-secret")
    client, session_factory = _build_test_client(monkeypatch)

    db = session_factory()
    try:
        admin = db.query(models.UserAccount).filter(models.UserAccount.username == "admin").one()
        admin.must_change_password = True
        db.commit()
    finally:
        db.close()

    token = _login(client, "admin", "admin123456")
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.json()["must_change_password"] is True

    change_resp = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "admin123456", "new_password": "new-admin-pass"},
    )
    assert change_resp.status_code == 200
    body = change_resp.json()
    assert body["user"]["must_change_password"] is False
    assert body["access_token"]

    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["must_change_password"] is False


def test_me_reads_latest_user_state_from_database(monkeypatch):
    monkeypatch.setattr("app.config.settings.auth_secret_key", "unit-test-secret")
    client, session_factory = _build_test_client(monkeypatch)

    db = session_factory()
    try:
        admin = db.query(models.UserAccount).filter(models.UserAccount.username == "admin").one()
        admin.must_change_password = True
        db.commit()
    finally:
        db.close()

    token = _login(client, "admin", "admin123456")

    db = session_factory()
    try:
        admin = db.query(models.UserAccount).filter(models.UserAccount.username == "admin").one()
        admin.must_change_password = False
        db.commit()
    finally:
        db.close()

    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["must_change_password"] is False


def test_task_endpoints_work_for_authenticated_user(monkeypatch):
    monkeypatch.setattr("app.config.settings.auth_secret_key", "unit-test-secret")
    client, session_factory = _build_test_client(monkeypatch)
    token = _login(client, "operator1", "operator123")
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = client.post(
        "/api/v1/proofread/tasks",
        headers=headers,
        json={"text": "测试文本", "mode": "review", "scene": "general", "owner_id": "someone-else"},
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["task_id"]

    status_resp = client.get(f"/api/v1/proofread/tasks/{task_id}", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "queued"

    db = session_factory()
    try:
        task = db.get(models.ProofreadTask, task_id)
        assert task.owner_id == "operator1"
        task.status = "failed"
        task.failure_reason = "timeout"
        db.commit()
    finally:
        db.close()

    retry_resp = client.post(f"/api/v1/proofread/tasks/{task_id}/retry", headers=headers)
    assert retry_resp.status_code == 200
    assert retry_resp.json()["status"] == "queued"


def test_template_endpoints_work_for_admin(monkeypatch):
    monkeypatch.setattr("app.config.settings.auth_secret_key", "unit-test-secret")
    client, _ = _build_test_client(monkeypatch)
    token = _login(client, "admin", "admin123456")
    headers = {"Authorization": f"Bearer {token}"}

    with TemporaryDirectory() as temp_dir:
        monkeypatch.setattr(templates_module, "TEMPLATE_STORAGE_DIR", Path(temp_dir))
        monkeypatch.setattr(
            templates_module,
            "parse_template_file",
            lambda path, suffix: ("模板正文", '{"required_sections":["一、目标"]}'),
        )

        upload_resp = client.post(
            "/api/v1/templates",
            headers=headers,
            data={"name": "通知模板", "doc_type": "general"},
            files={"file": ("notice.md", io.BytesIO(b"# test"), "text/markdown")},
        )
        assert upload_resp.status_code == 200
        template_id = upload_resp.json()["template_id"]

        list_resp = client.get("/api/v1/templates", headers=headers)
        assert list_resp.status_code == 200
        assert list_resp.json()[0]["template_id"] == template_id

        detail_resp = client.get(f"/api/v1/templates/{template_id}", headers=headers)
        assert detail_resp.status_code == 200
        assert detail_resp.json()["parsed"]["required_sections"] == ["一、目标"]


def test_ops_metrics_endpoint_returns_counts(monkeypatch):
    monkeypatch.setattr("app.config.settings.auth_secret_key", "unit-test-secret")
    client, session_factory = _build_test_client(monkeypatch)
    token = _login(client, "admin", "admin123456")
    headers = {"Authorization": f"Bearer {token}"}

    class DummyQueue:
        name = "proofread"

        def __len__(self):
            return 3

    class DummyRedis:
        def ping(self):
            return True

    monkeypatch.setattr(ops_module, "get_queue", lambda: DummyQueue())
    monkeypatch.setattr(ops_module, "get_redis_conn", lambda: DummyRedis())

    db = session_factory()
    try:
        db.add(models.ProofreadTask(id="t1", mode="review", scene="general", status="queued", source_text="a"))
        db.add(models.ProofreadTask(id="t2", mode="review", scene="general", status="failed", source_text="b"))
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/ops/metrics", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["queue"]["queued_jobs"] == 3
    assert body["tasks"]["total"] == 2
    assert body["tasks"]["by_status"]["queued"] == 1
    assert body["tasks"]["by_status"]["failed"] == 1
