# Saguaro 41B-18A

Plot coordinates: easting 525362, northing 3563278
Plant height: 6.13 m (2023) → 6.41 m (2026)
Stem diameter at 1 m: 0.5 m (2023) → 0.545 m (2026)

## 2023 arms (5 rows recorded 2023-11-01)

```
  Arm   1  direction  348°  A=2.73  B=1  C=3.55  D=0.93  E=0.65
  Arm   2  direction  140°  A=2.32  B=1.03  C=3.49  D=1.04  E=0.9
  Arm   3  direction  193°  A=2.54  B=1.03  C=4.05  D=1.09  E=0.65
  Arm   4  direction  250°  A=2.27  B=0.95  C=4.36  D=1.12  E=0.9
  Arm   5  direction  310°  A=2.16  B=0.97  C=4.32  D=1.04  E=0.8
```

## 2026 arms (6 rows recorded 2026-04-01)

```
  Arm   1  direction    5°  A=2.71  B=0.99  C=3.74  D=0.995  E=0.7
  Arm   2  direction  152°  A=2.3  B=1.057  C=3.7  D=1.08  E=0.95
  Arm   3  direction  160°  A=3.44  B=1.045  C=3.51  D=1.045  E=0.03
  Arm   4  direction  185°  A=2.53  B=1.053  C=4.27  D=1.125  E=0.7
  Arm   5  direction  230°  A=2.31  B=1.035  C=4.58  D=1.185  E=0.9
  Arm   6  direction  310°  A=2.15  B=1.003  C=4.53  D=1.067  E=0.9
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
