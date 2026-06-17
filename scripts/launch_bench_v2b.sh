#!/usr/bin/env bash
# SaguaroBench v2b — the RECOVERED (formerly-misaligned, sheet-corrected) tasks.
# Kept separate from bench_v2 (clean-24) since this set is less hard-QA'd.
# Same harnesses / config / effort / 3 rollouts / save+resume as bench_v2; only the
# run-id and task list differ. All lanes parallel (no serial throttling).
set -u
cd "$(dirname "$0")/.."

# 25 recovered tasks (re-bundled this session; 15-106 & 6-08A run with one survey _excluded)
TASKS="15-66,15-67,15-75,15-80,15-81,15-106,15-108,15-109,15-111,15-112,40-102,40-105,40-107,40-108,40-121,41B-12A,41B-13A,41B-14,41B-15A,41B-17,41B-17A,41F-08,6-08A,6-08B,6-10A"
RID_NATIVE="bench_v2b_native"
RID_OS="bench_v2b_os"
TD="tasks_test"; RO=3; TO=1500

hd() { python3 harness/home_driver.py --tasks-dir "$TD" --tasks "$TASKS" --rollouts "$RO" --run-id "$RID_NATIVE" --resume --timeout "$TO" "$@"; }

case "${1:-help}" in
  opus_4_8)        hd --agent claude_code --model claude-opus-4-8 --model-tag opus_4_8 ;;
  opus_4_7)        hd --agent claude_code --model claude-opus-4-7 --model-tag opus_4_7 ;;
  gpt_5_5)         hd --agent codex_cli                            --model-tag gpt_5_5 ;;
  gemini_3_1_pro)  hd --agent antigravity --model "Gemini 3.1 Pro (Low)"   --model-tag gemini_3_1_pro --effort low ;;
  gemini35_flash)  hd --agent antigravity --model "Gemini 3.5 Flash (Low)" --model-tag gemini35_flash --effort low ;;
  os_create)       python3 harness/run.py --run-id "$RID_OS" --models qwen3_vl_plus --tasks "$TASKS" --tasks-dir "$TD" --rollouts "$RO" ;;
  qwen3_vl_plus)   python3 harness/run.py --resume "$RID_OS"  --models qwen3_vl_plus --tasks "$TASKS" --tasks-dir "$TD" --rollouts "$RO" ;;
  minimax_m3)      python3 harness/run.py --resume "$RID_OS"  --models minimax_m3    --tasks "$TASKS" --tasks-dir "$TD" --rollouts "$RO" ;;
  *) echo "usage: $0 {opus_4_8|opus_4_7|gpt_5_5|gemini_3_1_pro|gemini35_flash|os_create|qwen3_vl_plus|minimax_m3}"; exit 1 ;;
esac
