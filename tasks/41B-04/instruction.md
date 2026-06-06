# Curate this saguaro

Two biologists measured this saguaro on a plot at Saguaro National Park: one in 2023, one in 2026. Each produced a handwritten field-form recording per-arm measurements. Your job is to take in both years' raw sheets + photos and produce one cleaned spreadsheet: matched arms across years, canonical arm numbers, every measurement and note re-keyed into the canonical schema. It should be clean and accurate, following what the biologist in the field intended.

## Measurement columns

Each arm has, per year:

- `direction` — compass bearing from main stem out to the arm, degrees (0=N, 90=E, 180=S, 270=W).
- `A` — height in meters from the ground to where the arm emerges from the main stem.
- `B` — height in meters from the ground to a 1-meter datum mark on the stem near where A was measured.
- `C` — height from the ground to the tip of the arm.
- `D` — height from the ground to a 1-meter datum mark on the stem near where C was measured.
- `E` — horizontal distance in meters from the main stem to the arm tip.
- `note` — recorder annotation (e.g. "5 nubbins", "arm broke off", "tag 69"). Use `""` if none.

Saguaro arms grow slowly. They rarely shrink. New arms can emerge between surveys; existing arms only rarely disappear.

## Inputs

`/workspace/datasheets/` — 2 field forms. One sheet covers each year. The arm numbers visible are the volunteer's paper-arm numbers, which may differ between years. The 2023 arm numbers are the canonical arm number labels for both years. 2026 arms must be recorded by matching and using the canonical arm number.

`/workspace/photos/` — 13 field photo(s). Years are mixed and not annotated. Photos help disambiguate arm matching when two arms are at similar directions or when the digitized measurements are inconclusive.

## Output

Write your cleaned table to `/workspace/submission.json` as a JSON list of row objects. Each row has these fields:

```
saguaro_id   string  — formatted <Plot>-<Saguaro #>
year         int
arm          string  — canonical arm number
direction    number  — compass bearing from main stem, degrees (0–360)
A            number  — height where arm emerges from main stem, meters
B            number  — datum-mark height near A, meters
C            number  — arm-tip height, meters
D            number  — datum-mark height near C, meters
E            number  — horizontal distance from main stem to arm tip, meters
note         string  — recorder note (use "" if none)
```

Example row: {"saguaro_id": "41B-13", "year": 2023, "arm": "1", "direction": 360, "A": 1.89, "B": 0.98, "C": 2.04, "D": 0.98, "E": 0.2, "note": ""}

You must return data which you think is accurate to the real world above all. Part of your job QA/QC, so your curated data may vary from what biologists record in the sheet if their recordings were inaccurate or a mistake was made.
