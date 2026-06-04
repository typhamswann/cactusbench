"""Materialize per-saguaro task directories under tasks/ from the source
v1 dataset + hand-redacted v2 sheets + v1 photo assets.

Inputs (resolved relative to --source-repo, which defaults to the
saguaro_arm_matching_env repo sitting next to this one):

    {source_repo}/data/dataset.json
        v1 dataset (25 saguaros, plot 41B). Provides rows_2023, rows_2026,
        ground_truth.mapping, easting/northing/heights/photos.

    {source_repo}/data/curation_workdir_v2/saguaro_sheet_map.json
        saguaro_id -> [hand-redacted v2 sheet basenames]. Used to pick which
        page in data/assets/datasheets_v2_hand_redacted/<plot>/*.png to
        bundle for the 2023 + 2026 datasheet.

    {source_repo}/data/assets/datasheets_v2_hand_redacted/<plot>/<file>.png
        The hand-redacted PNGs.

    {source_repo}/data/assets/photos/<sid>_<year>_photo_<n>.jpg
        The v1 photo assets (unchanged across v1 and v2).

For each v1 saguaro we materialize:

    tasks/<sid>/
        task.toml
        instruction.md
        source.json              # full per-task record consumed by `sab harbor-init`
        assets/
            datasheet_2023.png   # hand-redacted (or v1-auto-redacted fallback)
            datasheet_2026.png
            photos/<year>_photo_<n>.jpg
        environment/Dockerfile   # FROM saguaro-bench-base:1.0; COPY everything
        tests/test.sh            # `sab harbor-score`

When a hand-redacted v2 sheet is missing for a given (saguaro, year), the
generator falls back to the v1 auto-redacted PNG and marks
metadata.redaction_status = "auto" in task.toml so this is visible at a
glance. The default is "hand".

Usage:
    python3 scripts/build_tasks.py
    python3 scripts/build_tasks.py --source-repo /path/to/saguaro_arm_matching_env
    python3 scripts/build_tasks.py --only 41B-13 --only 41B-22  # subset
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "tasks"


def find_default_source_repo() -> Path:
    """Look for saguaro_arm_matching_env next to (or below) saguaro-bench."""
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
    """Return (path, status) where status ∈ {"hand", "auto", "missing"}."""
    plot = derive_plot(sid)
    candidates = sheet_map.get(sid, [])
    for fname in candidates:
        if f"_{year}_" in fname:
            p = hand_redacted_dir / plot / fname
            if p.exists():
                return p, "hand"
    return None, "missing"


def fallback_v1_sheet(sid: str, year: int, source_repo: Path) -> Path | None:
    """v1 auto-redacted sheet at data/assets/datasheets/{sid}_{year}.png."""
    p = source_repo / "data" / "assets" / "datasheets" / f"{sid}_{year}.png"
    return p if p.exists() else None


def write_task(sid: str, record: dict, source_repo: Path, sheet_map: dict,
               hand_redacted_dir: Path) -> dict:
    """Materialize tasks/<sid>/. Returns a small status dict for the summary."""
    task_dir = TASKS_DIR / sid
    if task_dir.exists():
        shutil.rmtree(task_dir)
    (task_dir / "assets" / "photos").mkdir(parents=True)
    (task_dir / "environment").mkdir(parents=True)
    (task_dir / "tests").mkdir(parents=True)

    # ---- Sheets (prefer hand-redacted v2, fall back to v1 auto) ------------
    redaction_status: dict[int, str] = {}
    for year in (2023, 2026):
        src, status = pick_sheet(sid, year, sheet_map, hand_redacted_dir)
        if src is None:
            fb = fallback_v1_sheet(sid, year, source_repo)
            if fb is None:
                raise SystemExit(
                    f"FATAL: no sheet (hand or auto) found for {sid} {year}"
                )
            src = fb
            status = "auto"
        dest = task_dir / "assets" / f"datasheet_{year}.png"
        shutil.copyfile(src, dest)
        redaction_status[year] = status

    # ---- Photos -------------------------------------------------------------
    n_photos = {2023: 0, 2026: 0}
    for year in (2023, 2026):
        for i, photo in enumerate(record["assets"].get(f"photos_{year}", []), start=1):
            # v1 photo paths look like "data/assets/photos/41B-13_2023_photo_1.jpg".
            src = source_repo / photo["path"]
            if not src.exists():
                # Try absolute path as stored.
                src = Path(photo["path"])
            if not src.exists():
                raise SystemExit(f"FATAL: missing photo {photo['path']} for {sid}")
            dest = task_dir / "assets" / "photos" / f"{year}_photo_{i}.jpg"
            shutil.copyfile(src, dest)
            n_photos[year] += 1

    # ---- source.json (everything `sab harbor-init` needs) ------------------
    src_record = {
        "saguaro_id": sid,
        "easting": record.get("easting"),
        "northing": record.get("northing"),
        "saguaro_height_m_2023": record.get("saguaro_height_m_2023"),
        "saguaro_height_m_2026": record.get("saguaro_height_m_2026"),
        "diameter_m_2023": record.get("diameter_m_2023"),
        "diameter_m_2026": record.get("diameter_m_2026"),
        "date_2023": record.get("date_2023"),
        "date_2026": record.get("date_2026"),
        "volunteer_2023": record.get("volunteer_2023"),
        "rows_2023": record["rows_2023"],
        "rows_2026": record["rows_2026"],
        "ground_truth": record["ground_truth"],
        "split": record.get("split"),
        # Asset paths are container-internal (the task Dockerfile copies to /task/assets).
        "assets": {
            "datasheet_2023": "/task/assets/datasheet_2023.png",
            "datasheet_2026": "/task/assets/datasheet_2026.png",
            "photos_2023": [
                {"path": f"/task/assets/photos/2023_photo_{i+1}.jpg",
                 "direction_label": p.get("direction_label")}
                for i, p in enumerate(record["assets"].get("photos_2023", []))
            ],
            "photos_2026": [
                {"path": f"/task/assets/photos/2026_photo_{i+1}.jpg",
                 "direction_label": p.get("direction_label")}
                for i, p in enumerate(record["assets"].get("photos_2026", []))
            ],
        },
    }
    (task_dir / "source.json").write_text(json.dumps(src_record, indent=2, default=str))

    # ---- instruction.md (the irreducible task statement) -------------------
    n23 = len(record["rows_2023"])
    n26 = len(record["rows_2026"])
    diff = record["ground_truth"].get("difficulty", "unknown")
    instruction = (
        f"Match the {n26} saguaro arms recorded on **{sid}** in 2026 against "
        f"the {n23} arms recorded in 2023.\n\n"
        f"For each 2026 arm number, decide which 2023 arm number is the same "
        f"physical arm — or `\"new\"` if the arm emerged since the 2023 survey.\n\n"
        f"The full environment contract — tools, arguments, scoring — is "
        f"printed by `sab help`. The per-saguaro brief (arm rows + available "
        f"photos) is at `/workspace/brief.md`. Paper datasheets are hand-"
        f"redacted; the curator's marginal canonical-arm renumbering has been "
        f"blacked out so the matching has to be done from arm orientation + "
        f"measurements + photos.\n\n"
        f"Difficulty: **{diff}**.\n"
    )
    (task_dir / "instruction.md").write_text(instruction)

    # ---- task.toml (Harbor schema) -----------------------------------------
    redaction_tag = "hand" if all(s == "hand" for s in redaction_status.values()) else (
        "mixed" if "hand" in redaction_status.values() else "auto"
    )
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

[verifier.env]

[agent]
timeout_sec = 1800.0

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
    dockerfile = f"""FROM saguaro-bench-base:1.0

