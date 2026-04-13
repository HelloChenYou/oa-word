import io
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.routers import knowledge as knowledge_module
from app.routers.knowledge import router as knowledge_router
from app.security import require_admin


def build_client():
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

    app = FastAPI()
    app.include_router(knowledge_router, dependencies=[Depends(require_admin)])
    app.dependency_overrides[knowledge_module.get_db] = override_get_db
    return TestClient(app)


def test_upload_and_list_knowledge(monkeypatch):
    monkeypatch.setattr("app.config.settings.admin_api_token", "secret-token")
    client = build_client()

    with TemporaryDirectory() as temp_dir:
        monkeypatch.setattr(knowledge_module, "KNOWLEDGE_STORAGE_DIR", Path(temp_dir))
        upload_resp = client.post(
            "/api/v1/knowledge",
            headers={"X-Admin-Token": "secret-token"},
            data={"name": "公文规范", "doc_type": "policy"},
            files={"file": ("policy.md", io.BytesIO("手机号应脱敏。".encode("utf-8")), "text/markdown")},
        )

    assert upload_resp.status_code == 200
    body = upload_resp.json()
    assert body["name"] == "公文规范"
    assert body["chunk_count"] == 1

    list_resp = client.get("/api/v1/knowledge", headers={"X-Admin-Token": "secret-token"})
    assert list_resp.status_code == 200
    assert list_resp.json()[0]["name"] == "公文规范"
    assert list_resp.json()[0]["chunk_count"] == 1


def test_update_toggle_delete_knowledge(monkeypatch):
    monkeypatch.setattr("app.config.settings.admin_api_token", "secret-token")
    client = build_client()

    with TemporaryDirectory() as temp_dir:
        monkeypatch.setattr(knowledge_module, "KNOWLEDGE_STORAGE_DIR", Path(temp_dir))
        upload_resp = client.post(
            "/api/v1/knowledge",
            headers={"X-Admin-Token": "secret-token"},
            data={"name": "policy", "doc_type": "style"},
            files={"file": ("policy.md", io.BytesIO("old text".encode("utf-8")), "text/markdown")},
        )

    document_id = upload_resp.json()["document_id"]
    update_resp = client.patch(
        f"/api/v1/knowledge/{document_id}",
        headers={"X-Admin-Token": "secret-token"},
        json={"name": "updated policy", "enabled": False, "raw_text": "new searchable text"},
    )

    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "updated policy"
    assert update_resp.json()["enabled"] is False
    assert update_resp.json()["chunk_count"] == 1

    search_resp = client.get(
        "/api/v1/knowledge?keyword=searchable&enabled=false",
        headers={"X-Admin-Token": "secret-token"},
    )
    assert search_resp.status_code == 200
    assert search_resp.json()[0]["document_id"] == document_id

    delete_resp = client.delete(f"/api/v1/knowledge/{document_id}", headers={"X-Admin-Token": "secret-token"})
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"ok": True}

    list_resp = client.get("/api/v1/knowledge", headers={"X-Admin-Token": "secret-token"})
    assert list_resp.json() == []
