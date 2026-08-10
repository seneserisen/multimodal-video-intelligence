# Multimodal Video Intelligence

This local-first project combines speech, visible text, visual events, and relevant audio evidence into one timestamped record instead of reducing a video to a transcript alone.

## 60-second demonstration

For a non-technical Windows walkthrough, read [START_HERE.md](START_HERE.md), double-click `SETUP.bat` once, then double-click `RUN.bat`. The deterministic report appears in `artifacts/demo/` and uses no network, private media, paid API, or live AI provider.

Linux/macOS users can run `./setup.sh` followed by `./run.sh`.

## What is implemented

- typed evidence items and stable JSON interchange schemas;
- speech, OCR, visual, and audio evidence with integer-millisecond timestamps;
- temporal grouping, speech/subtitle deduplication, importance scoring, uncertainty, and provenance;
- simple multimodal confirmation and contradiction relationships;
- evidence-backed JSON and Markdown export;
- safe local `ffprobe` metadata validation for authorized media;
- an authenticated `127.0.0.1` command center with temporary validation jobs;
- bounded uploads, true active-job cancellation, in-memory results, and media cleanup;
- replaceable provider interfaces with deterministic fake providers;
- a non-recording Chrome Manifest V3 platform and metadata scaffold;
- one-command setup, demo, diagnostics, tests, and generated-output cleanup.

No live AI service or network call is used by the test suite.

## Deterministic CLI example

```powershell
python -m pip install -e ".[dev]"
python -m video_intelligence.cli analyze-evidence `
  --input tests/fixtures/contradiction_case.json `
  --profile balanced `
  --output-dir build/example
```

The command writes an evidence-backed analysis JSON file and a Markdown report. Fixtures cover speech-only, visual-only, duplicated subtitles, uncertain OCR, contradictions, confirmations, missing timestamps, and provider failures.

## Architecture

```text
authorized input
      |
      v
media and evidence validation
      |
      v
provider boundary
      |
      v
temporal grouping and multimodal fusion
      |
      v
importance, agreement and contradiction analysis
      |
      v
JSON + Markdown export

Chrome MV3 scaffold: platform detection and metadata only
Command center: authenticated loopback and ephemeral jobs only
```

Acquisition, media validation, modality extraction, fusion, summarization, export, and cleanup remain separate responsibilities. See [Architecture](docs/ARCHITECTURE.md) and the recorded [design decisions](docs/DECISIONS/).

## Technology

| Layer | Tools |
| --- | --- |
| Backend | Python 3.12+, Pydantic, typed provider interfaces |
| Media metadata | Local FFmpeg/ffprobe |
| Contracts | JSON Schema |
| Local operations | Authenticated standard-library loopback service |
| Browser scaffold | TypeScript, Chrome Manifest V3, Vite |
| Tests | pytest with sockets disabled, Vitest, deterministic fixtures |
| Static checks | Ruff, strict mypy, ESLint |

## Verification

Run the complete repository workflow on Windows:

```powershell
.\SETUP.bat -RequireExtension
.\TEST.bat
```

Or run the engineering commands directly:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy backend/src
python scripts/validate_example.py build/example/analysis.json schemas/analysis-result.schema.json
cd extension
npm test
npm run lint
npm run build
```

The read-only GitHub Actions workflow executes the launcher contract on Windows and Ubuntu. The complete procedures and test boundaries are in [Testing](docs/TESTING.md).

## Authorized local media

With local `ffprobe` and media you own or are authorized to process:

```powershell
python -m video_intelligence.cli inspect-media --input video.mp4 --output build/media-report.json --confirm-authorized
```

Start and manage the authenticated local command center:

```powershell
python -m video_intelligence.cli doctor
python -m video_intelligence.cli start
python -m video_intelligence.cli status
python -m video_intelligence.cli stop
python -m video_intelligence.cli update
```

## Privacy and safety boundaries

- No cookie export, access-control bypass, CAPTCHA bypass, telemetry, or analytics.
- Provider secrets never enter extension JavaScript.
- Tests use fake providers and do not access the network.
- Real media, credentials, and authorization headers are never committed or intentionally logged.
- The command center binds only to loopback and requires a random bearer token.
- Uploads have explicit authorization, filename, size, concurrency, and cleanup controls.
- No launcher automatically stages, commits, pushes, deploys, or updates source files.

See [Security and privacy](docs/SECURITY_PRIVACY.md).

## Roadmap and current limits

The project does not yet capture browser media, transcribe speech, run OCR, analyze arbitrary frames or audio events, call live models, retain durable job history, or support production deployment. Planned milestones cover controlled acquisition, replaceable modality providers, adaptive frame selection, signal-quality checks, evidence-linked screenshots, search, question answering, and resumable processing.

See [Project status](docs/PROJECT_STATUS.md), [Roadmap](docs/ROADMAP.md), [Development](docs/DEVELOPMENT.md), and [Troubleshooting](docs/TROUBLESHOOTING.md).
