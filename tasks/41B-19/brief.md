# Saguaro 41B-19

Plot coordinates: easting 525375, northing 3563427
Plant height: 5.61 m (2023) → 5.79 m (2026)
Stem diameter at 1 m: 0.45 m (2023) → 0.45 m (2026)

## 2023 arms (3 rows recorded 2023-10-25)

```
  Arm   1  direction  290°  A=2.89  B=0.93  C=3.2  D=0.93  E=0.2  note: Uncounted nubbin
  Arm   2  direction  170°  A=2.98  B=1  C=3.83  D=1  E=0.4
  Arm   3  direction  220°  A=2.73  B=0.95  C=3.35  D=0.94  E=0.5
```

## 2026 arms (4 rows recorded 2026-03-10)

```
  Arm   1  direction  174°  A=3.02  B=0.98  C=3.99  D=0.96  E=0.47
  Arm   2  direction  223°  A=2.72  B=0.93  C=3.48  D=0.91  E=0.5
  Arm   3  direction  243°  A=2.91  B=0.92  C=2.95  D=0.93  E=0.3
  Arm   4  direction  283°  A=2.88  B=0.91  C=3.32  D=0.89  E=0.28
```

## Photos available in /workspace/photos/

  2023: 5 photo(s)
    photos/2023/photo_1.jpg
    photos/2023/photo_2.jpg
    photos/2023/photo_3.jpg
    photos/2023/photo_4.jpg
    photos/2023/photo_5.jpg

  2026: 4 photo(s)
    photos/2026/photo_1.jpg
    photos/2026/photo_2.jpg
    photos/2026/photo_3.jpg
    photos/2026/photo_4.jpg

## Datasheets

- /workspace/datasheets/2023.png — hand-redacted volunteer field form
- /workspace/datasheets/2026.png — hand-redacted volunteer field form

## Output

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4']`. Values: a 2023 arm id from `['1', '2', '3']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
