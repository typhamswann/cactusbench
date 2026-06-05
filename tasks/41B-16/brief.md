# Saguaro 41B-16

Plot coordinates: easting 525434, northing 3563372
Plant height: 5.61 m (2023) → 5.88 m (2026)
Stem diameter at 1 m: 0.43 m (2023) → 0.47 m (2026)

## 2023 arms (2 rows recorded 2023-10-25)

```
  Arm   1  direction  120°  A=3.19  B=1.03  C=3.27  D=1.03  E=0.1  note: Both almost nubbins + one uncounted nubbin
  Arm   2  direction  140°  A=3.23  B=1.03  C=3.32  D=1.03  E=0.1  note: Both almost nubbins + one uncounted nubbin
```

## 2026 arms (3 rows recorded 2026-03-10)

```
  Arm   1  direction  114°  A=3.18  B=1.02  C=3.51  D=0.97  E=0.3
  Arm   2  direction  145°  A=3.22  B=0.98  C=3.57  D=0.92  E=0.3
  Arm   3  direction  315°  A=3.16  B=0.88  C=3.23  D=0.88  E=0.06
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

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3']`. Values: a 2023 arm id from `['1', '2']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
