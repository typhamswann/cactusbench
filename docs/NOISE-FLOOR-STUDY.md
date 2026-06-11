# Noise-floor settings study (3 tasks)

Goal: choose the production-run settings per model by sweeping the knobs that add
measurement noise, on a small, fixed 3-task probe — *before* committing to the
expensive scored Phase 1. This is exactly Cai's discipline: pick (and declare) the
measurement surface before publishing numbers.

## Results (final)

Cross-harness × cross-reasoning, tasks 41B-04 / 04A / 13, 5 seeds/cell. Score =
per-cell accuracy reward (field tolerances, no LLM judge).

| Model | native low | native def | native high | my harness |
|---|---|---|---|---|
| **Frontier** — native = production CLI; my harness = first-party API | | | | |
| opus_4_8 (Claude Code → Bedrock) | 0.906 | 0.981 | **0.982** | 0.900 |
| opus_4_7 (Claude Code → Bedrock) | 0.865 | 0.964 | 0.941 | **0.994** |
| gpt_5_5 (Codex → OpenAI) | 0.975 | **0.994** | 0.993 | 0.986 |
| gemini_3_1_pro (Antigravity → Google AI) | **0.957** | — | 0.887 | 0.930 |
| gemini35_flash (Antigravity → Google AI) | **0.885** | — | 0.862 | 0.640 |
| **Open-source** — native = Qwen Code; my harness = OpenRouter/DashScope | | | | |
| qwen3_vl_plus | — | 0.819 | — | **0.890** † |
| minimax_m3 | — | 0.329 | — | **0.855** * |

† both sides DashScope · \* both sides OpenRouter — so the OS rows isolate scaffolding
alone (same model, same API). Gemini has no native "default" tier (Antigravity bakes
reasoning into the model name).

**Method (one line each):**
- **Routing:** frontier → first-party APIs (Claude→AWS Bedrock w/ explicit `cache_control`;
  GPT→OpenAI; Gemini→Google AI). OS → OpenRouter, except proprietary `qwen3-vl-plus`→DashScope.
  OpenRouter is OS-only. Code: `harness/providers.py`.
- **Caching on** everywhere (Bedrock explicit, OpenAI/Gemini/DashScope server-side).
- **Seeds:** 5 rollouts/task. **Reasoning:** native CLIs swept low/def/high; my harness single (default).
- **Recording:** per-cell JSONL transcripts (every turn, tool call, timing, tokens, cost) under `runs/<run>/transcripts/`.
- **Cut from table:** sonnet_4_6 (runs incomplete — 30-min process cap vs 23-min cells); glm5v_turbo, qwen37_plus,
  qwen35_397b, gemma4_26b, kimi_k26 (hang/bail on Qwen Code → no native OS counterpart).

**Findings:**
1. **Reasoning is non-monotonic and vendor-specific:** gpt/opus-4.8 climb with effort; opus-4.7 peaks at default;
   Gemini *inverts* (worse at high) on this transcription task.
2. **Harness sensitivity scales inversely with model strength:** strong models are harness-agnostic
   (gpt Δ≈0, opus-4.7 +0.03); the weakest collapses (gemini35_flash −0.245).
3. **Same model, same API, scaffolding alone:** minimax_m3 0.329 (Qwen Code) → 0.855 (my harness) — Qwen Code's
   multi-image tool-call serialization breaks MiniMax's API. qwen3_vl_plus 0.819 → 0.890. The controlled harness
   is never worse than the native CLI for any engaging model.

**Data:** `runs/frontier_native/` (frontier), `runs/qwenvl_myharness/` + `runs/nf_port/` (OS my-harness),
`runs/nf_qwencode/` (OS native), `runs/nf_low|nf_home|nf_high/` (frontier native reasoning sweep).

---

## The guardrail (read first — it shapes everything)

"Best performance for each model" has a trap Cai names directly: if you pick the
flattering harness/reasoning per model and then rank models against each other,
you've benchmark-maxxed, not measured. So the study must produce **two distinct
artifacts**, and never conflate them:

- **(A) Production-capability setting** — *per model*, its own best home harness +
  reasoning. This is "what a buyer who deploys this model in its native agent gets."
  Best-per-model is legitimate **here**, because each model is judged on its own
  surface. This is what your question is really asking for.
- **(B) Controlled-capability surface** — **one identical harness, image handoff,
  reasoning policy, and route for ALL models**. This is the apples-to-apples
  scientific ranking. The cross-model leaderboard MUST use this.

Publish both. The **gap between them, per model, is the headline finding** (the
noise floor / surface sensitivity), not a number to be optimized away.

## The reframe: image handoff dominates the knobs you named

You named harness + reasoning. Looking at the assets, a third knob almost certainly
dominates both for this task:

