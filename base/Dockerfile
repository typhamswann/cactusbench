# CactusBench base image.
# Build once:  docker build -t cactusbench-base:1.0 base/
# Each task image is `FROM cactusbench-base:1.0` (see tasks/*/environment/Dockerfile).
#
# Contains nothing benchmark-specific — just a Python interpreter for the
# verifier, plus `jq` for pulling reward.txt out of reward.json in test.sh.
# Per-task images bake in their own assets + verifier-only grade/ data and
# create an `agent` user that owns /workspace.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates jq && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
