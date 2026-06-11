"""Home-harness driver for SaguaroBench (Path A / H-home).

The OpenRouter harness (run.py) scores every model on ONE portable surface. But
Cai §1 requires also scoring each frontier model under the harness it was
post-trained against — Claude Code (`Read`/`str_replace`), Codex CLI
(`apply_patch`), Gemini CLI — because the image-read primitive and tool shape are
the lab's actual production surface. The gap between that and the portable surface
is the surface-stratification finding (`scripts/stratify.py`).

This driver does NOT reimplement those agents. It:
  1. materializes a real on-disk workspace per task (instruction.md + opaque
     datasheets/ + photos/), exactly the Path-A contract from the README;
  2. invokes a configured agent COMMAND (the production CLI in its non-interactive
     mode) with that workspace as cwd, telling it to write submission.json;
  3. scores the resulting submission.json with the SAME grade/score.py;
  4. writes a result record in the SAME schema as run.py, so aggregate.py /
     stratify.py / failure_taxonomy.py treat H-home and H-port uniformly.

Fields the home agents don't expose (served_provider, transmitted image_manifest)
are recorded null — H-home is the "production capability" number; the lab's
internal image handling is its surface, not observable here. That asymmetry is the
point of the H-home vs H-port comparison.

Agent profiles live in harness/home_agents.json (command templates per CLI).
Verify the CLI is installed + the invocation before a scored run — see
docs/TEST-MATRIX.md §2 (H-home).

Usage:
    python harness/home_driver.py --agent claude_code --tasks 41B-09,41B-13 \
        --run-id t2_home --timeout 1800
    python harness/home_driver.py --agent fake_perfect --tasks all   # self-test
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


# Parent Claude-Code session vars must be stripped before spawning a nested CLI —
# home_driver runs INSIDE a Claude Code session, and these leak into qwen/codex/
# nested-claude, colliding and hanging the child agent (the cause of the Qwen Code
# image-task hang; matches wanderbench run_native_harness._rollout_env).
_STRIP_PARENT_ENV = (
    "CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_EFFORT", "ANTHROPIC_MODEL", "CLAUDE_CODE_EXECPATH",
)


def build_env(profile: dict, model: str | None) -> dict:
    """Subprocess env = inherited env (minus parent Claude-Code session vars) +
    the profile's `route_env` (resolved). Used to point a native CLI at an
    OpenAI-compatible route (e.g. Qwen Code → OpenRouter via OPENAI_API_KEY/
    OPENAI_BASE_URL/OPENAI_MODEL). Values support `@file:~/path` and `{model}`."""
    env = dict(os.environ)
    for k in _STRIP_PARENT_ENV:
        env.pop(k, None)
    for k, v in (profile.get("route_env") or {}).items():
        if isinstance(v, str):
            if v.startswith("@file:"):
                v = Path(v[6:]).expanduser().read_text().strip()
            else:
                v = v.replace("{model}", model or "")
        env[k] = v
    return env

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# Isolation: home-agent workspaces are created OUTSIDE the repo tree (system temp),
# so a coding agent (Claude Code / Codex) cannot (a) reach the benchmark truth at
# tasks/<sid>/grade/truth.json by walking the filesystem, or (b) inherit the repo's
# / parent project's CLAUDE.md, .claude/settings, or git context. Each (agent, task,
# rollout) gets a fresh dir that is deleted after scoring.
ISOLATION_PREFIX = "sb_home_"

# Wrapper instruction appended to the task's own instruction.md when prompting the
# agent (the on-disk contract is otherwise identical to Path B).
WRAPPER_PROMPT = (
    "You are curating one saguaro. Read ./instruction.md in this directory, then "
    "read the datasheets in ./datasheets/ and the photos in ./photos/ using your "
    "image-read tool, and write your final cleaned table to ./submission.json "
    "(a JSON list of row objects, per the instruction). Write submission.json "
    "exactly once when done."
)

DEFAULT_AGENTS = {
    # Each profile: cmd is a list; {prompt} is replaced with WRAPPER_PROMPT.
    # The command runs with cwd = the task workspace. VERIFY before a scored run.
    "claude_code": {
        "cmd": ["claude", "-p", "--dangerously-skip-permissions", "--strict-mcp-config",
                "{model}", "{prompt}"],
        "model_flag": "--model",
        "notes": "Claude Code print-mode, isolated (no MCP, skip-permissions). Reads images "
                 "via Read; agent CHOOSES which images to open. Home harness for Opus/Sonnet.",
    },
    "codex_cli": {
        "cmd": ["codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write",
                "{model}", "{prompt}", "{images}"],
        "image_attach": "-i",
        "model_flag": "-m",
        "notes": "Codex CLI. Images MUST be pre-attached via -i (greedy flag, so {prompt} "
                 "must precede {images}); needs --skip-git-repo-check + workspace-write; "
                 "stdin closed. The agent cannot read images from disk like Claude Code.",
    },
    "gemini_cli": {
        "cmd": ["gemini", "-p", "{prompt}", "--yolo"],
        "notes": "Gemini CLI non-interactive. Home harness for Gemini. Native tool schema.",
    },
    # Self-test profile: writes the perfect submission from truth (no real agent).
    "fake_perfect": {"cmd": ["__FAKE_PERFECT__"], "notes": "self-test only"},
}


def load_agents() -> dict:
    p = HERE / "home_agents.json"
    if p.exists():
        blob = json.loads(p.read_text())
        return blob.get("agents", blob)
    return DEFAULT_AGENTS


PROBE_PROMPT = (
    "There are image files in ./datasheets/ (a saguaro field form). Open them with "
    "your image-viewing tool and READ the sheet header. Write ONLY this line to a "
    "file ./probe.txt: saguaro=<the Saguaro No. on the sheet> arms=<the 'No. arms "
    "including nubbins' value on the sheet>. You must read both from the image; do "
    "not guess. If you cannot see the image, write: NO_VISION."
)


def image_probe(agent: str, profile: dict, task_dir: Path, timeout: int,
                model: str | None = None) -> dict:
    """Run the agent on one task with a probe that's only answerable from the image,
    to verify the CLI actually passes images to the (vision-capable) model. Returns a
    verdict: vision exposed / not exposed / inconclusive."""
    sid = task_dir.name
    ws = Path(tempfile.mkdtemp(prefix=f"{ISOLATION_PREFIX}probe_{agent}_"))
    materialize_workspace(task_dir, ws)
    if profile["cmd"] == ["__FAKE_PERFECT__"]:
        (ws / "probe.txt").write_text("saguaro=13 arms=2")
    else:
        cmd = build_cmd(profile, PROBE_PROMPT, _image_files(ws, sheets_only=True), model)
        try:
            subprocess.run(cmd, cwd=str(ws), timeout=timeout, capture_output=True, text=True, input="")
        except FileNotFoundError:
            return {"agent": agent, "verdict": "agent_not_installed"}
        except subprocess.TimeoutExpired:
            return {"agent": agent, "verdict": "timeout"}
    pf = ws / "probe.txt"
    if not pf.exists():
        return {"agent": agent, "verdict": "no_output", "saw_image": None}
    txt = pf.read_text().strip()
    low = txt.lower()
    if "no_vision" in low:
        return {"agent": agent, "verdict": "vision_NOT_exposed", "probe": txt}
    # Expected, from truth: saguaro number (numeric part of sid) + arm count.
    truth = json.loads((task_dir / "grade" / "truth.json").read_text())
    sag_num = sid.split("-", 1)[-1].lstrip("0").lower()
    yrs = {}
    for r in truth["truth_rows"]:
        if not r.get("_excluded"):
            yrs.setdefault(r["year"], set()).add(str(r["arm"]))
    arm_counts = {len(v) for v in yrs.values()}
    saw_sag = sag_num and sag_num in low.replace(" ", "")
    saw_arms = any(str(c) in low for c in arm_counts)
    verdict = ("vision_exposed" if (saw_sag or saw_arms)
               else "inconclusive_or_text_only")
    return {"agent": agent, "verdict": verdict, "saw_saguaro_no": bool(saw_sag),
            "saw_arm_count": bool(saw_arms), "probe": txt[:200],
            "expected_saguaro": sag_num, "expected_arm_counts": sorted(arm_counts)}


def _image_files(ws: Path, sheets_only: bool) -> list:
    """Relative image paths in a workspace, for harnesses that need images
    pre-attached (e.g. Codex's -i) rather than discovered by the agent."""
    out = [f"datasheets/{p.name}" for p in sorted((ws / "datasheets").glob("*"))]
    if not sheets_only and (ws / "photos").exists():
        out += [f"photos/{p.name}" for p in sorted((ws / "photos").glob("*"))]
    return out


def build_cmd(profile: dict, prompt: str, image_files: list, model: str | None = None,
              effort: str | None = None) -> list:
    """Expand a profile cmd template. {prompt} -> the instruction; {images} ->
    the attach flag + files; {model} -> model_flag + model id; {effort} ->
    the profile's effort_tmpl with {e} filled in (e.g. --effort high for Claude,
    -c model_reasoning_effort=high for Codex)."""
    attach = profile.get("image_attach")       # e.g. "-i" (Codex) or None (Claude Code)
    mflag = profile.get("model_flag")          # e.g. "--model" (claude) / "-m" (codex)
    etmpl = profile.get("effort_tmpl")         # e.g. ["--effort","{e}"] / ["-c","model_reasoning_effort={e}"]
    cmd = []
    for tok in profile["cmd"]:
        if tok == "{prompt}":
            cmd.append(prompt)
        elif tok == "{images}":
            if attach and image_files:
                cmd.append(attach)
                cmd.extend(image_files)
        elif tok == "{model}":
            if model and mflag:
                cmd.extend([mflag, model])
        elif tok == "{effort}":
            if effort and etmpl:
                cmd.extend([t.replace("{e}", effort) for t in etmpl])
        else:
            cmd.append(tok)
    return cmd


def materialize_workspace(task_dir: Path, ws: Path) -> None:
    if ws.exists():
        shutil.rmtree(ws)
    (ws / "datasheets").mkdir(parents=True)
    (ws / "photos").mkdir(parents=True)
    shutil.copyfile(task_dir / "instruction.md", ws / "instruction.md")
    for f in sorted((task_dir / "assets" / "datasheets").iterdir()):
        shutil.copyfile(f, ws / "datasheets" / f.name)
    pdir = task_dir / "assets" / "photos"
    if pdir.exists():
        for f in sorted(pdir.iterdir()):
            if f.is_file():
                shutil.copyfile(f, ws / "photos" / f.name)


def _fake_perfect(task_dir: Path, ws: Path) -> None:
    truth = json.loads((task_dir / "grade" / "truth.json").read_text())
    rows = []
    for r in truth["truth_rows"]:
        if r.get("_excluded"):
            continue
        rr = {k: r[k] for k in ("saguaro_id", "year", "arm", "direction", "A", "B", "C", "D", "E")}
        n = r.get("note", "")
        rr["note"] = next((x for x in n if x), "") if isinstance(n, list) else n
        rows.append(rr)
    (ws / "submission.json").write_text(json.dumps(rows))


def run_one(agent: str, profile: dict, task_dir: Path, timeout: int,
            model: str | None = None, model_tag: str | None = None,
            rollout_idx: int = 0, effort: str | None = None,
            run_id: str | None = None) -> dict:
    sid = task_dir.name
    # Isolated workspace OUTSIDE the repo — agent can't reach truth or repo config.
    ws = Path(tempfile.mkdtemp(prefix=f"{ISOLATION_PREFIX}{agent}_"))
    started = time.time()
    stop = "ok"
    try:
        materialize_workspace(task_dir, ws)
        # Qwen Code (Gemini-CLI fork) routes vision-less models to its Computer Use
        # tool, whose first-run triggers an interactive install prompt that DEADLOCKS
        # under stdin=DEVNULL (the "hang"), and would otherwise drive the real desktop.
        # This is a file-based curation task — exclude the desktop-control surface so
        # every model gets the same file-read tools: vision models read the images,
        # vision-less models bail fast (0) instead of hanging or hijacking the screen.
        if agent.startswith("qwen"):
            qdir = ws / ".qwen"; qdir.mkdir(exist_ok=True)
            (qdir / "settings.json").write_text(json.dumps({"tools": {"exclude": [
                f"computer_use__{n}" for n in (
                    "click", "drag", "get_app_state", "list_apps",
                    "perform_secondary_action", "press_key", "scroll",
                    "set_value", "type_text")]}}))
        cap_out, cap_err = "", ""
        if profile["cmd"] == ["__FAKE_PERFECT__"]:
            _fake_perfect(task_dir, ws)
        else:
            imgs = _image_files(ws, sheets_only=False)
            cmd = build_cmd(profile, WRAPPER_PROMPT, imgs, model, effort)
            try:
                # stdin=DEVNULL is essential — qwen/codex block reading piped stdin.
                rp = subprocess.run(cmd, cwd=str(ws), timeout=timeout,
                                    capture_output=True, text=True,
                                    stdin=subprocess.DEVNULL, env=build_env(profile, model))
                cap_out, cap_err = rp.stdout or "", rp.stderr or ""
            except FileNotFoundError:
                stop = "agent_not_installed"
            except subprocess.TimeoutExpired as e:
                stop = "timeout"
                # On timeout the partial transcript is the key error-analysis signal.
                cap_out = (e.stdout.decode() if isinstance(e.stdout, bytes) else e.stdout) or ""
                cap_err = (e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr) or ""
            except Exception as e:  # noqa: BLE001
                stop = f"agent_error:{str(e)[:80]}"
        # Persist the agent transcript BEFORE the workspace is wiped, so hangs /
        # no-submission failures remain analyzable. One file per cell.
        if cap_out or cap_err:
            try:
                logdir = REPO / "runs" / (run_id or "_adhoc") / "transcripts"
                logdir.mkdir(parents=True, exist_ok=True)
                tag = model_tag or agent
                (logdir / f"{tag}__{sid}__r{rollout_idx}.log").write_text(
                    f"# agent={agent} model={model} tag={tag} sid={sid} "
                    f"rollout={rollout_idx} stop={stop}\n"
                    f"# ===== STDOUT =====\n{cap_out[:200000]}\n"
                    f"# ===== STDERR =====\n{cap_err[:200000]}\n")
            except Exception:  # noqa: BLE001
                pass

        sub = ws / "submission.json"
        score_py = task_dir / "grade" / "score.py"
        truth_path = task_dir / "grade" / "truth.json"
        try:
            proc = subprocess.run([sys.executable, str(score_py), str(sub), str(truth_path)],
                                  capture_output=True, text=True, timeout=60)
            reward = json.loads(proc.stdout)
        except Exception as e:  # noqa: BLE001
            reward = {"cell_accuracy_reward": 0.0, "structural_error": f"scoring_error:{e}"}
        submission_raw = sub.read_text()[:20000] if sub.exists() else None
        engaged = sub.exists()
    finally:
        shutil.rmtree(ws, ignore_errors=True)  # isolation: nothing persists

    return {
        "saguaro_id": sid,
        "model_tag": model_tag or agent,
        "agent": agent,
        "model": model,
        "effort": effort,
        "harness": f"home:{agent}",
        "rollout_idx": rollout_idx,
        "submission_raw": submission_raw,
        "cell_accuracy_reward": reward.get("cell_accuracy_reward", 0.0),
        "base_cell_accuracy": reward.get("base_cell_accuracy", 0.0),
        "row_f1": reward.get("row_f1", 0.0),
        "rows_truth": reward.get("rows_truth"),
        "rows_matched": reward.get("rows_matched"),
        "rows_missing": reward.get("rows_missing"),
        "rows_extra": reward.get("rows_extra"),
        "per_field_accuracy": reward.get("per_field_accuracy"),
        "note_accuracy_nonempty": reward.get("note_accuracy_nonempty"),
        "note_nonempty_total": reward.get("note_nonempty_total"),
        "structural_error": reward.get("structural_error"),
        "stop": stop,
        "engaged": engaged,
        # Home agents don't expose these — H-home is the production number; the
        # lab's internal image handling is its surface (not observable here).
        "served_providers_rollout": None,
        "image_manifest": None,
        "n_assets_read": None,
        "wall_time_sec": round(time.time() - started, 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--agent", required=True, help="agent profile (see harness/home_agents.json)")
    ap.add_argument("--model", default=None,
                    help="CLI model id passed to the agent (e.g. claude-opus-4.8, gpt-5.5). "
                         "Omit to use the CLI's default model.")
    ap.add_argument("--model-tag", default=None,
                    help="logical model name for result records + leaderboard join "
                         "(e.g. opus_4_8). Defaults to the agent name.")
    ap.add_argument("--tasks", default="all", help="comma-separated saguaro_ids or 'all'")
    ap.add_argument("--tasks-dir", default=str(REPO / "tasks"))
    ap.add_argument("--rollouts", type=int, default=1, help="rollouts per task (each isolated)")
    ap.add_argument("--effort", default=None,
                    help="reasoning effort: claude {low,medium,high,xhigh,max}; "
                         "codex {minimal,low,medium,high}. Omit for the CLI default.")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--resume", action="store_true",
                    help="append to runs/<run-id>/<model_tag>.json, skipping done cells")
    ap.add_argument("--timeout", type=int, default=1800, help="per-task agent timeout (s)")
    ap.add_argument("--image-probe", action="store_true",
                    help="run a one-task vision-exposure probe instead of scoring")
    args = ap.parse_args()

    agents = load_agents()
    if args.agent not in agents:
        raise SystemExit(f"unknown agent {args.agent!r}; known: {sorted(agents)}")
    profile = agents[args.agent]
    tasks_dir = Path(args.tasks_dir)
    model_tag = args.model_tag or args.agent

    if args.image_probe:
        probe_task = (args.tasks.split(",")[0].strip()
                      if args.tasks not in (None, "all") else "41B-13")
        v = image_probe(args.agent, profile, tasks_dir / probe_task, args.timeout, args.model)
        print(json.dumps(v, indent=2))
        return 0

    if args.tasks == "all":
        tasks = sorted(p for p in tasks_dir.iterdir() if p.is_dir() and (p / "task.toml").exists())
    else:
        tasks = [tasks_dir / s.strip() for s in args.tasks.split(",") if s.strip()]

    run_id = args.run_id or ("home_" + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ"))
    runs_dir = REPO / "runs" / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    out_path = runs_dir / f"{model_tag}.json"

    results, done = [], set()
    if args.resume and out_path.exists():
        prior = json.loads(out_path.read_text())
        results = prior.get("results", [])
        done = {(r["saguaro_id"], r.get("rollout_idx", 0)) for r in results}
        print(f"[home] resuming: {len(done)} cells already scored", flush=True)

    print(f"[home] agent={args.agent} model={args.model or 'default'} tag={model_tag} "
          f"n_tasks={len(tasks)} rollouts={args.rollouts} run={run_id}", flush=True)
    # Rate-limit abort: if a provider (Claude 5hr / Codex / Antigravity quota) is
    # throttling, cells return empty in <15s. Stop after N consecutive such cells so
    # a resume-into-an-active-limit self-terminates instead of flooding the file with
    # junk zero-cells (which --resume would then treat as done). Tunable.
    consec_ff = 0
    FF_ABORT = 4
    aborted = False
    for i, td in enumerate(tasks, 1):
        if aborted:
            break
        for r_idx in range(args.rollouts):
            if (td.name, r_idx) in done:
                continue
            rec = run_one(args.agent, profile, td, args.timeout,
                          model=args.model, model_tag=model_tag, rollout_idx=r_idx,
                          effort=args.effort, run_id=run_id)
            is_ff = (not rec.get("engaged")) and (rec.get("wall_time_sec") or 99) < 15
            consec_ff = consec_ff + 1 if is_ff else 0
            if is_ff and consec_ff < FF_ABORT:
                # don't record suspected rate-limit cells — avoids polluting resume
                print(f"  {i}/{len(tasks)} {td.name}#{r_idx}: FAST-FAIL "
                      f"({rec['wall_time_sec']}s, consec={consec_ff}) — not recorded", flush=True)
                continue
            if consec_ff >= FF_ABORT:
                print(f"[home] ABORT: {FF_ABORT} consecutive fast-fails — provider "
                      f"throttled; stopping (resume later).", flush=True)
                aborted = True
                break
            results.append(rec)
            print(f"  {i}/{len(tasks)} {td.name}#{r_idx}: reward={rec['cell_accuracy_reward']:.3f} "
                  f"engaged={rec['engaged']} stop={rec['stop']} {rec['wall_time_sec']}s", flush=True)
            out_path.write_text(json.dumps({
                "model_tag": model_tag, "agent": args.agent, "model": args.model,
                "harness": f"home:{args.agent}", "rollouts": args.rollouts,
                "results": results,
            }, indent=2))
    mean = sum(r["cell_accuracy_reward"] for r in results) / max(1, len(results))
    print(f"[home] done. mean={mean:.3f} (n={len(results)}) -> {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
