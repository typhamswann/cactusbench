"""Materialize per-saguaro task directories under tasks/ in the DeepSWE-style
files-on-disk layout.

For each v1 saguaro this writes:

    tasks/<sid>/
        task.toml                 Harbor schema
        instruction.md            "write your mapping to /workspace/submission.json"
        brief.md                  arm rows + photo inventory (rendered at build time)
        assets/
            datasheets/
                2023.png          hand-redacted volunteer field form
                2026.png
            photos/
                2023/photo_<N>.jpg
                2026/photo_<N>.jpg
        grade/
            truth.json            ground_truth.mapping + valid arm sets
            score.py              standalone stdlib-only scorer (copy of scripts/lib/score.py)
        environment/Dockerfile    FROM saguaro-bench-base; COPYs assets to /workspace,
                                  grade/ to /grade (root-locked), agent user owns /workspace
        tests/test.sh             python3 /grade/score.py /workspace/submission.json /grade/truth.json
                                  | tee /logs/verifier/reward.json
                                  jq -r .exact_mapping_reward → /logs/verifier/reward.txt

Inputs (resolved relative to --source-repo, default = saguaro_arm_matching_env
sitting next to this repo):

    {source_repo}/data/dataset.json
    {source_repo}/data/curation_workdir_v2/saguaro_sheet_map.json
    {source_repo}/data/assets/datasheets_v2_hand_redacted/<plot>/*.png
    {source_repo}/data/assets/photos/<sid>_<year>_photo_<n>.jpg

When a hand-redacted v2 sheet is missing for (saguaro, year), the generator
falls back to the v1 auto-redacted PNG and marks
metadata.redaction_status = "auto" in task.toml so it's visible at a glance.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "tasks"
LIB_DIR = REPO_ROOT / "scripts" / "lib"

sys.path.insert(0, str(LIB_DIR))
from brief import build_brief  # noqa: E402


def find_default_source_repo() -> Path:
    candidates = [
        REPO_ROOT.parent / "saguaro_arm_matching_env",
        REPO_ROOT.parent.parent / "saguaro-rl" / "saguaro_arm_matching_env",
    ]
    for c in candidates:
        if (c / "data" / "dataset.json").exists():
            return c
    raise FileNotFoundError(
        "Could not locate saguaro_arm_matching_env. Pass --source-repo explicitly."
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-repo", type=Path, default=None,
                   help="Path to saguaro_arm_matching_env (auto-detected if omitted)")
    p.add_argument("--only", action="append", default=None,
                   help="Restrict to these saguaro_ids (repeat to add more)")
    p.add_argument("--clean", action="store_true",
                   help="Wipe tasks/ before regenerating")
    return p.parse_args()


def derive_plot(sid: str) -> str:
    return sid.split("-", 1)[0]


def pick_sheet(sid: str, year: int, sheet_map: dict, hand_redacted_dir: Path) -> tuple[Path | None, str]:
    plot = derive_plot(sid)
    for fname in sheet_map.get(sid, []):
        if f"_{year}_" in fname:
            p = hand_redacted_dir / plot / fname
            if p.exists():
                return p, "hand"
    return None, "missing"


def fallback_v1_sheet(sid: str, year: int, source_repo: Path) -> Path | None:
    p = source_repo / "data" / "assets" / "datasheets" / f"{sid}_{year}.png"
    return p if p.exists() else None


INSTRUCTION_TEMPLATE = """\
# Match arms across two survey years on saguaro {sid}

A 2023 volunteer recorded {n23} arm(s) on this saguaro. A 2026 volunteer
recorded {n26} arm(s). Volunteers number arms independently each year — arm 3
in 2026 is NOT necessarily the same physical arm as arm 3 in 2023.

For every 2026 arm number, decide which 2023 arm number is the same physical
arm — or `"new"` if the arm has emerged since the 2023 survey.

## Inputs

All inputs live in `/workspace/`:

