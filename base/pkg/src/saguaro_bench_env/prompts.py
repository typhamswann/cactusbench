"""Agent-facing system prompt + per-task brief builder.

These strings are baked into /workspace/brief.md and /workspace/system.md on
``sab harbor-init`` so they are statically inspectable by any Harbor agent.
"""
from __future__ import annotations

from typing import Any


SYSTEM_PROMPT = """\
You are matching saguaro cactus arm measurements across two citizen-science survey years (2023 and 2026) on the same plant.

Volunteers numbered the arms independently each year, so the 2026 arm numbers do NOT necessarily correspond to the 2023 ones. For each 2026 arm, decide which 2023 arm is the same physical arm, or "new" if the arm appeared since 2023.

Measurement columns (per arm, per year):
- direction: compass bearing from saguaro center out to the arm, in degrees (0=N, 90=E, 180=S, 270=W).
- A: height in meters from the ground to the point where the arm emerges from the main stem.
- B: height in meters from the ground to a 1-meter datum mark on the stem near where A was measured.
- C: height in meters from the ground to the tip of the arm.
- D: height in meters from the ground to a 1-meter datum mark on the stem near where C was measured.
- E: horizontal distance in meters from the main stem to the arm tip.

Biological constraints: saguaro arms grow slowly. They rarely shrink. New arms can emerge between surveys; existing arms only rarely disappear.

Available tools (call exactly ONE per turn):
- view_paper_datasheet(year) — returns the volunteer's handwritten field form for the given year. Stages a PNG at /workspace/view.png and emits a stdout line with the path.
- view_photo(year, photo_index) — returns one field photo of the saguaro (1-based index into the photos listed in the brief). Stages a JPG at /workspace/view.jpg and emits a stdout line with the path.
- submit_mapping(mapping_json) — submit the final answer as a JSON-encoded string and end the rollout. The decoded object must have every 2026 arm number (as a string) as a key and either the matching 2023 arm number (as a string) or the literal "new" as the value. Do not call this more than once.

Submit a complete mapping covering every 2026 arm in the brief. The mapping must be a function — no two 2026 arms can map to the same 2023 arm.\
"""


def build_brief(record: dict[str, Any]) -> str:
    """Construct the per-task user-facing brief written to brief.md.

    Mirrors saguaro_arm_matching.prompts.build_brief from the source env so an
    agent that does well there will see substantially the same prompt here.
    """
    sid = record["saguaro_id"]
    easting = record.get("easting")
    northing = record.get("northing")
    h23 = record.get("saguaro_height_m_2023")
    h26 = record.get("saguaro_height_m_2026")
    d23 = record.get("diameter_m_2023")
    d26 = record.get("diameter_m_2026")
    date_23 = record.get("date_2023", "")
    date_26 = record.get("date_2026", "")
    rows_2023 = record["rows_2023"]
    rows_2026 = record["rows_2026"]
    photos_2023 = record["assets"].get("photos_2023", [])
    photos_2026 = record["assets"].get("photos_2026", [])

    def fmt_row(r: dict) -> str:
        nub = " [nubbin]" if r.get("is_nubbin") else ""
        note = f"  note: {r['note']}" if r.get("note") else ""
        return (
            f"  Arm {str(r['arm_n_raw']):>3}{nub}  "
            f"direction {str(r.get('direction_deg', '?')):>4}°  "
            f"A={r.get('A')}  B={r.get('B')}  C={r.get('C')}  D={r.get('D')}  E={r.get('E')}"
            f"{note}"
        )

    def photo_inventory(photos: list, year: int) -> str:
        if not photos:
            return f"  {year}: (no photos available)"
        labels = [p.get("direction_label") for p in photos]
        if all(lbl is None for lbl in labels):
            return f"  {year}: {len(photos)} photos available (use photo_index 1..{len(photos)}; no direction labels)"
        label_str = ", ".join(lbl if lbl else f"#{i+1}" for i, lbl in enumerate(labels))
        return f"  {year}: {len(photos)} photos available (use photo_index 1..{len(photos)}; labels: {label_str})"

    arm_ids_2026 = [str(r["arm_n_raw"]) for r in rows_2026]
    arm_ids_2023 = [str(r["arm_n_raw"]) for r in rows_2023]

    lines: list[str] = []
    lines.append(f"Saguaro: {sid}")
    if easting is not None and northing is not None:
        lines.append(f"Plot coordinates: easting {easting}, northing {northing}")
    if h23 is not None and h26 is not None:
        lines.append(f"Plant height: {h23} m (2023) -> {h26} m (2026)")
    if d23 is not None and d26 is not None:
        lines.append(f"Stem diameter at 1 m: {d23} m (2023) -> {d26} m (2026)")
    lines.append("")
    lines.append(f"2023 arms ({len(rows_2023)} rows recorded {date_23}):")
    for r in rows_2023:
        lines.append(fmt_row(r))
    lines.append("")
    lines.append(f"2026 arms ({len(rows_2026)} rows recorded {date_26}):")
    for r in rows_2026:
        lines.append(fmt_row(r))
    lines.append("")
    lines.append("Photos available:")
    lines.append(photo_inventory(photos_2023, 2023))
    lines.append(photo_inventory(photos_2026, 2026))
    lines.append("Paper datasheets available for both 2023 and 2026 via view_paper_datasheet(year).")
    lines.append("")
    lines.append(
        f"Produce a mapping covering every 2026 arm: {arm_ids_2026}. "
        f"Each value must be one of {arm_ids_2023} or \"new\". "
        f"Submit with submit_mapping(<json-string>)."
    )
    return "\n".join(lines)


HELP_TEXT = """\
SaguaroBench environment contract — agent reference.

You are inside a per-task Docker container. State lives at /workspace:
  /workspace/system.md   — system prompt (also shown above on rollout start)
  /workspace/brief.md    — this task's saguaro brief: arm rows, photos, datasheets
  /workspace/state.json  — current rollout state (turn count, last tool, view file)

Tool calls run as a separate process:
    sab harbor-step --tool NAME --args '<json>'
The CLI writes the result to /workspace and prints a one-line stdout summary.

Tools
-----
view_paper_datasheet(year: 2023 | 2026)
    Stages the (hand-redacted) volunteer field-form PNG at /workspace/view.png.
    Curator's marginal canonical-arm renumberings have been blacked out so
    the matching has to be done from arm orientation + measurements + photos.

view_photo(year: 2023 | 2026, photo_index: int)
    1-based index into the photos listed in the brief. Stages the JPG at
    /workspace/view.jpg. Useful for cross-checking measurements when the
    digitized rows are ambiguous (e.g. arm A vs arm B at the same height).

submit_mapping(mapping_json: str)
    JSON-encoded string mapping every 2026 arm number to either a 2023 arm
    number or the literal "new". Marks the rollout complete; further
    harbor-step calls are no-ops.

Scoring
-------
The verifier writes /logs/verifier/reward.txt with a single 1.0 or 0.0:
  1.0 — submission EXACTLY matches ground truth AND passes structural checks
        (keys = 2026 arms, values valid, mapping is a function).
  0.0 — anything else (structural error or wrong mapping).

A richer reward.json includes:
  exact_mapping_reward (1.0/0.0), arm_pair_f1 (continuous), and a
  structural_error string when the submission is malformed.
"""
