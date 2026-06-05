# Saguaro 41B-08A

Plot coordinates: easting 525374, northing 3563295
Plant height: 4.53 m (2023) → 4.64 m (2026)
Stem diameter at 1 m: 0.43 m (2023) → 0.46 m (2026)

## 2023 arms (7 rows recorded 2023-11-01)

```
  Arm   1  direction   40°  A=1.98  B=1.01  C=2.55  D=1  E=0.35
  Arm   2  direction  160°  A=2.19  B=1  C=2.79  D=1.02  E=0.4
  Arm   3  direction  230°  A=1.99  B=1.01  C=2.11  D=1.02  E=0.1
  Arm   4  direction  240°  A=1.91  B=1.03  C=2.02  D=1.03  E=0.1
  Arm   5  direction  270°  A=2.18  B=0.96  C=2.35  D=1.03  E=0.15
  Arm   6  direction  320°  A=2.23  B=0.93  C=2.33  D=0.96  E=0.1
  Arm   7  direction  340°  A=1.93  B=1.01  C=2.38  D=1.04  E=0.35  note: Gash in cactus
```

## 2026 arms (9 rows recorded 2026-04-01)

```
  Arm   1  direction   50°  A=1.97  B=0.983  C=2.72  D=0.965  E=0.35
  Arm   2  direction  166°  A=2.18  B=0.945  C=2.985  D=0.97  E=0.38
  Arm   3  direction  182°  A=2.07  B=0.96  C=2.125  D=0.96  E=0.05
  Arm   4  direction  198°  A=1.97  B=0.95  C=1.995  D=0.95  E=0.03
  Arm   5  direction  220°  A=1.985  B=0.97  C=2.25  D=0.97  E=0.2
  Arm   6  direction  240°  A=1.89  B=0.978  C=2.14  D=0.98  E=0.2
  Arm   7  direction  266°  A=2.215  B=1.002  C=2.51  D=1.005  E=0.08
  Arm   8  direction  312°  A=2.33  B=1.01  C=2.48  D=1.01  E=0.3
  Arm   9  direction  352°  A=1.92  B=1.008  C=2.6  D=1.021  E=0.2
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

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4', '5', '6', '7', '8', '9']`. Values: a 2023 arm id from `['1', '2', '3', '4', '5', '6', '7']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
