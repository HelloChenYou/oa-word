from app.services.task_recovery import classify_task_error, should_retry_task


def test_classify_task_error():
    assert classify_task_error(TimeoutError("boom")) == "timeout"
    assert classify_task_error(ConnectionError("boom")) == "llm_http_error"

    class ValidationProblem(Exception):
        pass

    assert classify_task_error(ValidationProblem("bad")) == "validation_error"


def test_should_retry_respects_reason_and_budget():
    assert should_retry_task(0, 1, "timeout") is True
    assert should_retry_task(0, 1, "validation_error") is False
    assert should_retry_task(1, 1, "timeout") is False
