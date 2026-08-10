#!/usr/bin/env sh
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ERRORS=0
check() { printf '%-24s %-8s %s\n' "$1" "$2" "$3"; [ "$2" != "ERROR" ] || ERRORS=1; }

printf '%s\n' "Multimodal Video Intelligence — environment doctor" "Repository: $ROOT" ""
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then PYTHON=$candidate; break; fi
done
if [ -n "$PYTHON" ]; then
    VERSION=$($PYTHON -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
    if "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then check "Python" "OK" "Version $VERSION"; else check "Python" "ERROR" "Version $VERSION; 3.12+ required."; fi
else
    check "Python" "ERROR" "Not found; install Python 3.12+."
fi

if [ -x "$ROOT/.venv/bin/python" ]; then
    check "Virtual environment" "OK" ".venv is available."
    if "$ROOT/.venv/bin/python" -c 'import video_intelligence' 2>/dev/null; then check "Package installation" "OK" "Installed in .venv."; else check "Package installation" "ERROR" "Run ./setup.sh again."; fi
else
    check "Virtual environment" "ERROR" "Missing. Run ./setup.sh."
    check "Package installation" "ERROR" "Unavailable until setup completes."
fi

if mkdir -p "$ROOT/artifacts" && PROBE=$(mktemp "$ROOT/artifacts/.write-test.XXXXXX") 2>/dev/null; then rm -f "$PROBE"; check "Writable artifacts" "OK" "$ROOT/artifacts"; else check "Writable artifacts" "ERROR" "The artifacts directory is not writable."; fi

if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    check "Git repository" "OK" "Local clone detected."
    BRANCH=$(git -C "$ROOT" branch --show-current 2>/dev/null)
    [ -n "$BRANCH" ] && check "Current branch" "OK" "$BRANCH" || check "Current branch" "WARNING" "Detached or unavailable."
    git -C "$ROOT" remote get-url origin >/dev/null 2>&1 && check "Git remote" "OK" "origin is configured." || check "Git remote" "WARNING" "No origin configured."
else
    check "Git repository" "WARNING" "Git checkout not detected; synchronization unavailable."
fi

if command -v node >/dev/null 2>&1; then check "Node.js" "OK" "$(node --version) (extension only)"; else check "Node.js" "WARNING" "Required only for extension development."; fi
if command -v npm >/dev/null 2>&1 && [ -d "$ROOT/extension/node_modules" ] && (cd "$ROOT/extension" && npm ls --depth=0 --silent >/dev/null 2>&1); then
    check "Extension tools" "OK" "Installed and consistent."
else
    check "Extension tools" "WARNING" "Run ./setup.sh --require-extension if needed."
fi
for binary in ffmpeg ffprobe; do
    if command -v "$binary" >/dev/null 2>&1; then check "$binary" "OK" "$(command -v "$binary")"; else check "$binary" "WARNING" "Optional for demo; required for real media."; fi
done

if [ -x "$ROOT/.venv/bin/python" ]; then
    printf '\n%s\n' "Application checks:"
    "$ROOT/.venv/bin/python" -m video_intelligence.cli doctor || ERRORS=1
fi

printf '\n'
if [ "$ERRORS" -ne 0 ]; then printf '%s\n' "Doctor found required problems. Correct them and run doctor.sh again."; exit 1; fi
printf '%s\n' "Required checks passed. Warnings apply only to advanced features."
