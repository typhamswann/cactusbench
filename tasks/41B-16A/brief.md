# Saguaro 41B-16A

Plot coordinates: easting 525364, northing 3563275
Plant height: 4.55 m (2023) → 4.785 m (2026)
Stem diameter at 1 m: 0.41 m (2023) → 0.445 m (2026)

## 2023 arms (3 rows recorded 2023-11-01)

```
  Arm   1  direction   30°  A=2.29  B=0.96  C=3.31  D=0.95  E=0.7
  Arm   2  direction  120°  A=2.55  B=0.98  C=2.94  D=0.96  E=0.35
  Arm   3  direction  160°  A=2.5  B=0.98  C=3.07  D=0.99  E=0.4
```

## 2026 arms (3 rows recorded 2026-04-01)

```
  Arm   1  direction  125°  A=2.55  B=1.03  C=3.11  D=1.001  E=0.3
  Arm   2  direction  160°  A=2.495  B=1.01  C=3.285  D=1.065  E=0.45
  Arm   3  direction  340°  A=2.27  B=0.993  C=3.5  D=1.01  E=0.55
```

## Photos available in /workspace/photos/

  2023: 4 photo(s)
    photos/2023/photo_1.jpg
    photos/2023/photo_2.jpg
    photos/2023/photo_3.jpg
    photos/2023/photo_4.jpg

  2026: 5 photo(s)
    photos/2026/photo_1.jpg
    photos/2026/photo_2.jpg
    photos/2026/photo_3.jpg
    photos/2026/photo_4.jpg
    photos/2026/photo_5.jpg

## Datasheets

- /workspace/datasheets/2023.png — hand-redacted volunteer field form
- /workspace/datasheets/2026.png — hand-redacted volunteer field form

## Output

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3']`. Values: a 2023 arm id from `['1', '2', '3']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
