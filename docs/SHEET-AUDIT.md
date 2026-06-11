# Sheet-assignment audit — 2026 "10A-22" off-by-one

## The bug
The 2026 scan batch `Pl-41B_2026_10A-22__pNN.png` has a **leading "10A" page (p01)**
that the 2023 batch `Pl-41B_2023_11-22__pNN.png` does not. The source sheet-map
assigned 2026 pages as if both batches started at the same saguaro, so **every 2026
sheet in the 11–22 region is shifted +1** — each task was bundled its *neighbour's*
2026 sheet (often the A-sibling's). The 2023 sheets are unaffected (no leading page).

First caught on **41B-13**: its bundled 2026 sheet (p06) was saguaro **13A** (2 arms),
while 41B-13's truth has 10 arms — capping any score at ~33% (only the 5 correct 2023
rows solvable). The correct 2026 sheet (p05) is saguaro 13, 10 arms.

## Verification — 8 header anchors, all `correct = current − 1`
Read directly off the page headers (`Saguaro No.`):

| page | true saguaro | current map said | shift |
|---|---|---|---|
| p02 | 11 | 10 | −1 |
| p03 | 12 | 11 | −1 |
| p05 | 13 (full-page verified) | 12A | −1 |
| p06 | 13A (full-page verified) | 13 | −1 |
| p11 | 16 | 15A | −1 |
| p17 | 19 | 18A | −1 |
| p19 | 20 | 19A | −1 |
| p20 | 21 | 20 | −1 |

Uniform −1 across the whole p02–p20 span → applied to all affected tasks.

## Corrected map (applied via `SHEET_OVERRIDES` in `scripts/build_tasks.py`)

| task | 2026 was | 2026 now |
|---|---|---|
| 41B-11 | p03 | **p02** |
| 41B-12 | p04 | **p03** |
| 41B-13 | p06 | **p05** |
| 41B-15 | p10 | **p09** |
| 41B-16 | p12 | **p11** |
| 41B-16A | p13 | **p12** |
| 41B-18A | p17 | **p16** |
| 41B-19 | p18 | **p17** |
| 41B-19A | p19 | **p18** |
| 41B-20 | p20 | **p19** |
| 41B-21 | p21 | **p20** |

Unaffected: the **1–10 region** (41B-01…10A — verified 41B-04A/04 correct) and all
**2023** sheets.

## Redaction-leak audit — DONE, clean (2026-06-08)
- The 10 corrected sheets (p02/p03/p09/p11/p12/p16/p17/p18/p19/p20) are
  **byte-identical to the Vercel Blob `redacted/41B/...` versions** (uploaded
  2026-06-03) — the site-pulled redactions are already in place; no re-pull needed.
- **No value leaks.** Right margins carry only process stamps ("QA/QC <date>",
  "entered <date>", item "2)"); notes columns carry only legitimate nubbin
  descriptors ("Baseball", "Nubbin", "tennis ball") that belong in the truth. The
  two curation-active sheets (41B-16, 41B-18A) were checked at full resolution —
  clean.
- The **p05 "probably 3.88" leak was a one-off** (saguaro 13's real recorder error
  + visible correction), re-redacted via the web app and pulled. No other sheet has
  an analogous answer-overlay. **No further re-redaction required.**

## Boundary cases — DONE (2026-06-08)
- **41B-10** — already correct: it bundles `_1-10_p16`, verified to be **saguaro 10**
  (pick_sheet takes the first 2026 match; the stray `_10A-22_p02` is unused). No change.
- **41B-22** — fixed. The source map had no hand 2026 sheet (it fell back to a rotated
  auto-redacted scan). Page **p21** is verified to be saguaro 22's real 2026 hand sheet
  (6 arms incl. a "same base" double arm, matches truth, leak-free) — pinned via
  `SHEET_OVERRIDES`. Both years are now hand-redacted, so **41B-22 joins the headline
  set → 25/25 headline-scored** (was 24/25).

## Still open — optional
- **2023 spot-check.** The 2023 batch has no leading offset and 41B-13 + 41B-22 2023
  were verified correct, but a quick spot-check of 2–3 more 2023 sheets is cheap
  insurance.

## How it was fixed
- `SHEET_OVERRIDES` in `build_tasks.py` maps `(saguaro, year) → correct filename`,
  checked at `pick_sheet`. Extensible for the boundary cases above.
- `--only` was changed to **merge** `INDEX.json` (a partial rebuild previously
  clobbered the index to just the rebuilt tasks).
