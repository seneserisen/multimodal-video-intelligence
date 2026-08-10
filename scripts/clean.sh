#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
for relative in artifacts build extension/dist .pytest_cache .mypy_cache .ruff_cache; do
    target="$ROOT/$relative"
    case "$target" in "$ROOT"/*) ;; *) printf '%s\n' "Refusing to clean outside repository: $target" >&2; exit 1;; esac
    if [ -e "$target" ]; then rm -rf -- "$target"; printf '%s\n' "Removed $relative"; fi
done
for source_root in "$ROOT/backend" "$ROOT/tests" "$ROOT/scripts"; do
    [ ! -d "$source_root" ] || find "$source_root" -type d -name __pycache__ -prune -exec rm -rf -- {} +
done
printf '%s\n' "Generated outputs were cleaned. .venv and extension/node_modules were preserved."
