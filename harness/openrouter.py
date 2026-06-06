"""Thin OpenRouter client — stdlib only, mirrors the wanderbench driver shape.

Tracks served providers (so we know which backend actually answered) and
exact $ cost (via OpenRouter's `usage.include = true`). Auto-retries on
transient errors with exponential backoff.

Supports native function-calling: pass `tools` (OpenAI tool schema list) and
the returned dict carries any `tool_calls` the model emitted, parsed
structurally from the provider's native format (OpenRouter normalizes every
backend — Gemma's special tokens, Gemini's format, etc. — into the same
OpenAI `tool_calls` shape). This is what frontier agentic benchmarks
(SWE-agent FunctionCallingParser, mini-swe-agent) use.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

OR_URL = "https://openrouter.ai/api/v1/chat/completions"

# Reasonable defaults for an OpenRouter benchmark client. Override per call.
_DEFAULT_MAX_TOKENS = 8192  # room for reasoning + a large multi-row JSON submission
_DEFAULT_TEMPERATURE = 0.6
_TIMEOUT_SEC = 180


class ToolsUnsupported(Exception):
    """Raised when a model/provider 400s specifically because of the `tools`
    parameter (no native function-calling support). The caller can retry in
    text-protocol mode."""


def _looks_tool_related(body: str) -> bool:
    b = (body or "").lower()
    return ("tool" in b or "function" in b) and (
        "support" in b or "not supported" in b or "unsupported" in b
        or "invalid" in b or "does not" in b or "no endpoints" in b
    )


class OpenRouterClient:
    """Stateful client: accumulates cost + provider set across calls."""

    def __init__(self, api_key: str, referer: str = "https://github.com/typhamswann/saguaro-bench",
                 title: str = "saguaro-bench"):
        self.api_key = api_key
        self.referer = referer
        self.title = title
        self.cost_usd = 0.0
        self.calls = 0
        self.served_providers: set[str] = set()
        self.last_usage: dict[str, Any] | None = None

    def chat(
        self,
        model: str,
        messages: list[dict],
        *,
        provider: dict | None = None,
        tools: list[dict] | None = None,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        temperature: float = _DEFAULT_TEMPERATURE,
        retries: int = 4,
    ) -> dict:
        """Call /chat/completions. Returns a dict:

            {"content": str, "tool_calls": [{"id","name","arguments"}], "finish_reason": str}

        `arguments` is the raw JSON string the model emitted for that call.
        Accumulates `self.cost_usd` and tracks served providers. Raises
        ToolsUnsupported if `tools` was passed and the provider rejected it.
        """
        payload: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            # Ask OpenRouter for the exact $ amount billed for this call.
            "usage": {"include": True},
        }
        if provider:
            payload["provider"] = provider
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(OR_URL, data=body, headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.referer,
            "X-Title": self.title,
        })

        last_err: Exception | None = None
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as r:
                    data = json.loads(r.read())
                # Cost + provider tracking
                if data.get("provider"):
                    self.served_providers.add(data["provider"])
                u = data.get("usage") or {}
                self.last_usage = u
                if u.get("cost") is not None:
                    try:
                        self.cost_usd += float(u["cost"])
                    except (TypeError, ValueError):
                        pass
                self.calls += 1

                choice = (data.get("choices") or [{}])[0]
                msg = choice.get("message") or {}

                # Content may be a string, a content-part list, or None.
                content = msg.get("content", "")
                if isinstance(content, list):
                    parts = []
                    for p in content:
                        if isinstance(p, dict) and p.get("type") in ("text", None) and p.get("text"):
                            parts.append(p["text"])
                    content = "\n".join(parts)
                content = content or ""

                # Native tool calls (OpenAI shape after OpenRouter normalization).
                tool_calls = []
                for tc in (msg.get("tool_calls") or []):
                    fn = tc.get("function") or {}
                    args = fn.get("arguments")
                    if not isinstance(args, str):
                        args = json.dumps(args or {})
                    tool_calls.append({
                        "id": tc.get("id") or f"call_{len(tool_calls)}",
                        "name": fn.get("name"),
                        "arguments": args,
                    })

                return {
                    "content": content,
                    "tool_calls": tool_calls,
                    "finish_reason": choice.get("finish_reason"),
                }
            except urllib.error.HTTPError as e:
                last_err = e
                # Read the body once so we can classify the failure.
                try:
                    err_body = e.read().decode("utf-8", "replace")
                except Exception:
                    err_body = ""
                if 400 <= e.code < 500 and e.code not in (408, 429):
                    if tools and e.code == 400 and _looks_tool_related(err_body):
                        raise ToolsUnsupported(err_body[:300]) from e
                    # Other 4xx (auth/billing/bad-model) is fatal.
                    raise urllib.error.HTTPError(
                        e.url, e.code, f"{e.reason}: {err_body[:200]}", e.headers, None
                    ) from e
                time.sleep(2 + 3 * attempt)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last_err = e
                time.sleep(2 + 3 * attempt)
        assert last_err is not None
        raise last_err
