# Saguaro 41B-12

Plot coordinates: easting 525426, northing 3563346
Plant height: 7.31 m (2023) → 7.54 m (2026)
Stem diameter at 1 m: 0.5 m (2023) → 0.53 m (2026)

## 2023 arms (7 rows recorded 2023-10-25)

```
  Arm   1  direction  320°  A=2.38  B=0.96  C=5.04  D=0.94  E=0.5
  Arm   2  direction   40°  A=2.36  B=1  C=5.5  D=1.1  E=1.2
  Arm   3  direction  110°  A=2.3  B=0.99  C=5.38  D=1.11  E=1.1
  Arm   4  direction  180°  A=2.27  B=0.97  C=5.33  D=1.02  E=0.7
  Arm   5  direction  215°  A=2.22  B=0.95  C=5.49  D=0.99  E=0.8
  Arm   6  direction  270°  A=2.26  B=0.95  C=4.39  D=0.93  E=0.8
  Arm   7  direction  180°  A=4.35  B=0.98  C=5.16  D=0.99  E=0.3
```

## 2026 arms (8 rows recorded 2026-03-10)

```
  Arm   1  direction   40°  A=2.44  B=0.99  C=5.68  D=1.05  E=1.4
  Arm   2  direction   98°  A=2.28  B=0.98  C=5.58  D=1.02  E=1.4
  Arm   3  direction  143°  A=4.32  B=0.99  C=5.31  D=0.99  E=2.5
  Arm   4  direction  163°  A=2.26  B=0.99  C=5.53  D=1  E=0.6
  Arm   5  direction  184°  A=2.31  B=0.98  C=2.34  D=0.98  E=0.03
  Arm   6  direction  220°  A=2.23  B=0.97  C=5.54  D=0.92  E=0.8
  Arm   7  direction  259°  A=2.24  B=0.945  C=4.54  D=0.88  E=0.8
  Arm   8  direction  336°  A=2.38  B=0.96  C=5.18  D=0.96  E=0.5
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

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4', '5', '6', '7', '8']`. Values: a 2023 arm id from `['1', '2', '3', '4', '5', '6', '7']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
