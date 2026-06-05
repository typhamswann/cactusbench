#!/usr/bin/env bash
# Harbor verifier — runs as root (per task.toml [verifier].user).
# Reads the agent's /workspace/submission.json, scores against /grade/truth.json,
# and writes /logs/verifier/reward.{json,txt}.
#
# Always exit 0 — the reward is the signal, not the exit code (mirrors deep-swe
# and wanderbench).
set -euo pipefail

LOG_PFX="[verifier]"

mkdir -p /logs/verifier /logs/agent /logs/artifacts

echo "${LOG_PFX} scoring saguaro-bench task 41B-11"

python3 /grade/score.py /workspace/submission.json /grade/truth.json \
    > /logs/verifier/reward.json

# Extract the canonical reward to reward.txt (Harbor reads either; we write both).
jq -r '.exact_mapping_reward' /logs/verifier/reward.json > /logs/verifier/reward.txt

REWARD=$(cat /logs/verifier/reward.txt)
F1=$(jq -r '.arm_pair_f1' /logs/verifier/reward.json)
ERR=$(jq -r '.structural_error // empty' /logs/verifier/reward.json)

echo "${LOG_PFX} reward=${REWARD} f1=${F1}${ERR:+ structural_error=$ERR}"

# Stash the submission (if present) into /logs/artifacts for the trajectory viewer.
if [[ -f /workspace/submission.json ]]; then
    cp /workspace/submission.json /logs/artifacts/submission.json
fi

exit 0
