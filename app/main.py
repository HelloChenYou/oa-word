from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, validate_runtime_settings
from app.logging_utils import configure_logging
from app.routers.auth import router as auth_router
from app.routers.knowledge import router as knowledge_router
from app.routers.ops import router as ops_router
from app.routers.rules import router as rules_router
from app.routers.tasks import router as tasks_router
from app.routers.templates import router as templates_router
from app.routers.users import router as users_router
from app.security import bootstrap_admin_user, require_admin, require_authenticated
from app.services.rule_repository import seed_builtin_rules

configure_logging()
validate_runtime_settings()
seed_builtin_rules()
bootstrap_admin_user()

app = FastAPI(title="Proofread MVP", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.middleware("http")
async def access_log_middleware(request, call_next):
    from app.logging_utils import elapsed_ms, get_logger, log_exception, log_info, now_perf

    request_logger = get_logger("app.access")
    started_at = now_perf()
    client_host = request.client.host if request.client else "unknown"
    try:
        response = await call_next(request)
    except Exception:
        log_exception(
            request_logger,
            "http_request_failed",
            method=request.method,
            path=request.url.path,
            client_ip=client_host,
            duration_ms=elapsed_ms(started_at),
        )
        raise

    log_info(
        request_logger,
        "http_request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        client_ip=client_host,
        duration_ms=elapsed_ms(started_at),
    )
    return response

app.include_router(auth_router)
app.include_router(users_router, dependencies=[Depends(require_admin)])
app.include_router(rules_router, dependencies=[Depends(require_authenticated)])
app.include_router(tasks_router, dependencies=[Depends(require_authenticated)])
app.include_router(templates_router, dependencies=[Depends(require_admin)])
app.include_router(knowledge_router, dependencies=[Depends(require_admin)])
app.include_router(ops_router, dependencies=[Depends(require_admin)])


@app.get("/healthz")
def healthz():
    return {"ok": True}
