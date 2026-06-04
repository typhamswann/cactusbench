# saguaro-bench-env

Vendored Harbor runtime for [SaguaroBench](https://github.com/typhamswann/saguaro-bench).
Ships the `sab` CLI used inside each benchmark task container:

```text
sab info                 # build info
sab help                 # env contract — printed to the agent on startup
sab harbor-init /task    # boot: read /task/{source.json, instruction.md},
                         # materialize /workspace/{brief.md, state.json}
sab harbor-step --tool NAME --args JSON
                         # apply one tool call, update /workspace
sab harbor-score         # write /logs/verifier/reward.{txt,json}
```

This package is intentionally dependency-free — it does no image decoding,
no network calls, no model inference. It just stages bundled PNG/JPG assets
into `/workspace` when the agent asks for them, and applies a structural-plus-
exact-match score to the final submission.

Built into the `saguaro-bench-base:1.0` image by `base/Dockerfile`.
