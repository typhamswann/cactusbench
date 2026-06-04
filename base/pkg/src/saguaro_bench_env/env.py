"""State management for one task container.

Layout (everything lives on the container filesystem so resume / inspect
works without an in-memory daemon):

/task/                  (read-only, baked into the image)
    source.json
    instruction.md
    task.toml
    assets/
        datasheet_2023.png  datasheet_2026.png
        photos/             2023_photo_1.jpg, 2026_photo_3.jpg, ...

/workspace/             (mutable, agent-visible)
    system.md           the SYSTEM_PROMPT
    brief.md            human-readable per-task brief
    state.json          rollout state — see STATE_SCHEMA below
    view.png            most recent datasheet view (if any)
    view.jpg            most recent photo view (if any)
    submission.json     {"submission": "<json-string-from-agent>"} once submitted

/logs/                  (mutable, harbor-visible)
    verifier/           reward.txt + reward.json get written here
    agent/              agent free-form logging
    artifacts/          published artifacts the verifier reads
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TASK_DIR = Path("/task")
WORKSPACE = Path("/workspace")
LOGS = Path("/logs")
LOGS_VERIFIER = LOGS / "verifier"
LOGS_AGENT = LOGS / "agent"
LOGS_ARTIFACTS = LOGS / "artifacts"

# Convention: photo files are named "{year}_photo_{1-based-index}.jpg".
PHOTOS_DIR_NAME = "photos"


# State.json schema (rough; not enforced):
# {
#   "saguaro_id": "41B-13",
#   "turn": 0,
#   "last_tool": null | {"name": str, "args": {...}, "result": str, "turn": int},
#   "history": [ ... last_tool entries ... ],
#   "submission_complete": false,
#   "view_paper": null | {"year": int, "path": "/workspace/view.png", "turn": int},
#   "view_photo": null | {"year": int, "index": int, "path": "/workspace/view.jpg", "turn": int},
#   "max_turns": null | int,
# }


def read_source() -> dict:
    p = TASK_DIR / "source.json"
    if not p.exists():
        raise FileNotFoundError(f"source.json missing at {p}")
    return json.loads(p.read_text())


def read_state() -> dict:
    p = WORKSPACE / "state.json"
    if not p.exists():
        raise FileNotFoundError(f"state.json missing at {p}; was `sab harbor-init` run?")
    return json.loads(p.read_text())


def write_state(state: dict) -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "state.json").write_text(json.dumps(state, indent=2))


def ensure_dirs() -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    LOGS_VERIFIER.mkdir(parents=True, exist_ok=True)
    LOGS_AGENT.mkdir(parents=True, exist_ok=True)
    LOGS_ARTIFACTS.mkdir(parents=True, exist_ok=True)


def append_history(state: dict, entry: dict) -> None:
    state.setdefault("history", []).append(entry)
    state["last_tool"] = entry


def datasheet_path(year: int) -> Path:
    return TASK_DIR / "assets" / f"datasheet_{year}.png"


def photo_path(year: int, index_1based: int) -> Path:
    return TASK_DIR / "assets" / PHOTOS_DIR_NAME / f"{year}_photo_{index_1based}.jpg"


def write_view_png(src: Path) -> Path:
    """Copy src bytes to /workspace/view.png; return dest path."""
    dest = WORKSPACE / "view.png"
    dest.write_bytes(src.read_bytes())
    return dest


def write_view_jpg(src: Path) -> Path:
    dest = WORKSPACE / "view.jpg"
    dest.write_bytes(src.read_bytes())
    return dest


def n_photos(record: dict, year: int) -> int:
    return len(record["assets"].get(f"photos_{year}", []))
