#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
REQUIRE_EXTENSION=0
TRANSCRIPTION=0
for option in "$@"; do
    case "$option" in
        --require-extension) REQUIRE_EXTENSION=1 ;;
        --transcription) TRANSCRIPTION=1 ;;
        *) printf '%s\n' "Unknown setup option: $option" >&2; exit 2 ;;
    esac
done

find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

PYTHON=$(find_python || true)
if [ -z "$PYTHON" ]; then
    printf '%s\n' "SETUP FAILED" "Python 3.12 or newer was not found." "Install Python with your operating-system package manager, then run setup.sh again." >&2
    exit 1
fi

if [ ! -x "$ROOT/.venv/bin/python" ]; then
    printf '%s\n' "Creating the local Python environment..."
    "$PYTHON" -m venv "$ROOT/.venv"
else
    printf '%s\n' "Existing .venv detected; reusing it."
fi

printf '%s\n' "Installing the project and test tools..."
EXTRAS=dev
[ "$TRANSCRIPTION" -eq 1 ] && EXTRAS=dev,transcription
"$ROOT/.venv/bin/python" -m pip install --disable-pip-version-check -e "$ROOT[$EXTRAS]"

if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1 && [ "$(node -p "Number(process.versions.node.split('.')[0])")" -ge 20 ]; then
    LOCK_HASH=$("$PYTHON" -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$ROOT/extension/package-lock.json")
    LOCK_MARKER="$ROOT/extension/node_modules/.mvi-package-lock.sha256"
    if [ -f "$LOCK_MARKER" ] && [ "$(tr -d '\r\n' < "$LOCK_MARKER")" = "$LOCK_HASH" ] && (cd "$ROOT/extension" && npm ls --depth=0 --silent >/dev/null 2>&1); then
        printf '%s\n' "Extension dependencies already installed; reusing them."
    else
        printf '%s\n' "Node.js detected; installing the Chrome extension tools..."
        (cd "$ROOT/extension" && npm ci --no-audit --no-fund)
        printf '%s\n' "$LOCK_HASH" > "$LOCK_MARKER"
    fi
elif [ "$REQUIRE_EXTENSION" -eq 1 ]; then
    printf '%s\n' "SETUP FAILED" "Node.js 20+ and npm are required for extension development." >&2
    exit 1
else
    printf '%s\n' "WARNING: Node.js 20+ was not found. The basic demo is ready; extension development is not."
fi

printf '\n%s\n' "Setup completed successfully." "Next: run ./run.sh to generate the deterministic demonstration."
