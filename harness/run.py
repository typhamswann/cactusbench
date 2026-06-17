"""OpenRouter harness for CactusBench — runs one or more models against
one or more tasks, scoring via each task's stdlib-only grade/score.py.

Designed to mirror the wanderbench harbor_driver.py shape so apples-to-
apples cross-benchmark comparisons are easy:

- JSON-only tool-call protocol (one tool per turn), so every model OpenRouter
  routes to is supported without provider-specific function-calling glue.
- Sliding image-window cap so old screenshots don't bloat the context.
- Per-model USD cost cap as a backstop.
- Results written to runs/<run_id>/<model_tag>.json incrementally so a kill
  mid-run leaves resumable state.

Workspace contract per task (matches the v0.3 curation task images):

    /workspace/
        instruction.md            THE prompt — delivered verbatim as the first
                                  user message; the harness system prompt is
                                  agent-shape (tools/protocol) only
        datasheets/sheet_{A,B}.png   opaque (year hidden; read the date header)
        photos/<year>_<NN>.jpg       year-labeled (within-year order opaque)
        submission.json    ← the agent writes this; score.py reads it

We don't build the docker images at runtime — the assets already live on
host at tasks/<sid>/assets/, and grade/score.py is stdlib-only. The host
runs the loop and shells out to score.py for grading.

Usage:
    export OPENROUTER_API_KEY=sk-or-v1-...
    python harness/run.py --models gemini35_flash,qwen37_plus --max-turns 12
    python harness/run.py --models all --tasks 41B-01,41B-13 --max-turns 12 \
                          --cost-cap 8.00 --run-id pilot_2026-06
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

from openrouter import OpenRouterClient, ToolsUnsupported
from providers import make_client, load_creds
from tools import DISPATCH, parse_tool_call, ALLOWED, TOOL_SCHEMAS


# -----------------------------------------------------------------------------
# System prompts — agent shape ONLY (tools + protocol). All task/domain content
# lives in the task's instruction.md, delivered verbatim as the first user
# message (DeepSWE convention: the task is pure prompt content; the agent
# supplies its own system prompt).
#
# Two modes, matching what frontier agentic benchmarks do:
#   FC   — native function-calling. The tool schemas are passed via the API's
#          `tools` parameter; the model reasons freely and emits structured
#          tool calls (SWE-agent FunctionCallingParser / mini-swe-agent default).
#   TEXT — fallback for models without function-calling support: the model
#          reasons, then emits one JSON tool call object (ReAct / ThoughtAction).
# -----------------------------------------------------------------------------

SYSTEM_PROMPT_FC = """\
You are an autonomous agent working inside a Unix workspace at /workspace/. You
complete the task described in the first user message by calling the provided
tools (list_dir, read_text, view_image, write_submission).

Think step by step, inspect the files and images you need, then call
write_submission exactly once with your final answer. Make exactly one tool
call at a time and wait for its result before the next."""

SYSTEM_PROMPT_TEXT = """\
You are an autonomous agent working inside a Unix workspace at /workspace/. You
complete the task described in the first user message by issuing tool calls.

You may reason briefly, but every reply MUST end with exactly one tool call as a
single JSON object on its own line:

    {"tool": "<name>", "args": {...}}

