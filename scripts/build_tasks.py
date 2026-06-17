"""Generate per-saguaro CURATION tasks under tasks/ in DeepSWE-style layout.

For each saguaro in the v1 25-saguaro 41B set, this writes:

    tasks/<sid>/
        task.toml                 Harbor schema
        instruction.md            THE prompt — single file with task
                                  statement + domain background + opaque asset
                                  inventory + output schema + canonical
                                  numbering rules + per-year arm schedule +
                                  scoring. DeepSWE-shape (one prompt per task,
                                  the agent provides its own system prompt).
        assets/
            datasheets/
                sheet_A.png       hand-redacted (v2) — opaque (year hidden)
                sheet_B.png       hand-redacted (v2) — opaque
            photos/
                2023_01.jpg       year-labeled (within-year order opaque)
                2026_01.jpg       ...
        grade/
            truth.json            v2 truth_rows (with notes/excluded) +
                                  scoring schema (scored_fields, tolerances)
            score.py              stdlib-only per-cell scorer
        environment/Dockerfile    FROM cactusbench-base; COPYs assets to
                                  /workspace, grade/ to /grade (root-locked),
                                  agent user owns /workspace
        tests/test.sh             python3 /grade/score.py /workspace/submission.json
                                  /grade/truth.json | tee /logs/verifier/reward.json
                                  jq -r .cell_accuracy_reward → /logs/verifier/reward.txt

Inputs (resolved relative to --source-repo, default =
saguaro_arm_matching_env next to this repo):

    {source_repo}/data/dataset.json
        v1 dataset — used ONLY for the 25-saguaro composition and the
        per-saguaro photo manifest.

    {source_repo}/data/curation_dataset_v2.json
        v2 dataset — provides the canonical-arm truth_rows that include
        all paper-faithful note overrides + _excluded rows accumulated
        during QA.

    {source_repo}/data/curation_workdir_v2/saguaro_sheet_map.json
        saguaro_id -> [hand-redacted v2 sheet basenames]. Used to pick which
        page in data/assets/datasheets_v2_hand_redacted/<plot>/*.png to
        bundle for the 2023 + 2026 datasheets.

    {source_repo}/data/assets/datasheets_v2_hand_redacted/<plot>/<file>.png
    {source_repo}/data/assets/photos/<sid>_<year>_photo_<n>.jpg

Sheet/photo bundles are renamed to opaque IDs at build time:
    {year, page}-bearing v2 names  ->  sheet_A.png, sheet_B.png  (order is
        deterministic per saguaro via a seeded shuffle, so the same task
        always gets the same opaque mapping)
    {sid, year, n}-bearing v1 names -> <year>_01.jpg, <year>_02.jpg, ...
        (survey year exposed in the name; within-year order shuffled via the
        same seed so no source ordering leaks)

When a hand-redacted v2 sheet is missing for (saguaro, year), the generator
falls back to the v1 auto-redacted PNG and marks
metadata.redaction_status = "mixed" or "auto" in task.toml.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "tasks"
LIB_DIR = REPO_ROOT / "scripts" / "lib"

sys.path.insert(0, str(LIB_DIR))
from brief import build_instruction  # noqa: E402
from scrub import scrub_to, assert_clean  # noqa: E402

# Tolerances baked into each task's truth.json. Mirrors saguaro_curation/rubric.py.
SCORED_FIELDS = ["saguaro_id", "direction", "A", "B", "C", "D", "E", "note"]
TOLERANCES = {
    "direction": 1.0,
    "A": 0.011, "B": 0.011, "C": 0.011, "D": 0.011, "E": 0.011,
}

# Published harness contract — declared in the prompt and the sandbox manifest
# (docs/MANIFEST.md). Keep this as the single source of truth for the turn cap.
MAX_TURNS = 50


def _bundle_asset(src: Path, dst: Path) -> None:
    """Copy an asset into the task bundle with all metadata stripped, then assert
    the result is clean. Enforces the no-EXIF/no-PNG-chunk property at build time
    (guidance §8) so a leak can never silently ship."""
    scrub_to(src, dst)
    assert_clean(dst)


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
    p.add_argument("--source-repo", type=Path, default=None)
    p.add_argument("--only", action="append", default=None,
                   help="Restrict to these saguaro_ids (repeat to add more)")
    p.add_argument("--clean", action="store_true",
                   help="Wipe the output dir before regenerating")
    # ---- Held-back-pool test draw (guidance §4c / docs/REFRESH.md) -----------
    p.add_argument("--draw-test", type=int, default=None, metavar="N",
                   help="Draw N saguaros fresh from the held-back 217-pool (excludes "
                        "the public 25 and any saguaro without both years hand-redacted), "
                        "and write them as a private test cycle. Implies --out-dir tasks_test/ "
                        "and split='test'.")
    p.add_argument("--seed", type=str, default="cycle-1",
                   help="Rotation seed for --draw-test (changing it draws a different "
                        "test set). Recorded in the cycle manifest.")
    p.add_argument("--stratify", action="store_true",
                   help="With --draw-test: balance the draw across plots (round-robin "
                        "over plots, shuffled within plot) instead of a flat random draw, "
                        "so the test set spans plots evenly (capped by each plot's supply).")
    p.add_argument("--out-dir", type=Path, default=None,
                   help="Output dir (default: tasks/ for the public build, "
                        "tasks_test/ for --draw-test).")
    return p.parse_args()


def derive_plot(sid: str) -> str:
    return sid.split("-", 1)[0]


# ---------------------------------------------------------------------------
# Sheet-assignment overrides. The 2026 "10A-22" scan batch has a leading "10A"
# page (p01) that the 2023 "11-22" batch lacks, so the source sheet-map is
# shifted +1 for the 11-22 region's 2026 sheets — each saguaro got its neighbour's
# (often the A-sibling's) page. We override the correct filename per (sid, year)
# here. Verified individually before adding. The full 11-22 region is audited +
# remapped separately; this dict carries the fixes already confirmed.
# ---------------------------------------------------------------------------
SHEET_OVERRIDES: dict[str, dict[int, str]] = {
    # 2026 "10A-22" batch off-by-one: correct page = current − 1. Verified by 8
    # header anchors (p02=11, p03=12, p05=13, p06=13A, p11=16, p17=19, p19=20,
    # p20=21) — all exactly current−1. See docs/SHEET-AUDIT.md.
    "41B-11":  {2026: "Pl-41B_2026_10A-22__p02.png"},  # was p03
    "41B-12":  {2026: "Pl-41B_2026_10A-22__p03.png"},  # was p04
    "41B-13":  {2026: "Pl-41B_2026_10A-22__p05.png"},  # was p06 (=13A); p05 = saguaro 13, 10 arms
    "41B-15":  {2026: "Pl-41B_2026_10A-22__p09.png"},  # was p10
    "41B-16":  {2026: "Pl-41B_2026_10A-22__p11.png"},  # was p12
    "41B-16A": {2026: "Pl-41B_2026_10A-22__p12.png"},  # was p13
    "41B-18A": {2026: "Pl-41B_2026_10A-22__p16.png"},  # was p17
    "41B-19":  {2026: "Pl-41B_2026_10A-22__p17.png"},  # was p18
    "41B-19A": {2026: "Pl-41B_2026_10A-22__p18.png"},  # was p19
    "41B-20":  {2026: "Pl-41B_2026_10A-22__p19.png"},  # was p20
    "41B-21":  {2026: "Pl-41B_2026_10A-22__p20.png"},  # was p21
    # 41B-22: source map had NO hand 2026 (fell back to auto). p21 is verified to be
    # saguaro 22's real 2026 hand sheet (6 arms, matches truth, leak-free) — pin it.
    # This makes both years hand-redacted, so 41B-22 joins the headline set (25/25).
    "41B-22":  {2026: "Pl-41B_2026_10A-22__p21.png"},
    # 41B-10: already correct — bundles _1-10_p16 (= saguaro 10, verified); the stray
    # _10A-22_p02 in its source list is unused (pick_sheet takes the first 2026 match).
}


# ---------------------------------------------------------------------------
# Truth corrections discovered via the benchmark (cells where EVERY model
# disagreed with the recorded truth, confirmed against the sheet by the curator).
# Keyed (saguaro_id, year, arm-as-str, field) -> corrected value. Applied at build
# so they survive source regeneration. See docs/SHEET-AUDIT.md.
# ---------------------------------------------------------------------------
TRUTH_OVERRIDES: dict[tuple, object] = {
    ("41B-13", 2026, "5", "C"): 3.7,   # was 3.17 (typo; all 15 rollouts read 3.7 off the sheet)
    ("41B-04", 2023, "3", "note"): "Nubbin growing off top of other nub",  # was "" (note omitted)
}


def _apply_truth_overrides(sid: str, truth_rows: list) -> list:
    out = []
    for r in truth_rows:
        r = dict(r)
        for fld in ("direction", "A", "B", "C", "D", "E", "note"):
            key = (sid, r.get("year"), str(r.get("arm")), fld)
            if key in TRUTH_OVERRIDES:
                r[fld] = TRUTH_OVERRIDES[key]
        out.append(r)
    return out


def pick_sheet(sid: str, year: int, sheet_map: dict, hand_redacted_dir: Path) -> tuple[Path | None, str]:
    plot = derive_plot(sid)
    ov = SHEET_OVERRIDES.get(sid, {}).get(year)
    if ov:
        p = hand_redacted_dir / plot / ov
        if p.exists():
            return p, "hand"
        print(f"  ! override sheet missing for {sid} {year}: {p}", file=sys.stderr)
    for fname in sheet_map.get(sid, []):
        if f"_{year}_" in fname:
            p = hand_redacted_dir / plot / fname
            if p.exists():
                return p, "hand"
    return None, "missing"


def fallback_v1_sheet(sid: str, year: int, source_repo: Path) -> Path | None:
    p = source_repo / "data" / "assets" / "datasheets" / f"{sid}_{year}.png"
    return p if p.exists() else None


def write_task(sid: str, truth_rows: list, split: str, difficulty: str,
               photos: list, source_repo: Path, sheet_map: dict,
               hand_redacted_dir: Path, out_dir: Path = TASKS_DIR) -> dict:
    """Write one task bundle. ``photos`` is a list of (year:int, src:Path).
    ``out_dir`` lets the held-back-pool draw write elsewhere than tasks/."""
    truth_rows = _apply_truth_overrides(sid, truth_rows)
    task_dir = out_dir / sid
    if task_dir.exists():
        shutil.rmtree(task_dir)
    (task_dir / "assets" / "datasheets").mkdir(parents=True)
    (task_dir / "assets" / "photos").mkdir(parents=True)
    (task_dir / "grade").mkdir()
    (task_dir / "environment").mkdir()
    (task_dir / "tests").mkdir()

    # Deterministic per-saguaro seed so the opaque shuffle is reproducible.
    rng = random.Random(f"cactusbench-curation::{sid}")

    # ---- Datasheets (prefer hand-redacted v2, fall back to v1 auto) --------
    # Bundle both years' sheets but rename to opaque sheet_A.png / sheet_B.png.
    raw_sheets: list[tuple[int, Path, str]] = []
    redaction_status: dict[int, str] = {}
    for year in (2023, 2026):
        src, status = pick_sheet(sid, year, sheet_map, hand_redacted_dir)
        if src is None:
            fb = fallback_v1_sheet(sid, year, source_repo)
            if fb is None:
                raise SystemExit(f"FATAL: no sheet for {sid} {year}")
            src, status = fb, "auto"
        raw_sheets.append((year, src, status))
        redaction_status[year] = status

    # Shuffle so opaque label A/B doesn't correlate with year.
    shuffled = list(raw_sheets)
    rng.shuffle(shuffled)
    sheet_opaque_map: dict[str, dict] = {}
    for letter, (year, src, status) in zip(("A", "B"), shuffled):
        dest_name = f"sheet_{letter}.png"
        _bundle_asset(src, task_dir / "assets" / "datasheets" / dest_name)
        sheet_opaque_map[dest_name] = {
            "true_year": year,
            "source_file": src.name,
            "redaction_status": status,
        }

    # ---- Photos: year-labeled naming --------------------------------------
    # The survey year IS exposed in the photo filename (<year>_<NN>.jpg) — a
    # legitimate input the field biologist always has. Within a year the order
    # is still opaque (seeded shuffle), so no source ordering leaks.
    raw_photos: list[tuple[int, Path]] = list(photos)
    rng.shuffle(raw_photos)
    photo_opaque_map: dict[str, dict] = {}
    year_count: dict[int, int] = {}
    for year, src in raw_photos:
        year_count[year] = year_count.get(year, 0) + 1
        dest_name = f"{year}_{year_count[year]:02d}.jpg"
        _bundle_asset(src, task_dir / "assets" / "photos" / dest_name)
        photo_opaque_map[dest_name] = {
            "true_year": year,
            "source_file": src.name,
        }

    # ---- instruction.md (THE prompt — single file, DeepSWE-shape) ----------
    # The prompt is near-identical across all tasks: the agent is told neither
    # the saguaro id, the per-year arm schedule, nor the scoring rules. It must
    # derive the saguaro id, the canonical numbering, and the row set itself.
    # The only per-task substitution is the photo count.
    n_excluded = sum(1 for tr in truth_rows if tr.get("_excluded"))
    diff = difficulty
    (task_dir / "instruction.md").write_text(build_instruction(
        n_photos=len(raw_photos),
        max_turns=MAX_TURNS,
    ))

    # ---- grade/truth.json + grade/score.py --------------------------------
    truth = {
        "saguaro_id": sid,
        "scored_fields": SCORED_FIELDS,
        "tolerances": TOLERANCES,
        "truth_rows": truth_rows,
        # Opaque-map is kept here for audit (it's in /grade so the agent can't see it).
        "_opaque_sheet_map": sheet_opaque_map,
        "_opaque_photo_map": photo_opaque_map,
    }
    (task_dir / "grade" / "truth.json").write_text(json.dumps(truth, indent=2, default=str))
    shutil.copyfile(LIB_DIR / "score.py", task_dir / "grade" / "score.py")

    # ---- task.toml --------------------------------------------------------
    redaction_tag = "hand" if all(s == "hand" for s in redaction_status.values()) else (
        "mixed" if "hand" in redaction_status.values() else "auto"
    )
    # Year-invariance guard (guidance §2b/§8): if the two years are redacted in
    # different styles, redaction artifacts can leak the year. Such a saguaro is
    # kept in the repo for completeness but flagged OUT of the headline-scored set.
    headline_scored = all(s == "hand" for s in redaction_status.values())
    n_rows_scored = sum(1 for tr in truth_rows if not tr.get("_excluded"))
    n_notes_overridden = sum(
        1 for tr in truth_rows
        if not tr.get("_excluded") and (
            isinstance(tr.get("note"), list) or (isinstance(tr.get("note"), str) and tr["note"])
        )
    )
    task_toml = f"""schema_version = "1.1"
