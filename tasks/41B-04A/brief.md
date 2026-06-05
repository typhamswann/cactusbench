# Saguaro 41B-04A

Plot coordinates: easting 525481, northing 3563378
Plant height: 5.35 m (2023) → 5.35 m (2026)
Stem diameter at 1 m: 0.435 m (2023) → 0.46 m (2026)

## 2023 arms (3 rows recorded 2023-10-25)

```
  Arm   1  direction    0°  A=2.33  B=1  C=3.36  D=1.06  E=0.6
  Arm   2  direction  128°  A=2.33  B=0.98  C=3.14  D=0.95  E=0.55
  Arm   3  direction  170°  A=2.37  B=0.98  C=2.95  D=0.96  E=0.5
```

## 2026 arms (3 rows recorded 2026-04-01)

```
  Arm   1  direction  131°  A=2.29  B=0.88  C=3.32  D=0.893  E=0.55
  Arm   2  direction  184°  A=2.35  B=0.904  C=3.07  D=0.9  E=0.52
  Arm   3  direction  350°  A=2.36  B=0.991  C=3.48  D=1.03  E=0.55
```

## Photos available in /workspace/photos/

  2023: (no photos available)

  2026: (no photos available)

## Datasheets

- /workspace/datasheets/2023.png — hand-redacted volunteer field form
- /workspace/datasheets/2026.png — hand-redacted volunteer field form

## Output

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1', '2', '3']`. Values: a 2023 arm id from `['1', '2', '3']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
