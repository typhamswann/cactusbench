"""`sab` — the SaguaroBench command-line runner inside a task container.

Subcommands:

    sab info                 build info — runtime version + env paths
    sab help                 print the agent-facing env contract

    # Per-task driver (one task per process, state on disk):
    sab harbor-init <task_dir>             boot the sim in /workspace
    sab harbor-step --tool NAME [--args JSON]
    sab harbor-score                       emit /logs/verifier/reward.{txt,json}

Mirrors the wanderbench `wb` harbor-* pattern: each subcommand reads/writes
a small amount of JSON state on disk, prints a one-line summary to stdout,
and exits 0 unless something irrecoverable happened (in which case it exits
non-zero AND writes a structural_error to state).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from . import env as ENV
from .prompts import SYSTEM_PROMPT, HELP_TEXT, build_brief
from .scoring import score
from .tools import dispatch, ALLOWED_TOOLS


# ----------------------------------------------------------------------------
# sab info / sab help
# ----------------------------------------------------------------------------

def cmd_info(_args: argparse.Namespace) -> int:
    info = {
        "package": "saguaro-bench-env",
        "version": __version__,
        "task_dir": str(ENV.TASK_DIR),
        "workspace": str(ENV.WORKSPACE),
        "logs": str(ENV.LOGS),
        "tools": sorted(ALLOWED_TOOLS),
    }
    print(json.dumps(info, indent=2))
    return 0


def cmd_help(_args: argparse.Namespace) -> int:
    print(HELP_TEXT)
    return 0


# ----------------------------------------------------------------------------
# sab harbor-init <task_dir>
# ----------------------------------------------------------------------------

def cmd_harbor_init(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir).resolve()
    if not task_dir.exists():
        print(f"[sab] ERROR: task dir {task_dir} does not exist", file=sys.stderr)
        return 2

    # Re-anchor ENV.TASK_DIR for this process (so subsequent harbor-step picks
    # it up via the source.json read on /task).
    ENV.ensure_dirs()

    src_path = task_dir / "source.json"
    if not src_path.exists():
        print(f"[sab] ERROR: source.json missing at {src_path}", file=sys.stderr)
        return 2

    # If task_dir != /task, symlink so all downstream code can assume /task.
    target = ENV.TASK_DIR
    if task_dir != target:
        if target.exists() or target.is_symlink():
            # Best-effort: only replace if the existing target points elsewhere.
            try:
                if target.is_symlink() and target.resolve() == task_dir:
                    pass
                else:
                    if target.is_symlink():
                        target.unlink()
                    elif target.is_dir():
                        # Existing /task baked in by the Dockerfile — leave it,
                        # the source.json is already there.
                        pass
            except FileNotFoundError:
                pass
        if not target.exists():
            try:
                target.symlink_to(task_dir, target_is_directory=True)
            except OSError as e:
                print(f"[sab] WARN: could not symlink /task -> {task_dir}: {e}", file=sys.stderr)

    record = json.loads((target / "source.json").read_text())

    # Materialize the static prompt artifacts.
    (ENV.WORKSPACE / "system.md").write_text(SYSTEM_PROMPT + "\n")
    (ENV.WORKSPACE / "brief.md").write_text(build_brief(record) + "\n")

    # Initialize state.json.
    import os as _os
    max_turns_env = _os.environ.get("SAGUARO_BENCH_MAX_TURNS")
    try:
        max_turns = int(max_turns_env) if max_turns_env else None
    except ValueError:
        max_turns = None

    state = {
        "saguaro_id": record["saguaro_id"],
        "turn": 0,
        "last_tool": None,
        "history": [],
        "submission_complete": False,
        "view_paper": None,
        "view_photo": None,
        "max_turns": max_turns,
    }
    ENV.write_state(state)

    print(f"[sab] harbor-init ok  saguaro={record['saguaro_id']}  "
          f"arms_2023={len(record['rows_2023'])}  arms_2026={len(record['rows_2026'])}  "
          f"photos_2023={ENV.n_photos(record, 2023)}  photos_2026={ENV.n_photos(record, 2026)}")
    return 0


# ----------------------------------------------------------------------------
# sab harbor-step --tool NAME --args JSON
# ----------------------------------------------------------------------------

def cmd_harbor_step(args: argparse.Namespace) -> int:
    tool = args.tool
    if tool not in ALLOWED_TOOLS:
        print(f"[sab] ERROR: unknown tool {tool!r}; allowed: {sorted(ALLOWED_TOOLS)}",
              file=sys.stderr)
        return 2
    raw = args.args or "{}"
    try:
        tool_args = json.loads(raw)
    except Exception as e:
        print(f"[sab] ERROR: --args must be JSON: {e}", file=sys.stderr)
        return 2
    if not isinstance(tool_args, dict):
        print(f"[sab] ERROR: --args must decode to an object", file=sys.stderr)
        return 2

    record = json.loads((ENV.TASK_DIR / "source.json").read_text())
    state = ENV.read_state()

    if state.get("submission_complete") and tool != "submit_mapping":
        # Tolerate but no-op.
        msg = f"[sab] step ignored (already submitted): {tool}"
        print(msg)
        return 0

    state["turn"] = int(state.get("turn", 0)) + 1
    summary, payload = dispatch(tool, tool_args, record, state)

    entry = {
        "turn": state["turn"],
        "name": tool,
        "args": tool_args,
        "result": summary,
        "payload": payload,
    }
    ENV.append_history(state, entry)
    ENV.write_state(state)

    print(f"[sab] turn={state['turn']} tool={tool} :: {summary}")
    return 0


# ----------------------------------------------------------------------------
# sab harbor-score
# ----------------------------------------------------------------------------

def cmd_harbor_score(_args: argparse.Namespace) -> int:
    ENV.ensure_dirs()
    record = json.loads((ENV.TASK_DIR / "source.json").read_text())

    sub_path = ENV.WORKSPACE / "submission.json"
    submission_raw = None
    if sub_path.exists():
        try:
            sub_obj = json.loads(sub_path.read_text())
            submission_raw = sub_obj.get("submission")
        except Exception as e:
            submission_raw = None
            print(f"[sab] WARN: could not parse submission.json: {e}", file=sys.stderr)

    metrics = score(submission_raw, record)
    reward = float(metrics.get("exact_mapping_reward", 0.0))

    (ENV.LOGS_VERIFIER / "reward.txt").write_text(f"{reward}\n")
    full = {
        "exact_mapping_reward": reward,
        "arm_pair_f1": float(metrics.get("arm_pair_f1", 0.0)),
        "saguaro_id": record["saguaro_id"],
    }
    if metrics.get("structural_error"):
        full["structural_error"] = metrics["structural_error"]
    (ENV.LOGS_VERIFIER / "reward.json").write_text(json.dumps(full, indent=2))

    # Also stash a copy of the state we used so verifier output is auditable.
    try:
        state = ENV.read_state()
        (ENV.LOGS_ARTIFACTS / "final_state.json").write_text(json.dumps(state, indent=2))
    except FileNotFoundError:
        pass

    print(f"[sab] reward={reward} f1={full['arm_pair_f1']:.3f} "
          f"saguaro={record['saguaro_id']}"
          + (f" structural_error={full['structural_error']}" if "structural_error" in full else ""))
    return 0


# ----------------------------------------------------------------------------
# argparse wiring
# ----------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sab", description="SaguaroBench task runner")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info", help="print runtime + paths").set_defaults(func=cmd_info)
    sub.add_parser("help", help="print env contract for the agent").set_defaults(func=cmd_help)

    p_init = sub.add_parser("harbor-init", help="boot the sim in /workspace from a task dir")
    p_init.add_argument("task_dir", help="path to the task dir (must contain source.json)")
    p_init.set_defaults(func=cmd_harbor_init)

    p_step = sub.add_parser("harbor-step", help="apply one tool call")
    p_step.add_argument("--tool", required=True, choices=sorted(ALLOWED_TOOLS))
    p_step.add_argument("--args", default="{}", help="JSON object of tool arguments")
    p_step.set_defaults(func=cmd_harbor_step)

    sub.add_parser("harbor-score", help="grade the submission and emit reward").set_defaults(
        func=cmd_harbor_score
    )

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
