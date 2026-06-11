#!/usr/bin/env python3
"""Re-score a completed run's stored submissions with the CURRENT scorer.

Every result record stores `submission_raw`, so a run can be re-graded offline
after a scorer change without spending API budget again. Writes
`<model>.rescored.json` next to each model file and prints a before/after table.

Usage:
    python scripts/rescore.py runs/<run-id> [--tasks-dir tasks]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def rescore_one(submission_raw, sid: str, tasks_dir: Path) -> dict:
    score_py = tasks_dir / sid / "grade" / "score.py"
    truth = tasks_dir / sid / "grade" / "truth.json"
    if submission_raw is None:
        return {"cell_accuracy_reward": 0.0, "structural_error": "no_submission"}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        fh.write(submission_raw)
        sub_path = fh.name
    try:
        proc = subprocess.run([sys.executable, str(score_py), sub_path, str(truth)],
                              capture_output=True, text=True, timeout=60)
        return json.loads(proc.stdout)
    except Exception as e:  # noqa: BLE001
        return {"cell_accuracy_reward": 0.0, "structural_error": f"rescore_error:{e}"}
    finally:
        Path(sub_path).unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--tasks-dir", type=Path, default=REPO / "tasks")
    args = ap.parse_args()

    print(f"{'model':16s} {'old_mean':>9s} {'new_mean':>9s} {'delta':>7s}")
    print("-" * 46)
    for f in sorted(args.run_dir.glob("*.json")):
        if f.name in ("config.json", "leaderboard.json") or ".rescored." in f.name:
            continue
        blob = json.loads(f.read_text())
        recs = blob.get("results", [])
        if not recs:
            continue
        old = sum(r.get("cell_accuracy_reward", 0) for r in recs) / len(recs)
        for r in recs:
            new = rescore_one(r.get("submission_raw"), r["saguaro_id"], args.tasks_dir)
            r["cell_accuracy_reward_old"] = r.get("cell_accuracy_reward")
            r["cell_accuracy_reward"] = new.get("cell_accuracy_reward", 0.0)
            r["row_f1"] = new.get("row_f1", r.get("row_f1"))
            r["rows_matched"] = new.get("rows_matched", r.get("rows_matched"))
            r["rows_extra"] = new.get("rows_extra", r.get("rows_extra"))
            r["per_field_accuracy"] = new.get("per_field_accuracy", r.get("per_field_accuracy"))
            r["note_accuracy_nonempty"] = new.get("note_accuracy_nonempty")
            r["structural_error"] = new.get("structural_error")
        new_mean = sum(r["cell_accuracy_reward"] for r in recs) / len(recs)
        out = f.with_suffix(".rescored.json")
        out.write_text(json.dumps({**blob, "results": recs, "rescored": True}, indent=2))
        print(f"{blob.get('model_tag', f.stem):16s} {old:9.3f} {new_mean:9.3f} "
              f"{new_mean - old:+7.3f}")
    print(f"\nrescored files written as *.rescored.json in {args.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
