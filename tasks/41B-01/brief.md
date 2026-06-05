# Saguaro 41B-01

Plot coordinates: easting 525386, northing 3563327
Plant height: 7.12 m (2023) → 7.2 m (2026)
Stem diameter at 1 m: 0.49 m (2023) → 0.52 m (2026)

## 2023 arms (4 rows recorded 2023-10-25)

```
  Arm   1  direction    4°  A=2.86  B=1  C=4.4  D=1  E=0.9
  Arm   2  direction  126°  A=2.73  B=0.99  C=4.44  D=0.97  E=0.8
  Arm   3  direction  180°  A=2.89  B=1  C=4.87  D=1.03  E=0.8
  Arm   4  direction  233°  A=2.95  B=1.03  C=4.79  D=1.09  E=0.9  note: another arm smaller than softball growing near
```

## 2026 arms (5 rows recorded 2026-03-10)

```
  Arm   1  direction    9°  A=2.82  B=0.99  C=4.61  D=0.98  E=0.8
  Arm   2  direction  143°  A=2.72  B=1  C=4.55  D=0.99  E=0.77
  Arm   3  direction  171°  A=2.91  B=1.01  C=5.11  D=1.04  E=0.73
  Arm   4  direction  209°  A=3.18  B=1.01  C=3.34  D=1.01  E=0.1
  Arm   5  direction  231°  A=2.97  B=1.01  C=5.05  D=1.03  E=0.85
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

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4', '5']`. Values: a 2023 arm id from `['1', '2', '3', '4']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
