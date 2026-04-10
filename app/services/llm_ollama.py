import json
from pathlib import Path

import httpx
from pydantic import ValidationError

from app.config import settings
from app.domain.issues import LlmIssuesResp, StoredIssue
from app.logging_utils import get_logger
from app.services.issue_converter import validate_llm_response


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
SYSTEM_PROMPT_PATH = PROMPT_DIR / "system_prompt.txt"
USER_PROMPT_TEMPLATE_PATH = PROMPT_DIR / "user_prompt_template.txt"

LLM_RESPONSE_SCHEMA = LlmIssuesResp.model_json_schema()
logger = get_logger(__name__)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


SYSTEM_PROMPT = load_text(SYSTEM_PROMPT_PATH)
USER_PROMPT_TEMPLATE = load_text(USER_PROMPT_TEMPLATE_PATH)


def _truncate_text(value: str, max_len: int = 1200) -> str:
    if len(value) <= max_len:
        return value
    return f"{value[:max_len]}...(truncated, total={len(value)})"


def build_user_prompt(chunk: str, mode: str, scene: str, rule_pack: str = "{}") -> str:
    return USER_PROMPT_TEMPLATE.format(
        mode=mode,
        scene=scene,
        rule_pack=rule_pack,
        chunk_text=chunk,
    )


def _build_repair_user_prompt(
    chunk: str,
    mode: str,
    scene: str,
    rule_pack: str,
    invalid_output: str,
    validation_error: str,
) -> str:
    base_prompt = build_user_prompt(chunk=chunk, mode=mode, scene=scene, rule_pack=rule_pack)
    return (
        f"{base_prompt}\n\n"
        "[Previous invalid output]\n"
        f"{invalid_output}\n\n"
        "[Validation error]\n"
        f"{validation_error}\n\n"
        "Repair the output so it matches the required schema exactly. "
        "Do not add explanations. Return only the corrected JSON object."
    )


def _build_payload(messages: list[dict]) -> dict:
    if settings.use_api_key_llm:
        return {
            "model": settings.effective_llm_model,
            "messages": messages,
            "temperature": 0.1,
            "top_p": 0.8,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "proofread_issues_response",
                    "strict": True,
                    "schema": LLM_RESPONSE_SCHEMA,
                },
            },
        }
    return {
        "model": settings.effective_llm_model,
        "stream": False,
        "format": "json",
        "messages": messages,
        "options": {
            "temperature": 0.1,
            "top_p": 0.8,
            "repeat_penalty": 1.1,
        },
    }


def _build_request_url() -> str:
    if settings.use_api_key_llm:
        return f"{settings.effective_llm_base_url}/chat/completions"
    return f"{settings.effective_llm_base_url}/api/chat"


def _build_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.use_api_key_llm and settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    return headers


def _extract_response_content(data: dict) -> str:
    if settings.use_api_key_llm:
        choices = data.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")
    return data.get("message", {}).get("content", "")


async def _call_llm_chat(messages: list[dict], attempt: int) -> str | None:
    payload = _build_payload(messages)
    headers = _build_headers()
    url = _build_request_url()
    provider = "api_key" if settings.use_api_key_llm else "ollama"

    debug_payload = {
        "provider": provider,
        "model": payload["model"],
        "messages": [
            {"role": payload["messages"][0]["role"], "content": _truncate_text(payload["messages"][0]["content"])},
            {"role": payload["messages"][1]["role"], "content": _truncate_text(payload["messages"][1]["content"])},
        ],
    }
    if settings.use_api_key_llm:
        debug_payload["response_format"] = payload["response_format"]
    else:
        debug_payload["format"] = payload["format"]

    print("--------------------------------", flush=True)
    logger.info(
        "[LLM_REQUEST] attempt=%s provider=%s url=%s payload=%s",
        attempt,
        provider,
        url,
        json.dumps(debug_payload, ensure_ascii=False),
    )

    try:
        async with httpx.AsyncClient(timeout=settings.default_timeout_sec) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info(
                "[LLM_RESPONSE] attempt=%s status=%s body=%s",
                attempt,
                response.status_code,
                _truncate_text(response.text, max_len=2000),
            )
            raw_content = _extract_response_content(data)
            logger.info(
                "[LLM_RESPONSE_CONTENT] attempt=%s content=%s",
                attempt,
                _truncate_text(raw_content, max_len=2000),
            )
            return raw_content
    except httpx.TimeoutException as exc:
        logger.warning(
            "[LLM_TIMEOUT] attempt=%s exc=%r timeout=%ss url=%s",
            attempt,
            exc,
            settings.default_timeout_sec,
            url,
        )
        logger.info("[LLM_REQUEST_END] status=failed(timeout)")
        return None
    except httpx.ConnectError as exc:
        logger.warning("[LLM_CONNECT_ERROR] attempt=%s exc=%r url=%s", attempt, exc, url)
        logger.info("[LLM_REQUEST_END] status=failed(connect_error)")
        return None
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text if exc.response is not None else ""
        logger.warning(
            "[LLM_HTTP_ERROR] attempt=%s status=%s exc=%r body=%s",
            attempt,
            getattr(exc.response, "status_code", "unknown"),
            exc,
            _truncate_text(response_text, max_len=2000),
        )
        logger.info("[LLM_REQUEST_END] status=failed(http_error)")
        return None
    except Exception as exc:
        logger.exception("[LLM_UNKNOWN_ERROR] attempt=%s url=%s", attempt, url)
        logger.info("[LLM_REQUEST_END] status=failed(unknown_error)")
        return None


def _validate_response(content: str) -> list[StoredIssue]:
    return validate_llm_response(content)


async def check_with_llm(chunk: str, mode: str, scene: str, rule_pack: str = "{}") -> list[StoredIssue]:
    messages_first = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(chunk, mode, scene, rule_pack)},
    ]
    content = await _call_llm_chat(messages=messages_first, attempt=1)
    if content is None:
        return []

    try:
        issues = _validate_response(content)
        logger.info("[LLM_SCHEMA_VALID] attempt=1 count=%s", len(issues))
        logger.info("[LLM_REQUEST_END] status=ok")
        return issues
    except ValidationError as exc:
        validation_error = exc.json()
        logger.warning(
            "[LLM_SCHEMA_ERROR] attempt=1 error=%s content=%s",
            _truncate_text(validation_error, max_len=2000),
            _truncate_text(content, max_len=2000),
        )

    retry_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _build_repair_user_prompt(
                chunk=chunk,
                mode=mode,
                scene=scene,
                rule_pack=rule_pack,
                invalid_output=content,
                validation_error=validation_error,
            ),
        },
    ]
    retry_content = await _call_llm_chat(messages=retry_messages, attempt=2)
    if retry_content is None:
        logger.info("[LLM_REQUEST_END] status=failed(retry_request_error)")
        return []

    try:
        retry_issues = _validate_response(retry_content)
        logger.info("[LLM_SCHEMA_VALID] attempt=2 count=%s", len(retry_issues))
        logger.info("[LLM_REQUEST_END] status=ok_after_retry")
        return retry_issues
    except ValidationError as exc:
        logger.warning(
            "[LLM_SCHEMA_ERROR] attempt=2 error=%s content=%s",
            _truncate_text(exc.json(), max_len=2000),
            _truncate_text(retry_content, max_len=2000),
        )

    logger.info("[LLM_REQUEST_END] status=failed(schema_error_after_retry)")
    return []