artifacts = []

[task]
name = "cactusbench-curation/{sid}"
description = "Curate the full cross-year arm-measurement table for saguaro {sid} on plot 41B. Difficulty: {diff}."
authors = ["Ty Pham-Swann"]
keywords = ["multimodal", "vlm", "saguaro", "curation", "digitization", "cactusbench"]

[metadata]
ext_id = "cactusbench-curation-{sid}"
task_id = "{sid}"
display_title = "Curate {sid}"
display_description = "Read hand-redacted volunteer field forms + field photos for saguaro {sid} (2023 and 2026), match arms across years, produce the cleaned canonical-arm table. Difficulty: {diff}."
category = "multimodal-curation"
language = "english"
repository_url = "https://github.com/typhamswann/cactusbench"
plot = "{derive_plot(sid)}"
split = "{split}"
difficulty = "{diff}"
n_arms_2023 = {sum(1 for tr in truth_rows if tr['year']==2023 and not tr.get('_excluded'))}
n_arms_2026 = {sum(1 for tr in truth_rows if tr['year']==2026 and not tr.get('_excluded'))}
n_truth_rows_scored = {n_rows_scored}
n_truth_rows_excluded = {n_excluded}
n_notes_with_override = {n_notes_overridden}
n_photos = {len(raw_photos)}
redaction_status_2023 = "{redaction_status[2023]}"
redaction_status_2026 = "{redaction_status[2026]}"
redaction_status = "{redaction_tag}"
# headline_scored = false when the two years use different redaction styles, so
# redaction artifacts cannot leak the year into the headline number (guidance §2b).
headline_scored = {str(headline_scored).lower()}
max_turns_per_rollout = {MAX_TURNS}

