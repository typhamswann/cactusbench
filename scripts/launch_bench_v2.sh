#!/usr/bin/env bash
# CactusBench v2 — clean-24 re-run with corrected truth + new prompt + year-labeled photos.
# Same harness selections / config / save-resume logic as bench_v1; only the run-id,
# task subset (clean-24, 23 tasks — 40-101 unavailable), and inputs differ.
#
# Idempotent: every command uses --resume / per-(task,rollout) skip, so re-running
# this script just continues where it left off. Safe to re-invoke after a limit pause.
#
# SERIAL LANES (5hr / quota limits, exactly as bench_v1):
#   * Claude lane (claude_code): run ONE opus at a time — opus_4_8 first, then opus_4_7.
#   * Antigravity lane (agy):     run ONE gemini at a time — gemini_3_1_pro first, then gemini35_flash.
#   * Codex (gpt) + OS (qwen/minimax) run in parallel with the above.
set -u
cd "$(dirname "$0")/.."

CLEAN24="15-100,15-104,28-02A,28-07A,28-100,28-108,28-109,28-112,40-01A,40-04,40-04A,40-05,40-12A,41B-03A,41B-07A,41B-08,41B-10A,41F-01,41F-02,6-01,6-047,6-051,6-07A"
RID_NATIVE="bench_v2_native"
RID_OS="bench_v2_os"
TD="tasks_test"
RO=3
TO=1500

hd() { python3 harness/home_driver.py --tasks-dir "$TD" --tasks "$CLEAN24" --rollouts "$RO" --run-id "$RID_NATIVE" --resume --timeout "$TO" "$@"; }

case "${1:-help}" in
  opus_4_8)        hd --agent claude_code --model claude-opus-4-8 --model-tag opus_4_8 ;;
  opus_4_7)        hd --agent claude_code --model claude-opus-4-7 --model-tag opus_4_7 ;;
  gpt_5_5)         hd --agent codex_cli                            --model-tag gpt_5_5 ;;
  gemini_3_1_pro)  hd --agent antigravity --model "Gemini 3.1 Pro (Low)"   --model-tag gemini_3_1_pro --effort low ;;
  gemini35_flash)  hd --agent antigravity --model "Gemini 3.5 Flash (Low)" --model-tag gemini35_flash --effort low ;;
  os_create)       python3 harness/run.py --run-id "$RID_OS" --models qwen3_vl_plus --tasks "$CLEAN24" --tasks-dir "$TD" --rollouts "$RO" ;;
  minimax_m3)      python3 harness/run.py --resume "$RID_OS"  --models minimax_m3    --tasks "$CLEAN24" --tasks-dir "$TD" --rollouts "$RO" ;;
  qwen3_vl_plus)   python3 harness/run.py --resume "$RID_OS"  --models qwen3_vl_plus --tasks "$CLEAN24" --tasks-dir "$TD" --rollouts "$RO" ;;
  *) echo "usage: $0 {opus_4_8|opus_4_7|gpt_5_5|gemini_3_1_pro|gemini35_flash|os_create|qwen3_vl_plus|minimax_m3}"; exit 1 ;;
esac
