# [SaguaroBench](https://github.com/typhamswann/saguaro-bench)

SaguaroBench is a benchmark for measuring multimodal language models on a
real-world citizen-science data-cleaning task: matching saguaro cactus
arm measurements across two survey years (2023 and 2026) on the same
plant.

Volunteers measure plots of saguaros every few years, numbering each
saguaro's arms independently each visit. Arm 3 on a saguaro in 2026 is
NOT necessarily the same physical arm as arm 3 in 2023 — the volunteer
re-counted from "north-most, then clockwise" and arms grow, split, die,
or appear in between. A human curator then hand-matches arms across
years so the team can compute per-arm growth.

This benchmark turns that matching task into a 25-task evaluation. Each
task is one saguaro from plot 41B: the agent receives the digitized arm
rows for both years and decides, for every 2026 arm, which 2023 arm is
the same physical arm — or `"new"` if the arm emerged since 2023. The
agent can inspect hand-redacted paper data sheets (the volunteer's field
forms with the curator's marginal arm-number renumberings blacked out)
and field photos from each survey.

## Task format

SaguaroBench tasks use the [Harbor](https://www.harborframework.com/docs/tasks)
task format:

```text
task.toml         Metadata: saguaro_id, plot, split, difficulty, redaction
                  status, resource limits
instruction.md    The prompt the agent sees
source.json       The underlying per-task definition (arm rows, ground
                  truth mapping, asset manifest)
assets/           Hand-redacted datasheets (datasheet_2023.png,
                  datasheet_2026.png) + field photos (photos/<year>_photo_<n>.jpg)
environment/      Dockerfile (FROM saguaro-bench-base) that bakes the task
                  into a self-contained image
tests/            Verifier: test.sh writes exact_mapping_reward (0.0 or 1.0)
                  to /logs/verifier/reward.txt
```

Inside each task container the agent has three tool calls and one terminal
action:

| tool | args | effect |
|---|---|---|
| `view_paper_datasheet` | `year ∈ {2023, 2026}` | stages the hand-redacted paper field-form PNG at `/workspace/view.png` |
| `view_photo` | `year`, `photo_index` (1-based) | stages a field photo JPG at `/workspace/view.jpg` |
| `submit_mapping` | `mapping_json` (JSON-encoded string) | records the final mapping and terminates |

Driving the benchmark requires a Harbor agent with image observation
support (Pier, Claude Code, OpenHands paired with a vision model, etc.)
Text-only agents cannot ground the visual input. Full contract is
printed by `sab help` inside the container.

This repo is **self-contained**: the runtime (`sab` CLI) is vendored
under `base/pkg` and baked into a local base image; each task's
datasheets and photos are baked into its own image. No external runtime
package, no model weights, no credentials, no network at task-build
time. Imagery bytes ship in the repo (~100 MB across 25 tasks).

## Quickstart

```bash
git clone https://github.com/typhamswann/saguaro-bench
cd saguaro-bench
docker build -t saguaro-bench-base:1.0 base/        # vendored runtime; build once
harbor run -p tasks --agent <agent> --model <model>
```

Each task image is `FROM saguaro-bench-base:1.0` and bakes in its own
`source.json` + assets, so once the base exists task builds are tiny.
The verifier emits `exact_mapping_reward ∈ {0.0, 1.0}` per task; Harbor
collates per-task rewards into a leaderboard summary.

To sanity-check a single task without a Harbor agent:

```bash
docker build -t sab-task -f tasks/41B-13/environment/Dockerfile tasks/41B-13
docker run --rm sab-task bash -c '
  cat /workspace/brief.md
  sab harbor-step --tool view_paper_datasheet --args "{\"year\": 2026}"
  sab harbor-step --tool submit_mapping --args "{\"mapping\": \"{\\\"1\\\":\\\"2\\\",\\\"2\\\":\\\"new\\\",\\\"3\\\":\\\"new\\\",\\\"4\\\":\\\"new\\\",\\\"5\\\":\\\"new\\\",\\\"6\\\":\\\"3\\\",\\\"7\\\":\\\"4\\\",\\\"8\\\":\\\"5\\\",\\\"9\\\":\\\"new\\\",\\\"10\\\":\\\"1\\\"}\"}"
  sab harbor-score
  cat /logs/verifier/reward.json
'
```

The task Dockerfile's `ENTRYPOINT` initializes the sim on container boot
— `/workspace/brief.md` and `/workspace/state.json` are ready from turn
0. The agent's job is to read `brief.md`, call view-tools to stage
PNG/JPG observations into `/workspace`, reason, and finally call
`submit_mapping`. `sab harbor-step` is the single CLI entry point for
all four interactions.

### Subsets and single tasks

```bash
harbor run -p saguaro-bench/tasks --agent <agent>                      # all 25
harbor run -p saguaro-bench/tasks --agent <agent> --n-tasks 4          # first 4
harbor run -p saguaro-bench/tasks/41B-13 --agent <agent>               # one task
```

### Turn budget

Tasks run unbounded by default — the agent decides when to call
`submit_mapping`. Set `SAGUARO_BENCH_MAX_TURNS` to surface a budget; the
boot-time `sab harbor-init` stamps it into `state.json` so the agent can
read it back.

```bash
docker run --rm -e SAGUARO_BENCH_MAX_TURNS=12 sab-task bash -c 'cat /workspace/state.json'
```

## Scoring

A submission is scored 1.0 ONLY if it passes structural validation AND
exactly matches the curator's ground-truth mapping:

- Keys exactly match the 2026 arms in the brief.
- Values are either `"new"` or a 2023 arm id present in the brief.
- The mapping is a function — no two 2026 arms map to the same non-`"new"` 2023 arm.

A structurally-broken submission gets 0.0 plus a `structural_error`
string in `reward.json` so it can be triaged separately from a
structurally-valid wrong answer.

Per-task `reward.json`:

```json
{
  "exact_mapping_reward":  1.0,
  "arm_pair_f1":           0.952,
  "saguaro_id":            "41B-13"
}
```

`arm_pair_f1` is a continuous diagnostic over the set of matched
`(2026_arm, 2023_arm)` pairs (treating `"new"` entries as no-match). It's
useful for ranking partial-credit answers but is NOT the primary reward.

## Dataset

- **Plot:** 41B (Saguaro National Park, Arizona). The same plot was
  re-measured by volunteers in 2023 and 2026.
- **Saguaros:** 25, each appearing in both years. 129 total
  arm-mapping decisions.
- **Splits** (stratified by per-saguaro difficulty): 17 train / 4 val / 4
  test. The split is preserved in each `task.toml` as `metadata.split`
  so leaderboards can report sub-scores per split.
- **Difficulty distribution:** 1 easy / 17 medium / 7 hard.
- **Sheets:** 50 paper data-sheet scans (2 per saguaro), hand-redacted to
  remove the curator's marginal canonical-arm renumberings. 24/25
  saguaros are fully hand-redacted on both years; 41B-22's 2026 sheet
  falls back to an auto-redacted version (flagged in its `task.toml` as
  `metadata.redaction_status_2026 = "auto"`).
- **Photos:** 209 field photos (4–9 per saguaro per year).

Ground truth was extracted from the curator's hand-cleaned `merge`
sheet and is bundled in each task's `source.json` under
`ground_truth.mapping`.

### Why hand-redacted?

An earlier (auto-redacted) version of this benchmark — the 25-saguaro v1
set — saw scores at the ceiling for several frontier models. Inspection
of the sheets revealed that auto-redaction sometimes left visible
fragments of the curator's canonical-arm renumbering, giving a partial
shortcut around the matching task. The hand-redacted set used here is a
careful pass over each sheet by the curator, removing every marginal
canonical number, "Yes/No" stamps, photo annotations, and arrow
overlays that leaked the answer. The matching has to be re-derived from
arm orientation + measurements + photos.

## Repo layout

```
saguaro-bench/
├── base/
│   ├── Dockerfile        # saguaro-bench-base:1.0 — python + vendored `sab` CLI
│   └── pkg/              # the `saguaro-bench-env` Python package
│       ├── pyproject.toml
│       └── src/saguaro_bench_env/
│           ├── cli.py        # `sab` entry point — harbor-init/step/score
│           ├── env.py        # /task and /workspace state management
│           ├── prompts.py    # SYSTEM_PROMPT, HELP_TEXT, build_brief
│           ├── scoring.py    # mapping → reward (exact + arm_pair_f1)
│           └── tools.py      # view_paper_datasheet, view_photo, submit_mapping
├── scripts/
│   └── build_tasks.py    # materialize tasks/ from the source dataset
└── tasks/
    ├── INDEX.json        # summary across all tasks (saguaro_id, split, diff, …)
    └── <saguaro_id>/     # one per saguaro (25 total)
        ├── instruction.md
        ├── task.toml
        ├── source.json
        ├── assets/
        │   ├── datasheet_2023.png       hand-redacted
        │   ├── datasheet_2026.png       hand-redacted
        │   └── photos/<year>_photo_<n>.jpg
        ├── environment/Dockerfile       FROM saguaro-bench-base
        └── tests/test.sh                 sab harbor-score
```

## Local development (without Harbor)

You can iterate on the runtime without rebuilding the Docker image:

```bash
pip install ./base/pkg
SAB_OFFLINE_TASK_DIR=tasks/41B-13 sab info
# Manually point `sab` at a task dir by overriding env paths in env.py if you want
# (the CLI assumes /task and /workspace by default — match that locally).
```

For a clean test loop the Docker route is easier; the slim base image
builds in <30s.

## Full curation pipeline

This repo is the frozen 25-task arm-matching benchmark slice. The full
saguaro-curation RL environment covers the rest of the citizen-science
workflow — digitizing the paper sheets, sanity-checking volunteer entries
against photos, and producing the matched cross-year table — across 7
plots and 217 saguaros with Harbor-compatible packaging. Available under
separate terms.

For access, contact phamswannty@gmail.com.

## License

MIT.
