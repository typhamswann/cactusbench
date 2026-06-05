# Saguaro 41B-09

Plot coordinates: easting 525356, northing 3563273
Plant height: 4.83 m (2023) → 5.25 m (2026)
Stem diameter at 1 m: 0.45 m (2023) → 0.5 m (2026)

## 2023 arms (1 rows recorded 2023-11-01)

```
  Arm   1  direction  160°  A=2.59  B=1.01  C=2.82  D=0.99  E=0.3
```

## 2026 arms (1 rows recorded 2026-04-01)

```
  Arm   1  direction  158°  A=2.54  B=1  C=3.05  D=0.99  E=0.55
```

## Photos available in /workspace/photos/

  2023: (no photos available)

  2026: (no photos available)

## Datasheets

- /workspace/datasheets/2023.png — hand-redacted volunteer field form
- /workspace/datasheets/2026.png — hand-redacted volunteer field form

## Output

Write your mapping to `/workspace/submission.json`. Keys: every 2026 arm id `['1']`. Values: a 2023 arm id from `['1']` or the literal `"new"`. The mapping must be a function — no two 2026 arms may map to the same non-`"new"` 2023 arm.
