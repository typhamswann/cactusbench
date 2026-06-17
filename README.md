# [CactusBench](https://typhamswann.com/cactusbench)

CactusBench measures multimodal models on a real scientific data-curation task: reading hand-written field forms and field photos of saguaro cacti, then producing the cleaned, cross-year-matched arm-measurement table a human biologist would have produced. The public set is **46 tasks** drawn from six plots at Saguaro National Park, each one saguaro measured in both 2023 and 2026.

Biologists re-measure every saguaro's arms on a plot every few years — compass direction, base height, tip height, arm length, and free-text notes — numbering the arms independently on each visit. A curator then reconciles both years' raw sheets and photos into one canonical table: arms matched across years, re-keyed to a single numbering, and quietly QA'd against the recorder's obvious slips. CactusBench turns that workflow into a benchmark. The agent gets two field forms and the field photos in a plain Unix workspace and must derive the saguaro id, which sheet is which year, the arm count, the cross-year matching, and the cleaned values itself — none of it is in the prompt.

Frontier models reach ~0.93–0.97 per-cell accuracy but none reach the precision a biologist needs to trust the table unattended, and failures are dominated by handwriting OCR rather than reasoning. The full failure taxonomy, cross-harness sensitivity, reasoning-effort ablation, reproducibility manifest, and a playable task are on the site: **[typhamswann.com/cactusbench](https://typhamswann.com/cactusbench)**.

## Task format

CactusBench tasks use the [Harbor](https://www.harborframework.com/docs/tasks) task format:

```text
task.toml         Metadata: saguaro_id, plot, split, difficulty, redaction status, counts, limits
instruction.md    The prompt the agent sees — task statement, column reference, output schema
assets/
  datasheets/     sheet_A.png, sheet_B.png — one per year, hand-redacted; the filename gives nothing away
  photos/         2023_NN.jpg, 2026_NN.jpg — field photos (year in the name, within-year index opaque)
grade/            Verifier-only (root-owned, mode 0700 in the image)
  truth.json      Ground-truth rows + scoring schema (scored_fields, tolerances)
  score.py        Stdlib-only per-cell scorer
environment/      Dockerfile (FROM cactusbench-base:1.0) baking assets → /workspace, grade → /grade
tests/test.sh     Verifier entry point → /logs/verifier/reward.{json,txt}
```

### The agent's contract

Inside the container the agent works in `/workspace/`:

```
/workspace/
├── instruction.md      task statement + measurement-column reference + output schema
├── datasheets/         sheet_A.png, sheet_B.png   (which sheet is which year is NOT given)
├── photos/             2023_NN.jpg, 2026_NN.jpg
└── submission.json     ← the agent writes its cleaned table here
```

It reads the PNG/JPG assets with whatever image-read primitive it already has (Claude Code's `Read`, Codex's image read, …) and writes `submission.json` — a JSON list with one row per `(year, canonical_arm)`:

```json
{ "saguaro_id": "15-66", "year": 2023, "arm": "1", "direction": 359,
  "A": 3.21, "B": 0.98, "C": 3.99, "D": 0.99, "E": 0.6, "note": "" }
```

The prompt gives neither the saguaro id, the arm count, nor which sheet is which year — the agent derives all of it. Canonical numbering follows the curator convention: the 2023 paper-arm numbers are the canonical labels, and each 2026 arm takes the number of the 2023 arm it matches (new 2026-only arms continue the sequence). The agent is also expected to QA: where a measurement is a clear recording slip, the curated value may diverge from the literal sheet to reflect what the recorder intended.

## Quickstart

Any [Harbor](https://www.harborframework.com/)-compatible runtime works. Build the base image once, then run:

```bash
git clone https://github.com/typhamswann/cactusbench
cd cactusbench
docker build -t cactusbench-base:1.0 base/        # build once
harbor run -p tasks --agent <agent> --model <model>
```

Each task image is `FROM cactusbench-base:1.0` and bakes in its own assets + ground truth; the verifier emits `cell_accuracy_reward ∈ [0, 1]` per task, which Harbor collates into a leaderboard.

Sanity-check a single task without an agent:

```bash
docker build -t cb-task -f tasks/15-66/environment/Dockerfile tasks/15-66
docker run --rm --user root -v "$PWD/tasks/15-66/tests:/tests:ro" cb-task bash -c '
  echo "[]" > /workspace/submission.json          # empty placeholder
  bash /tests/test.sh; cat /logs/verifier/reward.json'
```

`/grade/` is root-owned mode 0700, so the agent user cannot read the truth.

### Controlled harness

`harness/run.py` is a self-contained image→tool-call completion loop for running the set across models without Harbor — first-party routes for frontier models (Anthropic via Bedrock, OpenAI, Google) and OpenRouter for open models. See [`harness/README.md`](harness/README.md).

```bash
python harness/run.py --models all --tasks-dir tasks --rollouts 3 --max-turns 50
python scripts/aggregate.py runs/<run-id>          # leaderboard: means, 95% CIs, reward/$
```

## Scoring

Per-cell match against ground truth, keyed by `(year, arm)`. Each task is a single saguaro, so `saguaro_id` is scored as an ordinary cell rather than part of the key. Field-typed tolerances:

| field | match rule |
|---|---|
| `direction` | numeric, circular, ±1.0° |
| `A` `B` `C` `D` `E` | numeric, ±0.011 m |
| `note` | normalized-exact, or any member of a list of accepted phrasings (empty = empty) |
| `saguaro_id` | normalized string equality |

Two structural rules reflect the real task:

- **Year-tolerant matching.** A model's two surveys are mapped to the truth years by chronological order, so reading the early/late ordering right but writing the wrong absolute year is not penalized — while genuinely swapping which sheet is which year still is.
- **Ambiguous arms.** A few truth rows are flagged `_excluded` (the paper is genuinely ambiguous — e.g. a partial nubbin recorded inconsistently across years). They are skipped entirely: present-or-absent both score, and the cells count for no one.

Missing rows score 0 across their cells; extra (hallucinated) rows cost 5% each, capped at 50%:

```
cell_accuracy_reward = max(0, correct / total − extra_penalty)   ∈ [0, 1]
```

Notes are mostly empty (43 of 376 rows carry one) and matched leniently, so per-task `reward.json` also breaks out `note_accuracy_nonempty` and per-field accuracy alongside `row_f1` and the structural counts — `cell_accuracy_reward` is the headline.

## Leaderboard

46-task set, models run in their **native CLIs** at default/low reasoning, 3 rollouts each. Per-cell accuracy; 95% CIs are task-level bootstrap (n = 46).

| Model | Harness | Mean | 95% CI |
|---|---|---|---|
| Gemini 3.1 Pro | Antigravity | **0.967** | 0.937–0.987 |
| GPT-5.5 | Codex | 0.961 | 0.930–0.982 |
| Gemini 3.5 Flash | Antigravity | 0.957 | 0.926–0.979 |
| Claude Opus 4.8 | Claude Code | 0.942 | 0.909–0.969 |
| Claude Opus 4.7 | Claude Code | 0.928 | 0.892–0.957 |
| Qwen3-VL-Plus | completion loop | 0.879 | 0.839–0.915 |
| MiniMax-M3 | completion loop | 0.728 | 0.654–0.797 |

Frontier models run on their native agent CLIs; open models run on the controlled completion loop — each on its stronger configuration (models are notably harness-dependent; see the [cross-harness study](docs/NOISE-FLOOR-STUDY.md)). The within-frontier ordering at the top is not statistically resolved at n = 46 — the CIs overlap heavily. Full numbers in [`leaderboard.json`](leaderboard.json); per-task metadata in [`INDEX.json`](INDEX.json).

## Dataset

- **46 saguaros** across six plots at Saguaro National Park — 15, 28, 40, 41B, 41F, and 6 — each measured in both 2023 and 2026.
- **376 ground-truth rows** (2 `_excluded`), **380 field photos**, 43 rows carrying a recorder note.
- **Sheets** are hand-redacted to remove the curator's marginal arm-renumberings and stamps; realistic decoy redactions are added to sheets that needed no correction, so a redaction never signals which values are wrong. All assets are stripped of EXIF/XMP/PNG metadata at build.
- **Filenames** give nothing away on the sheets (`sheet_A`/`sheet_B`; the agent reads the date header to assign the year). Photo names carry only the year, which is anyway visible in the photo.

Ground truth lives in each task's `grade/truth.json`, unreadable by the agent inside the container.

## Reporting

- [`docs/MANIFEST.md`](docs/MANIFEST.md) — sandbox + provider-route reproducibility manifest.
- [`docs/NOISE-FLOOR-STUDY.md`](docs/NOISE-FLOOR-STUDY.md) — cross-harness and reasoning-effort study.

Full writeup, charts, and a playable task: **[typhamswann.com/cactusbench](https://typhamswann.com/cactusbench)**.