[verifier]
timeout_sec = 300.0
user = "root"

[verifier.env]

[agent]
timeout_sec = 1800.0
user = "agent"

[environment]
build_timeout_sec = 600.0
docker_image = "cactusbench-task:1.0"
os = "linux"
cpus = 1
memory_mb = 2048
storage_mb = 2048
gpus = 0
allow_internet = false
mcp_servers = []

[environment.env]

# Sandbox + harness manifest (Cai §4 / guidance §4). A buyer cannot re-run the
# benchmark without these. See docs/MANIFEST.md for the canonical, run-wide copy.
[manifest]
max_turns_per_rollout = {MAX_TURNS}
network_egress_policy = "none"        # allow_internet=false; no egress in-task
tool_approval_policy = "auto"          # tools execute without human approval
isolation_granularity = "per-task-container"
observation_truncation_policy = "text>=50000 chars truncated; images elided beyond a sliding window (default 6)"
asset_metadata_policy = "stripped"     # EXIF/XMP/PNG-text removed + asserted at build
filename_policy = "opaque"             # sheet_{{A,B}}.png, photo_NNN.jpg; year hidden

[solution]

[solution.env]
"""
    (task_dir / "task.toml").write_text(task_toml)

    # ---- environment/Dockerfile -------------------------------------------
    dockerfile = """FROM cactusbench-base:1.0

