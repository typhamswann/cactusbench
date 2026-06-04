#!/usr/bin/env bash
# Harbor verifier — invoked once the agent has finished its rollout.
# Mirrors the deep-swe / wanderbench pattern: writes a single reward (0.0 or
# 1.0) to /logs/verifier/reward.txt, exits 0 on success regardless of reward.
set -euo pipefail

LOG_PFX="[verifier]"

mkdir -p /logs/verifier /logs/agent /logs/artifacts

echo "${LOG_PFX} scoring saguaro-bench task 41B-01A"
sab harbor-score

if [[ ! -f /logs/verifier/reward.txt ]]; then
    echo "${LOG_PFX} ERROR: reward.txt was not written" >&2
    exit 1
fi

REWARD=$(cat /logs/verifier/reward.txt)
echo "${LOG_PFX} reward=${REWARD}"

# Always exit 0 — the reward is the signal, not the exit code.
exit 0