- `brief.md` — the digitized arm rows + photo inventory for both years.
- `datasheets/2023.png`, `datasheets/2026.png` — the volunteers' handwritten
  field forms (hand-redacted: the curator's marginal arm-number renumbering
  has been blacked out, so the matching has to be done from arm orientation,
  measurements, and photos).
- `photos/2023/photo_<N>.jpg`, `photos/2026/photo_<N>.jpg` — field photos
  from each survey. 1-based indexing; the brief lists how many are
  available.

## Output

Write your final mapping to `/workspace/submission.json` as a JSON object:

- Keys: every 2026 arm number, as strings.
- Values: a 2023 arm number (as a string) or the literal `"new"`.
- The mapping must be a function — no two 2026 arms may map to the same
  non-`"new"` 2023 arm.

Example shape (NOT the answer to this task):

```json
{{"1": "2", "2": "3", "3": "new", "4": "1", "5": "4"}}
```

## Measurement columns

Each arm row has:
- `direction`: compass bearing from saguaro center out to the arm, in
  degrees (0=N, 90=E, 180=S, 270=W).
- `A`: height in meters from the ground to where the arm emerges from the
  main stem.
- `B`: height in meters from the ground to a 1 m datum mark on the stem
  near where A was measured.
- `C`: height from the ground to the tip of the arm.
- `D`: height from the ground to a 1 m datum mark on the stem near where
  C was measured.
- `E`: horizontal distance in meters from the main stem to the arm tip.

Biological constraints: saguaro arms grow slowly. They rarely shrink. New
arms can emerge between surveys; existing arms only rarely disappear.

## Difficulty

**{difficulty}** ({split} split).
"""


def write_task(sid: str, record: dict, source_repo: Path, sheet_map: dict,
               hand_redacted_dir: Path) -> dict:
    task_dir = TASKS_DIR / sid
    if task_dir.exists():
        shutil.rmtree(task_dir)
    (task_dir / "assets" / "datasheets").mkdir(parents=True)
    (task_dir / "assets" / "photos" / "2023").mkdir(parents=True)
    (task_dir / "assets" / "photos" / "2026").mkdir(parents=True)
    (task_dir / "grade").mkdir()
    (task_dir / "environment").mkdir()
    (task_dir / "tests").mkdir()

    # ---- Datasheets (prefer hand-redacted v2, fall back to v1 auto) --------
    redaction_status: dict[int, str] = {}
    for year in (2023, 2026):
        src, status = pick_sheet(sid, year, sheet_map, hand_redacted_dir)
        if src is None:
            fb = fallback_v1_sheet(sid, year, source_repo)
            if fb is None:
                raise SystemExit(f"FATAL: no sheet for {sid} {year}")
            src, status = fb, "auto"
        shutil.copyfile(src, task_dir / "assets" / "datasheets" / f"{year}.png")
        redaction_status[year] = status

    # ---- Photos -------------------------------------------------------------
    n_photos = {2023: 0, 2026: 0}
    for year in (2023, 2026):
        for i, ph in enumerate(record["assets"].get(f"photos_{year}", []), start=1):
            src = source_repo / ph["path"]
            if not src.exists():
                src = Path(ph["path"])
            if not src.exists():
                raise SystemExit(f"FATAL: missing photo {ph['path']} for {sid}")
            shutil.copyfile(src, task_dir / "assets" / "photos" / str(year) / f"photo_{i}.jpg")
            n_photos[year] += 1

    # ---- Reconstruct a record-with-rendered-paths for brief.md -------------
    rendered = dict(record)
    rendered["assets"] = {
        "photos_2023": record["assets"].get("photos_2023", []),
        "photos_2026": record["assets"].get("photos_2026", []),
    }
    (task_dir / "brief.md").write_text(build_brief(rendered))

    # ---- instruction.md ----------------------------------------------------
    diff = record["ground_truth"].get("difficulty", "unknown")
    (task_dir / "instruction.md").write_text(INSTRUCTION_TEMPLATE.format(
        sid=sid,
        n23=len(record["rows_2023"]),
        n26=len(record["rows_2026"]),
        difficulty=diff,
        split=record.get("split", "unknown"),
    ))

    # ---- grade/truth.json + grade/score.py ---------------------------------
    truth = {
        "saguaro_id": sid,
        "ground_truth_mapping": {
            str(k): str(v) for k, v in record["ground_truth"]["mapping"].items()
        },
        "valid_2023_arms": [str(r["arm_n_raw"]) for r in record["rows_2023"]],
        "valid_2026_arms": [str(r["arm_n_raw"]) for r in record["rows_2026"]],
    }
    (task_dir / "grade" / "truth.json").write_text(json.dumps(truth, indent=2))
    shutil.copyfile(LIB_DIR / "score.py", task_dir / "grade" / "score.py")

    # ---- task.toml ---------------------------------------------------------
    redaction_tag = "hand" if all(s == "hand" for s in redaction_status.values()) else (
        "mixed" if "hand" in redaction_status.values() else "auto"
    )
    n23 = len(record["rows_2023"])
    n26 = len(record["rows_2026"])
    task_toml = f"""schema_version = "1.1"
