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
from app.routers.ops import router as ops_router
from app.routers.rules import router as rules_router
from app.routers import tasks as tasks_module
from app.routers.tasks import router as tasks_router
from app.routers import templates as templates_module
from app.routers.templates import router as templates_router
from app.security import require_admin


def _build_test_client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    test_app = FastAPI()
    test_app.include_router(rules_router, dependencies=[Depends(require_admin)])
    test_app.include_router(tasks_router, dependencies=[Depends(require_admin)])
    test_app.include_router(templates_router, dependencies=[Depends(require_admin)])
    test_app.include_router(ops_router, dependencies=[Depends(require_admin)])

    test_app.dependency_overrides[tasks_module.get_db] = override_get_db
    test_app.dependency_overrides[templates_module.get_db] = override_get_db
    monkeypatch.setattr(tasks_module, "ensure_submit_rate_limit", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks_module, "ensure_active_tasks_within_limit", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks_module, "enqueue_proofread_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(ops_module, "SessionLocal", TestingSessionLocal)

    client = TestClient(test_app)
    return client, TestingSessionLocal


def test_task_endpoints_work_with_admin_token(monkeypatch):
    monkeypatch.setattr("app.config.settings.admin_api_token", "secret-token")
    client, session_factory = _build_test_client(monkeypatch)

    create_resp = client.post(
        "/api/v1/proofread/tasks",
        headers={"X-Admin-Token": "secret-token"},
        json={"text": "测试文本", "mode": "review", "scene": "general", "owner_id": "demo_user"},
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["task_id"]

    status_resp = client.get(
        f"/api/v1/proofread/tasks/{task_id}",
        headers={"X-Admin-Token": "secret-token"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "queued"
    assert status_resp.json()["retry_count"] == 0

    retry_resp = client.post(
        f"/api/v1/proofread/tasks/{task_id}/retry",
        headers={"X-Admin-Token": "secret-token"},
    )
    assert retry_resp.status_code == 409

    db = session_factory()
    try:
        task = db.get(models.ProofreadTask, task_id)
        task.status = "failed"
        task.failure_reason = "timeout"
        db.commit()
    finally:
        db.close()

    retry_resp = client.post(
        f"/api/v1/proofread/tasks/{task_id}/retry",
        headers={"X-Admin-Token": "secret-token"},
    )
    assert retry_resp.status_code == 200
    assert retry_resp.json()["status"] == "queued"


def test_template_endpoints_work(monkeypatch):
    monkeypatch.setattr("app.config.settings.admin_api_token", "secret-token")
    client, _ = _build_test_client(monkeypatch)

    with TemporaryDirectory() as temp_dir:
        monkeypatch.setattr(templates_module, "TEMPLATE_STORAGE_DIR", Path(temp_dir))
        monkeypatch.setattr(
            templates_module,
            "parse_template_file",
            lambda path, suffix: ("模板正文", '{"required_sections":["一、目标"]}'),
        )

        upload_resp = client.post(
            "/api/v1/templates",
            headers={"X-Admin-Token": "secret-token"},
            data={"name": "通知模板", "doc_type": "general"},
            files={"file": ("notice.md", io.BytesIO(b"# test"), "text/markdown")},
        )
        assert upload_resp.status_code == 200
        template_id = upload_resp.json()["template_id"]

        list_resp = client.get("/api/v1/templates", headers={"X-Admin-Token": "secret-token"})
        assert list_resp.status_code == 200
        assert list_resp.json()[0]["template_id"] == template_id

        detail_resp = client.get(
            f"/api/v1/templates/{template_id}",
            headers={"X-Admin-Token": "secret-token"},
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["parsed"]["required_sections"] == ["一、目标"]


def test_ops_metrics_endpoint_returns_counts(monkeypatch):
    monkeypatch.setattr("app.config.settings.admin_api_token", "secret-token")
    client, session_factory = _build_test_client(monkeypatch)

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

    response = client.get("/api/v1/ops/metrics", headers={"X-Admin-Token": "secret-token"})
    assert response.status_code == 200
    body = response.json()
    assert body["queue"]["queued_jobs"] == 3
    assert body["tasks"]["total"] == 2
    assert body["tasks"]["by_status"]["queued"] == 1
    assert body["tasks"]["by_status"]["failed"] == 1