- Sheets are **2200×1700 / 1854×2400 px**; the data is **light pencil**, values like
  `.99` / `2.21` / `.19`, scored at **±0.011 m** — a single misread decimal fails the
  cell. Provider vision encoders downsample/tile (Anthropic ~1568 px long edge;
  OpenAI 768 px detail tiles; Gemini 768 px tiles), all **below** the sheet's native
  size. So the third decimal and the A/B/C/D/E column boundaries blur *before the
  model ever reasons*.
- Photos are auxiliary (arm geometry/count + the trunk ID tag), lower-res, sun-flared
  — they don't carry measurements.

**Implication:** the image-handoff knob (native-res vs client-downsample vs
crop/tile, and whether the harness even passes the image at full quality) will move
scores more than tool-shape or reasoning. Treat it as a first-class axis, not a
footnote. A model can look weak purely because its harness handed it a 768-px mush of
the table.

## The 3 probe tasks (fixed, headline-scored)

Chosen to span the axes that interact with noise — photo load, note/free-text load,
table density, difficulty:

| task | diff | rows | photos | notes | why it's in the probe |
|---|---|---|---|---|---|
| **41B-04A** | medium | 6 | **0** | 0 | pure sheet-reading — cleanest isolation of the downsampling/legibility effect, no photo confound |
| **41B-13** | medium | 15 | 9 | **5** | mixed load: dense table + free-text note transcription + photos; exercises every path |
| **41B-04** | **hard** | 8 | **13** | 0 | max image-handoff stress (most photos) + hardest matching; exposes image-window eliding + many-image cost |

