# Saguaro 41B-15

Plot coordinates: easting 525499, northing 3563352
Plant height: 6.07 m (2023) → 6.59 m (2026)
Stem diameter at 1 m: 0.44 m (2023) → 0.47 m (2026)

## 2023 arms (7 rows recorded 2023-10-25)

```
  Arm   1  direction   20°  A=2.59  B=1  C=2.99  D=1.05  E=0.4
  Arm   2  direction   80°  A=2.59  B=1.02  C=3.85  D=1.1  E=0.6
  Arm   3  direction  120°  A=2.57  B=1  C=3.63  D=1.05  E=0.6
  Arm   4  direction  170°  A=2.49  B=0.94  C=3.5  D=0.95  E=0.6
  Arm   5  direction  230°  A=2.37  B=0.9  C=3.46  D=0.85  E=0.6
  Arm   6  direction  270°  A=2.48  B=0.9  C=3.28  D=0.87  E=0.5
  Arm   7  direction  310°  A=2.46  B=0.93  C=3.11  D=0.91  E=0.5
```

## 2026 arms (7 rows recorded 2026-04-01)

```
  Arm   1  direction   82°  A=2.59  B=1.075  C=4.04  D=1.144  E=0.65
  Arm   2  direction  120°  A=2.54  B=1.034  C=3.83  D=1.073  E=0.6
  Arm   3  direction  180°  A=2.44  B=0.96  C=3.71  D=0.946  E=0.65
  Arm   4  direction  240°  A=2.34  B=0.91  C=3.7  D=0.884  E=0.65
  Arm   5  direction  284°  A=2.47  B=0.91  C=3.47  D=0.872  E=0.5
  Arm   6  direction  292°  A=2.45  B=0.941  C=3.32  D=0.956  E=0.5
  Arm   7  direction  312°  A=2.565  B=1.01  C=3.15  D=1.049  E=0.4
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

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4', '5', '6', '7']`. Values: a 2023 arm id from `['1', '2', '3', '4', '5', '6', '7']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
