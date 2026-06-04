"""Tool dispatch for `sab harbor-step`. One Python function per agent tool;
each is invoked with already-parsed JSON args and the loaded source record.
"""
from __future__ import annotations

import json
from typing import Any

from . import env as ENV


ALLOWED_TOOLS = {"view_paper_datasheet", "view_photo", "submit_mapping"}


def _err(msg: str) -> tuple[str, dict]:
    return msg, {"error": msg}


def view_paper_datasheet(args: dict[str, Any], record: dict, state: dict) -> tuple[str, dict]:
    year = args.get("year")
    if year not in (2023, 2026):
        return _err(f"view_paper_datasheet: year must be 2023 or 2026 (got {year!r})")
    src = ENV.datasheet_path(int(year))
    if not src.exists():
        return _err(f"view_paper_datasheet: no datasheet found for {year} (looked at {src})")
    dest = ENV.write_view_png(src)
    state["view_paper"] = {"year": int(year), "path": str(dest), "turn": state["turn"]}
    return (
        f"Wrote {dest} ({src.stat().st_size} bytes). "
        f"This is the volunteer's {year} paper datasheet (hand-redacted).",
        {"path": str(dest), "year": int(year)},
    )


def view_photo(args: dict[str, Any], record: dict, state: dict) -> tuple[str, dict]:
    year = args.get("year")
    if year not in (2023, 2026):
        return _err(f"view_photo: year must be 2023 or 2026 (got {year!r})")
    idx = args.get("photo_index")
    try:
        idx = int(idx)
    except Exception:
        return _err(f"view_photo: photo_index must be an int (got {idx!r})")
    n_avail = ENV.n_photos(record, int(year))
    if idx < 1 or idx > n_avail:
        return _err(f"view_photo: photo_index {idx} out of range (year {year} has {n_avail} photos)")
    src = ENV.photo_path(int(year), idx)
    if not src.exists():
        return _err(f"view_photo: photo file missing at {src}")
    dest = ENV.write_view_jpg(src)
    state["view_photo"] = {"year": int(year), "index": idx, "path": str(dest), "turn": state["turn"]}
    return (
        f"Wrote {dest} ({src.stat().st_size} bytes). "
        f"This is photo {idx}/{n_avail} from the {year} survey.",
        {"path": str(dest), "year": int(year), "photo_index": idx},
    )


def submit_mapping(args: dict[str, Any], record: dict, state: dict) -> tuple[str, dict]:
    if state.get("submission_complete"):
        return _err("submit_mapping: already submitted; ignoring duplicate call")
    mapping_json = args.get("mapping_json", args.get("mapping"))
    if mapping_json is None:
        return _err("submit_mapping: missing 'mapping_json' (or 'mapping') argument")
    # The agent may pass either a JSON-encoded string OR a raw object; tolerate both.
    if isinstance(mapping_json, dict):
        payload = json.dumps(mapping_json)
    elif isinstance(mapping_json, str):
        payload = mapping_json
    else:
        return _err(f"submit_mapping: expected string or object, got {type(mapping_json).__name__}")

    (ENV.WORKSPACE / "submission.json").write_text(
        json.dumps({"submission": payload}, indent=2)
    )
    state["submission_complete"] = True
    return (
        f"Submission recorded ({len(payload)} chars). The verifier will score it; "
        "no further tool calls will mutate state.",
        {"submission_chars": len(payload)},
    )


DISPATCH = {
    "view_paper_datasheet": view_paper_datasheet,
    "view_photo": view_photo,
    "submit_mapping": submit_mapping,
}


def dispatch(tool: str, args: dict[str, Any], record: dict, state: dict) -> tuple[str, dict]:
    fn = DISPATCH.get(tool)
    if fn is None:
        return _err(f"unknown tool: {tool!r}. allowed: {sorted(ALLOWED_TOOLS)}")
    return fn(args, record, state)
