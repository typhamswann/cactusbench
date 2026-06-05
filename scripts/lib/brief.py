"""Render the per-task brief.md (arm rows + photo inventory) at build time.

The same content was generated at boot by `sab harbor-init` in v0.1; in
v0.2 it's baked into the image so the agent sees it as a regular file.
"""
from __future__ import annotations


def build_brief(record: dict) -> str:
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
        listing = []
        for i, p in enumerate(photos, start=1):
            lbl = p.get("direction_label")
            listing.append(
                f"    photos/{year}/photo_{i}.jpg" + (f"  ({lbl})" if lbl else "")
            )
        return f"  {year}: {len(photos)} photo(s)\n" + "\n".join(listing)

    arm_ids_2026 = [str(r["arm_n_raw"]) for r in rows_2026]
    arm_ids_2023 = [str(r["arm_n_raw"]) for r in rows_2023]

    lines: list[str] = []
    lines.append(f"# Saguaro {sid}")
    lines.append("")
    if easting is not None and northing is not None:
        lines.append(f"Plot coordinates: easting {easting}, northing {northing}")
    if h23 is not None and h26 is not None:
        lines.append(f"Plant height: {h23} m (2023) → {h26} m (2026)")
    if d23 is not None and d26 is not None:
        lines.append(f"Stem diameter at 1 m: {d23} m (2023) → {d26} m (2026)")
    lines.append("")
    lines.append(f"## 2023 arms ({len(rows_2023)} rows recorded {date_23})")
    lines.append("")
    lines.append("```")
    for r in rows_2023:
        lines.append(fmt_row(r))
    lines.append("```")
    lines.append("")
    lines.append(f"## 2026 arms ({len(rows_2026)} rows recorded {date_26})")
    lines.append("")
    lines.append("```")
    for r in rows_2026:
        lines.append(fmt_row(r))
    lines.append("```")
    lines.append("")
    lines.append("## Photos available in /workspace/photos/")
    lines.append("")
    lines.append(photo_inventory(photos_2023, 2023))
    lines.append("")
    lines.append(photo_inventory(photos_2026, 2026))
    lines.append("")
    lines.append("## Datasheets")
    lines.append("")
    lines.append("- /workspace/datasheets/2023.png — hand-redacted volunteer field form")
    lines.append("- /workspace/datasheets/2026.png — hand-redacted volunteer field form")
    lines.append("")
    lines.append("## Output")
    lines.append("")
    lines.append(
        f"Write your mapping to `/workspace/submission.json`. "
        f"Keys: every 2026 arm id `{arm_ids_2026}`. "
        f"Values: a 2023 arm id from `{arm_ids_2023}` or the literal `\"new\"`. "
        f"The mapping must be a function — no two 2026 arms may map to the "
        f"same non-`\"new\"` 2023 arm."
    )
    return "\n".join(lines) + "\n"
