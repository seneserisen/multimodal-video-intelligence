# Testing

Tests are deterministic, disable sockets through `pytest-socket`, use only fake providers, and isolate output under pytest temporary directories.

Portfolio users can run the complete local verification through `TEST.bat` or `sh test.sh`. These are thin wrappers around the same commands below and also execute the deterministic demo. Launcher contract tests verify the expected entry points, ignored artifact location, thin-wrapper structure, cleanup scope, and absence of automatic Git staging or publishing.

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy backend/src
python -m video_intelligence.cli analyze-evidence --input tests/fixtures/contradiction_case.json --profile balanced --output-dir build/example
python scripts/validate_example.py build/example/analysis.json schemas/analysis-result.schema.json
# With ffprobe installed and authorised local media:
python -m video_intelligence.cli inspect-media --input <video.mp4> --output build/media-report.json --confirm-authorized
python -m video_intelligence.cli doctor
python -m video_intelligence.cli start --no-open
python -m video_intelligence.cli status
python -m video_intelligence.cli stop
python -m video_intelligence.cli update
python scripts/smoke_command_center.py --media build/synthetic-smoke.mp4
cd extension
npm install
npm test
npm run lint
npm run build
```

`npm audit` is run manually when refreshing the extension lockfile. It queries the npm registry and is therefore intentionally excluded from the deterministic, network-disabled test launcher.

Media-probe and audio-extraction tests inject deterministic command runners and never execute external binaries. Faster-Whisper tests inject a local model-shaped fake and validate timestamps, language, confidence, and provenance without loading a model. A real `inspect-media` smoke test is environment-dependent and must be reported as blocked when `ffprobe` is absent. Real local ASR validation must be reported as unavailable when the optional package and local model are not configured. Real browser playback, recording, signal-level video/audio validation, OCR, visual analysis, and cloud provider APIs remain outside the implemented scope.

Command-center unit tests do not open sockets. Job tests inject deterministic processors and cover durable reload, interrupted-job recovery, safe unexpected failure, cancellation/retry, active-capacity enforcement, duplicate media, provenance-preserving edits, and explicit source deletion. Backup tests cover database/media restoration, path relocation, and traversal rejection. The cancellable subprocess test launches only the local Python interpreter and verifies prompt termination; it performs no network access. Manual lifecycle verification binds only to loopback, uses a random port, checks unauthorized and hostile-origin rejection, imports synthetic authorized media, polls the result, verifies retention followed by explicit deletion, and stops the service cleanly. Update tests use a deterministic Git runner; automated tests never fetch a remote.

The MV3 scaffold was checked against the official Chrome documentation for the
[Side Panel API](https://developer.chrome.com/docs/extensions/reference/api/sidePanel),
[`activeTab`](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab), and
[static content scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts)
on 2026-07-20. The declared content-script matches are restricted to the three supported platforms.
