from app.config import settings


def classify_task_error(exc: Exception) -> str:
    name = exc.__class__.__name__.lower()
    if "timeout" in name:
        return "timeout"
    if "validation" in name:
        return "validation_error"
    if "http" in name or "connect" in name:
        return "llm_http_error"
    return "unknown_error"


def should_retry_task(retry_count: int, max_retries: int, failure_reason: str) -> bool:
    return (
        failure_reason in settings.retryable_task_error_types_set
        and retry_count < max_retries
    )
