# Cross-harness & reasoning-effort study

Each model's production settings were chosen on a small, fixed three-task probe before the full run, by sweeping the knobs that add measurement noise — harness, reasoning effort, and image handoff — so the scored numbers come from a declared surface rather than a flattering one.

The probe is three plot-41B saguaros, chosen to span the axes that interact with noise:

| task | difficulty | rows | photos | notes | role in the probe |
|---|---|---|---|---|---|
| 41B-04A | medium | 6 | 0 | 0 | pure sheet-reading — isolates legibility/downsampling with no photo confound |
| 41B-13 | medium | 15 | 9 | 5 | mixed load: dense table + free-text note transcription + photos |
| 41B-04 | hard | 8 | 13 | 0 | maximum image-handoff stress + hardest cross-year matching |

Every cell is 5 rollouts; the score is per-cell accuracy under the field tolerances (no LLM judge).

## Results

Cross-harness × cross-reasoning, 5 seeds per cell.

| Model | native low | native default | native high | controlled loop |
|---|---|---|---|---|
| **Frontier** — native = production CLI; controlled loop = first-party API | | | | |
| Opus 4.8 (Claude Code → Bedrock) | 0.906 | 0.981 | **0.982** | 0.900 |
| Opus 4.7 (Claude Code → Bedrock) | 0.865 | 0.964 | 0.941 | **0.994** |
| GPT-5.5 (Codex → OpenAI) | 0.975 | **0.994** | 0.993 | 0.986 |
| Gemini 3.1 Pro (Antigravity → Google) | **0.957** | — | 0.887 | 0.930 |
| Gemini 3.5 Flash (Antigravity → Google) | **0.885** | — | 0.862 | 0.640 |
| **Open-weight** — native = Qwen Code; controlled loop = OpenRouter / DashScope | | | | |
| Qwen3-VL-Plus | — | 0.819 | — | **0.890** † |
| MiniMax-M3 | — | 0.329 | — | **0.855** ‡ |

† both sides DashScope · ‡ both sides OpenRouter — so the open-weight rows isolate scaffolding alone (same model, same API). Gemini has no native "default" tier; Antigravity bakes the reasoning level into the model name.

## Method

- **Routing.** Frontier models route to first-party APIs (Claude → AWS Bedrock with explicit cache control; GPT → OpenAI; Gemini → Google). Open-weight models route to OpenRouter, except the proprietary `qwen3-vl-plus`, which uses DashScope. Implemented in `harness/providers.py`.
- **Caching** on everywhere — Bedrock explicit, the others server-side.
- **Seeds.** 5 rollouts per (model, config, task). The native CLIs were swept across low/default/high reasoning; the controlled loop ran at a single default.
- **Recording.** Per-turn JSONL transcripts — every tool call, timing, token count, and cost — under `runs/<run>/transcripts/`.

## Findings

1. **Reasoning effort is non-monotonic and vendor-specific.** GPT-5.5 and Opus 4.8 climb with effort; Opus 4.7 peaks at default; Gemini *inverts*, scoring worse at high effort on this transcription task.
2. **Harness sensitivity scales inversely with model strength.** The strongest models are nearly harness-agnostic (GPT-5.5 Δ≈0, Opus 4.7 +0.03 on the controlled loop); the weakest collapse (Gemini 3.5 Flash drops 0.245 off its native CLI).
3. **Scaffolding alone can dominate, with the model and API held fixed.** MiniMax-M3 goes 0.329 (Qwen Code) → 0.855 (controlled loop) on the *same* DashScope/OpenRouter API — Qwen Code's multi-image tool-call serialization breaks its input. Qwen3-VL-Plus goes 0.819 → 0.890. The controlled loop is never worse than the native CLI for any model that engages.

The benchmark therefore runs frontier models on their native CLIs and open-weight models on the controlled loop — each on its stronger configuration — and reports the gap between configurations, rather than optimizing it away.

## Why image handoff is the dominant axis

The sheets are 2200×1700 / 1854×2400 px and the data is light pencil — values like `.99`, `2.21`, `.19`, scored at ±0.011 m, where a single misread decimal fails the cell. Every provider's vision encoder downsamples or tiles below the sheet's native size (Anthropic ~1568 px long edge; OpenAI 768 px detail tiles; Gemini 768 px tiles), so the third decimal and the A–E column boundaries blur *before the model reasons at all*. The photos are auxiliary — arm geometry, the trunk ID tag — and carry no measurements.

The practical consequence is that *how* a harness hands over the image — native resolution vs client downsample vs tiling, and whether it passes the sheet at full quality at all — moves scores more than tool shape or reasoning effort. The controlled harness exposes this as a first-class flag (`--image-mode {full,downsample,tiles}`, `--image-max-edge`, `--image-grid`) and records the transmitted variant and dimensions per attachment in `image_manifest`.

## Native-CLI image handling

The native coding CLIs hand images to the model in materially different ways, and that asymmetry is itself part of each model's production surface:

| CLI | passes images? | how |
|---|---|---|
| Claude Code | yes | the agent reads images from disk via `Read`, choosing which to open |
| Codex | yes | images are pre-attached up front via `-i`; the agent cannot read them from disk |
| Antigravity | yes | native Gemini vision |
| Qwen Code | partial | Gemini-CLI fork; multi-image tool-call serialization is fragile for some models |

Claude Code lets the *agent* choose which photos to open — a model that opens 3 of 13 differs from one that opens all 13 — while Codex requires every image attached up front, so there is no agent-mediated selection and the resolution is whatever Codex/OpenAI applies to attachments. Where a native CLI cannot show the sheet at all, the model scores near zero there; that is a real production-surface finding ("the deployed coding harness doesn't expose vision"), not a capability gap, and is reported as such.
