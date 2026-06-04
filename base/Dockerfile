# SaguaroBench base image — the runtime, baked in.
# Build once:  docker build -t saguaro-bench-base:1.0 base/
# Task images then `FROM saguaro-bench-base:1.0` (see tasks/*/environment/Dockerfile).
# Self-contained: the `sab` CLI comes from the vendored package in this repo,
# NOT from any external GitHub repo. No network is needed at task-build time.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates && rm -rf /var/lib/apt/lists/*

# Vendored, slim runtime — pure stdlib, no Pillow/numpy/verifiers. Tasks
# bundle their own PNGs/JPGs and the agent reads them directly; the CLI only
# stages them into /workspace and grades the submission.
COPY pkg /opt/saguaro-bench-pkg
RUN pip install --no-cache-dir /opt/saguaro-bench-pkg && sab info

# Per-task images set ENTRYPOINT to run `sab harbor-init /task` on boot so
# /workspace/{system.md, brief.md, state.json} are ready from turn 0.

# Optional turn budget. Left UNSET on purpose — by default a task runs with NO
# turn limit (the agent decides when to submit_mapping). To surface a budget
# to the agent, set it at run time:
#     docker run -e SAGUARO_BENCH_MAX_TURNS=20 saguaro-bench-task-<id>
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace
