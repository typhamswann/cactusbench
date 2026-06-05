# Saguaro 41B-09A

Plot coordinates: easting 525384, northing 3563389
Plant height: 5.7 m (2023) → 5.9 m (2026)
Stem diameter at 1 m: 0.51 m (2023) → 0.55 m (2026)

## 2023 arms (5 rows recorded 2023-10-25)

```
  Arm   1  direction  141°  A=2.42  B=1  C=3.83  D=1.03  E=0.45
  Arm   2  direction  176°  A=2.19  B=0.99  C=3.67  D=0.98  E=0.75
  Arm   3  direction  220°  A=2.25  B=0.95  C=3.63  D=0.94  E=0.7
  Arm   4  direction  280°  A=2.39  B=0.94  C=3.01  D=0.94  E=0.4
  Arm   5  direction  338°  A=2.31  B=0.98  C=3.64  D=0.98  E=0.55
```

## 2026 arms (6 rows recorded 2026-03-10)

```
  Arm   2  direction  153°  A=2.44  B=0.99  C=4.01  D=1  E=0.6
  Arm   3  direction  180°  A=2.19  B=0.99  C=3.875  D=0.97  E=0.85
  Arm   4  direction  232°  A=2.24  B=0.96  C=3.81  D=0.95  E=0.8
  Arm   5  direction  292°  A=2.41  B=0.99  C=3.14  D=0.97  E=0.5
  Arm   6  direction  352°  A=2.335  B=1.015  C=3.78  D=1.04  E=0.6
  Arm   1 [nubbin]  direction   69°  A=4.41  B=1.005  C=4.45  D=1.005  E=0.02  note: nubbin ping-pong
```

## Photos available in /workspace/photos/

  2023: 4 photo(s)
    photos/2023/photo_1.jpg  (E)
    photos/2023/photo_2.jpg  (N)
    photos/2023/photo_3.jpg  (S)
    photos/2023/photo_4.jpg  (W)

  2026: 8 photo(s)
    photos/2026/photo_1.jpg
    photos/2026/photo_2.jpg
    photos/2026/photo_3.jpg
    photos/2026/photo_4.jpg
    photos/2026/photo_5.jpg
    photos/2026/photo_6.jpg
    photos/2026/photo_7.jpg
    photos/2026/photo_8.jpg

## Datasheets

- /workspace/datasheets/2023.png — hand-redacted volunteer field form
- /workspace/datasheets/2026.png — hand-redacted volunteer field form

## Output

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['2', '3', '4', '5', '6', '1']`. Values: a 2023 arm id from `['1', '2', '3', '4', '5']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
