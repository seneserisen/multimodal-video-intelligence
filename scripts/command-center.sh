#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON="$ROOT/.venv/bin/python"
ACTION=${1:-start}
if [ "$#" -gt 0 ]; then shift; fi

case "$ACTION" in
    start|status|stop|update) ;;
    *)
        printf '%s\n' "Usage: ./command-center.sh [start|status|stop|update] [options]" >&2
        exit 2
        ;;
esac

if [ ! -x "$PYTHON" ]; then
    printf '%s\n' "The project is not set up yet. Running setup now..."
    sh "$ROOT/scripts/setup.sh"
fi

exec "$PYTHON" -m video_intelligence.cli "$ACTION" "$@"
