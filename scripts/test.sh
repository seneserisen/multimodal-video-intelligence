#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON="$ROOT/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    printf '%s\n' "TESTS FAILED: .venv is missing. Run ./setup.sh first." >&2
    exit 1
fi

cd "$ROOT"
"$PYTHON" -m pytest
"$PYTHON" -m ruff check .
"$PYTHON" -m ruff format --check .
"$PYTHON" -m mypy backend/src
sh "$ROOT/scripts/run.sh" --no-open

if ! command -v npm >/dev/null 2>&1 || [ ! -d "$ROOT/extension/node_modules" ]; then
    printf '%s\n' "TESTS FAILED: extension tools are missing. Run ./setup.sh --require-extension." >&2
    exit 1
fi
(cd "$ROOT/extension" && npm test && npm run lint && npm run build && npm audit)
printf '\n%s\n' "All project verification completed successfully."
