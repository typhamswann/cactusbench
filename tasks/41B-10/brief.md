# Saguaro 41B-10

Plot coordinates: easting 525366, northing 3563363
Plant height: 5.22 m (2023) → 5.43 m (2026)
Stem diameter at 1 m: 0.42 m (2023) → 0.428 m (2026)

## 2023 arms (3 rows recorded 2023-10-25)

```
  Arm   1  direction   84°  A=2.78  B=0.97  C=3.69  D=0.96  E=0.35
  Arm   2  direction  152°  A=2.79  B=0.97  C=3.21  D=0.91  E=0.35
  Arm   3  direction  196°  A=2.84  B=0.99  C=2.96  D=0.96  E=0.15
```

## 2026 arms (6 rows recorded 2026-03-10)

```
  Arm   1  direction   70°  A=2.77  B=1  C=3.91  D=0.97  E=0.4
  Arm   2  direction  140°  A=2.79  B=0.96  C=3.41  D=0.96  E=0.35
  Arm   3  direction  200°  A=2.82  B=0.98  C=3.095  D=0.95  E=0.25
  Arm   4 [nubbin]  direction  210°  A=3.1  B=0.98  C=3.125  D=0.98  E=0.01  note: nubbin; lg marble
  Arm   5 [nubbin]  direction  258°  A=2.97  B=0.91  C=3.07  D=0.91  E=0.075  note: baseball+ nubbin
  Arm   6 [nubbin]  direction  270°  A=2.97  B=0.98  C=3.09  D=0.98  E=0.1  note: softball nubbin
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

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3', '4', '5', '6']`. Values: a 2023 arm id from `['1', '2', '3']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
