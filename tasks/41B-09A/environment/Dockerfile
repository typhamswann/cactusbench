FROM saguaro-bench-base:1.0

# Agent-visible workspace. Bake the assets in at build time so the agent
# never has to call a custom tool to "load" them — its standard file-read
# primitive sees them directly.
RUN mkdir -p /workspace/datasheets /workspace/photos/2023 /workspace/photos/2026

COPY assets/datasheets/2023.png  /workspace/datasheets/2023.png
COPY assets/datasheets/2026.png  /workspace/datasheets/2026.png
COPY assets/photos/2023/         /workspace/photos/2023/
COPY assets/photos/2026/         /workspace/photos/2026/
COPY brief.md instruction.md     /workspace/

# Verifier-only data (ground truth + scorer). Root-owned, mode-locked so the
# agent user cannot read it.
COPY grade/ /grade/
RUN chmod 700 /grade && chmod 600 /grade/truth.json && chmod 700 /grade/score.py

# Create the agent user and give it the workspace.
RUN useradd -m -s /bin/bash agent && chown -R agent:agent /workspace

USER agent
WORKDIR /workspace
CMD ["/bin/bash"]
