#!/usr/bin/env python3
"""SaguaroBench curation scorer — copied verbatim into each task's grade/score.py.

Verifier-side. Reads:
    /workspace/submission.json   the agent's output (list of row dicts)
    /grade/truth.json            ground truth + scoring schema:
        {
          "saguaro_id": "41B-13",
          "scored_fields": ["saguaro_id","direction","A","B","C","D","E","note"],
          "tolerances": {"direction": 1.0, "A": 0.011, ...},
          "truth_rows": [
            {"saguaro_id": "41B-13", "year": 2023, "arm": "1",
             "direction": 360, "A": 1.89, ..., "note": ["5 nubbins","5 nubbins!"]},
            ...
            {... "_excluded": true ...}   # skipped: any/no submission accepted
          ]
        }

Writes a JSON object on stdout. test.sh redirects it to
/logs/verifier/reward.json and pulls reward.txt out via jq.

Scoring (mirrors saguaro_curation/rubric.py from the source env):
- Submission must parse as a list of dicts each with at least {saguaro_id, year, arm}.
  Accepts {"rows": [...]} wrapper, or {"submission": "<json-string>"} wrapper.
- Truth rows are keyed by (year, arm-string) — one saguaro per task, so saguaro_id
  is constant and scored as a cell, not part of the key (see _row_key).
- _excluded rows are skipped entirely: their cells don't count and an extra
  submission at that key is not penalized.
- For each non-excluded truth row, score per-cell:
    * direction: numeric ±1.0°
    * A, B, C, D, E: numeric ±0.011 m
    * note: normalized-exact match against the truth string OR any member of a
            list-of-acceptable (empty matches empty). Jaccard is OFF the headline
            reward and reported only as a diagnostic (note_accuracy_jaccard_diag).
    * saguaro_id: normalized string equality
- Missing truth rows score 0 across all their cells.
- "Extra" predicted rows (not in truth, not _excluded) incur 0.05 each penalty,
  capped at 0.5.
- Final: cell_accuracy_reward = max(0, correct/total - extra_penalty), in [0,1].

Self-contained (stdlib only) — runs under any python3.10+ without pip.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Field schema
# ---------------------------------------------------------------------------
NUMERIC_FIELDS = ("direction", "A", "B", "C", "D", "E")
DEFAULT_TOLERANCES = {
    "direction": 1.0,
    "A": 0.011, "B": 0.011, "C": 0.011, "D": 0.011, "E": 0.011,
}
STRING_FIELDS = ("saguaro_id", "note")
ALL_FIELDS = NUMERIC_FIELDS + STRING_FIELDS  # 8 cells per row

EXTRA_ROW_PENALTY = 0.05
EXTRA_ROW_PENALTY_CAP = 0.5


# ---------------------------------------------------------------------------
# Field matchers
# ---------------------------------------------------------------------------
def _norm_str(s: Any) -> str:
    if s is None:
        return ""
    s = str(s).lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _numeric_match(pred: Any, truth: Any, tol: float) -> bool:
    if truth is None and (pred is None or pred == ""):
        return True
    if truth is None or pred is None or pred == "":
        return False
    try:
        return abs(float(pred) - float(truth)) <= tol
    except (TypeError, ValueError):
        return False


def _direction_match(pred: Any, truth: Any, tol: float) -> bool:
    """Compass bearing is circular: 360° == 0° == North. Compare on the circle so
    a model writing 0 for a truth of 360 (or 359 vs 1) is not falsely penalized."""
    if truth is None and (pred is None or pred == ""):
        return True
    if truth is None or pred is None or pred == "":
        return False
    try:
        diff = abs(float(pred) - float(truth)) % 360.0
        return min(diff, 360.0 - diff) <= tol
    except (TypeError, ValueError):
        return False


_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "of", "to", "in", "on",
    "and", "or", "but", "with", "for", "at", "by", "from", "as", "that",
    "this", "it", "be", "has", "have", "had",
})


def _word_set(s: Any) -> set:
    return {w for w in _norm_str(s).split() if w and w not in _STOPWORDS}


def _note_match_single(pred: Any, truth: Any, *, use_jaccard: bool = False) -> bool:
    """Compare one predicted note against one truth note string.

    The headline reward uses normalized-exact matching only (``use_jaccard=False``):
    truth notes that admit defensible recorder variation are stored as a
    *list-of-acceptable* in the truth file, so the fuzzy Jaccard path is no longer
    needed for the score and would only add a gameable rule to the headline (pad a
    note with common tokens to clear 0.5). Jaccard is still available as an
    OFF-headline diagnostic (``use_jaccard=True``) so we can report the gap between
    the strict and fuzzy note metric. See guidance §9 / docs/MANIFEST.md.
    """
    p_norm = _norm_str(pred)
    t_norm = _norm_str(truth)
    if p_norm == "" and t_norm == "":
        return True
    if p_norm == t_norm:
        return True
    if not use_jaccard:
        return False
    # Diagnostic-only: Jaccard word-set ≥ 0.5 (ignoring stopwords).
    p_words = _word_set(pred)
    t_words = _word_set(truth)
    if not p_words and not t_words:
        return True
    if not p_words or not t_words:
        return False
    j = len(p_words & t_words) / len(p_words | t_words)
    return j >= 0.5


def _note_match(pred: Any, truth: Any, *, use_jaccard: bool = False) -> bool:
    """Truth may be a string OR a list of acceptable strings. If list, any
    member matching counts.
    """
    if isinstance(truth, list):
        return any(_note_match_single(pred, t, use_jaccard=use_jaccard) for t in truth)
    return _note_match_single(pred, truth, use_jaccard=use_jaccard)


def _truth_note_is_empty(truth: Any) -> bool:
    """True if the truth note is empty / absent. A list-of-acceptable counts as
    non-empty if any member is non-empty."""
    if isinstance(truth, list):
        return not any(_norm_str(t) for t in truth)
    return _norm_str(truth) == ""


_SAGUARO_ID_RE = re.compile(r"^([A-Za-z0-9]+)-?(.+)$")


def _strip_leading_zeros(tok: str) -> str:
    """Normalize the integer prefix of a token, preserving any alpha suffix.
    "09" -> "9", "01A" -> "1A", "10A" -> "10A", "13" -> "13", "new" -> "new".
    Zero-padding is a cosmetic transcription choice (the recorder writes "9",
    the workbook may store "09"); it must not affect identity.
    """
    m = re.match(r"^(\d+)(.*)$", tok)
    if not m:
        return tok
    return str(int(m.group(1))) + m.group(2)


def _canon_saguaro_id(s: Any) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    m = _SAGUARO_ID_RE.match(s)
    if m:
        plot, rest = m.group(1), m.group(2).strip()
        # Plot: strip leading zeros if purely numeric ("06" -> "6").
        try:
            plot = str(int(plot))
        except ValueError:
            pass
        # Saguaro number: strip leading zeros from the integer prefix, keep any
        # alpha suffix, uppercase it ("09" -> "9", "01a" -> "1A").
        rest = _strip_leading_zeros(rest.upper())
        return f"{plot}-{rest}"
    return s


def _saguaro_id_match(pred: Any, truth: Any) -> bool:
    return _canon_saguaro_id(pred) == _canon_saguaro_id(truth)


def _field_match(field: str, pred: Any, truth: Any, tolerances: dict,
                 *, use_jaccard_notes: bool = False) -> bool:
    if field == "direction":
        return _direction_match(pred, truth, tolerances.get("direction", 0.0))
    if field in NUMERIC_FIELDS:
        return _numeric_match(pred, truth, tolerances.get(field, 0.0))
    if field == "saguaro_id":
        return _saguaro_id_match(pred, truth)
    if field == "note":
        return _note_match(pred, truth, use_jaccard=use_jaccard_notes)
    return _norm_str(pred) == _norm_str(truth)


# ---------------------------------------------------------------------------
# Key + submission parsing
# ---------------------------------------------------------------------------
def _canon_arm(a: Any) -> str:
    """Normalize an arm label for keying: strip leading zeros from a numeric
    arm ("01" -> "1") so cosmetic padding doesn't break row matching."""
    return _strip_leading_zeros(str(a).strip().upper())