# Bake this task's definition + assets into the image.
COPY source.json instruction.md task.toml /task/
COPY assets /task/assets/

WORKDIR /workspace

# Boot the sim on container start — /workspace/{{system.md, brief.md, state.json}}
# are then ready from turn 0.
RUN {{ \\
      echo '#!/usr/bin/env bash'; \\
      echo 'set -euo pipefail'; \\
      echo 'sab harbor-init /task'; \\
      echo 'exec "$@"'; \\
    }} > /usr/local/bin/sab-entrypoint.sh \\
 && chmod +x /usr/local/bin/sab-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/sab-entrypoint.sh"]
CMD ["/bin/bash"]
"""
    (task_dir / "environment" / "Dockerfile").write_text(dockerfile)

    # ---- tests/test.sh -----------------------------------------------------
    test_sh = f"""#!/usr/bin/env bash
# Harbor verifier — invoked once the agent has finished its rollout.
# Mirrors the deep-swe / wanderbench pattern: writes a single reward (0.0 or
# 1.0) to /logs/verifier/reward.txt, exits 0 on success regardless of reward.
set -euo pipefail

LOG_PFX="[verifier]"

mkdir -p /logs/verifier /logs/agent /logs/artifacts

echo "${{LOG_PFX}} scoring saguaro-bench task {sid}"
sab harbor-score

if [[ ! -f /logs/verifier/reward.txt ]]; then
    echo "${{LOG_PFX}} ERROR: reward.txt was not written" >&2
    exit 1
fi

REWARD=$(cat /logs/verifier/reward.txt)
echo "${{LOG_PFX}} reward=${{REWARD}}"

# Always exit 0 — the reward is the signal, not the exit code.
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

    wanted: Iterable[str] | None = args.only
    summary = []
    for record in dataset:
        sid = record["saguaro_id"]
        if wanted is not None and sid not in wanted:
            continue
        try:
            s = write_task(sid, record, source_repo, sheet_map, hand_redacted_dir)
            summary.append(s)
            print(f"  ✓ {sid:10s} split={s['split']:5s} diff={s['difficulty']:7s} "
                  f"arms={s['n_arms_2023']}/{s['n_arms_2026']} "
                  f"photos={s['n_photos_2023']}/{s['n_photos_2026']} "
                  f"redaction={s['redaction_status_2023']}/{s['redaction_status_2026']}")
        except SystemExit as e:
            print(f"  ✗ {sid}: {e}")
            raise

    # tasks/INDEX.json for downstream tooling.
    (TASKS_DIR / "INDEX.json").write_text(json.dumps(summary, indent=2))

    n_hand = sum(1 for s in summary if s["redaction_status_2023"] == "hand" and s["redaction_status_2026"] == "hand")
    print()
    print(f"  built {len(summary)} task(s) under {TASKS_DIR}")
    print(f"  fully-hand-redacted: {n_hand} / {len(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
