# CactusBench reproducibility manifest

A buyer cannot re-run a benchmark without knowing the exact surface it was scored
under (Cai §4). This is the canonical, run-wide manifest; each task also embeds a
`[manifest]` block in its `task.toml`.

## Task / sandbox contract

| key | value |
|---|---|
| `max_turns_per_rollout` | **50** (declared in the prompt; `harness/run.py --max-turns` default) |
| `network_egress_policy` | `none` — `allow_internet = false`; no network inside the task |
| `tool_approval_policy` | `auto` — tools execute without human approval |
| `isolation_granularity` | per-task container (Path A) / per-task temp workspace (Path B) |
| `observation_truncation_policy` | text reads truncated at 50,000 chars; images elided beyond a sliding window (default 6 most-recent user messages) |
| `asset_metadata_policy` | stripped + asserted clean at build (EXIF/XMP/IPTC/PNG-text removed) |
| `filename_policy` | sheets opaque (`sheet_A.png`/`sheet_B.png`, year hidden); photos year-tagged (`2023_NN.jpg`/`2026_NN.jpg`, within-year index opaque) |
| `docker_image` | `cactusbench-base:1.0` (`python:3.11-slim` + `jq`); per-task `cactusbench-task:1.0`. Record the built digest with `docker images --digests`. |
| `cpus / memory / storage` | 1 CPU / 2048 MB / 2048 MB per task |

> **docker_image_digest:** pin and publish the digest of the base image you built
> (`docker build -t cactusbench-base:1.0 base/ && docker images --digests`).
> It is environment-specific, so it is recorded at run time, not in the repo.

## Scoring contract

- Deterministic, **stdlib-only**, **no LLM judge** (`scripts/lib/score.py`, copied
  verbatim into each task's `grade/score.py`).
- `cell_accuracy_reward = max(0, correct_cells/total_cells - extra_row_penalty)`.
- Field tolerances: `direction ±1.0°`, `A,B,C,D,E ±0.011 m`.
- `note`: normalized-exact OR list-of-acceptable. **Jaccard is OFF the headline**
  (diagnostic only: `note_accuracy_jaccard_diag`). Note accuracy on non-empty
  truth notes is reported separately (`note_accuracy_nonempty`).
- Extra (hallucinated) rows: −0.05 each, capped at −0.5. Excluded rows: skipped.
- **Headline restricted to `headline_scored = true` tasks** (both years
  hand-redacted). 41B-22 (mixed redaction) is shipped but out of the headline.

## Harness contract (Path B — OpenRouter host harness)

These choices change the number and MUST be declared with any published result:

| knob | flag | default | why it matters |
|---|---|---|---|
| reasoning budget | `--reasoning {none,low,medium,high}` | `none` | Cai §5 — same model, different output per budget |
| provider route | `--pin-provider <Backend>` | unpinned | Cai §3 — OpenRouter load-balances across backends with different image preprocessing; pin for a scored run |
| rollouts / cell | `--rollouts N` | 1 (use ≥5 to score) | Cai §6 — CIs need n>1 |
| empty-resp shim | built-in | 4 retries | Cai §2 — open-weight clean-stop pattern; `terminator_shimmed` + raw/engaged reported |
| image window | `--image-window N` | 6 | truncation policy above |
| tool surface | native function-calling, text fallback | fc | tool-shape post-training (Cai §3) |
| image handoff | base64 data URL in user message | — | resolution actually transmitted recorded per attachment (`image_manifest`) |

Each result file records `served_providers_rollout`, `pin_provider`,
`provider_mismatch`, `reasoning`, `image_manifest`, `n_assets_read`, `engaged`,
and `terminator_shimmed` per rollout so the surface is fully reconstructable.

## What a published result must include

1. Headline: raw mean + 95% CI **and** engaged-subset mean + 95% CI.
2. The harness config row above (reasoning, route, rollouts, shim).
3. Provider route per model (`served_providers`), with a pin for scored runs.
4. A surface-stratification table across ≥2 configs (`scripts/stratify.py`),
   flagging cells with >5pp spread.
5. Per-difficulty breakdown with per-bucket n.
6. Cost / reward-per-dollar / median latency.
7. Failure-class taxonomy (`scripts/failure_taxonomy.py`).
8. The contamination check date (see [CONTAMINATION.md](CONTAMINATION.md)).
