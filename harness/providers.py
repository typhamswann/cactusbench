"""Native first-party provider routing for FRONTIER models.

Per the user's directive (and Cai §3 — don't let a gateway confound the result):
frontier models hit their OWN API, never OpenRouter. Only OS models use OpenRouter.

  anthropic/*  -> AWS Bedrock (AnthropicBedrock). Caching: EXPLICIT cache_control
                  on the system prompt + a rolling breakpoint on the latest turn.
                  Driven through the harness TEXT protocol (raises ToolsUnsupported
                  so run_task falls back to JSON-in-text tool calls).
  openai/*     -> OpenAI API (native function-calling). Caching: AUTOMATIC.
  google/*     -> Gemini OpenAI-compatible endpoint (native FC). Caching: implicit.
  everything else -> OpenRouter (the existing OpenRouterClient).

Each client mirrors OpenRouterClient's surface:
  .chat(model, messages, *, provider, tools, max_tokens, temperature, reasoning)
    -> {"content", "tool_calls", "finish_reason", "served_provider"}
  and accumulates .cost_usd / .tok_in / .tok_out / .tok_cached / .calls /
  .served_providers / .last_usage  (so run.py's logging + transcript work unchanged).

Credentials are sourced from the spinstack env file (same creds the spinstack
apps + ai-social Bedrock client use). Values are never logged.
"""
from __future__ import annotations

import json
import os
import re
import time

from openrouter import OpenRouterClient, ToolsUnsupported  # noqa: F401  (re-exported)

SPINSTACK_ENV = "/Users/typham-swann/Desktop/spinstack_apps/spinstack/.env.local"
_CRED_NAMES = {
    "OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY",
    "AWS_BEDROCK_ACCESS_KEY_ID", "AWS_BEDROCK_SECRET_ACCESS_KEY", "AWS_BEDROCK_REGION",
}


