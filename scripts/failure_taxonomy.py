#!/usr/bin/env python3
"""Per-model failure-class taxonomy for SaguaroBench (Cai §7 / guidance §7).

Aggregate-mean-only is the thing Cai mocks; the per-model failure-class breakdown
is what makes a benchmark a service. This labels every failing scored cell with a
domain-specific class, mostly deterministically from the scorer + the opaque maps
in truth.json + the agent's submission.

Classes:
  schema_violation        — submission didn't parse / wrong shape (whole rollout)
  image_not_read          — agent never opened an image (whole rollout)
  hallucinated_row        — predicted (year,arm) not in truth
  missing_row             — truth (year,arm) absent from submission
  year_misassignment      — right values, wrong YEAR (cross-year confusion)
  arm_matching_error      — right values, wrong canonical ARM (match/renumber slip)
  transcription_error     — numeric cell present but off-tolerance
  saguaro_id_error        — wrong/absent saguaro id
  note_error              — note cell wrong
  qaqc_over_correction    — model changed a value the sheet recorded correctly
  qaqc_under_correction   — model kept a genuine recorder slip the curator fixed
                            (qaqc_* require `literal` in truth — see docs/REFRESH.md;
                             reported as "n/a (no literal data)" until that lands)

Usage:
    python scripts/failure_taxonomy.py runs/<run-id>
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "lib"))
from score import (  # noqa: E402
    parse_submission, _row_key, _canon_saguaro_id, _canon_arm,
    _numeric_match, _note_match, _saguaro_id_match, NUMERIC_FIELDS,
)


def _truth(sid: str, tasks_dir: Path) -> dict:
    return json.loads((tasks_dir / sid / "grade" / "truth.json").read_text())


def classify_rollout(rec: dict, truth: dict) -> Counter:
    c: Counter = Counter()
    if rec.get("structural_error"):
        c["schema_violation"] += 1
        return c
    if not rec.get("images_viewed"):
        c["image_not_read"] += 1
        # keep going — still classify the cells
    raw = rec.get("submission_raw")
    if not raw:
        c["schema_violation"] += 1
        return c
    rows, err = parse_submission(raw)
    if err:
        c["schema_violation"] += 1
        return c

    tol = truth.get("tolerances", {})
    fields = tuple(truth.get("scored_fields", ()))
    truth_rows = [r for r in truth["truth_rows"] if not r.get("_excluded")]
    truth_by_key = {_row_key(r): r for r in truth_rows}
    excluded = {_row_key(r) for r in truth["truth_rows"] if r.get("_excluded")}
    pred_by_key = {_row_key(r): r for r in rows}
    # value index for year/arm-swap detection: (sid, tuple-of-numeric) -> (year,arm)
    pred_vals = {}
    for r in rows:
        key = tuple(r.get(f) for f in NUMERIC_FIELDS)
        pred_vals.setdefault(key, []).append(_row_key(r))

    # Extra / hallucinated rows
    for k in set(pred_by_key) - set(truth_by_key) - excluded:
        c["hallucinated_row"] += 1

    for key, trow in truth_by_key.items():
        prow = pred_by_key.get(key)
        if prow is None:
            # right values elsewhere? -> year or arm misassignment, else missing.
            tv = tuple(trow.get(f) for f in NUMERIC_FIELDS)
            cand = pred_vals.get(tv, [])
            labeled = False
            for (psid, pyear, parm) in cand:
                if psid == key[0] and parm != key[2] and pyear == key[1]:
                    c["arm_matching_error"] += 1; labeled = True; break
                if psid == key[0] and pyear != key[1]:
                    c["year_misassignment"] += 1; labeled = True; break
            if not labeled:
                c["missing_row"] += 1
            continue
        # Cell-level mismatches on a matched row.
        for f in fields:
            pv, tv = prow.get(f), trow.get(f)
            if f in NUMERIC_FIELDS:
                if not _numeric_match(pv, tv, tol.get(f, 0.0)):
                    lit = (trow.get("literal") or {}).get(f) if isinstance(trow.get("literal"), dict) else None
                    if lit is not None:
                        # QA/QC analysis (requires literal sheet value).
                        if _numeric_match(pv, lit, tol.get(f, 0.0)) and not _numeric_match(lit, tv, tol.get(f, 0.0)):
                            c["qaqc_under_correction"] += 1  # kept the slip
                        elif _numeric_match(lit, tv, tol.get(f, 0.0)):
                            c["qaqc_over_correction"] += 1   # changed a correct value
                        else:
                            c["transcription_error"] += 1
                    else:
                        c["transcription_error"] += 1
            elif f == "saguaro_id":
                if not _saguaro_id_match(pv, tv):
                    c["saguaro_id_error"] += 1
            elif f == "note":
                if not _note_match(pv, tv):
                    c["note_error"] += 1
    return c


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--md", type=Path, default=None)
    ap.add_argument("--tasks-dir", type=Path, default=REPO / "tasks")
    args = ap.parse_args()

    index = {r["saguaro_id"]: r for r in
             json.loads((args.tasks_dir / "INDEX.json").read_text())}
    truth_cache: dict = {}
    has_literal = False
    per_model: dict[str, Counter] = {}

    for f in sorted(args.run_dir.glob("*.json")):
        if f.name in ("config.json", "leaderboard.json"):
            continue
        blob = json.loads(f.read_text())
        tag = blob.get("model_tag", f.stem)
        agg: Counter = Counter()
        for rec in blob.get("results", []):
            sid = rec.get("saguaro_id")
            if not index.get(sid, {}).get("headline_scored", True):
                continue
            if sid not in truth_cache:
                truth_cache[sid] = _truth(sid, args.tasks_dir)
                if any(isinstance(r.get("literal"), dict) for r in truth_cache[sid]["truth_rows"]):
                    has_literal = True
            agg += classify_rollout(rec, truth_cache[sid])
        per_model[tag] = agg

    all_classes = sorted({k for c in per_model.values() for k in c})
    lines = ["# Failure-class taxonomy\n"]
    if not has_literal:
        lines.append("> **QA/QC over/under-correction is `n/a`** — no `literal` sheet "
                     "values in truth yet. Add them (docs/REFRESH.md §QA-QC) to unlock "
                     "the over- vs under-correction split — the marquee finding.\n")
    header = "| model | " + " | ".join(all_classes) + " |"
    lines.append(header)
    lines.append("|---|" + "---|" * len(all_classes))
    for tag, c in sorted(per_model.items()):
        lines.append(f"| {tag} | " + " | ".join(str(c.get(k, 0)) for k in all_classes) + " |")
    out = "\n".join(lines) + "\n"
    print(out)
    (args.md or (args.run_dir / "failure_taxonomy.md")).write_text(out)
    print(f"[failure_taxonomy] wrote {args.run_dir / 'failure_taxonomy.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
