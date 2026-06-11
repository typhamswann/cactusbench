# SaguaroBench 2026 SOTA test matrix

What it takes to publish a SaguaroBench leaderboard that survives the scrutiny in
Cai's *State of Data (May 2026)*. This is the run plan: which models, which
harnesses, every scored run, and the per-axis considerations + cleanup.

The governing fact (Cai's thesis, sharpened for a multimodal task): **the harness
is the primary measurement instrument, and for SaguaroBench the dominant harness
axis is how each surface hands the model an image** — resolution, downsampling,
tiling. The sheets are 2200×1700 px and the task is reading handwriting at the
limit of legibility, where a ±0.011 m tolerance on a transcribed tip-height is
exactly where preprocessing decides pass/fail. So image handoff is a first-class
experimental variable here, not a footnote.

Our structural advantage: **scoring is deterministic, stdlib, no LLM judge.** The
measured noise floor is therefore *purely* model × harness, with zero judge
variance — cleaner than Cai's own finance work can be. Every run below exploits
that: the only thing moving between cells is the surface.

---

## 1. Models

Vision capability is a hard gate — this is a multimodal task. Text-only frontier
variants are out. Group the panel into three tiers; report tiers separately.

### Frontier closed (the headline panel)
| model | API id (verify before run) | route(s) to test | notes |
|---|---|---|---|
| Claude Opus 4.8 | `claude-opus-4-8` | Anthropic-direct, Bedrock | home harness = Claude Code |
| Claude Opus 4.7 | `claude-opus-4-7` | Anthropic-direct, Bedrock | reference (Cai shows 4.7→4.8 regressions) |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | Anthropic-direct, Bedrock | cheap reference; high determinism in Cai |
| GPT-5.5 | `gpt-5.5` | OpenAI-direct | home harness = Codex CLI |
| Gemini 3.1 Pro | `gemini-3.1-pro` | Vertex, AI Studio | home harness = Gemini CLI; watch Vertex content-filter aborts |
| Gemini 3.5 Flash | `google/gemini-3.5-flash` | Vertex, OpenRouter | cheap vision-native; already wired |

### Open-weight (the instability story — Cai §2)
| model | OpenRouter slug | notes |
|---|---|---|
| GLM-5.1 / GLM-5V | `z-ai/glm-5v-turbo` (+ GLM-5.1 when vision) | empty-response terminator expected; needs shim |
| MiniMax M2.7 | `minimax/minimax-m2.7` (verify vision) | bimodal pair_trade-style instability in Cai |
| Kimi K2.6 | `moonshotai/kimi-k2.6` | already wired |
| Qwen 3.7-VL Plus | `qwen/qwen3.7-vl-plus` (verify vision slug) | current `qwen3.7-plus` may be text-only — CHECK |
| Qwen 3.5-397B-A17B | `qwen/qwen3.5-397b-a17b` | fp8 pin; MoE |
| Gemma 4 26B-A4B | `google/gemma-4-26b-a4b-it` | cheapest; high reward/$ in pilots |

> **Cleanup before any run:** confirm every slug is (a) live on its route and
> (b) **vision-capable** at that route. In our pilots `qwen3.7-plus` and the
> Gemma slug both needed verification; a text-only route silently scores ~0 on a
> vision task and looks like a capability gap when it is a routing error.

---

## 2. Harness configurations (the columns)

Each model is scored under ≥2 configs; one must be a production-deployed harness
(Cai §1). The configs differ primarily on image handoff and tool shape.

| id | harness | image handoff | tool shape | purpose |
|---|---|---|---|---|
| **H-home** | lab's own agent (Claude Code / Codex CLI / Gemini CLI) | the lab's image-read primitive (its post-training target) | `Read`/`apply_patch`/native | "production capability" — the number a buyer actually deploys |
| **H-port** | this repo's OpenRouter host harness (Path B) | base64 data URL in user message | portable `view_image` + native FC | apples-to-apples across all models on one surface |
| **H-direct** | provider-direct API (Anthropic / OpenAI / Vertex / Bedrock) | provider default preprocessing | provider-native tools | route disclosure (Cai §3) |
| **H-harbor** | Harbor/Pier container (Path A) | agent-supplied | container `bash`+files | the canonical published evaluator |

Image-handoff sub-axis (applied within H-port, the controllable one):
- **I-native** — send the 2200×1700 sheet as-is (the harness records transmitted
  dims via `image_manifest`).
- **I-downsampled** — pre-shrink to a provider-typical cap (e.g. 1568 px long edge)
  to measure the legibility cliff.

Reasoning sub-axis: **R-low** vs **R-high** (`--reasoning low|high`).

---

## 3. The runs

Notation: a cell is (model × config × split). Score test cells; use dev for
iteration. **≥5 rollouts/cell** for CIs (Cai §6); **10** for the open-weight
models (their variance is higher). All Path-B runs pin the provider and a
reasoning budget and emit the per-rollout surface fields.

### Phase 0 — dev shake-out (public 25, free to iterate)
Purpose: confirm slugs, vision, prompt, scorer; catch terminator/route issues.
```bash
python harness/run.py --models all --tasks all --rollouts 1 \
  --reasoning none --max-turns 50 --run-id dev_shakeout
python scripts/aggregate.py runs/dev_shakeout
python scripts/failure_taxonomy.py runs/dev_shakeout
```
Pass bar: every model engaged on >90% of tasks; no `provider_mismatch`; no slug
errors. Fix routing/vision before spending on scored runs.

### Phase 1 — portable baseline, scored (H-port, test split)
Purpose: apples-to-apples panel on one surface, with CIs.
```bash
python scripts/build_tasks.py --draw-test 30 --seed cycle-1 --clean   # private test
# per model: pin its best vision backend; 5–10 rollouts
python harness/run.py --models gemini35_flash --pin-provider Google \
  --reasoning medium --rollouts 5 --tasks all --run-id t1_port \
  --registry harness/models.json   # point tasks at tasks_test/ via a registry/env tweak
# ... repeat per model with its pin ...
python scripts/aggregate.py runs/t1_port --md runs/t1_port/leaderboard.md
```
Deliverable: raw + engaged means with 95% CIs, per-difficulty, reward/$, taxonomy.

### Phase 2 — home-harness panel (H-home, the production number)
Purpose: each frontier model under the harness it was post-trained against.
- Opus 4.8 / 4.7 / Sonnet 4.6 under **Claude Code** (`Read` for images).
- GPT-5.5 under **Codex CLI**.
- Gemini 3.1 Pro / 3.5 Flash under **Gemini CLI**.
Run via Path A (Harbor task images) driven by each agent, OR each agent pointed at
a task workspace. Score with the same `grade/score.py`.
Deliverable: H-home vs H-port spread per cell (the surface-stratification table).
```bash
python scripts/stratify.py \
  --config home=runs/t2_home --config port=runs/t1_port --md runs/stratify.md
```
**Headline rule:** if >5pp of cells are scaffolding-sensitive, declare which config
the headline is calibrated against (recommend H-home for the "deployable capability"
headline, H-port for the "model capability, controlled" headline — publish both).

### Phase 3 — route disclosure (H-direct vs H-port)
Purpose: show route changes the number (Cai §3).
- Anthropic-direct vs Bedrock for Opus 4.8.
- AI Studio vs Vertex for Gemini 3.1 Pro (record Vertex content-filter abort rate).
- OpenRouter single-pinned-backend vs OpenRouter unpinned (load-balanced) for one
  open model — demonstrates the fragmentation we already observed (qwen35_397b
  served by 4 backends in one run).

### Phase 4 — image-resolution sensitivity (I-native vs I-downsampled)
Purpose: quantify the legibility cliff — the multimodal noise axis unique to us.
```bash
# same model/route, two image handoffs
python harness/run.py --models <m> --pin-provider <b> --rollouts 5 --run-id t4_native     # I-native
# I-downsampled: add a pre-shrink step in setup_workspace (documented), run again
python scripts/stratify.py --config native=runs/t4_native --config small=runs/t4_small
```
Expected: hard saguaros (faint pencil, arm-4 geometry) move most.

### Phase 5 — reasoning-budget sensitivity (R-low vs R-high)
Purpose: HAL found higher effort hurts ~58% of the time; for transcribe-then-
reconcile, high budget can induce over-correction.
```bash
python harness/run.py --models <m> --reasoning low  --rollouts 5 --run-id t5_low
python harness/run.py --models <m> --reasoning high --rollouts 5 --run-id t5_high
python scripts/stratify.py --config low=runs/t5_low --config high=runs/t5_high
```

### Phase 6 — synthesis
- `aggregate.py` on the chosen headline config → leaderboard with CIs, reward/$.
- `stratify.py` across H-home/H-port/route/resolution/reasoning → the spread table.
- `failure_taxonomy.py` per model → the failure-class table (and, once `literal`
  values land, the over/under-correction split — the marquee finding).
- Contamination date refreshed ([CONTAMINATION.md](CONTAMINATION.md)).

---

## 4. Per-axis considerations & cleanup

### Image processing
- **Caps & tiling differ by provider.** Anthropic ~1568 px long-edge; OpenAI
  low/high-detail 768 px tiles; Gemini 768 px tiles. Our 2200×1700 sheets exceed
  all of them → each surface downsamples differently. `image_manifest` records the
  bytes/dims we *send*; the provider's internal resize is not observable, so test
  I-native vs I-downsampled to bound it.
- **Encoding:** sheets are PNG (lossless — keep), photos JPEG. `scrub.py` strips
  metadata without re-encoding pixels (verified: images still decode, dims intact).
  Do **not** re-compress sheets; lossy artifacts hurt faint-pencil legibility.
- **Consider a crop/zoom affordance.** A model that can request a higher-DPI crop
  of a cell would change the ceiling. If added, it becomes a declared harness knob
  and must be held constant within a config.
- **Cleanup:** verify every shipped asset passes `assert_clean`; confirm sheet DPI
  is uniform across years (a year-correlated resolution would be a shortcut).

### Tool calling
- **Home tool shape ≠ portable.** Opus expects `str_replace`/`Read`, GPT expects
  `apply_patch`, Gemini its JSON tool schema. H-port's `view_image`/`write_submission`
  is a *different* surface — that gap is exactly what H-home vs H-port measures.
  Don't conflate "model can't" with "model wasn't given its home tools."
- **Empty-response terminator (Cai §2):** open-weight models emit `content=""` +
  no tool call as a clean-stop; the shim retries 4× and tags `terminator_shimmed`.
  Always publish raw **and** engaged-subset means.
- **Cleanup:** standardize the submission contract across harnesses (a JSON list at
  a known path) so the scorer is identical everywhere; confirm each harness's
  image-read actually transmits the full image (not a thumbnail).

### Provider routing
- **Pin for scored runs** (`--pin-provider`); `provider_mismatch` flags any
  fallback. Publish `served_providers` per model.
- **Vertex content-filter:** record abort rate (Cai saw ~33% on PE rollouts);
  unlikely on cactus measurements but disclose if non-zero. AI-Studio-direct is a
  different surface — test both for Gemini.
- **Cleanup:** never publish an OpenRouter unpinned number as "the model" — it is a
  load-balanced average over backends with different preprocessing.

### Reasoning budget
- **Pin and report** (`--reasoning`); run R-low vs R-high as a sensitivity pass.
- Watch for over-correction at high budget (the Opus-4.8 pattern: "fixes" a value
  that was already correct) — the failure taxonomy's `qaqc_over_correction` class
  is built to catch it once literal values exist.

### Statistical power
- **≥5 rollouts/cell** (10 for open-weight); report **per-cell and per-task 95%
  bootstrap CIs**. Cell-level accuracy is reported but flagged as **correlated**
  within a saguaro — never claimed as independent n.
- **Per-difficulty with n.** The public dev set is degenerate at "easy" (1 task,
  2 rows); the pool-drawn test set rebalances via arm-count-derived difficulty.
- **Dev vs test discipline:** tune on the public 25; score on the private pool draw
  ([REFRESH.md](REFRESH.md)). Rotate the seed each cycle.

### Determinism / temperature
- Default `temperature=0.6`. For a determinism diagnostic (Cai's cross-rollout
  commitment metric), also run `temperature=0` where the provider honors it (note:
  reasoning models often ignore temp). Report cross-rollout pass-consistency per
  criterion to surface "noisy middle" models the way Cai does for Opus 4.8.

### No judge — but still validate
- There is no LLM judge, so no same-family bias check is needed. Instead validate
  the **scorer**: the perfect-submission test (`reward == 1.0` from truth) is the
  determinism floor; run it after every regeneration.

---

## 5. Minimal credible publication (if budget-limited)

If a full matrix is too costly, the smallest defensible result is:
1. **H-port, pinned, 5 rollouts, R-medium**, on a **private pool-drawn test set**,
   with raw + engaged CIs (Phase 1).
2. **One H-home column** for the three frontier models (Phase 2) → a 2-config
   stratification table.
3. Reward/$ Pareto + failure taxonomy + contamination date.

That is already past the bar Cai says most 2026 benchmarks fail to clear:
multi-harness spread, real rollout CIs, route disclosure, a refresh mechanism, and
a realism story grounded in a real curator's real workflow.
