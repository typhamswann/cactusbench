"""Tool definitions + dispatch for the CactusBench OpenRouter loop.

The model emits one tool call per turn as a JSON object:

    {"tool": "<name>", "args": {...}}

We parse, dispatch, and return either:
- a plain string (becomes a `text` content part in the next user message)
- a dict with {"text": ..., "image_b64": ..., "image_mime": ...} (becomes
  a text + image_url content list)

This matches the wanderbench harbor_driver pattern (one tool call per
turn, JSON-only assistant output) — universally portable across every
chat-completions-style provider OpenRouter routes to, no provider-specific
function-calling format required.
"""
from __future__ import annotations

import base64
import json
import re
import struct
from pathlib import Path

ALLOWED = {"list_dir", "read_text", "view_image", "write_submission"}

# Sandbox: the agent's "workspace" is a host directory we set up per task.
# Everything else is off-limits — paths must resolve under this root.


def _safe_join(root: Path, path: str) -> Path:
    p = Path(path)
    if p.is_absolute():
        # Strip a leading "/workspace/" if present so the agent's mental model
        # ("files live in /workspace") still works when we run on the host.
        try:
            rel = p.relative_to("/workspace")
            return (root / rel).resolve()
        except ValueError:
            return (root / p.relative_to(p.anchor)).resolve()
    return (root / p).resolve()


def _under(root: Path, p: Path) -> bool:
    """Resolve both sides before comparison so /tmp ↔ /private/tmp symlinks
    on macOS don't trip the sandbox check."""
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _rel(root: Path, p: Path) -> str:
    """Pretty path for display: always rooted at /workspace/ in the agent's
    mental model, regardless of where the host root actually lives."""
    try:
        return str(p.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(p)


def _err(msg: str) -> str:
    return f"ERROR: {msg}"


def list_dir(args: dict, root: Path, state: dict) -> str:
    path = args.get("path", ".")
    p = _safe_join(root, path)
    if not _under(root, p):
        return _err(f"path {path!r} resolves outside the workspace")
    if not p.exists():
        return _err(f"path {path!r} does not exist")
    if not p.is_dir():
        return _err(f"path {path!r} is not a directory")
    entries = []
    for child in sorted(p.iterdir()):
        kind = "dir" if child.is_dir() else "file"
        size = child.stat().st_size if child.is_file() else "-"
        entries.append(f"  {kind:4s}  {size!s:>10s}  {_rel(root, child)}")
    return f"# /workspace/{_rel(root, p)}\n" + "\n".join(entries)


def read_text(args: dict, root: Path, state: dict) -> str:
    path = args.get("path")
    if not isinstance(path, str):
        return _err("read_text: missing 'path' string argument")
    p = _safe_join(root, path)
    if not _under(root, p):
        return _err(f"path {path!r} resolves outside the workspace")
    if not p.exists() or not p.is_file():
        return _err(f"no such file: {path!r}")
    LIMIT = 50_000
    text = p.read_text(errors="replace")
    if len(text) > LIMIT:
        text = text[:LIMIT] + f"\n... [truncated, total {len(text)} chars]"
    return text


_IMG_MIME = {
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif":  "image/gif",
    ".webp": "image/webp",
}


def _image_dims(data: bytes, suffix: str) -> tuple[int | None, int | None]:
    """Best-effort (width, height) from raw bytes, stdlib only. The image handoff
    (resolution actually transmitted) is the dominant multimodal-harness variable
    for a handwriting-legibility task (guidance §1/§3d) — record it per attachment.
    """
    s = suffix.lower()
    try:
        if s == ".png" and data[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", data[16:24])
            return w, h
        if s in (".jpg", ".jpeg") and data[:2] == b"\xff\xd8":
            i, n = 2, len(data)
            while i < n:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                              0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):  # SOFn
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
                i += 2 + seg_len
    except Exception:
        pass
    return None, None


def _preprocess(b: bytes, suffix: str, mode: str, max_edge: int, grid: int):
    """Client-side image handoff transform (noise-floor study knob §1).

    Returns a list of (bytes, mime, label, w, h) — usually 1, but `tiles` returns
    several. Requires Pillow; if unavailable, falls back to `full`. The provider
    still resizes server-side, but this controls what *reaches* that resize:
      full       — original bytes (provider then downsamples a 2200px sheet).
      downsample — cap the long edge at max_edge before sending (measures the cliff).
      tiles      — split into a grid×grid of full-res tiles; each tile is downsampled
                   separately by the provider, ~grid× the effective resolution on the
                   measurement table without needing per-sheet crop boxes.
    """
    if mode == "full":
        w, h = _image_dims(b, suffix)
        return [(b, _IMG_MIME.get(suffix.lower(), "image/png"), "full", w, h)]
    try:
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(b)); im.load()
    except Exception:
        w, h = _image_dims(b, suffix)
        return [(b, _IMG_MIME.get(suffix.lower(), "image/png"), "full(pil-missing)", w, h)]

    def _enc(img, label):
        buf = io.BytesIO()
        fmt = "PNG" if suffix.lower() == ".png" else "JPEG"
        img.save(buf, format=fmt, quality=95) if fmt == "JPEG" else img.save(buf, format=fmt)
        data = buf.getvalue()
        return (data, "image/png" if fmt == "PNG" else "image/jpeg", label, img.width, img.height)

    if mode == "downsample":
        long_edge = max(im.width, im.height)
        if long_edge > max_edge:
            scale = max_edge / long_edge
            im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))),
                           Image.LANCZOS)
        return [_enc(im, f"downsample<= {max_edge}")]

    if mode == "tiles":
        out = []
        gw, gh = im.width // grid, im.height // grid
        for r in range(grid):
            for c in range(grid):
                box = (c * gw, r * gh,
                       im.width if c == grid - 1 else (c + 1) * gw,
                       im.height if r == grid - 1 else (r + 1) * gh)
                out.append(_enc(im.crop(box), f"tile_r{r}c{c}"))
        return out

    w, h = _image_dims(b, suffix)
    return [(b, _IMG_MIME.get(suffix.lower(), "image/png"), "full", w, h)]


