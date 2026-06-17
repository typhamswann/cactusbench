#!/usr/bin/env python3
"""Aggregate a CactusBench run into a defensible leaderboard (stdlib only).

Turns the per-rollout records in runs/<run-id>/*.json into the report shape a single-number leaderboard does not provide:

  * RAW vs ENGAGED-subset means — open-weight models that hit the
    empty-response terminator score 0 with no real attempt; both are reported.
  * Bootstrap 95% CIs over tasks — no point estimate without an interval.
  * Cell-level accuracy with an explicit "cells within a saguaro are correlated"
    caveat — real n without overclaiming independence.
  * Per-difficulty breakdown with per-bucket n — a single mean over a
    68%-medium set hides everything; the degenerate 1-task "easy" bucket is shown
    with its n so it can't masquerade as a real number.
  * Note accuracy conditioned on NON-EMPTY truth notes.
  * Cost + reward-per-dollar + latency Pareto.
  * Headline restricted to headline_scored tasks (year-invariant redaction).

Usage:
    python scripts/aggregate.py runs/<run-id>            # all model files
    python scripts/aggregate.py runs/<run-id> --md report.md
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
random.seed(20260607)  # deterministic bootstrap


def _load_index(tasks_dir: Path) -> dict:
    idx = json.loads((tasks_dir / "INDEX.json").read_text())
    return {r["saguaro_id"]: r for r in idx}


def _bootstrap_ci(values: list[float], n_boot: int = 2000, alpha: float = 0.05):
    """95% CI of the mean by resampling the list of per-task means."""
    if not values:
        return (None, None)
    n = len(values)
    means = []
    for _ in range(n_boot):
        sample = [values[random.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[int((1 - alpha / 2) * n_boot)]
    return (round(lo, 4), round(hi, 4))


def _task_means(records: list[dict]) -> dict:
    """saguaro_id -> mean cell_accuracy_reward across its rollouts."""
    by: dict[str, list[float]] = {}
    for r in records:
        by.setdefault(r["saguaro_id"], []).append(r.get("cell_accuracy_reward", 0.0) or 0.0)
    return {sid: sum(v) / len(v) for sid, v in by.items()}


def summarize_model(model_file: Path, index: dict) -> dict:
    blob = json.loads(model_file.read_text())
    records = blob.get("results", [])
    tag = blob.get("model_tag", model_file.stem)

    # Restrict the headline to headline_scored tasks (year-invariant redaction).
    headline = [r for r in records
                if index.get(r["saguaro_id"], {}).get("headline_scored", True)]
    engaged = [r for r in headline if r.get("engaged")]

    def mean(recs):
        return sum(r.get("cell_accuracy_reward", 0.0) or 0.0 for r in recs) / max(1, len(recs))

    raw_task_means = list(_task_means(headline).values())
    eng_task_means = list(_task_means(engaged).values())

    # Per-difficulty (headline tasks).
    by_diff: dict[str, list[float]] = {}
    for r in headline:
        d = index.get(r["saguaro_id"], {}).get("difficulty", "unknown")
        by_diff.setdefault(d, []).append(r.get("cell_accuracy_reward", 0.0) or 0.0)

    # Cell-level accuracy (sum correct / total over all headline rollouts).
    cell_correct = cell_total = 0
    note_ne_correct = note_ne_total = 0
    for r in headline:
        pf = r.get("per_field_accuracy") or {}
        rt = r.get("rows_truth") or 0
        # reconstruct correct/total from base_cell_accuracy is lossy; use per-field.
        for f, acc in pf.items():
            cell_total += rt
            cell_correct += round((acc or 0.0) * rt)
        nnt = r.get("note_nonempty_total") or 0
        nna = r.get("note_accuracy_nonempty")
        if nnt and nna is not None:
            note_ne_total += nnt
            note_ne_correct += round(nna * nnt)

    cost = blob.get("cost_usd", 0.0)
    n_roll = len(headline)
    lat = [r.get("wall_time_sec", 0.0) for r in headline if r.get("wall_time_sec")]
    lat.sort()
    median_lat = lat[len(lat) // 2] if lat else None

    raw_mean = mean(headline)
    return {
        "model_tag": tag,
        "model_slug": blob.get("model_slug"),
        "served_providers": blob.get("served_providers"),
        "pin_provider": blob.get("pin_provider"),
        "reasoning": blob.get("reasoning"),
        "rollouts": blob.get("rollouts", 1),
        "n_rollouts_headline": n_roll,
        "n_tasks_headline": len(set(r["saguaro_id"] for r in headline)),
        "raw_mean": round(raw_mean, 4),
        "raw_ci95": _bootstrap_ci(raw_task_means),
        "engaged_mean": round(mean(engaged), 4),
        "engaged_ci95": _bootstrap_ci(eng_task_means),
        "n_engaged": len(engaged),
        "n_shimmed": sum(1 for r in headline if r.get("terminator_shimmed")),
        "n_provider_mismatch": sum(1 for r in headline if r.get("provider_mismatch")),
        "cell_level_accuracy": round(cell_correct / max(1, cell_total), 4),
        "note_accuracy_nonempty": (round(note_ne_correct / note_ne_total, 4)
                                   if note_ne_total else None),
        "note_nonempty_n": note_ne_total,
        "per_difficulty": {d: {"mean": round(sum(v) / len(v), 4), "n": len(v)}
                           for d, v in sorted(by_diff.items())},
        "cost_usd": round(cost, 4),
        "reward_per_usd": round(raw_mean / cost, 3) if cost else None,
        "median_latency_sec": median_lat,
        "excluded_nonheadline_tasks": sorted(
            set(r["saguaro_id"] for r in records) -
            set(r["saguaro_id"] for r in headline)),
    }


def render_md(rows: list[dict]) -> str:
    rows = sorted(rows, key=lambda r: r["raw_mean"], reverse=True)
    out = ["# CactusBench leaderboard\n",
           "Headline = `cell_accuracy_reward` over **headline-scored** tasks "
           "(both years hand-redacted). CIs are 95% bootstrap over tasks. "
           "Cell-level accuracy is shown for reference but **cells within a saguaro "
           "are correlated** — do not read it as independent n.\n",
           "| model | raw mean (95% CI) | engaged mean (95% CI) | shim | "
           "note≠∅ | $/run | reward/$ | med lat | route |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ci = r["raw_ci95"]; eci = r["engaged_ci95"]
        ci_s = f"[{ci[0]:.3f}, {ci[1]:.3f}]" if ci[0] is not None else "—"
        eci_s = f"[{eci[0]:.3f}, {eci[1]:.3f}]" if eci[0] is not None else "—"
        note = f"{r['note_accuracy_nonempty']:.2f} (n={r['note_nonempty_n']})" \
            if r["note_accuracy_nonempty"] is not None else "—"
        out.append(
            f"| {r['model_tag']} | {r['raw_mean']:.3f} {ci_s} | "
            f"{r['engaged_mean']:.3f} {eci_s} | {r['n_shimmed']} | {note} | "
            f"${r['cost_usd']:.2f} | {r['reward_per_usd'] or '—'} | "
            f"{r['median_latency_sec'] or '—'}s | {','.join(r['served_providers'] or []) or '—'} |")
    out.append("\n## Per-difficulty (headline tasks)\n")
    out.append("| model | " + " | ".join(["easy", "medium", "hard"]) + " |")
    out.append("|---|---|---|---|")
    for r in rows:
        cells = []
        for d in ("easy", "medium", "hard"):
            pd = r["per_difficulty"].get(d)
            cells.append(f"{pd['mean']:.3f} (n={pd['n']})" if pd else "—")
        out.append(f"| {r['model_tag']} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--md", type=Path, default=None, help="write a markdown leaderboard here")
    ap.add_argument("--tasks-dir", type=Path, default=REPO / "tasks",
                    help="task root the run was scored against (for INDEX.json join)")
    args = ap.parse_args()
    index = _load_index(args.tasks_dir)
    model_files = sorted(p for p in args.run_dir.glob("*.json")
                         if p.name not in ("config.json", "leaderboard.json"))
    rows = [summarize_model(f, index) for f in model_files]
    out_json = args.run_dir / "leaderboard.json"
    out_json.write_text(json.dumps(rows, indent=2))
    md = render_md(rows)
    (args.md or (args.run_dir / "leaderboard.md")).write_text(md)
    print(md)
    print(f"[aggregate] wrote {out_json} and leaderboard.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
