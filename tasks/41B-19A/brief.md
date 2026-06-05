# Saguaro 41B-19A

Plot coordinates: easting 525379, northing 3563246
Plant height: 6.85 m (2023) → 7.16 m (2026)
Stem diameter at 1 m: 0.51 m (2023) → 0.525 m (2026)

## 2023 arms (5 rows recorded 2023-11-01)

```
  Arm   1  direction   73°  A=2.83  B=0.96  C=3.14  D=0.93  E=0.45
  Arm   2  direction  120°  A=2.81  B=0.97  C=3.29  D=0.98  E=0.45
  Arm   3  direction  180°  A=2.46  B=0.99  C=4.17  D=1.06  E=0.75
  Arm   4  direction  270°  A=2.79  B=1  C=4.05  D=1.06  E=0.5
  Arm   5  direction  320°  A=2.75  B=1.02  C=3.7  D=1  E=0.6
```

## 2026 arms (5 rows recorded 2026-04-01)

```
  Arm   1  direction   69°  A=2.79  B=0.979  C=3.3  D=0.939  E=0.55
  Arm   2  direction  111°  A=2.74  B=0.961  C=3.47  D=1  E=0.66
  Arm   3  direction  170°  A=2.44  B=1.002  C=4.34  D=1.045  E=0.95
  Arm   4  direction  289°  A=2.775  B=1.06  C=3.8  D=1.09  E=0.55
  Arm   5  direction  310°  A=2.71  B=1.037  C=3.82  D=1.032  E=0.68
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

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4', '5']`. Values: a 2023 arm id from `['1', '2', '3', '4', '5']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
