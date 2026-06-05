# Saguaro 41B-01A

Plot coordinates: easting 525350, northing 3563354
Plant height: 5.14 m (2023) → 5.44 m (2026)
Stem diameter at 1 m: 0.375 m (2023) → 0.428 m (2026)

## 2023 arms (2 rows recorded 2023-11-01)

```
  Arm   1  direction  140°  A=3.14  B=0.96  C=3.68  D=1.02  E=0.4
  Arm   2  direction  200°  A=3.08  B=0.93  C=3.52  D=0.91  E=0.4
```

## 2026 arms (2 rows recorded 2026-03-10)

```
  Arm   1  direction  129°  A=3.12  B=0.97  C=3.95  D=1  E=0.3
  Arm   2  direction  207°  A=3.065  B=0.955  C=3.75  D=0.98  E=0.35
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
