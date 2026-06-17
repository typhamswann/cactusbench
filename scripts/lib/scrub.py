#!/usr/bin/env python3
"""Stdlib-only image metadata scrubber for CactusBench asset bundling.

Removes every metadata vector a model with a metadata-read primitive could use
to shortcut the task: EXIF capture dates, GPS, XMP, camera make,
and any PNG text/time chunks. We do this by COPYING the compressed image data
into a fresh file that contains only the structural chunks/segments — we never
re-encode the pixels, so legibility (the whole point of the task) is untouched.

Vectors closed:
  * JPEG  — drop APP0..APP15 (0xFFE0..0xFFEF, incl. EXIF/JFIF/XMP) and COM
            (0xFFFE) segments; keep DQT/DHT/SOF/SOS + entropy data verbatim.
  * PNG   — keep only the structural/colour chunks; drop tEXt/zTXt/iTXt/tIME/eXIf
            and any other ancillary chunk.

`scrub_to(src, dst)` writes the cleaned image. `assert_clean(path)` raises if a
file still carries a known metadata marker — call it after writing so a build
fails loudly rather than silently shipping a leak.
"""
from __future__ import annotations

import struct
from pathlib import Path

# ---------------------------------------------------------------------------
# JPEG
# ---------------------------------------------------------------------------
# Drop every APPn that can carry a metadata leak (EXIF dates/GPS in APP1, XMP in
# APP1, Photoshop/IPTC captions+dates in APP13, JFIF thumbnail in APP0) plus COM.
# PRESERVE APP2 (ICC colour profile) and APP14 (Adobe colour transform) so colour
# rendering — hence handwriting legibility — is untouched. Neither carries a
# capture date or GPS, so they are not a year-inference vector.
_JPEG_KEEP_APP = {0xE2, 0xEE}  # APP2 (ICC), APP14 (Adobe)
_JPEG_DROP = ({m for m in range(0xE0, 0xF0) if m not in _JPEG_KEEP_APP}) | {0xFE}
_JPEG_STANDALONE = {0xD8, 0xD9} | set(range(0xD0, 0xD8))  # SOI/EOI/RSTn: no length


def _scrub_jpeg(data: bytes) -> bytes:
    if data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG (no SOI)")
    out = bytearray(b"\xff\xd8")
    i = 2
    n = len(data)
    while i < n:
        if data[i] != 0xFF:
            # Shouldn't happen in a well-formed marker stream; bail safe by
            # copying the remainder verbatim.
            out += data[i:]
            break
        # Skip fill bytes (0xFF padding).
        j = i + 1
        while j < n and data[j] == 0xFF:
            j += 1
        if j >= n:
            break
        marker = data[j]
        if marker == 0xDA:  # SOS — entropy-coded data follows to EOI; copy rest.
            out += data[i:]
            break
        if marker in _JPEG_STANDALONE:
            out += data[i:j + 1]
            i = j + 1
            continue
        seg_len = struct.unpack(">H", data[j + 1:j + 3])[0]
        seg_end = j + 1 + seg_len
        if marker not in _JPEG_DROP:
            out += data[i:seg_end]
        i = seg_end
    return bytes(out)


# ---------------------------------------------------------------------------
# PNG
# ---------------------------------------------------------------------------
_PNG_SIG = b"\x89PNG\r\n\x1a\n"
# Structural + colour chunks we keep. Everything else (tEXt/zTXt/iTXt/tIME/eXIf/…)
# is dropped.
_PNG_KEEP = {
    b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"cHRM",
    b"sRGB", b"iCCP", b"bKGD", b"pHYs", b"sBIT", b"hIST", b"sPLT",
}


def _scrub_png(data: bytes) -> bytes:
    if data[:8] != _PNG_SIG:
        raise ValueError("not a PNG (bad signature)")
    out = bytearray(_PNG_SIG)
    i = 8
    n = len(data)
    while i < n:
        length = struct.unpack(">I", data[i:i + 4])[0]
        ctype = data[i + 4:i + 8]
        chunk_end = i + 12 + length  # len(4) + type(4) + data + crc(4)
        if ctype in _PNG_KEEP:
            out += data[i:chunk_end]
        i = chunk_end
        if ctype == b"IEND":
            break
    return bytes(out)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def scrub_bytes(data: bytes, suffix: str) -> bytes:
    s = suffix.lower()
    if s in (".jpg", ".jpeg"):
        return _scrub_jpeg(data)
    if s == ".png":
        return _scrub_png(data)
    # Unknown type: pass through unchanged (caller decides whether to allow it).
    return data


def scrub_to(src: Path, dst: Path) -> None:
    """Read src, strip metadata, write to dst."""
    data = Path(src).read_bytes()
    cleaned = scrub_bytes(data, Path(src).suffix)
    Path(dst).write_bytes(cleaned)


_MARKERS = (
    b"Exif\x00", b"http://ns.adobe.com/xap", b"<x:xmpmeta", b"<?xpacket",
    b"tEXt", b"zTXt", b"iTXt", b"tIME", b"eXIf",
)


def assert_clean(path: Path) -> None:
    """Raise AssertionError if a metadata marker survives in `path`."""
    data = Path(path).read_bytes()
    hits = [m.decode("latin1", "replace") for m in _MARKERS if m in data]
    if hits:
        raise AssertionError(f"metadata leak in {path}: {hits}")


if __name__ == "__main__":  # tiny self-check / CLI: scrub.py <src> <dst>
    import sys
    if len(sys.argv) == 3:
        scrub_to(Path(sys.argv[1]), Path(sys.argv[2]))
        assert_clean(Path(sys.argv[2]))
        print(f"scrubbed {sys.argv[1]} -> {sys.argv[2]} (clean)")
    else:
        print("usage: scrub.py <src> <dst>")
