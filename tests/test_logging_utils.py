import json
import logging

from app.logging_utils import JsonFormatter


def test_json_formatter_includes_event_and_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.event = "sample_event"
    record.fields = {"task_id": "t_123", "status": "ok"}

    payload = json.loads(formatter.format(record))
    assert payload["logger"] == "test.logger"
    assert payload["event"] == "sample_event"
    assert payload["task_id"] == "t_123"
    assert payload["status"] == "ok"