artifacts = []

[task]
name = "saguarobench/{sid}"
description = "Match 2026 arm numbers to 2023 arm numbers (or 'new') for saguaro {sid} on plot 41B. Difficulty: {diff}."
authors = ["Ty Pham-Swann"]
keywords = ["multimodal", "vlm", "saguaro", "arm-matching", "saguaro-bench"]

[metadata]
ext_id = "saguarobench-{sid}"
task_id = "{sid}"
display_title = "Match arms across years for {sid}"
display_description = "Match 2026 arm numbers to 2023 arm numbers (or 'new') for saguaro {sid}. Difficulty: {diff}."
category = "multimodal-matching"
language = "english"
repository_url = "https://github.com/typhamswann/saguaro-bench"
plot = "{derive_plot(sid)}"
split = "{record.get('split', 'unknown')}"
difficulty = "{diff}"
n_arms_2023 = {n23}
n_arms_2026 = {n26}
n_photos_2023 = {n_photos[2023]}
n_photos_2026 = {n_photos[2026]}
redaction_status_2023 = "{redaction_status[2023]}"
redaction_status_2026 = "{redaction_status[2026]}"
redaction_status = "{redaction_tag}"

[verifier]
timeout_sec = 300.0
user = "root"

[verifier.env]

[agent]
timeout_sec = 1800.0
user = "agent"

[environment]
build_timeout_sec = 600.0
docker_image = "saguaro-bench-task:1.0"
os = "linux"
cpus = 1
memory_mb = 2048
storage_mb = 2048
gpus = 0
allow_internet = false
mcp_servers = []

[environment.env]

[solution]

[solution.env]
"""
    (task_dir / "task.toml").write_text(task_toml)

    # ---- environment/Dockerfile -------------------------------------------
    dockerfile = """FROM saguaro-bench-base:1.0

# Agent-visible workspace. Bake the assets in at build time so the agent
# never has to call a custom tool to "load" them — its standard file-read
# primitive sees them directly.
RUN mkdir -p /workspace/datasheets /workspace/photos/2023 /workspace/photos/2026

COPY assets/datasheets/2023.png  /workspace/datasheets/2023.png
COPY assets/datasheets/2026.png  /workspace/datasheets/2026.png
COPY assets/photos/2023/         /workspace/photos/2023/
COPY assets/photos/2026/         /workspace/photos/2026/
COPY brief.md instruction.md     /workspace/

# Verifier-only data (ground truth + scorer). Root-owned, mode-locked so the
# agent user cannot read it.
COPY grade/ /grade/
RUN chmod 700 /grade && chmod 600 /grade/truth.json && chmod 700 /grade/score.py