def _row_key(row: dict) -> tuple:
    """Row identity for matching. Each SaguaroBench task is ONE saguaro, so the
    key is (year, canonical_arm) — saguaro_id is constant within a task and is
    scored as an ordinary cell instead. (The upstream batch env keyed by
    saguaro_id because its submissions spanned many cacti; here that would make a
    single constant id-slip zero the whole task — e.g. a model copying the
    prompt's placeholder id onto every row — which is a disproportionate, fragile
    penalty unrelated to the curation skill being measured.)"""
    return (int(row["year"]), _canon_arm(row.get("arm")))


def _is_excluded(row: dict) -> bool:
    return bool(row.get("_excluded"))


def _strip_code_fence(text: str) -> str:
    """If the submission is wrapped in a ```/```json markdown fence, unwrap it.
    Models routinely emit fenced JSON; tolerate it rather than scoring 0.
    """
    s = text.strip()
    if s.startswith("```"):
        # Drop the opening fence line (``` or ```json) and the trailing fence.
        lines = s.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def parse_submission(text: str):
    """Returns (rows_list, error_str)."""
    text = _strip_code_fence(text)
    try:
        obj = json.loads(text)
    except Exception as e:
        return None, f"invalid_json: {e}"
    # Accept {"submission": "<json-string>"} wrapper
    if isinstance(obj, dict) and "submission" in obj and len(obj) == 1:
        inner = obj["submission"]
        if isinstance(inner, str):
            try:
                obj = json.loads(inner)
            except Exception as e:
                return None, f"invalid_json (inner submission): {e}"
        elif isinstance(inner, (list, dict)):
            obj = inner
    # Accept {"rows": [...]} wrapper
    if isinstance(obj, dict) and "rows" in obj:
        obj = obj["rows"]
    if not isinstance(obj, list):
        return None, f"submission_not_list: {type(obj).__name__}"
    out = []
    for i, r in enumerate(obj):
        if not isinstance(r, dict):
            return None, f"row_{i}_not_dict"
        for required in ("saguaro_id", "year", "arm"):
            if required not in r:
                return None, f"row_{i}_missing_{required}"
        try:
            r["year"] = int(r["year"])
        except (TypeError, ValueError):
            return None, f"row_{i}_year_not_int"
        r["arm"] = str(r["arm"])
        out.append(r)
    return out, None


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------
def cell_accuracy_reward(pred_rows, truth):
    truth_rows = truth["truth_rows"]
    scored_fields = tuple(truth.get("scored_fields", ALL_FIELDS))
    tolerances = truth.get("tolerances", DEFAULT_TOLERANCES)

    truth_scored = [r for r in truth_rows if not _is_excluded(r)]
    excluded_keys = {_row_key(r) for r in truth_rows if _is_excluded(r)}
    truth_by_key = {_row_key(r): r for r in truth_scored}
    pred_by_key = {_row_key(r): r for r in pred_rows}

    # Per-field stats for diagnostics.
    per_field = {f: {"correct": 0, "total": 0} for f in scored_fields}

    # Note diagnostics (guidance §9): 94% of truth notes are empty, so the raw
    # note per-field accuracy mostly measures "did the model blank the field."
    # Track note accuracy conditioned on NON-EMPTY truth notes, and what the note
    # field would score under the (off-headline) Jaccard rule, so the gap is
    # visible without ever putting Jaccard in the headline reward.
    note_nonempty = {"correct": 0, "total": 0}
    note_jaccard = {"correct": 0, "total": 0}  # over all note cells, fuzzy rule

    correct_total = 0
    total = 0
    for key, truth_row in truth_by_key.items():
        pred_row = pred_by_key.get(key)
        for field in scored_fields:
            total += 1
            per_field[field]["total"] += 1
            matched = pred_row is not None and _field_match(
                field, pred_row.get(field), truth_row.get(field), tolerances
            )
            if matched:
                correct_total += 1
                per_field[field]["correct"] += 1
            if field == "note":
                t_note = truth_row.get("note")
                note_jaccard["total"] += 1
                if pred_row is not None and _field_match(
                    "note", pred_row.get("note"), t_note, tolerances, use_jaccard_notes=True
                ):
                    note_jaccard["correct"] += 1
                if not _truth_note_is_empty(t_note):
                    note_nonempty["total"] += 1
                    if matched:
                        note_nonempty["correct"] += 1

    base = correct_total / max(1, total)
    n_extra = len(set(pred_by_key) - set(truth_by_key) - excluded_keys)
    penalty = min(EXTRA_ROW_PENALTY_CAP, EXTRA_ROW_PENALTY * n_extra)

    reward = max(0.0, base - penalty)

    # Row presence stats.
    truth_keys = set(truth_by_key)
    pred_keys_scored = set(pred_by_key) - excluded_keys
    tp = len(truth_keys & pred_keys_scored)
    missing = len(truth_keys - pred_keys_scored)
    extra = len(pred_keys_scored - truth_keys)
    row_p = tp / max(1, len(pred_keys_scored))
    row_r = tp / max(1, len(truth_keys))
    row_f1 = 2 * row_p * row_r / (row_p + row_r) if (row_p + row_r) > 0 else 0.0

    return {
        "cell_accuracy_reward": round(reward, 6),
        "base_cell_accuracy": round(base, 6),
        "extra_row_penalty": round(penalty, 6),
        "row_f1": round(row_f1, 6),
        "rows_truth": len(truth_keys),
        "rows_pred_scored": len(pred_keys_scored),
        "rows_matched": tp,
        "rows_missing": missing,
        "rows_extra": extra,
        "rows_excluded": len(excluded_keys),
        "per_field_accuracy": {
            f: round(s["correct"] / max(1, s["total"]), 6) for f, s in per_field.items()
        },
        # Off-headline note diagnostics (do NOT feed cell_accuracy_reward):
        "note_accuracy_nonempty": (
            round(note_nonempty["correct"] / note_nonempty["total"], 6)
            if note_nonempty["total"] else None
        ),
        "note_nonempty_total": note_nonempty["total"],
        "note_accuracy_jaccard_diag": round(
            note_jaccard["correct"] / max(1, note_jaccard["total"]), 6
        ),
    }


def main(argv):
    if len(argv) != 3:
        print('{"cell_accuracy_reward": 0.0, "structural_error": '
              '"score.py: expected <submission.json> <truth.json>"}')
        return 0

    sub_path = Path(argv[1])
    truth_path = Path(argv[2])
    truth = json.loads(truth_path.read_text())
    saguaro_id = truth.get("saguaro_id")

    if not sub_path.exists():
        out = {
            "cell_accuracy_reward": 0.0,
            "saguaro_id": saguaro_id,
            "structural_error": "no_submission",
        }
        print(json.dumps(out))
        return 0

    rows, err = parse_submission(sub_path.read_text())
    if err is not None:
        out = {
            "cell_accuracy_reward": 0.0,
            "saguaro_id": saguaro_id,
            "structural_error": err,
        }
        print(json.dumps(out))
        return 0

    result = cell_accuracy_reward(rows, truth)
    result["saguaro_id"] = saguaro_id
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
