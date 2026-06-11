# Refresh & rotation policy

The single design choice that defeats contamination over time (Cai's 4th pillar):
**the public slice is a dev set; the scored test set is drawn fresh from a
held-back pool each cycle, with test truth kept private.**

## The pool

The full curation dataset is **217 saguaros across 7 plots** (15, 28, 40, 41B, 41F,
6, RT) in `curation_dataset_v2.json`. Of these, **184 are fully hand-redacted on
both years** (the eligibility bar — RT's 23 are not yet hand-redacted and are
excluded). The public benchmark is the **25-saguaro 41B slice** (`tasks/`), which
serves as the **dev set**.

That leaves **~159 held-back hand-redacted saguaros** to draw scored test cycles
from. Photos exist only for the 41B set, so non-41B draws are **sheets-only** —
which is cleaner anyway (it removes the photo-availability confound).

## Drawing a private test cycle

```bash
# Draw 30 saguaros from the held-back pool with rotation seed 'cycle-2'.
python scripts/build_tasks.py --draw-test 30 --seed cycle-2 --clean
# -> writes tasks_test/<sid>/ + tasks_test/INDEX.json + tasks_test/CYCLE.json
```

- Eligible = in v2, **both years hand-redacted**, and **not** in the public 25.
- The draw is a seeded shuffle, so a given seed is reproducible; changing the seed
  draws a different set.
- Difficulty for pool saguaros is derived from canonical-arm count
  (`≤2 easy / ≤6 medium / >6 hard`) since they lack a curator rating.
- `tasks_test/` contains **truth** — keep it OUT of the public repo. Add
  `tasks_test/` to `.gitignore` (already done) and store it privately.

## Cadence

- **Per release cycle:** draw a fresh test set with a new seed; score models on it;
  publish only aggregate numbers + the seed (not the truth).
- Keep the public 25 frozen as the dev set so iteration is reproducible and the
  prompt/scorer can be tuned without touching scored data.
- Rotate the seed whenever there is reason to believe the prior test set may have
  leaked (e.g., a model was trained after your publication date).

## QA-QC literal-value pass (unlocks the marquee finding)

The over- vs under-correction taxonomy (Cai §7 — "smarter models score worse
because they overthink the recorder's intent") needs, for every row where the
curated value diverges from the literal sheet, **both** values recorded:

```json
{
  "saguaro_id": "41B-XX", "year": 2026, "arm": "3",
  "A": 2.13,                       // curated (the scored truth)
  "literal": {"A": 21.3},          // what the sheet literally says (the slip)
  "qaqc": true
}
```

`build_tasks.py` passes any `literal` / `qaqc` keys straight through into
`truth.json`, and `scripts/failure_taxonomy.py` already reads them:

- **over-correction** — model changed a value where `literal == curated`
  (no correction was needed).
- **under-correction** — model reproduced `literal` where `literal != curated`
  (it kept the recorder's slip the curator had fixed).

Until the curator adds `literal` values, the taxonomy reports those two classes as
`n/a (no literal data)`. This is the one feature gated on data collection, not code
— everything downstream is built and waiting.