Tools:
- list_dir({"path": "<dir>"})            — list a directory.
- read_text({"path": "<file>"})          — return a text file's contents.
- view_image({"path": "<file>"})         — attach an image so you can see it.
- write_submission({"content": "<str>"}) — write <content> to
                                           /workspace/submission.json and end
                                           the task. Call this exactly once."""


# -----------------------------------------------------------------------------
# Per-task driver
# -----------------------------------------------------------------------------

def setup_workspace(task_dir: Path) -> Path:
    """Copy a task's bundled assets into a temp host dir that becomes
    /workspace from the agent's perspective. Mirrors the curation v0.3
    layout: opaque sheet/photo filenames, flat photo dir.
    """
    ws = Path(tempfile.mkdtemp(prefix="sb_ws_"))
    shutil.copyfile(task_dir / "instruction.md", ws / "instruction.md")
    src_sheets = task_dir / "assets" / "datasheets"
    (ws / "datasheets").mkdir()
    for f in sorted(src_sheets.iterdir()):
        shutil.copyfile(f, ws / "datasheets" / f.name)
    src_photos = task_dir / "assets" / "photos"
    (ws / "photos").mkdir()
    if src_photos.exists():
        for f in sorted(src_photos.iterdir()):
            if f.is_file():
                shutil.copyfile(f, ws / "photos" / f.name)
    return ws


def strip_old_images(messages: list[dict], window: int, pin_sheets: bool = False) -> None:
    """Keep image attachments only on the most recent `window` user messages.
    Older ones get their image_url parts replaced with a placeholder text.

    With `pin_sheets`, a user message whose text mentions a datasheet attachment is
    NEVER elided — so the model can still re-reference the sheet late in a long,
    photo-heavy rollout instead of transcribing from memory (noise-floor study §6).
    """
    user_idx = [i for i, m in enumerate(messages) if m["role"] == "user"]
    keep = set(user_idx[-window:])
    for i in user_idx:
        if i in keep:
            continue
        m = messages[i]
        if not isinstance(m["content"], list):
            continue
        if pin_sheets:
            text_blob = " ".join(p.get("text", "") for p in m["content"]
                                 if p.get("type") == "text")
            if "datasheets/" in text_blob:
                continue
        m["content"] = [
            {"type": "text", "text": "[earlier image elided to fit context]"}
            if p.get("type") == "image_url" else p
            for p in m["content"]
        ]


def _cc_strip(messages: list[dict]) -> None:
    """Remove every cache_control marker (so we can re-place ≤4 each turn)."""
    for m in messages:
        c = m.get("content")
        if isinstance(c, list):
            for p in c:
                if isinstance(p, dict):
                    p.pop("cache_control", None)


def _cc_mark(msg: dict) -> bool:
    """Put one ephemeral cache breakpoint on msg's last content part. Converts a
    plain-string content to a single text part. Returns True if a marker was set."""
    c = msg.get("content")
    if isinstance(c, str):
        if not c.strip():
            return False
        msg["content"] = [{"type": "text", "text": c,
                           "cache_control": {"type": "ephemeral"}}]
        return True
    if isinstance(c, list) and c:
        for p in reversed(c):
            if isinstance(p, dict):
                p["cache_control"] = {"type": "ephemeral"}
                return True
    return False


def apply_cache_control(messages: list[dict]) -> None:
    """Anthropic prompt-caching via OpenRouter. Re-placed each turn (≤4 breakpoints):
    - system (caches system prompt + tool schemas, re-sent every turn) — STABLE
    - instruction user message — STABLE
    - rolling breakpoint on the most-recent message (caches the in-window image
      prefix on the turns between strip_old_images elisions)
    Only call for providers that accept cache_control (Anthropic); OpenAI/Gemini
    cache server-side automatically and need no markers."""
    _cc_strip(messages)
    if messages:
        _cc_mark(messages[0])           # system + tools
    if len(messages) >= 2:
        _cc_mark(messages[1])           # instruction
    if len(messages) >= 3:
        _cc_mark(messages[-1])          # rolling recent prefix


def run_task(
    client: OpenRouterClient,
    model_tag: str,
    model_slug: str,
    provider: dict | None,
    task_dir: Path,
    *,
    max_turns: int,
    image_window: int,
    log_path: Path,
    reasoning: dict | None = None,
    pin_provider: str | None = None,
    rollout_idx: int = 0,
    temperature: float = 0.6,
    img_cfg: dict | None = None,
    pin_sheets: bool = False,
) -> dict:
    """Run one (model, task) rollout. Returns a result record."""
    sid = task_dir.name
    ws = setup_workspace(task_dir)
    state: dict = {"images_viewed": [], "image_manifest": [], "done": False,
                   "submission_path": None, "terminator_shimmed": False,
                   "img_cfg": img_cfg or {"mode": "full"}}

    instruction = (task_dir / "instruction.md").read_text()
    use_fc = True  # try native function-calling first; fall back to text mode
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT_FC},
        {"role": "user",   "content": instruction},
    ]

    started = time.time()
    stop = "max_turns"
    last_error_streak = 0
    MAX_ERRORS = 5
    # Explicit empty-response terminator shim (Cai §2). Open-weight models
    # (GLM/MiniMax-class) sometimes return content="" + tool_calls=None, which a
    # naive loop scores as an empty submission (0.0). Retry a bounded number of
    # times before giving up; tag the rollout so raw-vs-engaged means can split it.
    MAX_TERMINATOR_RETRIES = 4
    terminator_retries = 0
    rollout_providers: list[str] = []   # served backend per call, in order
    provider_mismatch = False

    # Pin the served backend so a scored run is single-route (Cai §3). OpenRouter
    # silently load-balances across backends with different image preprocessing.
    eff_provider = dict(provider) if provider else None
    if pin_provider:
        eff_provider = {**(eff_provider or {}), "order": [pin_provider],
                        "allow_fallbacks": False}

    # Prompt caching: only Anthropic via OpenRouter accepts explicit cache_control
    # breakpoints; OpenAI/Gemini cache server-side automatically.
    supports_cc = model_slug.startswith("anthropic/")
    transcript: list[dict] = []          # full per-turn record (saved at cell end)
    cur_tool_io: list[dict] = []         # this turn's tool calls+results (rebound each turn)

    def _log(line: str) -> None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} [{model_tag}] {sid} {line}\n")

    def _run_tool(name: str, raw_args) -> object:
        """Dispatch one tool call. raw_args may be a JSON string or a dict."""
        if isinstance(raw_args, str):
            try:
                a = json.loads(raw_args or "{}")
            except Exception:
                a = {}
        else:
            a = raw_args or {}
        if name not in ALLOWED:
            return f"ERROR: unknown tool {name!r}; allowed: {sorted(ALLOWED)}"
        if not isinstance(a, dict):
            return f"ERROR: arguments for {name!r} must be a JSON object"
        result = DISPATCH[name](a, ws, state)
        try:  # record tool call + result preview for the transcript
            if isinstance(result, dict):
                prev = result.get("text") or ("[image]" if result.get("image_b64") else "")
            else:
                prev = str(result)
            cur_tool_io.append({"name": name, "args": a,
                                "result_preview": (prev or "")[:1000]})
        except Exception:
            pass
        return result

    def _img_subparts(out: dict) -> list[dict]:
        """Expand a view_image result into image_url parts (1 for full/downsample,
        several for tiles). Falls back to the back-compat single-image fields."""
        subs = out.get("images") or [{"image_b64": out.get("image_b64"),
                                       "image_mime": out.get("image_mime")}]
        return [{"type": "image_url",
                 "image_url": {"url": f"data:{s['image_mime']};base64,{s['image_b64']}"}}
                for s in subs if s.get("image_b64")]

    def _stage_image_user_msg(staged: list[dict]) -> None:
        if not staged:
            return
        parts: list[dict] = []
        for im in staged:
            if im.get("text"):
                parts.append({"type": "text", "text": im["text"]})
            parts.extend(_img_subparts(im))
        messages.append({"role": "user", "content": parts})

    turn = 0
    for turn in range(1, max_turns + 1):
        cur_tool_io = []  # fresh per turn; _run_tool appends to the current binding
        if supports_cc:
            apply_cache_control(messages)
        _t0 = time.time()
        _c0, _i0, _o0, _ca0 = (client.cost_usd, client.tok_in,
                               client.tok_out, client.tok_cached)
        try:
            resp = client.chat(
                model=model_slug,
                messages=messages,
                provider=eff_provider,
                tools=TOOL_SCHEMAS if use_fc else None,
                reasoning=reasoning,
                temperature=temperature,
            )
        except ToolsUnsupported as e:
            # Provider has no native function-calling. Switch to text protocol
            # and restart the rollout (only happens on turn 1, before any
            # tool/assistant messages have accumulated).
            _log(f"turn={turn} tools_unsupported -> text mode ({str(e)[:80]})")
            use_fc = False
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_TEXT},
                {"role": "user",   "content": instruction},
            ]
            continue
        except Exception as e:
            stop = f"api_error:{str(e)[:80]}"
            _log(f"turn={turn} {stop}")
            break

        tool_calls = resp.get("tool_calls") or []
        content = resp.get("content") or ""
        finish = resp.get("finish_reason")
        sp = resp.get("served_provider")
        if sp:
            rollout_providers.append(sp)
            if pin_provider and sp != pin_provider:
                provider_mismatch = True
                _log(f"turn={turn} PROVIDER_MISMATCH pinned={pin_provider} served={sp}")

        # Full per-turn transcript (interaction, tool calls, timing, tokens, cost).
        # tool_io is filled in-place as this turn's tools execute below.
        transcript.append({
            "turn": turn, "ts": time.strftime("%H:%M:%S"),
            "wall_sec": round(time.time() - _t0, 2),
            "cost_delta": round(client.cost_usd - _c0, 5),
            "tok_in_delta": client.tok_in - _i0,
            "tok_out_delta": client.tok_out - _o0,
            "tok_cached_delta": client.tok_cached - _ca0,
            "n_messages_sent": len(messages),
            "assistant_content": (content or "")[:2000],
            "tool_calls": [{"name": tc.get("name"), "args": tc.get("arguments")}
                           for tc in tool_calls],
            "finish_reason": finish, "served_provider": sp,
            "tool_io": cur_tool_io,
        })

        # ---- Empty-response terminator shim (Cai §2) ------------------------
        # FC reply with no tool_calls AND empty content = the open-weight clean-
        # stop pattern. Retry rather than scoring an empty submission as zero.
        if use_fc and not tool_calls and not content.strip():
            terminator_retries += 1
            state["terminator_shimmed"] = True
            _log(f"turn={turn} empty_response_terminator retry={terminator_retries}/"
                 f"{MAX_TERMINATOR_RETRIES} finish={finish}")
            if terminator_retries > MAX_TERMINATOR_RETRIES:
                stop = "empty_terminator"
                break
            messages.append({"role": "assistant", "content": ""})
            messages.append({"role": "user", "content":
                "Your previous response was empty. You have not finished the task. "
                "Continue by calling a tool (view_image / read_text / list_dir), and "
                "call write_submission once your table is ready."})
            strip_old_images(messages, image_window, pin_sheets)
            continue

        # ---- Native function-calling path -----------------------------------
        if use_fc and tool_calls:
            last_error_streak = 0
            messages.append({
                "role": "assistant",
                "content": content or None,
                "tool_calls": [
                    {"id": tc["id"], "type": "function",
                     "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                    for tc in tool_calls
                ],
            })
            staged: list[dict] = []
            for tc in tool_calls:
                out = _run_tool(tc["name"], tc["arguments"])
                if isinstance(out, dict):  # view_image
                    messages.append({"role": "tool", "tool_call_id": tc["id"],
                                     "content": out.get("text", "(image attached below)")})
                    if out.get("image_b64"):
                        staged.append(out)
                else:
                    messages.append({"role": "tool", "tool_call_id": tc["id"],
                                     "content": str(out)})
                _log(f"turn={turn} tool={tc['name']} ok cost_usd={client.cost_usd:.4f}")
            _stage_image_user_msg(staged)
            if state.get("done"):
                stop = "write_submission"
                break
            strip_old_images(messages, image_window, pin_sheets)
            continue

        # ---- Text fallback path (also covers FC replies with no tool_calls) -
        messages.append({"role": "assistant", "content": content})
        call = parse_tool_call(content)
        if call is None:
            last_error_streak += 1
            preview = " ".join(content.split())[:300]
            _log(f"turn={turn} no_tool_call (streak={last_error_streak}) finish={finish} reply={preview!r}")
            if last_error_streak >= MAX_ERRORS:
                stop = "no_tool_call_x5"
                break
            nudge = ("Make a tool call to proceed." if use_fc else
                     'End your reply with one JSON tool call: {"tool":"<name>","args":{...}}.')
            messages.append({"role": "user", "content": nudge})
            continue
        last_error_streak = 0
        tool, args = call
        result = _run_tool(tool, args)
        if isinstance(result, dict):
            parts = []
            if result.get("text"):
                parts.append({"type": "text", "text": result["text"]})
            parts.extend(_img_subparts(result))
            messages.append({"role": "user", "content": parts})
        else:
            messages.append({"role": "user", "content": [{"type": "text", "text": str(result)}]})
        _log(f"turn={turn} tool={tool} ok cost_usd={client.cost_usd:.4f}")
        if state.get("done"):
            stop = "write_submission"
            break
        strip_old_images(messages, image_window, pin_sheets)

    # Score
    sub_path = ws / "submission.json"
    truth_path = task_dir / "grade" / "truth.json"
    score_py = task_dir / "grade" / "score.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(score_py), str(sub_path), str(truth_path)],
            capture_output=True, text=True, timeout=60,
        )
        reward_json = json.loads(proc.stdout)
    except Exception as e:
        reward_json = {
            "cell_accuracy_reward": 0.0,
            "structural_error": f"scoring_subprocess_error: {e}",
        }

    # Capture the raw submission the agent wrote, for offline inspection.
    submission_raw = None
    try:
        if sub_path.exists():
            submission_raw = sub_path.read_text()[:20000]
    except Exception:
        pass

    images_viewed = state.get("images_viewed", [])
    # "engaged" = the rollout actually produced a submission. Open-weight models
    # that hit the empty-response terminator score 0 with no real attempt; raw vs
    # engaged-subset means must be reported separately (Cai §2).
    engaged = bool(state.get("done"))
    rec = {
        "saguaro_id": sid,
        "model_tag": model_tag,
        "model_slug": model_slug,
        "rollout_idx": rollout_idx,
        "tool_mode": "fc" if use_fc else "text",
        "submission_raw": submission_raw,
        "cell_accuracy_reward": reward_json.get("cell_accuracy_reward", 0.0),
        "base_cell_accuracy": reward_json.get("base_cell_accuracy", 0.0),
        "extra_row_penalty": reward_json.get("extra_row_penalty", 0.0),
        "row_f1": reward_json.get("row_f1", 0.0),
        "rows_truth": reward_json.get("rows_truth"),
        "rows_pred_scored": reward_json.get("rows_pred_scored"),
        "rows_matched": reward_json.get("rows_matched"),
        "rows_missing": reward_json.get("rows_missing"),
        "rows_extra": reward_json.get("rows_extra"),
        "rows_excluded": reward_json.get("rows_excluded"),
        "per_field_accuracy": reward_json.get("per_field_accuracy"),
        "note_accuracy_nonempty": reward_json.get("note_accuracy_nonempty"),
        "note_nonempty_total": reward_json.get("note_nonempty_total"),
        "note_accuracy_jaccard_diag": reward_json.get("note_accuracy_jaccard_diag"),
        "structural_error": reward_json.get("structural_error"),
        "stop": stop,
        "engaged": engaged,
        "terminator_shimmed": state.get("terminator_shimmed", False),
        "turns_taken": turn,
        "max_turns": max_turns,
        "reasoning": reasoning,
        "images_viewed": images_viewed,
        "n_assets_read": len(images_viewed),
        "image_manifest": state.get("image_manifest", []),
        "served_providers_rollout": sorted(set(rollout_providers)),
        "pin_provider": pin_provider,
        "provider_mismatch": provider_mismatch,
        "cost_usd_running": round(client.cost_usd, 4),
        "tok_in_running": client.tok_in,
        "tok_out_running": client.tok_out,
        "tok_cached_running": client.tok_cached,
        "wall_time_sec": round(time.time() - started, 1),
    }

    # Persist the full transcript (every turn: interaction, tool I/O, timing,
    # per-turn tokens + cost) as JSONL — line 0 is a meta header.
    try:
        tdir = log_path.parent / "transcripts"
        tdir.mkdir(parents=True, exist_ok=True)
        tf = tdir / f"{model_tag}__{sid}__r{rollout_idx}.jsonl"
        with tf.open("w") as f:
            f.write(json.dumps({"_meta": {
                "saguaro_id": sid, "model_tag": model_tag, "model_slug": model_slug,
                "rollout_idx": rollout_idx, "reasoning": reasoning,
                "cache_control": supports_cc, "stop": stop, "engaged": engaged,
                "turns_taken": turn, "wall_time_sec": rec["wall_time_sec"],
                "cost_usd_running": rec["cost_usd_running"],
                "tok_in_running": client.tok_in, "tok_out_running": client.tok_out,
                "tok_cached_running": client.tok_cached,
                "cell_accuracy_reward": rec["cell_accuracy_reward"],
            }}) + "\n")
            for t in transcript:
                f.write(json.dumps(t) + "\n")
        rec["transcript_path"] = str(tf)
    except Exception as e:  # noqa: BLE001
        rec["transcript_path"] = f"(transcript write failed: {e})"

    # Best-effort cleanup
    try:
        shutil.rmtree(ws)
    except Exception:
        pass
    return rec


# -----------------------------------------------------------------------------
# Top-level run
# -----------------------------------------------------------------------------

def _expand_models(models_arg: str, registry: dict) -> list[tuple[str, str, dict | None]]:
    """Resolve a comma-separated model arg into [(tag, slug, provider), ...]."""
    if models_arg == "all":
        tags = list(registry["models"].keys())
    else:
        tags = [m.strip() for m in models_arg.split(",") if m.strip()]
    out = []
    for tag in tags:
        if tag not in registry["models"]:
            raise SystemExit(f"unknown model tag: {tag!r}. known: {sorted(registry['models'])}")
        rec = registry["models"][tag]
        out.append((tag, rec["slug"], rec.get("provider")))
    return out


def _expand_tasks(tasks_arg: str | None, tasks_dir: Path | None = None) -> list[Path]:
    tasks_dir = tasks_dir or (REPO / "tasks")
    if tasks_arg is None or tasks_arg == "all":
        return sorted([p for p in tasks_dir.iterdir() if p.is_dir() and (p / "task.toml").exists()])
    out = []
    for sid in tasks_arg.split(","):
        sid = sid.strip()
        if not sid:
            continue
        p = tasks_dir / sid
        if not p.exists():
            raise SystemExit(f"no such task: {sid!r}")
        out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", default="all",
                    help="comma-separated model tags (see harness/models.json) or 'all'")
    ap.add_argument("--tasks", default=None,
                    help="comma-separated saguaro_ids or 'all' (default: all 25)")
    ap.add_argument("--tasks-dir", default=None,
                    help="task root to run against (default: tasks/). Point at a private "
                         "tasks_test/ draw to score the held-back test set (see docs/REFRESH.md)")
    ap.add_argument("--max-turns", type=int, default=50,
                    help="max tool-call turns per rollout (published contract: 50)")
    ap.add_argument("--rollouts", type=int, default=1,
                    help="rollouts per (model, task) cell — use >=5 for confidence intervals")
    ap.add_argument("--reasoning", default="none",
                    choices=["none", "low", "medium", "high"],
                    help="pin the reasoning budget (Cai §5). Recorded per cell.")
    ap.add_argument("--pin-provider", default=None,
                    help="pin the OpenRouter backend (e.g. 'Google', 'Z.AI') so a scored "
                         "run is single-route; mismatches are flagged per rollout (Cai §3)")
    ap.add_argument("--temperature", type=float, default=0.6,
                    help="sampling temperature (use 0 for the lowest-variance scored runs)")
    ap.add_argument("--image-mode", default="full",
                    choices=["full", "downsample", "tiles"],
                    help="client-side image handoff (noise-floor study §1): full | "
                         "downsample (cap long edge at --image-max-edge) | tiles "
                         "(split into --image-grid^2 full-res tiles)")
    ap.add_argument("--image-max-edge", type=int, default=1568,
                    help="long-edge cap in px for --image-mode downsample")
    ap.add_argument("--image-grid", type=int, default=2,
                    help="grid size N for --image-mode tiles (N*N tiles per image)")
    ap.add_argument("--pin-sheets", action="store_true",
                    help="never elide the datasheets from context, only window photos")
    ap.add_argument("--image-window", type=int, default=6,
                    help="keep image attachments only on the most recent N user messages")
    ap.add_argument("--cost-cap", type=float, default=None,
                    help="abort a model once its running OpenRouter cost exceeds this (USD)")
    ap.add_argument("--run-id", default=None,
                    help="run identifier (default: timestamp). results land at runs/<run-id>/")
    ap.add_argument("--resume", default=None,
                    help="resume a prior run by run-id. Loads existing results from "
                         "runs/<resume>/<model_tag>.json, skips saguaros already scored, "
                         "appends new ones to the SAME file. --run-id is ignored when set.")
    ap.add_argument("--registry", default=str(HERE / "models.json"))
    args = ap.parse_args()

    # Native first-party creds for frontier models (Bedrock/OpenAI/Gemini).
    load_creds()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        # Convenience: try ~/.openrouter_key like wanderbench's pattern.
        key_file = Path.home() / ".openrouter_key"
        if key_file.exists():
            api_key = key_file.read_text().strip()
    # OpenRouter is now OS-models-only; frontier models route to first-party APIs.
    # Don't hard-fail if the key is absent — only OS-model cells need it.
    if not api_key:
        print("[run] note: no OpenRouter key — OS-model cells would fail, "
              "but frontier (Bedrock/OpenAI/Gemini) routes are unaffected.", flush=True)

    registry = json.loads(Path(args.registry).read_text())
    models = _expand_models(args.models, registry)
    tasks = _expand_tasks(args.tasks, Path(args.tasks_dir) if args.tasks_dir else None)
    reasoning = None if args.reasoning == "none" else {"effort": args.reasoning}
    img_cfg = {"mode": args.image_mode, "max_edge": args.image_max_edge, "grid": args.image_grid}

    resuming = args.resume is not None
    run_id = args.resume or args.run_id or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    runs_dir = REPO / "runs" / run_id
    if resuming and not runs_dir.exists():
        raise SystemExit(f"--resume {args.resume!r}: runs dir {runs_dir} not found")
    runs_dir.mkdir(parents=True, exist_ok=True)
    if not resuming:
        (runs_dir / "config.json").write_text(json.dumps({
            "run_id": run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "models": [{"tag": t, "slug": s, "provider": p} for (t, s, p) in models],
            "tasks": [t.name for t in tasks],
            "max_turns": args.max_turns,
            "rollouts": args.rollouts,
            "reasoning": reasoning,
            "pin_provider": args.pin_provider,
            "temperature": args.temperature,
            "image_mode": args.image_mode,
            "image_max_edge": args.image_max_edge,
            "image_grid": args.image_grid,
            "pin_sheets": args.pin_sheets,
            "image_window": args.image_window,
            "cost_cap": args.cost_cap,
            "harness": "openrouter-host",
            "harness_version": "v0.5-noisefloor",
        }, indent=2))

    print(f"[run] id={run_id}  models={[m[0] for m in models]}  n_tasks={len(tasks)}"
          f"{'  (RESUMING)' if resuming else ''}", flush=True)

    for (tag, slug, provider) in models:
        # Route each model to its first-party API (frontier) or OpenRouter (OS).
        client, call_slug = make_client(slug, api_key)
        if call_slug != slug:
            print(f"[{tag}] routing {slug} -> native {call_slug} "
                  f"({type(client).__name__})", flush=True)
        results: list[dict] = []
        capped = False
        out_path = runs_dir / f"{tag}.json"
        log_path = runs_dir / f"{tag}.log"

        # ---- Resume: load completed (saguaro, rollout) cells, skip them ------
        done_keys: set = set()
        if resuming and out_path.exists():
            try:
                prior = json.loads(out_path.read_text())
                results = prior.get("results", [])
                done_keys = {(r["saguaro_id"], r.get("rollout_idx", 0))
                             for r in results if r.get("saguaro_id")}
                client.cost_usd = float(prior.get("cost_usd", 0.0))
                client.calls = int(prior.get("calls", 0))
                client.served_providers = set(prior.get("served_providers", []))
                print(f"[{tag}] resuming: {len(done_keys)} cells already scored, "
                      f"prior cost ${client.cost_usd:.3f}", flush=True)
            except Exception as e:
                print(f"[{tag}] WARN: failed to load prior {out_path}: {e}", flush=True)
                results = []
                done_keys = set()

        def _flush() -> None:
            out_path.write_text(json.dumps({
                "model_tag": tag,
                "model_slug": slug,
                "provider": provider,
                "pin_provider": args.pin_provider,
                "reasoning": reasoning,
                "rollouts": args.rollouts,
                "served_providers": sorted(client.served_providers),
                "cost_usd": round(client.cost_usd, 4),
                "calls": client.calls,
                "capped_cost": capped,
                "results": results,
            }, indent=2))

        for i, task_dir in enumerate(tasks, 1):
            if capped:
                break
            for r_idx in range(args.rollouts):
                if (task_dir.name, r_idx) in done_keys:
                    continue
                if args.cost_cap and client.cost_usd >= args.cost_cap:
                    print(f"[{tag}] cost cap ${args.cost_cap:.2f} reached at "
                          f"${client.cost_usd:.4f} — stopping", flush=True)
                    capped = True
                    break
                tag_r = f"{task_dir.name}#{r_idx}" if args.rollouts > 1 else task_dir.name
                print(f"[{tag}] task {i}/{len(tasks)}: {tag_r}  [cost ${client.cost_usd:.3f}]",
                      flush=True)
                try:
                    rec = run_task(
                        client, tag, call_slug, provider, task_dir,
                        max_turns=args.max_turns,
                        image_window=args.image_window,
                        log_path=log_path,
                        reasoning=reasoning,
                        pin_provider=args.pin_provider,
                        rollout_idx=r_idx,
                        temperature=args.temperature,
                        img_cfg=img_cfg,
                        pin_sheets=args.pin_sheets,
                    )
                except Exception as e:
                    rec = {
                        "saguaro_id": task_dir.name, "model_tag": tag, "model_slug": slug,
                        "rollout_idx": r_idx, "error": str(e)[:200],
                        "cell_accuracy_reward": 0.0, "row_f1": 0.0, "engaged": False,
                    }
                results.append(rec)
                print(f"    -> reward={rec.get('cell_accuracy_reward', 0):.3f}  "
                      f"row_f1={rec.get('row_f1', 0):.3f}  "
                      f"rows={rec.get('rows_matched')}/{rec.get('rows_truth')}  "
                      f"engaged={rec.get('engaged')}  shim={rec.get('terminator_shimmed')}  "
                      f"prov={rec.get('served_providers_rollout')}  "
                      f"turns={rec.get('turns_taken')}  stop={rec.get('stop')}", flush=True)
                _flush()  # incremental write so a SIGINT doesn't lose results

        # ---- Raw vs engaged-subset summary (Cai §2) -------------------------
        n = len(results)
        raw_mean = sum(r.get("cell_accuracy_reward", 0) for r in results) / max(1, n)
        eng = [r for r in results if r.get("engaged")]
        eng_mean = sum(r.get("cell_accuracy_reward", 0) for r in eng) / max(1, len(eng))
        n_shim = sum(1 for r in results if r.get("terminator_shimmed"))
        n_mismatch = sum(1 for r in results if r.get("provider_mismatch"))
        print(f"[{tag}] done. raw_mean={raw_mean:.3f} (n={n})  "
              f"engaged_mean={eng_mean:.3f} (n={len(eng)})  "
              f"shimmed={n_shim}  provider_mismatch={n_mismatch}  "
              f"cost=${client.cost_usd:.3f}  providers={sorted(client.served_providers)}"
              f"{'  CAPPED' if capped else ''}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
