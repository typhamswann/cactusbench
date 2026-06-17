# CactusBench OpenRouter harness

Drop-in driver for running CactusBench against any model OpenRouter
exposes — no Docker required at runtime. It is a small, self-contained image→tool-call driver, so runs are
apples-to-apples across every model OpenRouter exposes.

The agent works in a host-side `/workspace` (a temp dir per task) that
the harness sets up from `tasks/<sid>/assets/`. Scoring shells out to the
task's stdlib-only `grade/score.py` — no container build, no model SDK.

## Quickstart

```bash
# 1. Set your OpenRouter API key.
export OPENROUTER_API_KEY=sk-or-v1-...
# (or write the bare key to ~/.openrouter_key)

# 2. Run the six pre-configured models against all 25 tasks.
python harness/run.py --models all --max-turns 14 --cost-cap 10

# 3. Inspect the results.
ls runs/<timestamp>/
cat runs/<timestamp>/gemini35_flash.json | jq '.results[] | {sid: .saguaro_id, reward: .cell_accuracy_reward}'
```

## Args

| Flag | Default | What it does |
|---|---|---|
| `--models` | `all` | Comma-sep model tags (see `harness/models.json`) or `all` |
| `--tasks` | `all` | Comma-sep saguaro IDs (e.g. `41B-01,41B-13`) or `all` |
| `--max-turns` | `50` | Max tool calls per rollout (published contract; declared in the prompt) |
| `--rollouts` | `1` | Rollouts per (model, task) cell — use ≥5 for confidence intervals |
| `--reasoning` | `none` | Pin the reasoning budget: `none\|low\|medium\|high` |
| `--pin-provider` | `None` | Pin the OpenRouter backend (e.g. `Google`, `Z.AI`); mismatches flagged per rollout |
| `--image-window` | `6` | Keep image attachments only on the most recent N user messages |
| `--cost-cap` | `None` | Abort a model once its running OpenRouter cost (USD) exceeds this |
| `--run-id` | timestamp | Run identifier; results land at `runs/<run-id>/` |
| `--resume` | `None` | Resume a run by id, skipping already-scored (saguaro, rollout) cells |
| `--registry` | `harness/models.json` | Model registry path |

## Protocol

Each task is one rollout per model. The harness installs a system prompt
describing the workspace + the four available tools, then loops:

1. Call OpenRouter `/chat/completions` with the current message history.
2. Parse the assistant reply as JSON `{"tool": "<name>", "args": {...}}`.
3. Dispatch to the host-side handler:
   - `list_dir` — directory listing under `/workspace`
   - `read_text` — read a text file (e.g. instruction.md)
   - `view_image` — base64-encode an image; attached to the next user message
   - `write_submission` — write `/workspace/submission.json` and end the task
4. Append the tool result as a user message (text + optional image).
5. If `write_submission` was called, exit; otherwise, repeat.

When the loop ends (`write_submission`, `--max-turns` reached, 5 consecutive
parse failures, or an API error), the harness shells out to the task's
`grade/score.py` and records the result.

## Result format

`runs/<run-id>/<model_tag>.json`:

```json
{
  "model_tag": "gemini35_flash",
  "model_slug": "google/gemini-3.5-flash",
  "provider": null,
  "served_providers": ["Google"],
  "cost_usd": 0.3142,
  "calls": 247,
  "capped_cost": false,
  "pin_provider":     "Google",
  "reasoning":        {"effort": "medium"},
  "rollouts":         5,
  "results": [
    {
      "saguaro_id":               "41B-01",
      "model_tag":                "gemini35_flash",
      "model_slug":               "google/gemini-3.5-flash",
      "rollout_idx":              0,
      "cell_accuracy_reward":     0.95,
      "row_f1":                   0.978,
      "per_field_accuracy":       {"A": 1.0, "C": 0.93, "note": 1.0, "...": "..."},
      "note_accuracy_nonempty":   1.0,
      "note_accuracy_jaccard_diag": 1.0,
      "engaged":                  true,
      "terminator_shimmed":       false,
      "served_providers_rollout": ["Google"],
      "pin_provider":             "Google",
      "provider_mismatch":        false,
      "reasoning":                {"effort": "medium"},
      "n_assets_read":            3,
      "image_manifest":           [{"path": "datasheets/sheet_A.png", "bytes": 855707, "width": 2200, "height": 1700, "mime": "image/png"}],
      "stop":                     "write_submission",
      "turns_taken":              7,
      "max_turns":                50,
      "cost_usd_running":         0.0149,
      "wall_time_sec":            18.4
    }
  ]
}
```

