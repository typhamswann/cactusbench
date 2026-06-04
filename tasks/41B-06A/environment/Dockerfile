FROM saguaro-bench-base:1.0

# Bake this task's definition + assets into the image.
COPY source.json instruction.md task.toml /task/
COPY assets /task/assets/

WORKDIR /workspace

# Boot the sim on container start — /workspace/{system.md, brief.md, state.json}
# are then ready from turn 0.
RUN { \
      echo '#!/usr/bin/env bash'; \
      echo 'set -euo pipefail'; \
      echo 'sab harbor-init /task'; \
      echo 'exec "$@"'; \
    } > /usr/local/bin/sab-entrypoint.sh \
 && chmod +x /usr/local/bin/sab-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/sab-entrypoint.sh"]
CMD ["/bin/bash"]
