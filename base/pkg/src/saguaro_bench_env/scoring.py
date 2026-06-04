"""Mapping → reward.

Mirrors the rubric in saguaro_arm_matching/rubric.py so any agent that does
well on the source verifiers env scores identically here. A submission earns
1.0 iff it (a) is a JSON object, (b) has keys exactly equal to the 2026 arm
set, (c) values are valid 2023 arms or "new", (d) is a function (no two
2026 arms map to the same non-"new" 2023 arm), and (e) matches ground truth
exactly. arm_pair_f1 is a continuous diagnostic.
"""
from __future__ import annotations

import json
from typing import Any


def parse_submission(submission_raw: Any) -> tuple[dict[str, str] | None, str | None]:
    """Decode the agent's submission. Returns (mapping, error_str)."""
    if submission_raw is None:
        return None, "no_submission"
    if isinstance(submission_raw, str):
        try:
            obj = json.loads(submission_raw)
        except Exception as e:
            return None, f"invalid_json: {e}"
    else:
        obj = submission_raw
    if not isinstance(obj, dict):
        return None, "not_a_json_object"
    norm: dict[str, str] = {}
    for k, v in obj.items():
        norm[str(k)] = str(v)
    return norm, None


def structural_check(mapping: dict[str, str], info: dict) -> str | None:
    """Return error string if structurally invalid, else None."""
    rows_2026 = info.get("rows_2026") or []
    rows_2023 = info.get("rows_2023") or []
    expected_keys = {str(r["arm_n_raw"]) for r in rows_2026}
    valid_targets = {str(r["arm_n_raw"]) for r in rows_2023} | {"new"}

    submitted_keys = set(mapping.keys())
    if submitted_keys != expected_keys:
        missing = expected_keys - submitted_keys
        extra = submitted_keys - expected_keys
        bits = []
        if missing:
            bits.append(f"missing={sorted(missing)}")
        if extra:
            bits.append(f"extra={sorted(extra)}")
        return "keys_mismatch: " + ", ".join(bits)

    bad = [v for v in mapping.values() if v not in valid_targets]
    if bad:
        return f"invalid_targets: {bad}"

    seen: dict[str, str] = {}
    for k, v in mapping.items():
        if v == "new":
            continue
        if v in seen:
            return f"not_a_function: 2023 arm {v!r} used by both 2026 arm {seen[v]!r} and {k!r}"
        seen[v] = k

    return None


def arm_pair_f1(submission: dict[str, str], truth: dict[str, str]) -> float:
    """F1 over the SET of matched arm pairs (treating "new" as 'no match').

    Pairs are unordered (2026_arm, 2023_arm) tuples. "new" entries contribute
    nothing because they aren't matches. This is the same metric as v1.
    """

    def pairs(m: dict[str, str]) -> set[tuple[str, str]]:
        return {(k, v) for k, v in m.items() if v != "new"}

    sub = pairs(submission)
    ref = pairs(truth)
    if not sub and not ref:
        return 1.0
    if not sub or not ref:
        return 0.0
    tp = len(sub & ref)
    if tp == 0:
        return 0.0
    p = tp / len(sub)
    r = tp / len(ref)
    return 2 * p * r / (p + r)


def score(submission_raw: Any, info: dict) -> dict:
    """Returns {exact_mapping_reward, arm_pair_f1, structural_error?}."""
    truth = info["ground_truth"]["mapping"]
    truth = {str(k): str(v) for k, v in truth.items()}

    mapping, parse_err = parse_submission(submission_raw)
    if parse_err is not None:
        return {
            "exact_mapping_reward": 0.0,
            "arm_pair_f1": 0.0,
            "structural_error": parse_err,
        }

    struct_err = structural_check(mapping, info)
    if struct_err is not None:
        return {
            "exact_mapping_reward": 0.0,
            "arm_pair_f1": arm_pair_f1(mapping, truth),
            "structural_error": struct_err,
        }

    exact = 1.0 if mapping == truth else 0.0
    return {
        "exact_mapping_reward": exact,
        "arm_pair_f1": arm_pair_f1(mapping, truth),
    }