# Create the agent user and give it the workspace.
RUN useradd -m -s /bin/bash agent && chown -R agent:agent /workspace

USER agent
WORKDIR /workspace
CMD ["/bin/bash"]
"""
    (task_dir / "environment" / "Dockerfile").write_text(dockerfile)

    # ---- tests/test.sh -----------------------------------------------------
    test_sh = f"""#!/usr/bin/env bash
# Harbor verifier — runs as root (per task.toml [verifier].user).
# Reads the agent's /workspace/submission.json, scores against /grade/truth.json,
# and writes /logs/verifier/reward.{{json,txt}}.
#
# Always exit 0 — the reward is the signal, not the exit code (mirrors deep-swe
# and wanderbench).
set -euo pipefail

LOG_PFX="[verifier]"

mkdir -p /logs/verifier /logs/agent /logs/artifacts

echo "${{LOG_PFX}} scoring saguaro-bench task {sid}"

python3 /grade/score.py /workspace/submission.json /grade/truth.json \\
    > /logs/verifier/reward.json

# Extract the canonical reward to reward.txt (Harbor reads either; we write both).
jq -r '.exact_mapping_reward' /logs/verifier/reward.json > /logs/verifier/reward.txt

REWARD=$(cat /logs/verifier/reward.txt)
F1=$(jq -r '.arm_pair_f1' /logs/verifier/reward.json)
ERR=$(jq -r '.structural_error // empty' /logs/verifier/reward.json)

echo "${{LOG_PFX}} reward=${{REWARD}} f1=${{F1}}${{ERR:+ structural_error=$ERR}}"

# Stash the submission (if present) into /logs/artifacts for the trajectory viewer.
if [[ -f /workspace/submission.json ]]; then
    cp /workspace/submission.json /logs/artifacts/submission.json
fi

exit 0
"""
    test_path = task_dir / "tests" / "test.sh"
    test_path.write_text(test_sh)
    test_path.chmod(0o755)

    return {
        "saguaro_id": sid,
        "split": record.get("split"),
        "difficulty": diff,
        "n_arms_2023": n23,
        "n_arms_2026": n26,
        "n_photos_2023": n_photos[2023],
        "n_photos_2026": n_photos[2026],
        "redaction_status_2023": redaction_status[2023],
        "redaction_status_2026": redaction_status[2026],
    }


def main() -> int:
    args = parse_args()
    source_repo: Path = args.source_repo or find_default_source_repo()

    dataset = json.loads((source_repo / "data" / "dataset.json").read_text())
    sheet_map = json.loads(
        (source_repo / "data" / "curation_workdir_v2" / "saguaro_sheet_map.json").read_text()
    )
    hand_redacted_dir = source_repo / "data" / "assets" / "datasheets_v2_hand_redacted"

    if args.clean and TASKS_DIR.exists():
        shutil.rmtree(TASKS_DIR)
    TASKS_DIR.mkdir(parents=True, exist_ok=True)

    summary: list[dict] = []
    wanted = args.only
    for record in dataset:
        sid = record["saguaro_id"]
        if wanted is not None and sid not in wanted:
            continue
        s = write_task(sid, record, source_repo, sheet_map, hand_redacted_dir)
        summary.append(s)
        print(f"  ✓ {sid:10s} split={s['split']:5s} diff={s['difficulty']:7s} "
              f"arms={s['n_arms_2023']}/{s['n_arms_2026']} "
              f"photos={s['n_photos_2023']}/{s['n_photos_2026']} "
              f"redaction={s['redaction_status_2023']}/{s['redaction_status_2026']}")

    (TASKS_DIR / "INDEX.json").write_text(json.dumps(summary, indent=2))
    n_hand = sum(1 for s in summary
                 if s["redaction_status_2023"] == "hand"
                 and s["redaction_status_2026"] == "hand")
    print()
    print(f"  built {len(summary)} task(s) under {TASKS_DIR}")
    print(f"  fully-hand-redacted: {n_hand} / {len(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
