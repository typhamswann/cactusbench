# Saguaro 41B-06A

Plot coordinates: easting 525370, northing 3563312
Plant height: 5.6 m (2023) → 5.75 m (2026)
Stem diameter at 1 m: 0.45 m (2023) → 0.52 m (2026)

## 2023 arms (5 rows recorded 2023-11-01)

```
  Arm   1  direction   40°  A=2.66  B=1.03  C=3.4  D=1.05  E=0.5
  Arm   2  direction  100°  A=2.67  B=0.98  C=3.02  D=0.93  E=0.35
  Arm   3  direction  130°  A=2.66  B=0.98  C=3  D=0.95  E=0.35
  Arm   4  direction  180°  A=2.58  B=0.99  C=3.51  D=0.93  E=0.7
  Arm   5  direction  230°  A=2.61  B=1.01  C=3.49  D=1.01  E=0.6
```

## 2026 arms (7 rows recorded 2026-03-10)

```
  Arm   1  direction   42°  A=2.645  B=0.98  C=3.56  D=1  E=0.45
  Arm   2  direction   86°  A=2.66  B=0.91  C=3.23  D=0.9  E=0.4
  Arm   3  direction  124°  A=2.64  B=0.91  C=3.15  D=0.89  E=0.45
  Arm   4  direction  178°  A=2.58  B=0.94  C=3.66  D=0.88  E=0.9
  Arm   5  direction  222°  A=2.6  B=0.96  C=3.59  D=0.94  E=0.6
  Arm   6  direction  307°  A=2.84  B=1.01  C=2.97  D=1.01  E=1.5
  Arm   7  direction  323°  A=2.85  B=1.01  C=2.9  D=1.01  E=0.5
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

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4', '5', '6', '7']`. Values: a 2023 arm id from `['1', '2', '3', '4', '5']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