def load_creds(path: str = SPINSTACK_ENV) -> None:
    """Load provider keys from the spinstack env file into os.environ (no overwrite
    of anything already set; values never printed)."""
    if os.path.exists(path):
        for line in open(path):
            m = re.match(r'(?:export\s+)?([A-Z_]+)\s*=\s*(.*)', line.strip())
            if m and m.group(1) in _CRED_NAMES and not os.environ.get(m.group(1)):
                os.environ[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    # DashScope (Alibaba) key for proprietary Qwen models (e.g. qwen3-vl-plus),
    # which are NOT on OpenRouter — routed to their first-party API instead.
    dkey = os.path.expanduser("~/.dashscope_key")
    if not os.environ.get("DASHSCOPE_API_KEY") and os.path.exists(dkey):
        os.environ["DASHSCOPE_API_KEY"] = open(dkey).read().strip()


# logical (OpenRouter) slug -> (provider, native model id)
ROUTE = {
    "anthropic/claude-opus-4.8":      ("bedrock", "us.anthropic.claude-opus-4-8"),
    "anthropic/claude-opus-4.7":      ("bedrock", "us.anthropic.claude-opus-4-7"),
    "anthropic/claude-sonnet-4.6":    ("bedrock", "us.anthropic.claude-sonnet-4-6"),
    "openai/gpt-5.5":                 ("openai",  "gpt-5.5"),
    "google/gemini-3.1-pro-preview":  ("gemini",  "gemini-3.1-pro-preview"),
    "google/gemini-3.5-flash":        ("gemini",  "gemini-3.5-flash"),
    # Proprietary Qwen vision model — not on OpenRouter; first-party = DashScope.
    "qwen3-vl-plus":                  ("dashscope", "qwen3-vl-plus"),
}

# price per Mtok: (input, output). Anthropic exact; OpenAI/Google best-estimate.
PRICE = {
    "us.anthropic.claude-opus-4-8":   (5.0, 25.0),
    "us.anthropic.claude-opus-4-7":   (5.0, 25.0),
    "us.anthropic.claude-sonnet-4-6": (3.0, 15.0),
    "gpt-5.5":                        (1.25, 10.0),
    "gemini-3.1-pro-preview":         (2.0, 12.0),
    "gemini-3.5-flash":               (0.30, 2.5),
    "qwen3-vl-plus":                  (0.21, 0.63),   # DashScope est.
}

_TRANSIENT = ("429", "500", "502", "503", "504", "timeout", "Timeout",
              "Connection", "Throttl", "ServiceUnavailable")


def route(slug: str):
    """Return (provider, native_id) for a frontier slug, or None for OS (OpenRouter)."""
    return ROUTE.get(slug)


def _parse_data_url(url: str):
    m = re.match(r"data:([^;]+);base64,(.*)", url or "", re.S)
    return (m.group(1), m.group(2)) if m else (None, None)


def _to_anthropic(messages: list[dict]):
    """OpenAI-style messages -> (system_blocks, conversation) for AnthropicBedrock.
    Adds cache_control to the last system block and a rolling breakpoint on the
    last conversation block. Merges consecutive same-role turns (anthropic requires
    alternation) and guarantees the conversation starts with a user turn."""
    system_txt: list[str] = []
    conv: list[dict] = []
    for msg in messages:
        role = msg.get("role")
        c = msg.get("content")
        if role == "system":
            t = c if isinstance(c, str) else " ".join(
                p.get("text", "") for p in (c or []) if isinstance(p, dict))
            if t:
                system_txt.append(t)
            continue
        blocks: list[dict] = []
        if isinstance(c, str):
            if c:
                blocks.append({"type": "text", "text": c})
        elif isinstance(c, list):
            for p in c:
                if not isinstance(p, dict):
                    continue
                if p.get("type") == "text" and p.get("text"):
                    blocks.append({"type": "text", "text": p["text"]})
                elif p.get("type") == "image_url":
                    mt, data = _parse_data_url((p.get("image_url") or {}).get("url", ""))
                    if data:
                        blocks.append({"type": "image", "source":
                                       {"type": "base64", "media_type": mt, "data": data}})
        if not blocks:
            blocks = [{"type": "text", "text": "(continue)"}]
        a_role = "assistant" if role == "assistant" else "user"
        if conv and conv[-1]["role"] == a_role:          # merge consecutive same-role
            conv[-1]["content"].extend(blocks)
        else:
            conv.append({"role": a_role, "content": blocks})

    sys_blocks = [{"type": "text", "text": t} for t in system_txt if t]
    if sys_blocks:
        sys_blocks[-1]["cache_control"] = {"type": "ephemeral"}
    if conv and conv[0]["role"] != "user":
        conv.insert(0, {"role": "user", "content": [{"type": "text", "text": "(begin)"}]})
    if conv:                                              # rolling cache breakpoint
        for b in reversed(conv[-1]["content"]):
            if isinstance(b, dict):
                b["cache_control"] = {"type": "ephemeral"}
                break
    return sys_blocks, conv


class BedrockClient:
    """Claude via AWS Bedrock (AnthropicBedrock), text protocol + explicit caching."""

    def __init__(self, model_id: str):
        from anthropic import AnthropicBedrock
        self.model_id = model_id
        self._c = AnthropicBedrock(
            aws_access_key=os.environ["AWS_BEDROCK_ACCESS_KEY_ID"],
            aws_secret_key=os.environ["AWS_BEDROCK_SECRET_ACCESS_KEY"],
            aws_region=os.environ.get("AWS_BEDROCK_REGION", "us-east-1"))
        self.cost_usd = 0.0
        self.calls = 0
        self.tok_in = self.tok_out = self.tok_cached = 0
        self.served_providers: set[str] = set()
        self.last_usage = None

    def chat(self, model, messages, *, provider=None, tools=None,
             max_tokens=None, temperature=0.6, reasoning=None):
        if tools:  # force the harness into JSON-in-text protocol (no anthropic FC)
            raise ToolsUnsupported("bedrock: text protocol")
        system_blocks, conv = _to_anthropic(messages)
        kw = dict(model=self.model_id, max_tokens=max_tokens or 8192,
                  messages=conv)
        if system_blocks:
            kw["system"] = system_blocks
        # NOTE: no temperature — removed on Opus 4.7/4.8 (would 400). reasoning=none
        # => omit thinking (4.7/4.8 run without thinking when omitted).
        last = None
        for attempt in range(4):
            try:
                r = self._c.messages.create(**kw)
                break
            except Exception as e:  # noqa: BLE001
                last = e
                if attempt < 3 and any(x in str(e) for x in _TRANSIENT):
                    time.sleep(2 + 3 * attempt)
                    continue
                raise
        content = "".join(getattr(b, "text", "") for b in r.content
                          if getattr(b, "type", "") == "text")
        u = r.usage
        tin = getattr(u, "input_tokens", 0) or 0
        tout = getattr(u, "output_tokens", 0) or 0
        cc = getattr(u, "cache_creation_input_tokens", 0) or 0
        cr = getattr(u, "cache_read_input_tokens", 0) or 0
        self.tok_in += tin + cc + cr
        self.tok_out += tout
        self.tok_cached += cr
        self.calls += 1
        self.served_providers.add("bedrock")
        self.last_usage = {"input_tokens": tin, "output_tokens": tout,
                           "cache_creation_input_tokens": cc, "cache_read_input_tokens": cr}
        pi, po = PRICE.get(self.model_id, (5.0, 25.0))
        self.cost_usd += (tin * pi + cc * pi * 1.25 + cr * pi * 0.1 + tout * po) / 1e6
        return {"content": content, "tool_calls": [],
                "finish_reason": getattr(r, "stop_reason", None), "served_provider": "bedrock"}


class OpenAICompatClient:
    """OpenAI (gpt) or Gemini (OpenAI-compat endpoint). Native function-calling."""

    def __init__(self, kind: str, model_id: str):
        from openai import OpenAI
        self.kind = kind
        self.model_id = model_id
        if kind == "openai":
            self._c = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        elif kind == "dashscope":
            self._c = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"],
                             base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
        else:
            self._c = OpenAI(api_key=os.environ["GEMINI_API_KEY"],
                             base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
        self.cost_usd = 0.0
        self.calls = 0
        self.tok_in = self.tok_out = self.tok_cached = 0
        self.served_providers: set[str] = set()
        self.last_usage = None

    def chat(self, model, messages, *, provider=None, tools=None,
             max_tokens=None, temperature=0.6, reasoning=None):
        kw: dict = {"model": self.model_id, "messages": messages}
        if tools:
            kw["tools"] = tools
        if self.kind == "openai":
            kw["max_completion_tokens"] = max_tokens or 16000   # gpt-5.5 param; no temperature
        else:
            kw["max_tokens"] = max_tokens or 16000
            kw["temperature"] = temperature
        last = None
        for attempt in range(4):
            try:
                r = self._c.chat.completions.create(**kw)
                break
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                if tools and "tool" in msg.lower() and any(
                        k in msg.lower() for k in ("support", "invalid", "not allowed")):
                    raise ToolsUnsupported(msg[:300])
                last = e
                if attempt < 3 and any(x in msg for x in _TRANSIENT):
                    time.sleep(2 + 3 * attempt)
                    continue
                raise
        ch = r.choices[0]
        m = ch.message
        content = m.content or ""
        tcs = []
        for tc in (getattr(m, "tool_calls", None) or []):
            args = tc.function.arguments
            if not isinstance(args, str):
                args = json.dumps(args or {})
            tcs.append({"id": tc.id or f"call_{len(tcs)}",
                        "name": tc.function.name, "arguments": args})
        u = r.usage
        pin = getattr(u, "prompt_tokens", 0) or 0
        pout = getattr(u, "completion_tokens", 0) or 0
        cached = 0
        ptd = getattr(u, "prompt_tokens_details", None)
        if ptd is not None:
            cached = getattr(ptd, "cached_tokens", 0) or 0
        self.tok_in += pin
        self.tok_out += pout
        self.tok_cached += cached
        self.calls += 1
        self.served_providers.add(self.kind)
        self.last_usage = {"prompt_tokens": pin, "completion_tokens": pout, "cached_tokens": cached}
        pi, po = PRICE.get(self.model_id, (0.0, 0.0))
        billable_in = (pin - cached) + cached * 0.1     # cached input ~0.1x
        self.cost_usd += (billable_in * pi + pout * po) / 1e6
        return {"content": content, "tool_calls": tcs,
                "finish_reason": ch.finish_reason, "served_provider": self.kind}


def make_client(slug: str, openrouter_key: str | None):
    """Return (client, call_id). Frontier slugs -> native first-party client +
    native model id; everything else -> OpenRouter with the slug unchanged."""
    r = route(slug)
    if r is None:
        return OpenRouterClient(api_key=openrouter_key), slug
    provider, native = r
    if provider == "bedrock":
        return BedrockClient(native), native
    return OpenAICompatClient(provider, native), native
