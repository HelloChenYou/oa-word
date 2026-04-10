from fastapi import FastAPI

from app.db import Base, engine
from app.routers.tasks import router as tasks_router
from app.routers.templates import router as templates_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Proofread MVP", version="0.1.0")
app.include_router(tasks_router)
app.include_router(templates_router)


@app.get("/healthz")
def healthz():
    return {"ok": True}
