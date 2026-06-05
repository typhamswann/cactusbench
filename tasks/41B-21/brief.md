# Saguaro 41B-21

Plot coordinates: easting 525393, northing 3563378
Plant height: 5.71 m (2023) → 5.66 m (2026)
Stem diameter at 1 m: 0.43 m (2023) → 0.442 m (2026)

## 2023 arms (7 rows recorded 2023-10-25)

```
  Arm   1  direction  340°  A=2.97  B=1  C=4.06  D=1.01  E=0.5
  Arm   2  direction   60°  A=2.8  B=1  C=3.88  D=1.03  E=0.6
  Arm   3  direction   90°  A=2.83  B=1.01  C=3.65  D=1.03  E=0.5
  Arm   4  direction  165°  A=2.82  B=1.01  C=3.92  D=1.04  E=0.5
  Arm   5  direction  190°  A=2.9  B=1.01  C=3.98  D=1  E=0.5
  Arm   6  direction  230°  A=2.79  B=1.01  C=3.41  D=0.91  E=0.6
  Arm   7  direction  260°  A=2.87  B=0.94  C=4.1  D=0.94  E=0.5
```

## 2026 arms (8 rows recorded 2026-03-10)

```
  Arm   1  direction   52°  A=2.79  B=1  C=4.05  D=1.02  E=0.65
  Arm   2  direction  105°  A=2.855  B=1.005  C=3.83  D=1.02  E=0.5
  Arm   3  direction  160°  A=2.82  B=1  C=4.08  D=1.005  E=0.55
  Arm   4  direction  188°  A=2.9  B=1  C=4.12  D=0.96  E=0.5
  Arm   5  direction  217°  A=2.79  B=0.98  C=3.33  D=0.68  E=0.6
  Arm   6  direction  250°  A=2.89  B=0.92  C=4.2  D=0.87  E=0.5
  Arm   8  direction  358°  A=2.96  B=0.97  C=4.18  D=1  E=0.55
  Arm   7 [nubbin]  direction  285°  A=2.99  B=0.93  C=3.07  D=0.93  E=0.05  note: baseball nubbin
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

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4', '5', '6', '8', '7']`. Values: a 2023 arm id from `['1', '2', '3', '4', '5', '6', '7']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
