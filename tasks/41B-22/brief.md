# Saguaro 41B-22

Plot coordinates: easting 525369, northing 3563372
Plant height: 7.25 m (2023) → 7.38 m (2026)
Stem diameter at 1 m: 0.46 m (2023) → 0.48 m (2026)

## 2023 arms (5 rows recorded 2023-10-25)

```
  Arm   1  direction  320°  A=2.7  B=0.97  C=3.47  D=1.02  E=0.3  note: Secondary appendage growing out of arm, narrower and further from trunk
  Arm   2  direction   50°  A=2.84  B=1.01  C=3.82  D=1.03  E=0.5  note: Arm on Arm!!
  Arm   3  direction  110°  A=2.9  B=0.98  C=3.91  D=1.01  E=0.5
  Arm   4  direction  220°  A=3.1  B=0.91  C=4.05  D=0.89  E=0.5
  Arm   5  direction  240°  A=2.8  B=0.89  C=3.1  D=0.89  E=0.2
```

## 2026 arms (6 rows recorded 2026-04-01)

```
  Arm   1  direction   46°  A=2.85  B=1.045  C=3.97  D=1.075  E=0.45
  Arm   2  direction   98°  A=2.92  B=1.033  C=4.1  D=1.073  E=0.4
  Arm   3  direction  226°  A=3.02  B=0.925  C=4.07  D=0.925  E=0.4
  Arm   4  direction  259°  A=2.8  B=0.92  C=3.21  D=0.919  E=0.35
  Arm   5  direction  322°  A=2.26  B=0.986  C=3.68  D=1.04  E=0.25
  Arm   6  direction  322°  A=2.26  B=0.986  C=2.96  D=1.019  E=0.7
```

## Photos available in /workspace/photos/

  2023: 4 photo(s)
    photos/2023/photo_1.jpg
    photos/2023/photo_2.jpg
    photos/2023/photo_3.jpg
    photos/2023/photo_4.jpg

  2026: 6 photo(s)
    photos/2026/photo_1.jpg
    photos/2026/photo_2.jpg
    photos/2026/photo_3.jpg
    photos/2026/photo_4.jpg
    photos/2026/photo_5.jpg
    photos/2026/photo_6.jpg

## Datasheets

- /workspace/datasheets/2023.png — hand-redacted volunteer field form
- /workspace/datasheets/2026.png — hand-redacted volunteer field form

## Output

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4', '5', '6']`. Values: a 2023 arm id from `['1', '2', '3', '4', '5']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
