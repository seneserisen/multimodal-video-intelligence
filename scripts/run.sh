#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON="$ROOT/.venv/bin/python"
OUTPUT="$ROOT/artifacts/demo"
NO_OPEN=0
[ "${1:-}" = "--no-open" ] && NO_OPEN=1

if [ ! -x "$PYTHON" ]; then
    printf '%s\n' "The project is not set up yet. Running setup now..."
    sh "$ROOT/scripts/setup.sh"
fi

printf '%s\n' "Running the deterministic multimodal evidence demonstration..."
"$PYTHON" -m video_intelligence.cli analyze-evidence \
    --input "$ROOT/tests/fixtures/contradiction_case.json" \
    --profile balanced \
    --output-dir "$OUTPUT"
"$PYTHON" "$ROOT/scripts/validate_example.py" \
    "$OUTPUT/analysis.json" \
    "$ROOT/schemas/analysis-result.schema.json"

cat > "$OUTPUT/README.txt" <<'EOF'
Multimodal Video Intelligence - deterministic demonstration

Open summary.md for the readable result.
Open analysis.json for the complete versioned evidence output.

This demo uses synthetic checked-in evidence. It makes no network or AI-provider calls.
EOF

printf '\n%s\n' \
    "Demo completed successfully." \
    "The result identifies a contradiction across speech and screen evidence." \
    "Results: $OUTPUT" \
    "Open: $OUTPUT/summary.md"

if [ "$NO_OPEN" -eq 0 ] && [ "${CI:-}" != "true" ]; then
    if command -v xdg-open >/dev/null 2>&1; then xdg-open "$OUTPUT" >/dev/null 2>&1 || true
    elif command -v open >/dev/null 2>&1; then open "$OUTPUT" >/dev/null 2>&1 || true
    fi
fi
