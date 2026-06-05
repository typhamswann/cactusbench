# Saguaro 41B-05

Plot coordinates: easting 525451, northing 3563369
Plant height: 6.33 m (2023) → 6.8 m (2026)
Stem diameter at 1 m: 0.43 m (2023) → 0.49 m (2026)

## 2023 arms (7 rows recorded 2023-10-25)

```
  Arm   1  direction    2°  A=1.11  B=0.96  C=2.42  D=1.04  E=0.45  note: Northside has a small drainage, southside packrat mound. Basketball sized hole
  Arm   2  direction   99°  A=2.17  B=0.6  C=3.51  D=0.83  E=0.66
  Arm   3  direction  140°  A=2.01  B=0.58  C=2.38  D=0.76  E=0.45
  Arm   4  direction  194°  A=2.33  B=0.79  C=3.13  D=0.66  E=0.75
  Arm   5  direction  209°  A=2.56  B=0.85  C=3.72  D=0.85  E=0.6
  Arm   6  direction  267°  A=2.84  B=0.98  C=3.56  D=1.06  E=0.5
  Arm   7  direction  311°  A=2.84  B=1.06  C=3.58  D=1.19  E=0.4
```

## 2026 arms (7 rows recorded 2026-04-01)

```
  Arm   1  direction    8°  A=1.12  B=1  C=2.7  D=1.109  E=0.41
  Arm   2  direction  134°  A=2.27  B=0.723  C=3.75  D=0.768  E=0.57
  Arm   3  direction  138°  A=2.1  B=0.704  C=2.51  D=0.79  E=0.6
  Arm   4  direction  173°  A=2.33  B=0.823  C=3.4  D=0.755  E=0.72
  Arm   5  direction  210°  A=2.54  B=0.97  C=3.9  D=0.87  E=0.55
  Arm   6  direction  268°  A=2.87  B=1.05  C=3.82  D=1.112  E=0.5
  Arm   7  direction  308°  A=2.92  B=1.169  C=3.85  D=1.195  E=0.5
```

## Photos available in /workspace/photos/

  2023: 4 photo(s)
    photos/2023/photo_1.jpg  (E)
    photos/2023/photo_2.jpg  (N)
    photos/2023/photo_3.jpg  (S)
    photos/2023/photo_4.jpg  (W)

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
