# Saguaro 41B-05A

Plot coordinates: easting 525373, northing 3563316
Plant height: 5.84 m (2023) → 6.15 m (2026)
Stem diameter at 1 m: 0.46 m (2023) → 0.5 m (2026)

## 2023 arms (2 rows recorded 2023-11-01)

```
  Arm   1  direction   20°  A=2.44  B=1.04  C=2.6  D=1.02  E=0.15
  Arm   2  direction  190°  A=2.56  B=1.05  C=3.1  D=1.08  E=0.65
```

## 2026 arms (2 rows recorded 2026-03-10)

```
  Arm   1  direction   19°  A=2.45  B=1  C=2.71  D=0.98  E=0.35
  Arm   2 [nubbin]  direction  176°  A=2.51  B=0.98  C=3.28  D=1.05  E=0.75  note: possible nubbin in between 
```

## Photos available in /workspace/photos/

  2023: 4 photo(s)
    photos/2023/photo_1.jpg
    photos/2023/photo_2.jpg
    photos/2023/photo_3.jpg
    photos/2023/photo_4.jpg

  2026: 4 photo(s)
    photos/2026/photo_1.jpg
    photos/2026/photo_2.jpg
    photos/2026/photo_3.jpg
    photos/2026/photo_4.jpg

## Datasheets

- /workspace/datasheets/2023.png — hand-redacted volunteer field form
- /workspace/datasheets/2026.png — hand-redacted volunteer field form

## Output

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2']`. Values: a 2023 arm id from `['1', '2']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
