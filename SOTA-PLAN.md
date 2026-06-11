# SaguaroBench → SOTA Plan

> **STATUS (v0.4.0 — implemented).** All code/doc items below are done and verified
> (perfect-submission still scores 1.0; harness loop tested end-to-end with a mocked
> client; pool draw + scrubber + manifest all pass). The **only** remaining item is
> data, not code: the QA/QC `literal`-value curator pass (§5b) — the taxonomy code
> is built and degrades to `n/a` until those values land. Then run the matrix in
> [docs/TEST-MATRIX.md](docs/TEST-MATRIX.md). Item-by-item:
> - **P0** 2a self-leak ✅ · 2b 41B-22 flagged out of headline ✅ · 2c contamination
>   check + doc ✅ · 2d enforced metadata strip ✅
> - **P1 harness** 3a per-rollout provider pin/disclosure ✅ · 3b terminator shim +
>   raw/engaged ✅ · 3c reasoning pin ✅ · 3d transmitted-image manifest ✅ ·
>   3e `stratify.py` ✅ · 3f MANIFEST.md + `max_turns=50` everywhere ✅
> - **P1 power** 4a `--rollouts` + bootstrap CIs ✅ · 4b per-difficulty w/ n ✅ ·
>   4c held-back-pool draw + REFRESH.md ✅
> - **P2** 5a note conditioning + Jaccard off headline ✅ · 5b QA/QC taxonomy code ✅
>   (data-gated) · 6a `failure_taxonomy.py` ✅ · 6b reward/$ Pareto ✅ · 6c rotation ✅ ·
>   docs hygiene ✅
> - **Plus** the 2026 model/harness run matrix ([docs/TEST-MATRIX.md](docs/TEST-MATRIX.md)).

---


A prioritized engineering plan to take SaguaroBench from "good" to a benchmark
that survives the scrutiny Sean Cai's *State of Data (May 2026)* lays out. Each
item ties to a specific Cai/guidance point, names the files to touch, and states
an acceptance bar.

Legend: **P0** = integrity, must land before any number is published ·
**P1** = the core "noise-floor" story (our differentiator) + statistical power ·
**P2** = service layer / citability.

---

## 0. What is already SOTA-grade — protect, don't redo

These are real strengths. Build on them; the plan below is additive.

- **Deterministic, stdlib, no-LLM-in-the-loop scorer** (`scripts/lib/score.py`).
  This is the *credibility anchor*. Every failure mode in Cai's finance deep-dive
  routes through the judge (same-family bias, replay determinism, "is the judge
  just bad"). We have zero judge variance, so our noise floor is purely
  model × harness. **Lean into this hard in the methods section** — it is the one
  axis where we are strictly cleaner than Cai's own work can be.
- **EXIF / metadata already clean.** Verified: 0/209 photos carry EXIF/XMP,
  0/50 PNG sheets carry text/time chunks. Guidance point 8's biggest worry is
  already closed — but it is currently *accidental* (re-encode side effect), not
  *enforced*. See §2d.
- **`max_tokens` false-zero already fixed** (`openrouter.py:32`) — reasoning
  models are no longer truncated mid-thought. Keep it.
- **Cost + served-provider already captured** (`openrouter.py`), **resumable
  incremental writes**, **opaque filenames**, **hand-redaction** of canonical
  renumbering. All good foundations.

---

## P0 — Integrity fixes (block publication until done)

### 2a. Kill the prompt self-leak (NEW — not in guidance doc)
**Cai:** contamination/shortcuts · **Severity:** high.
`scripts/lib/brief.py:80` hardcodes the instruction's "Example row" as
`{"saguaro_id":"41B-13","year":2023,"arm":"1","direction":360,"A":1.89,...}`.
That is **41B-13's real 2023 arm-1 truth row, verbatim** (confirmed against
`tasks/41B-13/grade/truth.json`). Consequences:
- Task **41B-13** is handed its own `saguaro_id` *and* a full 8-cell row for free.
- **Every** task is told a real saguaro id (`41B-13`) exists, leaking the id space
  and the exact numeric formatting/precision of real answers.

