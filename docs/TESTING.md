# Testing

Tests are deterministic, disable sockets through `pytest-socket`, use only fake providers, and isolate output under pytest temporary directories.

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy backend/src
python -m video_intelligence.cli analyze-evidence --input tests/fixtures/contradiction_case.json --profile balanced --output-dir build/example
python scripts/validate_example.py build/example/analysis.json schemas/analysis-result.schema.json
cd extension
npm install
npm test
npm run lint
npm run build
```

Real browser playback, recording, FFmpeg, OCR, ASR, visual analysis, and provider APIs are outside Milestone 1.

The MV3 scaffold was checked against the official Chrome documentation for the
[Side Panel API](https://developer.chrome.com/docs/extensions/reference/api/sidePanel),
[`activeTab`](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab), and
[static content scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts)
on 2026-07-20. The declared content-script matches are restricted to the three supported platforms.
