#!/usr/bin/env python3
"""SaguaroBench scorer — copied verbatim into each task's grade/score.py.

Verifier-side. Reads:
    /workspace/submission.json   (the agent's output)
    /grade/truth.json            (ground truth + valid arm sets)

Writes a JSON object on stdout. test.sh redirects it to
/logs/verifier/reward.json and pulls reward.txt out via jq.

Structural validation gates the exact_mapping_reward: a malformed submission
gets 0.0 with a populated `structural_error` so it can be triaged separately
from a structurally-valid wrong answer. arm_pair_f1 is a continuous
diagnostic over the SET of matched (2026_arm, 2023_arm) pairs.

Self-contained (stdlib only) — runs under any python3.10+ without pip.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def parse_submission(text: str):
    try:
        obj = json.loads(text)
    except Exception as e:
        return None, f"invalid_json: {e}"
    # The agent may have written either a bare mapping object OR something
    # like {"submission": "<json-string>"}. Accept either.
    if isinstance(obj, dict) and "submission" in obj and len(obj) == 1:
        inner = obj["submission"]
        if isinstance(inner, str):
            try:
                obj = json.loads(inner)
            except Exception as e:
                return None, f"invalid_json (inner submission): {e}"
        elif isinstance(inner, dict):
            obj = inner
    if not isinstance(obj, dict):
        return None, "not_a_json_object"
    return {str(k): str(v) for k, v in obj.items()}, None


def structural_check(mapping, truth):
    expected_keys = set(truth["valid_2026_arms"])
    valid_targets = set(truth["valid_2023_arms"]) | {"new"}

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
        return f"invalid_targets: {sorted(set(bad))}"

    seen = {}
    for k, v in mapping.items():
        if v == "new":
            continue
        if v in seen:
            return f"not_a_function: 2023 arm {v!r} used by both 2026 arm {seen[v]!r} and {k!r}"
        seen[v] = k
    return None


def arm_pair_f1(submission, truth_mapping):
    def pairs(m):
        return {(k, v) for k, v in m.items() if v != "new"}
    sub = pairs(submission)
    ref = pairs(truth_mapping)
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


def main(argv):
    if len(argv) != 3:
        print('{"exact_mapping_reward": 0.0, "arm_pair_f1": 0.0, '
              '"structural_error": "score.py: expected '
              '<submission.json> <truth.json>"}')
        return 0

    sub_path = Path(argv[1])
    truth_path = Path(argv[2])

    truth = json.loads(truth_path.read_text())
    truth_mapping = {str(k): str(v) for k, v in truth["ground_truth_mapping"].items()}

    if not sub_path.exists():
        out = {
            "exact_mapping_reward": 0.0,
            "arm_pair_f1": 0.0,
            "saguaro_id": truth.get("saguaro_id"),
            "structural_error": "no_submission",
        }
        print(json.dumps(out))
        return 0

    text = sub_path.read_text()
    mapping, err = parse_submission(text)
    if err is not None:
        out = {
            "exact_mapping_reward": 0.0,
            "arm_pair_f1": 0.0,
            "saguaro_id": truth.get("saguaro_id"),
            "structural_error": err,
        }
        print(json.dumps(out))
        return 0

    err = structural_check(mapping, truth)
    if err is not None:
        out = {
            "exact_mapping_reward": 0.0,
            "arm_pair_f1": arm_pair_f1(mapping, truth_mapping),
            "saguaro_id": truth.get("saguaro_id"),
            "structural_error": err,
        }
        print(json.dumps(out))
        return 0

    exact = 1.0 if mapping == truth_mapping else 0.0
    out = {
        "exact_mapping_reward": exact,
        "arm_pair_f1": arm_pair_f1(mapping, truth_mapping),
        "saguaro_id": truth.get("saguaro_id"),
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
