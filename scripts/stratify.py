#!/usr/bin/env python3
"""Surface-stratification table for SaguaroBench (Cai §1 / guidance §1).

Given two or more run directories — each a DIFFERENT harness/route/image/reasoning
configuration of the same models — compute, per (model, saguaro) cell, the spread
(max - min mean reward) across configurations. A spread > 5pp flags the dataset as
scaffolding-sensitive at that cell, and the headline must declare which config it
is calibrated against.

This is the rigor artifact Cai says benchmarks surviving the next twelve months
will ship and most will not: the headline number is one draw from a distribution
whose width is measured here.

Usage:
    python scripts/stratify.py \
        --config claude_code=runs/cc_2026 \
        --config openrouter=runs/or_2026 \
        --config highres=runs/or_highres_2026
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FLAG_PP = 0.05  # >5pp spread flags the cell as scaffolding-sensitive


def _cell_means(run_dir: Path) -> dict:
    """(model_tag, saguaro_id) -> mean cell_accuracy_reward across rollouts."""
    out: dict = {}
    for f in run_dir.glob("*.json"):
        if f.name in ("config.json", "leaderboard.json"):
            continue
        blob = json.loads(f.read_text())
        tag = blob.get("model_tag", f.stem)
        per: dict = {}
        for r in blob.get("results", []):
            per.setdefault(r["saguaro_id"], []).append(r.get("cell_accuracy_reward", 0.0) or 0.0)
        for sid, vals in per.items():
            out[(tag, sid)] = sum(vals) / len(vals)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", action="append", required=True,
                    metavar="NAME=run_dir",
                    help="a named configuration, e.g. claude_code=runs/cc_2026 (repeat)")
    ap.add_argument("--md", type=Path, default=None)
    args = ap.parse_args()

    configs = {}
    for spec in args.config:
        name, _, path = spec.partition("=")
        configs[name] = _cell_means(Path(path))
    names = list(configs)

    keys = sorted(set().union(*[set(c) for c in configs.values()]))
    rows = []
    for key in keys:
        vals = {n: configs[n].get(key) for n in names}
        present = [v for v in vals.values() if v is not None]
        if len(present) < 2:
            continue
        spread = max(present) - min(present)
        rows.append({"model": key[0], "saguaro_id": key[1],
                     **{n: vals[n] for n in names},
                     "spread": round(spread, 4),
                     "scaffolding_sensitive": spread > FLAG_PP})

    rows.sort(key=lambda r: r["spread"], reverse=True)
    n_flag = sum(1 for r in rows if r["scaffolding_sensitive"])

    md = [f"# Surface-stratification ({' vs '.join(names)})\n",
          f"Configs: {', '.join(names)}. A cell is **scaffolding-sensitive** when "
          f"the cross-config spread exceeds {FLAG_PP*100:.0f}pp.\n",
          f"**{n_flag} / {len(rows)} cells are scaffolding-sensitive.** "
          f"{'⚠ the dataset is scaffolding-sensitive — declare the headline config.' if n_flag else 'Stable across configs.'}\n",
          "| model | saguaro | " + " | ".join(names) + " | spread | flag |",
          "|---|---|" + "---|" * len(names) + "---|---|"]
    for r in rows[:60]:
        cells = " | ".join(f"{r[n]:.3f}" if r[n] is not None else "—" for n in names)
        md.append(f"| {r['model']} | {r['saguaro_id']} | {cells} | "
                  f"{r['spread']:.3f} | {'⚠' if r['scaffolding_sensitive'] else ''} |")
    out = "\n".join(md) + "\n"
    print(out)
    if args.md:
        args.md.write_text(out)
        print(f"[stratify] wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
