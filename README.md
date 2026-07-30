# Multimodal Video Intelligence

This project explores how speech, visible text, visual events and relevant audio events can be combined into one timestamped evidence record instead of reducing a video to a transcript alone.

The current release is deliberately a foundation. It processes deterministic evidence JSON and includes a non-recording Chrome extension scaffold; it does not yet capture or analyse real media.

## What the foundation does

- validates typed evidence items and stable JSON interchange schemas;
- accepts speech, OCR, visual and audio evidence with integer-millisecond timestamps;
- groups nearby evidence into timeline segments;
- removes duplicated speech/subtitle content;
- identifies simple confirmation and contradiction relationships;
- scores importance while preserving uncertainty and provenance;
- exports schema-valid JSON and readable Markdown;
- uses replaceable provider interfaces with deterministic fake providers;
- includes a Chrome Manifest V3 scaffold that detects supported platforms and visible video metadata;
- keeps acquisition quality separate from analysis quality.

No live AI service or network call is used by the test suite.

## Example

```powershell
python -m pip install -e ".[dev]"
python -m video_intelligence.cli analyze-evidence `
  --input tests/fixtures/contradiction_case.json `
  --profile balanced `
  --output-dir build/example
```

The command writes an evidence-backed analysis JSON file and a Markdown report. The fixtures include speech-only, visual-only, duplicated subtitles, uncertain OCR, contradictions, confirmations, missing timestamps and provider failures.

## Architecture

```text
evidence input
     |
     v
schema and model validation
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
```

Acquisition, media validation, modality extraction, fusion, summarization, export and cleanup are kept as separate responsibilities. See [Architecture](docs/ARCHITECTURE.md) and the recorded [design decisions](docs/DECISIONS/).

## Technology

| Layer | Tools |
| --- | --- |
| Backend | Python 3.12, Pydantic and typed provider interfaces |
| Contracts | JSON Schema |
| Browser scaffold | TypeScript, Chrome Manifest V3 and Vite |
| Tests | pytest with sockets disabled, Vitest and deterministic fixtures |
| Static checks | Ruff, strict mypy and ESLint |

## Verification

Backend checks:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy backend/src
python scripts/validate_example.py build/example/analysis.json schemas/analysis-result.schema.json
```

Extension checks:

```powershell
cd extension
npm install
npm test
npm run lint
npm run build
```

The complete procedure and test boundaries are in [Testing](docs/TESTING.md).

## Privacy and safety boundaries

- No cookie export, access-control bypass, CAPTCHA bypass, telemetry or analytics.
- Provider secrets must never enter extension JavaScript.
- Tests use fake providers and do not access the network.
- Real media, credentials and authorization headers must not be logged or committed.
- Future local services must bind to loopback and require authentication.
- Any captured session data must have size/duration limits and reliable cleanup.

See [Security and privacy](docs/SECURITY_PRIVACY.md).

## Roadmap

### In progress

A draft branch is developing local media validation and a command-center workflow. It is not part of the default branch and is not described here as complete.

### Later milestones

1. Validate authorised local media and report acquisition quality separately.
2. Add controlled tab capture without cookie export or access-control workarounds.
3. Introduce replaceable transcription and OCR providers.
4. Add adaptive frames, scene/slide changes and relevant-audio analysis.
5. Support evidence-linked screenshots, search and question answering.
6. Add resumable long-video processing and confidence-driven reprocessing.
7. Compare local and hybrid provider modes with explicit privacy/cost reporting.

FFmpeg, real browser recording, OCR, speech recognition and visual-analysis providers are future dependencies, not current capabilities. The broader direction is documented in the [product specification](docs/PRODUCT_SPEC.md) and [roadmap](docs/ROADMAP.md).

## Current limits

The project does not currently acquire real media, call live models, transcribe speech, run OCR, analyse arbitrary video frames or support production deployment. Milestone 1 demonstrates data contracts, deterministic fusion behavior, export and a browser integration boundary.
