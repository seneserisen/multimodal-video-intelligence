# Development workflow

## Local setup

Windows:

```powershell
.\SETUP.bat -RequireExtension
.\TEST.bat
```

Linux/macOS:

```sh
sh setup.sh --require-extension
sh test.sh
```

The setup is idempotent. It creates or reuses `.venv`, installs the Python project in editable mode with development tools, and uses the checked-in npm lockfile for the extension. It does not install Python, Node.js, FFmpeg, Git, browsers, or other system software.

`SETUP.bat -Transcription` (or `sh setup.sh --transcription`) explicitly adds the optional Faster-Whisper runtime. Model files are not dependencies and are never downloaded by setup; point `VIDEO_INTELLIGENCE_WHISPER_MODEL` at a separately obtained, trusted local model directory.

## Direct engineering commands

The wrappers do not replace the underlying interfaces. From the repository root on Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy backend/src
.\.venv\Scripts\python.exe -m video_intelligence.cli analyze-evidence --input tests/fixtures/contradiction_case.json --profile balanced --output-dir artifacts/demo
cd extension
npm test
npm run lint
npm run build
```

See [TESTING.md](TESTING.md) for the complete verification contract and [COMMAND_CENTER.md](COMMAND_CENTER.md) for local service operation.

## Local and GitHub synchronization

Local file edits appear immediately in Git tools such as GitHub Desktop. GitHub.com changes only after deliberate review, commit, and push:

```text
edit → test → inspect diff → commit → push
```

No project launcher stages, commits, pushes, pulls, or continuously synchronizes files. `video-intelligence update` is also explicit: without `--apply` it only reports source-update status; applying requires a clean checkout and a fast-forward-only update.

The GitHub Actions workflow runs the same launcher contract on Windows and Ubuntu for pull requests and `main`. It has read-only repository permissions and pins official GitHub actions to immutable commit hashes; it cannot commit or push changes.

Use this repository as an independent Git clone with its own `origin`. Do not place a second Git repository around it.

## Generated files

Demo results belong in `artifacts/`; engineering examples may use `build/`. Both are ignored by Git. `CLEAN.bat` or `sh clean.sh` removes generated reports, builds, and caches while preserving installed local environments.
