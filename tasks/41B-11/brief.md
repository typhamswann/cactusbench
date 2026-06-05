# Saguaro 41B-11

Plot coordinates: easting 525389, northing 3563344
Plant height: 4.87 m (2023) → 5.12 m (2026)
Stem diameter at 1 m: 0.415 m (2023) → 0.46 m (2026)

## 2023 arms (5 rows recorded 2023-10-25)

```
  Arm   1  direction   40°  A=2.08  B=0.99  C=2.62  D=1.01  E=0.5
  Arm   2  direction   80°  A=2.21  B=1.01  C=2.64  D=1.06  E=0.4
  Arm   3  direction  130°  A=2.02  B=1.02  C=2.8  D=1.06  E=0.6
  Arm   4  direction  155°  A=2.28  B=1.05  C=2.87  D=1.07  E=0.5
  Arm   5  direction  240°  A=2.23  B=1.06  C=3.32  D=1.1  E=0.8
```

## 2026 arms (5 rows recorded 2026-03-10)

```
  Arm   1  direction   40°  A=2.06  B=0.98  C=2.8  D=1.01  E=0.6
  Arm   2  direction   80°  A=2.19  B=0.98  C=2.845  D=1.01  E=0.45
  Arm   3  direction  110°  A=2  B=1  C=3  D=1.015  E=0.66
  Arm   4  direction  140°  A=2.26  B=1  C=3.07  D=1.03  E=0.55
  Arm   5  direction  240°  A=2.185  B=0.98  C=3.52  D=1.03  E=0.8
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

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4', '5']`. Values: a 2023 arm id from `['1', '2', '3', '4', '5']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