# Agent-visible workspace. Assets are baked in under OPAQUE filenames so the
# agent can read them with its standard file-read primitive but can't tell
# which sheet is which year (or which photo is which year) from the path.
RUN mkdir -p /workspace/datasheets /workspace/photos

COPY assets/datasheets/  /workspace/datasheets/
COPY assets/photos/      /workspace/photos/
COPY instruction.md /workspace/

# Verifier-only data: ground truth + scorer + opaque->true-year map.
# Root-owned, mode 0700 so the agent user cannot read it.
COPY grade/ /grade/
RUN chmod 700 /grade && chmod 600 /grade/truth.json && chmod 700 /grade/score.py

# Create the agent user and give it the workspace.
RUN useradd -m -s /bin/bash agent && chown -R agent:agent /workspace

USER agent
WORKDIR /workspace
CMD ["/bin/bash"]
"""
    (task_dir / "environment" / "Dockerfile").write_text(dockerfile)

    # ---- tests/test.sh ----------------------------------------------------
    test_sh = f"""#!/usr/bin/env bash
# Harbor verifier — runs as root (per task.toml [verifier].user).
# Reads the agent's /workspace/submission.json, scores per-cell against
# /grade/truth.json using field-typed tolerances, writes
# /logs/verifier/reward.{{json,txt}}.
#
# Always exit 0 — the reward is the signal, not the exit code (mirrors deep-swe
# and wanderbench).
set -euo pipefail

