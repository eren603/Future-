#!/bin/bash
# SessionStart hook: install Python deps required by the
# data-analysis-deep-scan skill (pandas/numpy/scipy).
# Idempotent, non-interactive, web-only.
set -euo pipefail

# Only run in Claude Code on the web (remote) environment.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Skip if already importable (container state is cached after first run).
if python3 -c "import pandas, numpy, scipy" >/dev/null 2>&1; then
  exit 0
fi

python3 -m pip install -q --disable-pip-version-check pandas numpy scipy || true