**Fix:** replace with a synthetic example using a saguaro id that does not exist
in plot 41B (e.g. `"99Z-00"`) and obviously-fake values. Regenerate all 25
`instruction.md` via `scripts/build_tasks.py`. **Acceptance:** no real
`saguaro_id` or real truth value appears in any `instruction.md`.

### 2b. Redaction-style year-invariance audit
**Guidance 8 · Cai:** shortcut from metadata.
`41B-22`'s 2026 sheet is **auto-redacted** while every other sheet is
hand-redacted (`task.toml: redaction_status_2026 = "auto"`). If the *visual
signature* of redaction differs systematically between years, a model can infer
year from redaction artifacts instead of reading the date header — the exact
shortcut opaque filenames + hand-redaction were meant to close.
**Fix:** (1) hand-redact 41B-22's 2026 sheet to match, or drop the saguaro from
the scored set; (2) curator does a visual pass confirming 2023 vs 2026 redaction
style is indistinguishable across the set. **Acceptance:** a documented audit
note in README; zero saguaros with mixed redaction provenance in the scored set.

### 2c. Provenance / n-gram contamination check
**Guidance 8 · Cai:** "we verified the curated table is not web-present."
This is real Saguaro National Park plot-41B survey data. If the cleaned table or
underlying survey is reachable by a crawler, our test answers are in pretraining
corpora.
**Fix:** (1) web-search the distinctive value tuples + any survey identifiers;
(2) document the check ("we verified the curated 41B table is not web-present as
of <date>") in README; (3) add a short `docs/CONTAMINATION.md` recording method
+ date so it can be re-run each release. **Acceptance:** documented negative
result, or — if positive — those rows are excluded/replaced.

### 2d. Make the clean-metadata property *enforced*, not accidental
**Guidance 8.**
Add an EXIF/PNG-chunk strip + assert step to `scripts/build_tasks.py` so every
regeneration guarantees stripped assets, and a CI/`tests` check that fails if any
shipped asset carries EXIF/XMP/tEXt/tIME. **Acceptance:** build refuses to emit
an asset with embedded metadata.

---

## P1 — The harness noise-floor story (our central differentiator)

Cai's thesis: with reasoning-budget tuning, tool-shape post-training,
content-policy filtering, and provider-route fragmentation all stacking, **the
harness is now the primary measurement instrument**, and the noise floor is
approaching the signal. For a multimodal task this is *worse* than for his text
tasks, because the dominant axis is **how each harness hands the model an image**
(resolution, downsampling, tiling) — and we are reading handwriting at the limit
of legibility, where a ±0.011 m tolerance on a transcribed tip-height is exactly
where preprocessing decides pass/fail.

### 3a. Provider-route disclosure + pin, per rollout (evidence already in our runs)
**Cai 3 · Guidance 3.**
Our own runs already show the fragmentation Cai warns about: in one run
`qwen35_397b` was served by **AtlasCloud, Chutes, DeepInfra, and Parasail**;
`gemini35_flash` by **Google and Google AI Studio**. We currently record only the
*union* of providers at the model level (`served_providers`), so we cannot say
which backend (and thus which image preprocessing) served any given cell.
**Fix:**
- Record `served_provider` **per rollout** in each result record (the field is
  available on every `data["provider"]` response in `openrouter.py:112`).
- Add a `--pin-provider` path that uses OpenRouter `provider.order` +
  `allow_fallbacks:false` so a scored run is single-backend, and **fail loudly**
  if a different backend answers.
- Publish the endpoint per model (Anthropic-direct vs Bedrock vs Vertex vs
  OpenRouter-which-backend) in the run config + leaderboard.
**Acceptance:** every published cell carries the exact backend that served it;
scored runs are single-backend or flagged.

### 3b. Terminator shim + raw-vs-engaged-subset dual reporting
**Cai 2 (highest-leverage item in the essay) · Guidance 2.**
This already hits us: in `runs/curation_par`, `gemma4_26b` stopped with
`no_tool_call_x5` on **7/7** tasks and `kimi_k26` on 1/1 — the empty-response
terminator (`content="" , tool_calls=None`) scoring an empty submission as zero.
The current generic nudge loop partially masks it but does not isolate or report
it.
**Fix:**
- In `run.py`, detect the empty-response terminator explicitly (FC reply with no
  `tool_calls` and empty `content`, or `finish_reason` indicating a clean stop
  with no submission) and apply an explicit **retry shim** (Cai used 4 retries
  before fallback). Tag the rollout `terminator_shimmed: true`.
- **Report two means for every model: `raw` and `engaged-subset`** (engaged =
  rollouts that actually produced a submission). Never publish only one.
- **Declare the shim as part of the published harness contract** (retry count,
  fallback) — the shim is itself an experimental variable a re-runner must match.
**Acceptance:** for every open model the leaderboard shows raw + engaged means
and the per-model count of shimmed rollouts.

### 3c. Pin and report reasoning budget (+ 2-budget sensitivity)
**Cai 5 · Guidance 5.**
We send a fixed `temperature=0.6` and **no reasoning-effort control**
(`openrouter.py`). HAL found higher reasoning effort *hurt* accuracy in 21/36
runs; for a transcribe-then-reconcile task, more reasoning can induce exactly the
Opus-4.8-style over-correction ("fixes" a measurement that was already right).
**Fix:** add a `reasoning` parameter to the payload, pin it per scored run,
record it in config, and run a **low vs high** sensitivity pass on at least one
model. **Acceptance:** reasoning-effort recorded per cell; one published
sensitivity table.

### 3d. Log the image actually transmitted (the multimodal noise axis)
**Guidance 1 (the part unique to us).**
We log `images_viewed` (which assets the agent opened) but **not what the model
actually received**: byte size, pixel dimensions, re-encode/quantization, tiling.
That is the variable that decides handwriting legibility.
**Fix:** in `tools.py:view_image` / `run.py`, record per attached image:
`bytes_sent`, `width`, `height`, `mime`, and (where the provider exposes it) any
downsample/tile note. Also record **how many assets were actually read** per cell
— image selection is agent- *and* harness-mediated (a model that opens 3 of 13
photos matches arms differently than one that opens all 13, and how cheap it is
to open many is a harness property).
**Acceptance:** every cell record carries the transmitted-image manifest +
assets-read count.

### 3e. Surface-stratification table (the headline rigor artifact)
**Cai 1 · Guidance 1.**
Run every scored model under **≥2 scaffolding configurations**, one of which is a
production-deployed harness. Concretely:
- Config 1: Path A (Harbor/Pier container) with a production agent (e.g.
  Claude Code's `Read`).
- Config 2: Path B (OpenRouter host harness, this repo).
- Optionally a third axis: high-res vs downsampled image handoff.
Report **spread per cell**; **spread > 5 pp flags the dataset as
scaffolding-sensitive** and we must declare which config the headline is
calibrated against.
**Fix:** a `scripts/stratify.py` that joins per-cell results across configs and
emits the spread table. **Acceptance:** published per-cell spread across ≥2
configs; headline config declared.

### 3f. Sandbox manifest + single source of truth for `max_turns`
**Cai 4 · Guidance 4.**
A buyer cannot re-run us without the manifest, and our turn cap is currently
**inconsistent** (README says 14/30, real runs used **50**, `task.toml`
agent timeout is 1800 s). Publish one manifest per task image:
`docker_image_digest, network_egress_policy (currently allow_internet=false —
state it), tool_approval_policy, isolation_granularity, max_turns_per_rollout
(PIN it — pick one), observation_truncation_policy` (we truncate text reads at
50k chars in `tools.py:92` and elide images past an `--image-window` of 6 — both
are load-bearing and must be declared).
**Acceptance:** `docs/MANIFEST.md` + manifest block in each `task.toml`; all docs
agree on one `max_turns`.

---

## P1 — Statistical power & reporting

### 4a. Multi-rollout + confidence intervals
**Cai 6 · Guidance 6.**
Every real run is **n=1 per (model, task)** — indefensible no matter how clean the
scorer. The published test set is **4 saguaros / 24 rows / 192 cells**.
**Fix:**
- Add `--rollouts N` to `run.py`; run K≥5 per cell.
- Report **per-cell and per-task bootstrap CIs** (stdlib resampling; no deps).
- Report at the **cell level (192–1896 cells)** for real n, but state explicitly
  that cells within a saguaro are **correlated** (don't claim 1896 independent
  samples).
**Acceptance:** no point-estimate published without a CI; correlation caveat in
methods.

### 4b. Fix the degenerate difficulty buckets
**Guidance 6.**
Distribution is **1 easy / 17 medium / 7 hard**, and the single "easy" task has
only **2 rows** — a per-difficulty "easy" headline is meaningless, and 68% medium
hides everything under one mean.
**Fix:** either re-bucket into a defensible distribution drawn from the full pool,
or drop the easy bucket and report medium/hard separately with CIs.
**Acceptance:** every reported difficulty bucket has ≥ a stated minimum rows and
its own CI.

### 4c. Dev/test split from the 217-saguaro pool + rotation
**Guidance 6 + 10 · Cai 4th pillar (refresh).**
Hold the public 25 as a **dev set**; draw the **scored test set fresh from the
held-back 217-saguaro pool each cycle**, keeping test truth private. This is the
single design choice that defeats contamination over time and is the difference
between credible-for-one-release and credible-for-twelve-months.
**Fix:** `scripts/build_tasks.py` already regenerates deterministically from the
full source env with a seeded shuffle — extend it with a `--split test --seed
<cycle>` draw from the 217 pool and a private-truth packaging mode.
**Acceptance:** documented rotation policy; one test cycle drawn from the pool.

---

## P2 — Scoring refinements

### 5a. Note field: condition on non-empty, retire Jaccard
**Guidance 9.**
**94% of truth notes are empty** (223/237; only 14 non-empty, 9 already
list-of-acceptable). So `per_field_accuracy["note"]` today is ~"did the model
blank the field" — a model that always emits `""` banks 94% on notes for free.
The Jaccard ≥0.5 rule is also gameable (pad with common tokens) and inflatable
(empty=empty scores free).
**Fix:**
- Report **note accuracy conditioned on non-empty truth notes** separately (the
  14 rows that actually test transcription).
- Replace Jaccard with the **list-of-acceptable** mechanism wherever possible
  (it's the right design) so no gameable fuzzy rule reaches a headline; keep
  Jaccard only as a logged diagnostic, not in `cell_accuracy_reward`.
**Acceptance:** headline note metric is computed on non-empty-truth rows;
`cell_accuracy_reward` carries no Jaccard.

### 5b. QA/QC over- vs under-correction — the most citable feature (GATED)
**Cai 7 · Guidance 7.** This is our equivalent of Cai's BoP-averaging
contradiction penalty — "smarter models score worse because they overthink the
recorder's intent," the kind of finding that gets a benchmark cited.
**Blocker (found during this audit):** the source dataset
(`saguaro_arm_matching_env/data/curation_dataset_v2.json`) stores **only the
curated value** — there is no `literal` (raw sheet) value and no `qaqc` flag.
Without the literal sheet transcription we cannot distinguish:
- **over-correction**: model changed a value the sheet recorded correctly, and
- **under-correction**: model faithfully transcribed a genuine recorder slip the
  curator had corrected, from
- ordinary transcription error.

**Fix (data + code):**
1. **Data (curator pass, gating):** for every row where the curated value
   diverges from the literal sheet, record both `literal` and `curated` and set
   `qaqc: true`. Likely a small set (the 14 note overrides + the numeric
   corrections behind the QA/QC mandate).
2. **Code:** extend `truth.json` schema with `literal`; add an analysis pass that
   labels each scored cell as `correct / transcription-error / over-correction
   (matched literal, missed curated where curated≠literal... or *changed* a
   correct literal) / under-correction (matched curated-should-be but left the
   slip)`.
**Acceptance:** a published over/under-correction breakdown per model. **If the
literal data cannot be sourced, descope to a documented note in README** rather
than shipping a half-measure.

---

## P2 — Service layer (what makes a benchmark more than a leaderboard)

### 6a. Domain-specific failure-class taxonomy
**Cai 7 · Guidance 7.**
Aggregate-mean-only is the thing Cai mocks; the per-model failure-class breakdown
is what makes a benchmark a *service*. For every failed cell, label it (mostly
deterministically from the scorer + the opaque maps in `truth.json`):
`handwriting-transcription error / cross-year arm-matching error / canonical-
renumbering error / QA-QC over-correction / QA-QC under-correction / hallucinated
row / schema violation / image-not-read (cross-ref images_viewed) / year-
misassignment`.
**Fix:** `scripts/failure_taxonomy.py` consuming results + `truth.json`
(`_opaque_sheet_map`/`_opaque_photo_map` give year ground truth for
year-misassignment and image-not-read labels).
**Acceptance:** per-model failure-class table on the leaderboard.

### 6b. Reward-per-dollar and cost/latency Pareto
**Cai 11 · Guidance 11.**
We already capture `cost_usd` and `wall_time_sec` — we just don't report the
frontier. The signal is already striking in our runs: `gemini35_flash` 0.754 at
**$21.03** vs `kimi_k26` 0.758 at **$4.46** for the same 25 tasks. Curation is a
high-volume, cost-sensitive real workflow, so "efficient model selection on the
performance/cost/latency curve" is the honest framing for our domain.
**Fix:** leaderboard columns for reward, reward-per-dollar, median latency, and a
Pareto plot. **Acceptance:** every leaderboard row carries cost + latency, with a
Pareto view.

### 6c. Refresh mechanism (operationalize the rotation from 4c)
**Cai 4th pillar.** Make 4c a standing policy: public dev set frozen, scored test
set re-drawn each cycle from the 217 pool, test truth private. Document the cycle
cadence. **Acceptance:** `docs/REFRESH.md` with the policy and the first rotation.

---

## P2 — Docs hygiene (cheap, high trust signal)

- `harness/README.md` result-format example still shows the **old matching-task**
  fields (`exact_mapping_reward`, `arm_pair_f1`) — stale since the curation pivot.
  Update to `cell_accuracy_reward` / `row_f1` / `per_field_accuracy`.
- Reconcile `max_turns` across README, harness README, and `task.toml` (see 3f).
- Add a "Reproducibility contract" section pointing at MANIFEST.md, the provider
  pin, the shim spec, the reasoning-budget pin, and the contamination check.

---

## Suggested sequencing

1. **P0 integrity** (2a–2d) — a day or two; unblocks any honest number.
2. **P1 harness** (3a–3f) — the differentiator. 3a/3b/3d/3f are mostly logging +
   small `run.py`/`openrouter.py` changes; 3e is the cross-config harness.
3. **P1 power** (4a–4c) — multi-rollout + CIs + split policy.
4. **P2 scoring** (5a now; 5b gated on the curator literal-value pass).
5. **P2 service layer** (6a–6c) + docs.

## Single highest-leverage next step
Land **2a (self-leak)** + **3a/3b (per-rollout provider + terminator shim with
raw/engaged reporting)** + **4a (multi-rollout CIs)** together: that combination
turns the current single-number, single-route, n=1 table into a defensible,
re-runnable, noise-floor-aware result — which is exactly the bar Cai says most
benchmarks will fail to clear over the next twelve months.
