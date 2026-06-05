# Saguaro 41B-13

Plot coordinates: easting 525471, northing 3563323
Plant height: 5.94 m (2023) → 6.16 m (2026)
Stem diameter at 1 m: 0.44 m (2023) → 0.485 m (2026)

## 2023 arms (5 rows recorded 2023-10-25)

```
  Arm   1  direction  360°  A=1.89  B=0.98  C=2.04  D=0.98  E=0.2  note: 5 nubbins
  Arm   2  direction   50°  A=1.85  B=0.99  C=2.78  D=1.03  E=0.6  note: 5 nubbins
  Arm   3  direction  150°  A=2.02  B=1  C=3.68  D=0.98  E=0.6  note: 5 nubbins
  Arm   4  direction  200°  A=1.8  B=0.95  C=2.77  D=0.96  E=0.8  note: 5 nubbins
  Arm   5  direction  270°  A=1.81  B=0.94  C=2.84  D=0.92  E=0.6  note: 5 nubbins
```

## 2026 arms (10 rows recorded 2026-04-01)

```
  Arm   1  direction   57°  A=1.81  B=1.043  C=3  D=1.085  E=0.65
  Arm   2  direction   96°  A=1.895  B=1.03  C=2.075  D=1.04  E=0.19
  Arm   3  direction  111°  A=2.185  B=1.035  C=2.215  D=1.035  E=0.02
  Arm   4  direction  137°  A=2.13  B=1.04  C=2.14  D=1.04  E=0.02
  Arm   5  direction  156°  A=1.905  B=1.015  C=1.98  D=1.015  E=0.08
  Arm   6  direction  156°  A=1.98  B=1.01  C=3.88  D=1.044  E=0.55
  Arm   7  direction  198°  A=1.75  B=1.01  C=2.98  D=0.984  E=0.85
  Arm   8  direction  280°  A=1.74  B=0.965  C=3.7  D=0.967  E=0.68
  Arm   9  direction  305°  A=2.21  B=0.992  C=2.245  D=0.992  E=0.02
  Arm  10  direction  348°  A=1.82  B=1.005  C=2.12  D=1.01  E=0.3
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

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']`. Values: a 2023 arm id from `['1', '2', '3', '4', '5']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