def view_image(args: dict, root: Path, state: dict):
    path = args.get("path")
    if not isinstance(path, str):
        return _err("view_image: missing 'path' string argument")
    p = _safe_join(root, path)
    if not _under(root, p):
        return _err(f"path {path!r} resolves outside the workspace")
    if not p.exists() or not p.is_file():
        return _err(f"no such file: {path!r}")
    mime = _IMG_MIME.get(p.suffix.lower())
    if mime is None:
        return _err(f"unsupported image extension: {p.suffix!r}")
    b = p.read_bytes()
    rel = _rel(root, p)
    cfg = state.get("img_cfg", {})
    mode = cfg.get("mode", "full")
    pieces = _preprocess(b, p.suffix, mode, cfg.get("max_edge", 1568), cfg.get("grid", 2))
    state.setdefault("images_viewed", []).append(rel)
    is_sheet = rel.startswith("datasheets/")
    images = []
    for (data, m, label, w, h) in pieces:
        state.setdefault("image_manifest", []).append({
            "path": rel, "variant": label, "bytes": len(data),
            "width": w, "height": h, "mime": m, "is_sheet": is_sheet,
        })
        images.append({"image_b64": base64.b64encode(data).decode("ascii"),
                       "image_mime": m, "is_sheet": is_sheet})
    dims = ", ".join(f"{im['variant']} {im['width']}x{im['height']}"
                     for im in state["image_manifest"][-len(pieces):])
    return {
        "text": f"Image at /workspace/{rel} (mode={mode}; {dims}).",
        "images": images,
        # Back-compat single-image fields (first piece):
        "image_b64": images[0]["image_b64"],
        "image_mime": images[0]["image_mime"],
        "is_sheet": is_sheet,
    }


def write_submission(args: dict, root: Path, state: dict) -> str:
    content = args.get("content")
    if content is None:
        return _err("write_submission: missing 'content' argument")
    # Accept native list/dict objects too — re-serialize.
    if isinstance(content, (list, dict)):
        content = json.dumps(content)
    if not isinstance(content, str):
        return _err("write_submission: 'content' must be a JSON string, list, or object")
    # Soft validate: must at least be JSON-parseable. The curation scorer
    # expects a list of row dicts, but we also accept dict-wrapped forms
    # ({"rows": [...]} or {"submission": "<json-string>"}) — score.py handles
    # the unwrap. The matching scorer expects a dict.
    try:
        parsed = json.loads(content)
        if not isinstance(parsed, (list, dict)):
            return _err("write_submission: content must decode to a JSON list or object")
    except Exception as e:
        return _err(f"write_submission: content is not valid JSON: {e}")
    sub_path = root / "submission.json"
    sub_path.write_text(content)
    state["submission_path"] = str(sub_path)
    state["done"] = True
    return f"Submission written to /workspace/submission.json ({len(content)} chars). The task will end and be scored."


DISPATCH = {
    "list_dir":          list_dir,
    "read_text":         read_text,
    "view_image":        view_image,
    "write_submission":  write_submission,
}


# -----------------------------------------------------------------------------
# Native function-calling schemas (OpenAI tool format). Passed to the model via
# OpenRouter's `tools` parameter; OpenRouter normalizes each backend's native
# tool-call dialect into a structured `tool_calls` field. This is the modern
# frontier-benchmark default (SWE-agent FunctionCallingParser / mini-swe-agent).
# -----------------------------------------------------------------------------

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List the contents of a directory in the /workspace sandbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory to list, e.g. '.', 'datasheets', or 'photos'.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_text",
            "description": "Read a UTF-8 text file in the /workspace sandbox (e.g. instruction.md).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_image",
            "description": (
                "View an image file (a datasheet PNG or a field photo JPG) in the "
                "/workspace sandbox. The image is returned so you can read it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Image path, e.g. 'datasheets/sheet_A.png' or 'photos/photo_001.jpg'.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_submission",
            "description": (
                "Write the final cleaned table to /workspace/submission.json and end "
                "the task. Call this exactly once when your answer is ready."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": (
                            "The cleaned table as a JSON array (encoded as a string) of "
                            "row objects, each with keys saguaro_id, year, arm, direction, "
                            "A, B, C, D, E, note."
                        ),
                    }
                },
                "required": ["content"],
            },
        },
    },
]


# -----------------------------------------------------------------------------
# Parsing the assistant's reply -> (tool, args) | None
# -----------------------------------------------------------------------------

_JSON_OBJ_RE = re.compile(r"\{[\s\S]*\}")
_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def parse_tool_call(text: str):
    """Extract one tool call from the assistant's reply.

    Accepts:
        {"tool": "name", "args": {...}}
        ```json {"tool": "...", "args": {...}} ```
        plain prose with a JSON object somewhere inside
    """
    if not text:
        return None
    candidates: list[str] = []
    candidates.append(text.strip())
    for m in _FENCE_RE.finditer(text):
        candidates.append(m.group(1).strip())
    m = _JSON_OBJ_RE.search(text)
    if m:
        candidates.append(m.group(0))
    for c in candidates:
        try:
            obj = json.loads(c)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        tool = obj.get("tool") or obj.get("name") or obj.get("action")
        args = obj.get("args") or obj.get("arguments") or obj.get("params") or {}
        if isinstance(tool, str) and tool in ALLOWED and isinstance(args, dict):
            return tool, args
    return None