Results are flushed to disk after every rollout, so a SIGINT mid-run
doesn't lose work. Aggregate with `scripts/aggregate.py runs/<run-id>`.

## Model registry

`harness/models.json` holds the OpenRouter slug + provider routing for
each tag. Six models are pre-configured:

| Tag | OpenRouter slug | Provider pin |
|---|---|---|
| `gemini35_flash` | `google/gemini-3.5-flash` | (let OR pick) |
| `qwen37_plus` | `qwen/qwen3.7-plus` | (let OR pick) |
| `qwen35_397b` | `qwen/qwen3.5-397b-a17b` | fp8 |
| `glm5v_turbo` | `z-ai/glm-5v-turbo` | fp8 |
| `kimi_k26` | `moonshotai/kimi-k2.6` | fp8 |
| `gemma4_26b` | `google/gemma-4-26b-a4b` | (let OR pick) |

**Verify slugs** at https://openrouter.ai/models before running —
provider naming drifts between releases.

## Notes / caveats

- The harness uses **native function-calling** by default: the four tools
  are passed via OpenRouter's `tools=` parameter and the model emits
  structured `tool_calls` in the standard function-calling style.
  OpenRouter normalizes every backend's native tool dialect
  (Gemma's special tokens, Gemini's format, etc.) into the same shape, so
  results are comparable across providers. Each result records
  `tool_mode: "fc"`.
- If a provider has no function-calling support, the harness catches the
  tool-related 400 and transparently restarts that rollout in a **text
  protocol** (ReAct-style: reason, then emit one JSON tool call), recorded
  as `tool_mode: "text"`. A model gets 5 consecutive no-tool replies before
  `stop = no_tool_call_x5`.
- **Empty-response terminator shim:** open-weight models sometimes
  return `content=""` + no tool call as a clean-stop, which a naive loop scores
  as an empty submission (0.0). The harness retries this up to 4× and tags the
  rollout `terminator_shimmed: true`; the summary reports **raw vs engaged-subset**
  means separately. Always publish both.
- **Provider pinning:** OpenRouter silently load-balances across backends
  with different image preprocessing. `--pin-provider` forces a single backend
  (`allow_fallbacks:false`); any fallback sets `provider_mismatch: true`. Each
  rollout records `served_providers_rollout`.
- **Reasoning budget:** `--reasoning` pins the effort and is recorded per
  rollout; run low vs high as a sensitivity pass.
- `max_tokens` is **unset** by default — capping it truncated reasoning models
  mid-thought (`finish=length`) and produced false zeros. Each model generates
  until it naturally stops.
- **Transmitted-image manifest:** each `view_image` records the bytes + pixel
  dimensions actually sent (`image_manifest`) — the dominant multimodal-harness
  variable for a handwriting-legibility task.
- Images are sent as base64 data URLs in the user message — that's the
  most portable across OpenRouter providers. The `--image-window` flag
  caps how many images stay attached at once.
- This is intentionally NOT the Harbor runner, which is
  the canonical evaluator for the published leaderboard. This harness
  is for fast iteration + arbitrary-model exploration on a host
  machine; the results are directly comparable in absolute terms but
  use a slightly different loop shape (host-side tools vs. container-
  side `harbor-step`).
