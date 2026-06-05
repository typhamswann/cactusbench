# Saguaro 41B-06

Plot coordinates: easting 525419, northing 3563454
Plant height: 8.89 m (2023) → 8.15 m (2026)
Stem diameter at 1 m: 0.47 m (2023) → 0.478 m (2026)

## 2023 arms (4 rows recorded 2023-10-25)

```
  Arm   1  direction   56°  A=4.2  B=0.96  C=4.53  D=0.96  E=0.25
  Arm   2  direction   92°  A=1.97  B=1  C=5.44  D=1.02  E=0.7
  Arm   3  direction  192°  A=None  B=None  C=None  D=None  E=None
  Arm   4  direction  270°  A=2.13  B=0.99  C=4.92  D=1.01  E=0.6
```

## 2026 arms (4 rows recorded 2026-04-01)

```
  Arm   1  direction   54°  A=4.22  B=1.026  C=4.59  D=1.026  E=0.25
  Arm   2  direction  104°  A=1.965  B=1.004  C=5.7  D=1.01  E=0.7
  Arm   3  direction  196°  A=5.21  B=0.93  C=6.94  D=0.93  E=0.725
  Arm   4  direction  273°  A=2.02  B=1  C=4.86  D=1  E=1
```

## Photos available in /workspace/photos/

  2023: 4 photo(s)
    photos/2023/photo_1.jpg  (E)
    photos/2023/photo_2.jpg  (N)
    photos/2023/photo_3.jpg  (S)
    photos/2023/photo_4.jpg  (W)

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

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4']`. Values: a 2023 arm id from `['1', '2', '3', '4']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
