import json
from pathlib import Path

import httpx

from app.config import settings


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
SYSTEM_PROMPT_PATH = PROMPT_DIR / "system_prompt.txt"
USER_PROMPT_TEMPLATE_PATH = PROMPT_DIR / "user_prompt_template.txt"


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


async def check_with_llm(chunk: str, mode: str, scene: str, rule_pack: str = "{}") -> list[dict]:
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(chunk, mode, scene, rule_pack)},
        ],
        "options": {
            "temperature": 0.1,
            "top_p": 0.8,
            "repeat_penalty": 1.1,
        },
    }

    debug_payload = {
        "model": payload["model"],
        "stream": payload["stream"],
        "format": payload["format"],
        "options": payload["options"],
        "messages": [
            {"role": "system", "content": _truncate_text(payload["messages"][0]["content"])},
            {"role": "user", "content": _truncate_text(payload["messages"][1]["content"])},
        ],
    }
    url = f"{settings.ollama_base_url}/api/chat"
    print("--------------------------------", flush=True)
    print(f"[LLM_REQUEST] url={url} payload={json.dumps(debug_payload, ensure_ascii=False)}", flush=True)

    data = {}
    try:
        async with httpx.AsyncClient(timeout=settings.default_timeout_sec) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            print(
                f"[LLM_RESPONSE] status={response.status_code} body={_truncate_text(response.text, max_len=2000)}",
                flush=True,
            )
            raw_content = data.get("message", {}).get("content", "")
            print(f"[LLM_RESPONSE_CONTENT] {_truncate_text(raw_content, max_len=2000)}", flush=True)
    except httpx.TimeoutException as exc:
        print(f"[LLM_TIMEOUT] exc={repr(exc)} timeout={settings.default_timeout_sec}s url={url}", flush=True)
        print("[LLM_REQUEST_END] status=failed(timeout)", flush=True)
        return []
    except httpx.ConnectError as exc:
        print(f"[LLM_CONNECT_ERROR] exc={repr(exc)} url={url}", flush=True)
        print("[LLM_REQUEST_END] status=failed(connect_error)", flush=True)
        return []
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text if exc.response is not None else ""
        print(
            f"[LLM_HTTP_ERROR] status={getattr(exc.response, 'status_code', 'unknown')} "
            f"exc={repr(exc)} body={_truncate_text(response_text, max_len=2000)}",
            flush=True,
        )
        print("[LLM_REQUEST_END] status=failed(http_error)", flush=True)
        return []
    except Exception as exc:
        print(f"[LLM_UNKNOWN_ERROR] exc={repr(exc)} url={url}", flush=True)
        print("[LLM_REQUEST_END] status=failed(unknown_error)", flush=True)
        return []

    content = data.get("message", {}).get("content", "{}")
    print("--------------------------------", flush=True)
    print(content, flush=True)
    try:
        parsed = json.loads(content)
        issues = parsed.get("issues", [])
        if isinstance(issues, list):
            print(f"[LLM_PARSED_ISSUES] count={len(issues)}", flush=True)
            print("[LLM_REQUEST_END] status=ok", flush=True)
            return issues
        print("[LLM_PARSED_ISSUES] issues is not list, fallback to []", flush=True)
        print("[LLM_REQUEST_END] status=ok_with_fallback", flush=True)
        return []
    except Exception as exc:
        print(f"[LLM_PARSE_ERROR] exc={repr(exc)} content={_truncate_text(content, max_len=2000)}", flush=True)
        print("[LLM_REQUEST_END] status=failed(parse_error)", flush=True)
        return []
