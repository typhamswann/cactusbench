# Match arms across two survey years on saguaro 41B-06A

A 2023 volunteer recorded 5 arm(s) on this saguaro. A 2026 volunteer
recorded 7 arm(s). Volunteers number arms independently each year — arm 3
in 2026 is NOT necessarily the same physical arm as arm 3 in 2023.

For every 2026 arm number, decide which 2023 arm number is the same physical
arm — or `"new"` if the arm has emerged since the 2023 survey.

## Inputs

All inputs live in `/workspace/`:

- `brief.md` — the digitized arm rows + photo inventory for both years.
- `datasheets/2023.png`, `datasheets/2026.png` — the volunteers' handwritten
  field forms (hand-redacted: the curator's marginal arm-number renumbering
  has been blacked out, so the matching has to be done from arm orientation,
  measurements, and photos).
- `photos/2023/photo_<N>.jpg`, `photos/2026/photo_<N>.jpg` — field photos
  from each survey. 1-based indexing; the brief lists how many are
  available.

## Output

Write your final mapping to `/workspace/submission.json` as a JSON object:

- Keys: every 2026 arm number, as strings.
- Values: a 2023 arm number (as a string) or the literal `"new"`.
- The mapping must be a function — no two 2026 arms may map to the same
  non-`"new"` 2023 arm.

Example shape (NOT the answer to this task):

```json
{"1": "2", "2": "3", "3": "new", "4": "1", "5": "4"}
```

## Measurement columns

Each arm row has:
- `direction`: compass bearing from saguaro center out to the arm, in
  degrees (0=N, 90=E, 180=S, 270=W).
- `A`: height in meters from the ground to where the arm emerges from the
  main stem.
- `B`: height in meters from the ground to a 1 m datum mark on the stem
  near where A was measured.
- `C`: height from the ground to the tip of the arm.
- `D`: height from the ground to a 1 m datum mark on the stem near where
  C was measured.
- `E`: horizontal distance in meters from the main stem to the arm tip.

Biological constraints: saguaro arms grow slowly. They rarely shrink. New
arms can emerge between surveys; existing arms only rarely disappear.

## Difficulty

**medium** (train split).
