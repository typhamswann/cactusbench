"""Render the single per-task prompt (instruction.md) for CactusBench
curation tasks.

Each task has ONE prompt file. The agent (e.g. Claude Code, Codex,
or the OpenRouter harness) reads it as the task statement
and acts. The agent's own system prompt (tools/protocol) is provided by the
agent, NOT the task — the task is pure prompt content.

The prompt is intentionally near-identical across all tasks: the agent is
NOT told the saguaro id, the per-year arm count, or the scoring rules. It must
derive the saguaro id, the canonical arm numbering, and the full row schedule
itself from the two field forms + photos. The only per-task substitution is the
number of photos available (which the agent could anyway discover via list_dir,
so it is not answer leakage).

Canonical numbering rule (per the curator): the 2023 paper-arm numbers ARE the
canonical arm labels; 2026 arms are re-keyed to the canonical number of the
2023 arm they match.
"""
from __future__ import annotations


def build_instruction(n_photos: int, max_turns: int = 50) -> str:
    """Return the single per-task prompt. Per-task variation is the photo count
    only; ``max_turns`` is the published harness contract (declared in the prompt
    so the agent can budget its tool calls — see docs/MANIFEST.md)."""
    if n_photos:
        photos_line = (
            f"`/workspace/photos/` — {n_photos} field photo(s). Photos help "
            "disambiguate arm matching when two arms are at similar directions "
            "or when the digitized measurements are inconclusive."
        )
    else:
        photos_line = (
            "`/workspace/photos/` — empty (no field photos available for this "
            "saguaro)."
        )

    return f"""\
# Curate this saguaro

Two biologists measured this saguaro on a plot at Saguaro National Park: one in 2023, one in 2026. Each produced a handwritten field-form recording per-arm measurements. Your job is to take in both years' raw sheets + photos and produce one cleaned spreadsheet: matched arms across years, canonical arm numbers, every measurement and note re-keyed into the canonical schema. It should be clean and accurate, following what the biologist in the field intended.

## Measurement columns

Each arm has, per year:

- `direction` — compass bearing from main stem out to the arm, degrees (0=N, 90=E, 180=S, 270=W).
- `A` — height in meters from the ground to where the arm emerges from the main stem.
- `B` — height in meters from the ground to a 1-meter datum mark on the stem near where A was measured.
- `C` — height from the ground to the tip of the arm.
- `D` — height from the ground to a 1-meter datum mark on the stem near where C was measured.
- `E` — horizontal distance in meters from the main stem to the arm tip.
- `note` — recorder annotation (e.g. "5 nubbins", "arm broke off", "tag 69"). Use `""` if none.

Measurements are relative to the recorder's datum, which sets the "0" mark.

Saguaro arms grow slowly. They rarely shrink. New arms can emerge between surveys; existing arms only rarely disappear.

## Inputs

`/workspace/datasheets/` — 2 field forms. One sheet covers each year. The arm numbers visible are the volunteer's paper-arm numbers, which may differ between years. The 2023 arm numbers are the canonical arm number labels for both years. 2026 arms must be recorded by matching and using the canonical arm number.

{photos_line}

## Output

Write your cleaned table to `/workspace/submission.json` as a JSON list of row objects. Each row has these fields:

```
saguaro_id   string  — formatted <Plot>-<Saguaro #>
year         int
arm          string  — canonical arm number
direction    number  — compass bearing from main stem, degrees (0–360)
A            number  — height where arm emerges from main stem, meters
B            number  — datum-mark height near A, meters
C            number  — arm-tip height, meters
D            number  — datum-mark height near C, meters
E            number  — horizontal distance from main stem to arm tip, meters
note         string  — recorder note (use "" if none)
```

Example row (illustrative format only): {{"saguaro_id": "00X-00", "year": 2023, "arm": "1", "direction": 90, "A": 2.50, "B": 1.00, "C": 3.50, "D": 1.00, "E": 0.50, "note": ""}}

Derive the `saguaro_id` (plot + saguaro number), the number of arms, and which sheet is which year **from the datasheets themselves** — none of these are given to you.

You must return data which you think is accurate to the real world above all. Part of your job QA/QC, so your curated data may vary from what biologists record in the sheet if their recordings were inaccurate or a mistake was made.

Order the arms by canonical arm number.

## Working budget

You have up to {max_turns} tool-call turns to inspect the sheets and photos and write `submission.json`. Budget them: read both datasheets and the photos you need, then write your final table once. The task ends when you write `submission.json`.
"""


# Backwards compat: older build_tasks.py imported build_brief.
build_brief = build_instruction