LOG_PFX="[verifier]"

mkdir -p /logs/verifier /logs/agent /logs/artifacts

echo "${{LOG_PFX}} scoring cactusbench (curation) task {sid}"

python3 /grade/score.py /workspace/submission.json /grade/truth.json \\
    > /logs/verifier/reward.json

jq -r '.cell_accuracy_reward' /logs/verifier/reward.json > /logs/verifier/reward.txt

REWARD=$(cat /logs/verifier/reward.txt)
F1=$(jq -r '.row_f1 // empty' /logs/verifier/reward.json)
MISSING=$(jq -r '.rows_missing // empty' /logs/verifier/reward.json)
EXTRA=$(jq -r '.rows_extra // empty' /logs/verifier/reward.json)
ERR=$(jq -r '.structural_error // empty' /logs/verifier/reward.json)

echo "${{LOG_PFX}} reward=${{REWARD}} row_f1=${{F1}} missing=${{MISSING}} extra=${{EXTRA}}${{ERR:+ structural_error=$ERR}}"

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
        "split": split,
        "difficulty": diff,
        "n_truth_rows_scored": n_rows_scored,
        "n_truth_rows_excluded": n_excluded,
        "n_notes_with_override": n_notes_overridden,
        "n_photos": len(raw_photos),
        "redaction_status_2023": redaction_status[2023],
        "redaction_status_2026": redaction_status[2026],
        "headline_scored": headline_scored,
    }


def gather_v1_photos(v1_record: dict, source_repo: Path) -> list:
    """Return [(year, src_path), ...] from a v1 record's photo manifest."""
    out: list = []
    for year in (2023, 2026):
        for ph in v1_record["assets"].get(f"photos_{year}", []):
            src = source_repo / ph["path"]
            if not src.exists():
                src = Path(ph["path"])
            if not src.exists():
                raise SystemExit(f"FATAL: missing photo {ph['path']} for {v1_record['saguaro_id']}")
            out.append((year, src))
    return out


