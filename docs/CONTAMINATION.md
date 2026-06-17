# Contamination & provenance check

CactusBench is built on **real** Saguaro National Park plot-41B field data. If the
curated answer table or the underlying per-arm survey were reachable by a web
crawler, the test answers could already be in model pretraining corpora. This file records the check so it can
be re-run each release.

## Method

1. **Search for the dataset itself.** Query for the plot id + survey + year, and
   for distinctive value/term combinations from the truth table.
2. **Search for the raw artifacts.** The hand-redacted field sheets and photos are
   not published anywhere public; confirm no structured per-arm table is hosted on
   NPS DataStore / ScienceBase / GitHub.
3. **Strip asset metadata** (enforced at build — see below) so capture dates can't
   leak the year even if a crawler never had the table.

## Result (checked 2026-06-07)

- The saguaro-arms *methodology* and terminology are public — the NPS "Saguaro
  Arms Citizen Science Project" page, clinometer/compass measurement guides, and
  the definition of "nubbins" (arms < ~2 in) are all web-present.
- The **per-arm measurement table for plot 41B (direction / A–E heights / notes,
  matched across 2023 & 2026) is NOT web-present.** No NPS DataStore, ScienceBase,
  or GitHub artifact exposes the structured per-arm values that constitute the
  benchmark answers. General monitoring reports exist but contain no per-arm table.
- **Conclusion:** no evidence of answer contamination. The benchmark can only be
  solved by reading the recorder's handwriting on the bundled sheets.

Sources consulted:
- [NPS Saguaro Arms Citizen Science Project](https://home.nps.gov/sagu/learn/saguaro-arms-project.htm/index.htm)
- [NPS Long-term Saguaro Monitoring](https://www.nps.gov/sagu/learn/nature/long-term-monitoring.htm)
- [Desert Laboratory — Saguaro plots](https://desertlaboratory.arizona.edu/research/long-term-ecology/saguaro-plots)
- [NPS DataStore](https://irma.nps.gov/DataStore/) (no per-arm table located)

## Enforced asset-metadata strip

Every JPEG/PNG is run through `scripts/lib/scrub.py` at build time, which removes
EXIF (capture date, GPS), XMP, Photoshop/IPTC, and PNG text/time chunks, then
**asserts** the result is clean (`assert_clean`). The build fails if any metadata
marker survives. Verified state: **0/209 photos and 0/50 sheets** carry EXIF/XMP
or PNG text chunks.

## Re-running the check

```bash
# 1. assets are clean
python3 - <<'PY'
import sys, glob; sys.path.insert(0,'scripts/lib')
from scrub import assert_clean
for f in glob.glob('tasks/*/assets/**/*', recursive=True):
    if f.lower().endswith(('.png','.jpg','.jpeg')): assert_clean(f)
print("assets clean")
PY
# 2. re-search the web for the table (manual) and update the "Result" date above.
```

## Long-term defense

Contamination is a moving target. The durable defense is the **held-back-pool
rotation** the public set is a dev set, and the
scored test set is drawn fresh from the 184 held-back hand-redacted saguaros each
cycle, with test truth kept private — so even if the public slice leaks, the
scored numbers are computed on unseen data.