(Optional cheap floor: 41B-09 — easy, 2 rows, 0 photos — as a sanity check that a
config isn't broken. Too small to discriminate, so not a primary probe.)

## The knob matrix

Sweep these per model; hold everything else fixed and declared. Ordered by expected
impact for THIS task.

| # | knob | levels to test | why (Cai / task) |
|---|---|---|---|
| 1 | **image handoff** | `full` · `downsample` (cap 768 / 1568 px) · `tiles` (2×2 full-res tiles — generic high-res recovery, no per-sheet crop box needed) | the dominant axis; decides whether decimals survive to the encoder |
| 2 | **harness / tool-shape** | your OpenRouter harness vs the model's native home agent | tool-shape post-training; native = production surface |
| 3 | **reasoning level** | none · low · medium · high | HAL: higher effort hurt 58% of the time; watch over-correction "fixing" correct values |
| 4 | **provider route** | Anthropic-direct vs Bedrock · AI-Studio vs Vertex · OpenRouter pinned-backend | different server-side resize + content filters; pin for scored runs |
| 5 | **temperature** | 0 vs 0.6 | transcription wants low variance; but measure residual cross-rollout spread |
| 6 | **image-window / sheet pinning** | elide-beyond-6 (current) vs **always-pin the 2 sheets** | a 13-photo task can elide the sheet before the model writes — it then answers from memory |
| 7 | max_turns | 20 vs 50 | more turns = more re-checking but more over-correction; lower priority |

Knobs 1, 6, 7 are *your harness's* knobs (controllable + loggable). Knobs 2, 4 are
surface choices. Knob 3, 5 are model/API params.

## Native-harness → model map, and the vision caveat

| native harness | models | image primitive | ⚠ verify |
|---|---|---|---|
| Claude Code | Opus 4.8 / 4.7, Sonnet 4.6 | `Read` (renders + downsamples) | pass — Read shows images |
| Codex CLI | GPT-5.5 | image-aware read (detail param) | pass |
| Antigravity | Gemini 3.1 Pro / 3.5 Flash | Gemini native vision + tiling | pass |
| Qwen Code | Qwen 3.7-plus, Qwen 3.5-397B | ? | **VERIFY** — Gemini-CLI fork may be text-only even though the model is vision-capable |
| GLM Code | GLM-5V / GLM-5.1 | ? | **VERIFY** — coding CLI may not pass images |
| (none) | MiniMax M3, Kimi K2.6 | — | no native coding agent; their reference IS your harness |

**Critical:** several native coding agents may not pass images to the model at all,
even when the model is vision-capable. If a native harness can't show the sheet, the
model scores ~0 there — that is a **real production-surface finding** ("the deployed
coding harness doesn't expose vision"), NOT a capability gap. Record it as such; do
not let it contaminate the controlled-capability number. `harness/home_driver.py`
already drives these CLIs; add a one-task image-sanity check per agent first.

## Selection methodology (so the pick is signal, not luck)

- **≥5 rollouts per (model, config, task).** Selecting a config on n=1 is choosing
  noise. 3 tasks × 5 rollouts = 15 points/config — enough to rank configs for a
  model, **not** enough for a publishable headline (that's Phase 1 on the test draw).
- **Selection metric = mean reward AND cross-rollout spread.** Prefer a config that is
  high-mean *and* low-variance. A high-but-noisy config is worse for a benchmark than
  a slightly lower stable one. Because scoring is deterministic with **no LLM judge**,
  this spread is pure model×harness — your cleanest possible signal; lean on it.
- **Report the per-model spread across all configs** (the noise floor). The width is
  the deliverable.
- **Sclar et al. caution:** prompt/format wording alone caused up to 76-pt swings.
  Hold the wrapper prompt byte-identical across configs; treat wording as out of scope
  for this sweep (fix it once, declare it).

## Concrete run plan

Per model, the minimal informative sweep on the 3 tasks, 5 rollouts each:

1. **Controlled baseline (B):** your harness, image=full, reasoning=medium, temp=0,
   pinned route. (every model — this is the apples-to-apples surface)
2. **Reasoning sweep:** B with reasoning ∈ {none, low, high}.
3. **Image sweep:** B with image ∈ {downsample-1568, table-crop-2×}.
4. **Sheet-pinning:** B with always-pin-sheets on (esp. for 41B-04, 13 photos).
5. **Native harness (A):** model's home agent, its default reasoning, image sanity
   first.

```bash
# controlled baseline + reasoning sweep (your harness), 3 tasks, 5 rollouts
for R in none low medium high; do
  python harness/run.py --models <m> --tasks 41B-04A,41B-13,41B-04 \
    --rollouts 5 --reasoning $R --temperature 0 --pin-provider <backend> \
    --run-id nf_<m>_r$R
done
# native harness (production surface)
python harness/home_driver.py --agent <claude_code|codex_cli|antigravity|qwen_code|glm_code> \
    --tasks 41B-04A,41B-13,41B-04 --run-id nf_<m>_home
# compare every config for this model
python scripts/stratify.py --config base=runs/nf_<m>_rmedium \
    --config rlow=runs/nf_<m>_rlow --config rhigh=runs/nf_<m>_rhigh \
    --config home=runs/nf_<m>_home --md runs/nf_<m>_spread.md
```

(Image-handoff and temperature and sheet-pinning need small harness flags that don't
exist yet — see below.)

## Harness changes — DONE (v0.5-noisefloor)

All four knobs are landed and tested (Pillow-backed):

1. ✅ **`--image-mode {full,downsample,tiles}`** + `--image-max-edge` + `--image-grid`
   (`run.py`/`tools.py`). `downsample` caps the long edge; `tiles` splits into an
   N×N grid of full-res tiles (each downsampled separately by the provider → ~N×
   effective resolution on the table, no per-sheet crop box needed). The transmitted
   variant + dims are recorded per attachment in `image_manifest`.
2. ✅ **`--temperature`** flag (use 0 for lowest-variance scored runs).
3. ✅ **`--pin-sheets`** — datasheets are never elided from context; only photos are
   windowed.
4. ✅ **`home_driver.py --image-probe`** — one-task vision-exposure check.

### Native-CLI verification results (run 2026-06)

| CLI | installed? | passes images? | how |
|---|---|---|---|
| **Claude Code** | ✅ | **yes** (probe: `saguaro=13b`) | agent reads from disk via `Read` |
| **Codex** | ✅ | **yes** (probe: `saguaro=13A`) | images **pre-attached via `-i`** — agent canNOT read them from disk |
| Gemini CLI / Antigravity | not installed | verify on install | native vision |
| Qwen Code | not installed | **verify** | Gemini-CLI fork — may be text-only |
| GLM Code | not installed | **verify** | may be text-only |

**Structural finding (a real cross-harness difference, not a footnote):** Claude Code
and Codex hand images to the model in fundamentally different ways. Claude Code lets
the *agent choose* which images to open (so image-selection is agent-mediated — a
model that opens 3 of 13 photos differs from one that opens all 13). Codex requires
**all images pre-attached up front via `-i`** (greedy flag → the prompt must precede
it; also needs `--skip-git-repo-check`, `--sandbox workspace-write`, and a closed
stdin). So on Codex there is no agent-mediated image selection, and the resolution
handed to the model is whatever Codex/OpenAI does with attached images. This asymmetry
is itself part of the H-home surface and must be disclosed per model.

## Cost

3 tasks (not 25) makes this cheap relative to a full sweep. Rough: ~5 configs ×
3 tasks × 5 rollouts = 75 rollouts/model. Open models ≪ $5 each; frontier ~$5–20
each. Whole study ≈ **$100–150**, and it's what lets the ~$1.5–2k Phase 1 spend buy
defensible numbers instead of noise.
