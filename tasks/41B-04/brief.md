# Saguaro 41B-04

Plot coordinates: easting 525351, northing 3563310
Plant height: 6.12 m (2023) → 6.53 m (2026)
Stem diameter at 1 m: 0.455 m (2023) → 0.49 m (2026)

## 2023 arms (4 rows recorded 2023-11-01)

```
  Arm   1  direction   50°  A=2.68  B=0.97  C=3.53  D=0.82  E=0.55
  Arm   2  direction  180°  A=2.78  B=1.07  C=3.56  D=1.08  E=0.6
  Arm   3  direction  260°  A=3  B=1.35  C=None  D=None  E=None  note: Nubbin growing on top of other nub
  Arm   4  direction  290°  A=2.87  B=1.14  C=3.19  D=1.07  E=0.5
```

## 2026 arms (4 rows recorded 2026-03-10)

```
  Arm   1  direction   53°  A=2.67  B=1.01  C=3.73  D=0.89  E=0.55
  Arm   2  direction  151°  A=2.79  B=1.18  C=3.76  D=1.22  E=0.6
  Arm   3  direction  252°  A=2.99  B=1.21  C=3.34  D=1.24  E=0.22
  Arm   4  direction  280°  A=2.87  B=1.22  C=3.62  D=1.32  E=0.55
```

## Photos available in /workspace/photos/

  2023: 4 photo(s)
    photos/2023/photo_1.jpg  (E)
    photos/2023/photo_2.jpg  (N)
    photos/2023/photo_3.jpg  (S)
    photos/2023/photo_4.jpg  (W)

  2026: 9 photo(s)
    photos/2026/photo_1.jpg
    photos/2026/photo_2.jpg
    photos/2026/photo_3.jpg
    photos/2026/photo_4.jpg
    photos/2026/photo_5.jpg
    photos/2026/photo_6.jpg
    photos/2026/photo_7.jpg
    photos/2026/photo_8.jpg
    photos/2026/photo_9.jpg

## Datasheets

- /workspace/datasheets/2023.png — hand-redacted volunteer field form
- /workspace/datasheets/2026.png — hand-redacted volunteer field form

## Output

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4']`. Values: a 2023 arm id from `['1', '2', '3', '4']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