def _sid_variants(sid: str) -> list[str]:
    """photos_v2 dirs drop leading zeros from the numeric part (40-04A -> 40-4A,
    6-051 -> 6-51), while the dataset keeps them. Return candidate forms to match."""
    plot, _, rest = sid.partition("-")
    variants = {sid}
    m = re.match(r"0*(\d+)([A-Za-z]*)$", rest)
    if m:
        variants.add(f"{plot}-{int(m.group(1))}{m.group(2)}")
    return sorted(variants)


def gather_glob_photos(sid: str, source_repo: Path) -> list:
    """Photo discovery for pool saguaros with no v1 manifest. Searches the
    per-plot photos_v2/<plot>/<sid>_<year>/*.jpg tree (all plots) and the flat
    data/assets/photos/<sid>_<year>_photo_*.jpg dir (41B legacy). Sheets-only if
    none found. Handles the leading-zero ID mismatch between dataset and dirs."""
    out: list = []
    plot = derive_plot(sid)
    v2root = source_repo / "data" / "assets" / "photos_v2" / plot
    for year in (2023, 2026):
        hit = []
        for v in _sid_variants(sid):
            d = v2root / f"{v}_{year}"
            if d.is_dir():
                hit = sorted(d.glob("*.jpg"))
                break
        out.extend((year, src) for src in hit)
    if out:
        return out
    # legacy flat dir (41B public-25 only)
    pdir = source_repo / "data" / "assets" / "photos"
    if pdir.exists():
        for year in (2023, 2026):
            for src in sorted(pdir.glob(f"{sid}_{year}_photo_*.jpg")):
                out.append((year, src))
    return out


def derive_difficulty(truth_rows: list) -> str:
    """Heuristic difficulty for pool saguaros that lack a curated rating: by the
    number of canonical arms (the curator-rated 25 keep their explicit rating)."""
    n = len({tr["arm"] for tr in truth_rows if not tr.get("_excluded")})
    if n <= 2:
        return "easy"
    if n <= 6:
        return "medium"
    return "hard"


def _has_both_hand(sid: str, sheet_map: dict, hand_redacted_dir: Path) -> bool:
    return all(pick_sheet(sid, y, sheet_map, hand_redacted_dir)[0] is not None
               for y in (2023, 2026))


def build_test_pool(args, source_repo, v1, v2, v2_idx, sheet_map, hand_redacted_dir) -> int:
    """Draw N saguaros fresh from the held-back pool and write a private test
    cycle. Eligible = in v2, both years hand-redacted, NOT in the public 25."""
    out_dir = args.out_dir or (REPO_ROOT / "tasks_test")
    public_ids = {r["saguaro_id"] for r in v1}
    eligible = [r["saguaro_id"] for r in v2
                if r["saguaro_id"] not in public_ids
                and _has_both_hand(r["saguaro_id"], sheet_map, hand_redacted_dir)]
    eligible.sort()  # stable order before the seeded shuffle
    rng = random.Random(f"cactusbench-test-draw::{args.seed}")
    if getattr(args, "stratify", False):
        # Round-robin across plots (each plot shuffled) so the draw spans plots
        # evenly; a plot with few eligible saguaros simply contributes all it has.
        from collections import defaultdict as _dd
        by_plot: dict = _dd(list)
        for sid in eligible:
            by_plot[derive_plot(sid)].append(sid)
        for plot in by_plot:
            rng.shuffle(by_plot[plot])
        drawn = []
        plots = sorted(by_plot)
        while len(drawn) < args.draw_test and any(by_plot[p] for p in plots):
            for p in plots:
                if by_plot[p] and len(drawn) < args.draw_test:
                    drawn.append(by_plot[p].pop())
        from collections import Counter as _C
        print("  stratified draw by plot:", dict(_C(derive_plot(s) for s in drawn)))
    else:
        rng.shuffle(eligible)
        drawn = eligible[: args.draw_test]
    if len(drawn) < args.draw_test:
        print(f"  WARN: only {len(drawn)} eligible saguaros (requested {args.draw_test})",
              file=sys.stderr)

    if args.clean and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict] = []
    for sid in drawn:
        rec = v2_idx[sid]
        photos = gather_glob_photos(sid, source_repo)  # sheets-only if none
        s = write_task(sid, rec["truth_rows"], "test", derive_difficulty(rec["truth_rows"]),
                       photos, source_repo, sheet_map, hand_redacted_dir, out_dir=out_dir)
        summary.append(s)
        print(f"  ✓ {sid:10s} TEST diff={s['difficulty']:7s} "
              f"rows={s['n_truth_rows_scored']:>2} photos={s['n_photos']:>2} "
              f"redaction={s['redaction_status_2023']}/{s['redaction_status_2026']}")

    (out_dir / "INDEX.json").write_text(json.dumps(summary, indent=2))
    (out_dir / "CYCLE.json").write_text(json.dumps({
        "seed": args.seed,
        "n_drawn": len(drawn),
        "n_eligible": len(eligible),
        "excluded_public": sorted(public_ids),
        "drawn": drawn,
        "note": "PRIVATE test cycle — do not commit truth. See docs/REFRESH.md.",
    }, indent=2))
    print()
    print(f"  drew {len(drawn)} private test task(s) into {out_dir} (seed={args.seed!r})")
    print(f"  eligible pool size: {len(eligible)} held-back hand-redacted saguaros")
    print(f"  ⚠ {out_dir.name}/ contains truth — keep it OUT of the public repo (see docs/REFRESH.md)")
    return 0


