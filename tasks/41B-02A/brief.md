# Saguaro 41B-02A

Plot coordinates: easting 525317, northing 3563376
Plant height: 5.52 m (2023) → 5.69 m (2026)
Stem diameter at 1 m: 0.46 m (2023) → 0.49 m (2026)

## 2023 arms (3 rows recorded 2023-11-01)

```
  Arm   1  direction  130°  A=2.68  B=0.97  C=3.02  D=0.98  E=0.4
  Arm   2  direction  240°  A=2.61  B=1.05  C=3.99  D=1.14  E=0.7
  Arm   3  direction  310°  A=2.73  B=1.03  C=3.05  D=0.97  E=0.5
```

## 2026 arms (3 rows recorded 2026-03-10)

```
  Arm   1  direction  139°  A=2.68  B=1.02  C=3.18  D=0.97  E=0.4
  Arm   2  direction  221°  A=2.6  B=1.06  C=4.24  D=1.15  E=0.7
  Arm   3  direction  297°  A=2.71  B=1.04  C=3.34  D=1.07  E=0.48
```

## Photos available in /workspace/photos/

  2023: 4 photo(s)
    photos/2023/photo_1.jpg
    photos/2023/photo_2.jpg
    photos/2023/photo_3.jpg
    photos/2023/photo_4.jpg

  2026: 8 photo(s)
    photos/2026/photo_1.jpg
    photos/2026/photo_2.jpg
    photos/2026/photo_3.jpg
    photos/2026/photo_4.jpg
    photos/2026/photo_5.jpg
    photos/2026/photo_6.jpg
    photos/2026/photo_7.jpg
    photos/2026/photo_8.jpg

## Datasheets

- /workspace/datasheets/2023.png — hand-redacted volunteer field form
- /workspace/datasheets/2026.png — hand-redacted volunteer field form

## Output

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3']`. Values: a 2023 arm id from `['1', '2', '3']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
