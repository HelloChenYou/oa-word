from fastapi import FastAPI

from app.db import Base, engine
from app.logging_utils import configure_logging
from app.routers.rules import router as rules_router
from app.routers.tasks import router as tasks_router
from app.routers.templates import router as templates_router
from app.services.rule_repository import seed_builtin_rules

configure_logging()
Base.metadata.create_all(bind=engine)
seed_builtin_rules()

app = FastAPI(title="Proofread MVP", version="0.1.0")
app.include_router(rules_router)
app.include_router(tasks_router)
app.include_router(templates_router)


@app.get("/healthz")
def healthz():
    return {"ok": True}
