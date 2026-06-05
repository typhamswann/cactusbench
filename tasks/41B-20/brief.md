# Saguaro 41B-20

Plot coordinates: easting 525376, northing 3563423
Plant height: 5.9 m (2023) → 6.06 m (2026)
Stem diameter at 1 m: 0.47 m (2023) → 0.5 m (2026)

## 2023 arms (5 rows recorded 2023-10-25)

```
  Arm   1  direction  300°  A=2.92  B=0.93  C=3.1  D=0.93  E=0.2
  Arm   2  direction  120°  A=2.86  B=0.99  C=3.65  D=1.03  E=0.5
  Arm   3  direction  165°  A=2.87  B=0.93  C=3.8  D=0.96  E=0.5
  Arm   4  direction  225°  A=2.58  B=0.92  C=2.92  D=0.9  E=0.3
  Arm   5  direction  250°  A=3.03  B=0.92  C=3.27  D=0.9  E=0.3
```

## 2026 arms (5 rows recorded 2026-03-10)

```
  Arm   1  direction  138°  A=2.89  B=1.03  C=3.8  D=1.1  E=0.54
  Arm   2  direction  165°  A=2.9  B=0.96  C=3.96  D=0.97  E=0.51
  Arm   3  direction  225°  A=2.59  B=0.92  C=3.06  D=0.91  E=0.35
  Arm   4  direction  256°  A=3.03  B=0.92  C=3.36  D=0.88  E=0.35
  Arm   5  direction  290°  A=2.93  B=0.93  C=3.15  D=0.95  E=0.3
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
