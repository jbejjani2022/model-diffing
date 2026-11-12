"""Direct provider backends (OpenAI, Anthropic, Google) for the reproduction.

NOT PART OF UPSTREAM. The paper's code sends every LLM call through OpenRouter.
We have no OpenRouter key, so `ModelWrapper` delegates here for model names that
start with `openai/`, `anthropic/` or `google/` (see DEVIATIONS.md, D1).

Added behaviour relative to upstream's bare httpx call:
- disk cache keyed on the full request, so interrupted runs resume for free
  (set MD_CACHE_SALT to force fresh samples, e.g. for judge self-consistency);
- retries with exponential backoff on 429 / 5xx / network errors;
- a token-usage log (.api_cache/usage.jsonl) for cost accounting.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import time
from pathlib import Path

import httpx

# OpenRouter-style name -> (provider, pinned snapshot id).
MODEL_ALIASES = {
    "openai/gpt-5.4-mini": ("openai", "gpt-5.4-mini-2026-03-17"),
    "openai/gpt-5.2": ("openai", "gpt-5.2-2025-12-11"),
    "anthropic/claude-opus-4.5": ("anthropic", "claude-opus-4-5-20251101"),
    "anthropic/claude-haiku-4.5": ("anthropic", "claude-haiku-4-5-20251001"),
}
PROVIDERS = ("openai", "anthropic", "google")
KEY_ENV = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "google": "GOOGLE_API_KEY"}

CACHE_DIR = Path(os.environ.get("MD_API_CACHE", ".api_cache"))
MAX_RETRIES = int(os.environ.get("MD_MAX_RETRIES", "8"))  # raise for models with tight tokens-per-minute limits
RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}

_anthropic_client = None


def handles(model_name: str) -> bool:
    return model_name in MODEL_ALIASES or model_name.split("/", 1)[0] in PROVIDERS


def resolve(model_name: str) -> tuple[str, str]:
    if model_name in MODEL_ALIASES:
        return MODEL_ALIASES[model_name]
    provider, model_id = model_name.split("/", 1)
    return provider, model_id


def _load_dotenv_once() -> None:
    if getattr(_load_dotenv_once, "done", False):
        return
    from dotenv import load_dotenv

    load_dotenv()
    _load_dotenv_once.done = True


def _api_key(provider: str) -> str:
    _load_dotenv_once()
    key = os.environ.get(KEY_ENV[provider])
    if not key:
        raise ValueError(f"{KEY_ENV[provider]} is not set (needed for provider {provider!r})")
    return key


def _cache_path(request: dict) -> Path:
    blob = json.dumps(request, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return CACHE_DIR / "responses" / digest[:2] / f"{digest}.json"


def _log_usage(provider: str, model_id: str, usage: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "t": time.time(),
        "provider": provider,
        "model": model_id,
        "tag": os.environ.get("MD_RUN_TAG", ""),
        **usage,
    }
    with open(CACHE_DIR / "usage.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


async def _post_with_retries(client: httpx.AsyncClient, url: str, headers: dict, payload: dict) -> dict | None:
    """POST with backoff. Returns parsed JSON, or None for a non-retryable 4xx (logged)."""
    for attempt in range(MAX_RETRIES):
        try:
            res = await client.post(url, headers=headers, json=payload, timeout=httpx.Timeout(300.0, connect=20.0))
        except (httpx.TransportError, httpx.TimeoutException) as e:
            err = repr(e)
        else:
            if res.status_code == 200:
                return res.json()
            if res.status_code not in RETRY_STATUS:
                print(f"[direct_api] non-retryable {res.status_code} from {url}: {res.text[:300]}")
                return None
            err = f"{res.status_code} {res.text[:200]}"
        delay = min(2.0**attempt, 60.0) + random.uniform(0, 1)
        if attempt >= 3:
            print(f"[direct_api] retry {attempt + 1}/{MAX_RETRIES} in {delay:.0f}s: {err}")
        await asyncio.sleep(delay)
    raise RuntimeError(f"[direct_api] gave up after {MAX_RETRIES} retries: {err}")


async def _openai_compatible(
    provider: str, model_id: str, client: httpx.AsyncClient, conversation, max_new_tokens, enable_thinking, seed, extra
) -> tuple[str, dict]:
    if provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        payload = {"model": model_id, "messages": conversation, "max_completion_tokens": max_new_tokens}
        # Upstream runs Gemini 2.5 Flash with thinking off; the analogue here is reasoning_effort="none".
        if not enable_thinking:
            payload["reasoning_effort"] = "none"
        if seed is not None:
            payload["seed"] = seed
    else:  # google, via its OpenAI-compatible endpoint
        url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        payload = {"model": model_id, "messages": conversation, "max_tokens": max_new_tokens}
        if not enable_thinking:
            payload["reasoning_effort"] = "none"
    payload.update(extra)
    headers = {"Authorization": f"Bearer {_api_key(provider)}", "Content-Type": "application/json"}

    data = await _post_with_retries(client, url, headers, payload)
    if data is None:
        return "", {}
    choice = data["choices"][0]
    text = choice["message"].get("content") or ""
    u = data.get("usage", {})
    usage = {
        "input": u.get("prompt_tokens", 0),
        "cached_input": (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
        "output": u.get("completion_tokens", 0),
        "finish": choice.get("finish_reason"),
    }
    return text, usage


async def _anthropic(model_id: str, conversation, max_new_tokens, extra) -> tuple[str, dict]:
    import anthropic

    # One client per event loop: upstream calls asyncio.run() per batch, and a client outlives its loop badly.
    global _anthropic_client
    loop = asyncio.get_running_loop()
    if _anthropic_client is None or _anthropic_client[0] is not loop:
        _anthropic_client = (loop, anthropic.AsyncAnthropic(api_key=_api_key("anthropic"), max_retries=MAX_RETRIES))
    client = _anthropic_client[1]

    system = "\n".join(m["content"] for m in conversation if m["role"] == "system")
    messages = [m for m in conversation if m["role"] != "system"]
    kwargs = {"model": model_id, "max_tokens": max_new_tokens, "messages": messages, **extra}
    if system:
        kwargs["system"] = system
    try:
        response = await client.messages.create(**kwargs)
    except anthropic.BadRequestError as e:
        print(f"[direct_api] anthropic bad request: {e.message}")
        return "", {}
    text = "".join(block.text for block in response.content if block.type == "text")
    usage = {
        "input": response.usage.input_tokens,
        "cached_input": response.usage.cache_read_input_tokens or 0,
        "output": response.usage.output_tokens,
        "finish": response.stop_reason,
    }
    return text, usage


async def request(
    model_name: str,
    conversation: list[dict],
    client: httpx.AsyncClient,
    max_new_tokens: int,
    enable_thinking: bool,
    seed: int | None,
    **kwargs,
) -> str:
    provider, model_id = resolve(model_name)
    extra = {
        k: kwargs[k]
        for k in ("temperature", "top_p", "presence_penalty", "frequency_penalty")
        if kwargs.get(k) is not None
    }
    cache_key = {
        "provider": provider,
        "model": model_id,
        "messages": conversation,
        "max_new_tokens": max_new_tokens,
        "enable_thinking": enable_thinking,
        "seed": seed,
        "extra": extra,
        "salt": os.environ.get("MD_CACHE_SALT", ""),
    }
    path = _cache_path(cache_key)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["text"]

    if provider == "anthropic":
        text, usage = await _anthropic(model_id, conversation, max_new_tokens, extra)
    else:
        text, usage = await _openai_compatible(
            provider, model_id, client, conversation, max_new_tokens, enable_thinking, seed, extra
        )

    if usage:  # only cache real responses, never hard failures
        _log_usage(provider, model_id, usage)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps({"text": text, "usage": usage}), encoding="utf-8")
        tmp.replace(path)
    return text