def main() -> int:
    args = parse_args()
    source_repo: Path = args.source_repo or find_default_source_repo()

    v1 = json.loads((source_repo / "data" / "dataset.json").read_text())
    v2 = json.loads((source_repo / "data" / "curation_dataset_v2.json").read_text())
    v2_idx = {r["saguaro_id"]: r for r in v2}
    sheet_map = json.loads(
        (source_repo / "data" / "curation_workdir_v2" / "saguaro_sheet_map.json").read_text()
    )
    hand_redacted_dir = source_repo / "data" / "assets" / "datasheets_v2_hand_redacted"

    # ---- Held-back-pool test draw -------------------------------------------
    if args.draw_test:
        return build_test_pool(args, source_repo, v1, v2, v2_idx, sheet_map, hand_redacted_dir)

    # ---- Public 25-saguaro build (the frozen dev slice) ---------------------
    out_dir = args.out_dir or TASKS_DIR
    if args.clean and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict] = []
    wanted = args.only
    for v1_record in v1:
        sid = v1_record["saguaro_id"]
        if wanted is not None and sid not in wanted:
            continue
        v2_record = v2_idx.get(sid)
        if v2_record is None:
            print(f"  ✗ {sid}: missing in v2 dataset", file=sys.stderr)
            continue
        photos = gather_v1_photos(v1_record, source_repo)
        diff = v1_record["ground_truth"].get("difficulty", "unknown")
        s = write_task(sid, v2_record["truth_rows"], v1_record.get("split", "unknown"),
                       diff, photos, source_repo, sheet_map, hand_redacted_dir, out_dir=out_dir)
        summary.append(s)
        print(f"  ✓ {sid:10s} split={s['split']:5s} diff={s['difficulty']:7s} "
              f"rows={s['n_truth_rows_scored']:>2}(+{s['n_truth_rows_excluded']} excl) "
              f"notes_overridden={s['n_notes_with_override']:>2} "
              f"photos={s['n_photos']:>2} "
              f"redaction={s['redaction_status_2023']}/{s['redaction_status_2026']} "
              f"headline={'Y' if s['headline_scored'] else 'N'}")

    # Merge into INDEX.json rather than clobber it — a partial build (--only) must
    # not shrink the index to just the rebuilt tasks (that breaks aggregate.py).
    index_path = out_dir / "INDEX.json"
    if wanted is not None and index_path.exists():
        prior = {r["saguaro_id"]: r for r in json.loads(index_path.read_text())}
        for s in summary:
            prior[s["saguaro_id"]] = s
        merged = [prior[k] for k in sorted(prior)]
        index_path.write_text(json.dumps(merged, indent=2))
    else:
        index_path.write_text(json.dumps(summary, indent=2))
    n_hand = sum(1 for s in summary if s["headline_scored"])
    print()
    print(f"  built {len(summary)} task(s) under {out_dir}")
    print(f"  headline-scored (both years hand-redacted): {n_hand} / {len(summary)}")
    print(f"  total scored truth rows: {sum(s['n_truth_rows_scored'] for s in summary)}")
    print(f"  total notes overridden:  {sum(s['n_notes_with_override'] for s in summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
