# Multimodal Video Intelligence

A local-first foundation for turning speech, visible text, visual events, and relevant audio events into a timestamped evidence timeline and evidence-backed analysis.

Milestone 1 accepts deterministic evidence JSON rather than acquiring real media. It validates evidence, groups it temporally, removes duplicated speech/subtitles, identifies simple confirmations and contradictions, scores importance, and exports schema-valid JSON plus Markdown. It also includes a non-recording Chrome MV3 scaffold that detects supported platforms and visible video metadata.

Milestone 2A adds safe local media inspection through `ffprobe`: path, extension, size, duration, stream, dimension, frame-rate, and codec validation with versioned structured diagnostics. It does not yet decode frames, detect silence/black/frozen video, capture browser media, or invoke AI providers.

## Quick start

Requires Python 3.12+ and Node.js 20+. FFmpeg/ffprobe is optional for the deterministic evidence pipeline and required only for real local media inspection.

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m video_intelligence.cli analyze-evidence --input tests/fixtures/contradiction_case.json --profile balanced --output-dir build/example
cd extension
npm install
npm test
npm run build
```

With a local `ffprobe` installation and media you are authorised to process:

```powershell
python -m video_intelligence.cli inspect-media --input video.mp4 --output build/media-report.json --confirm-authorized
```

No live AI service is called. See [docs/TESTING.md](docs/TESTING.md) and [docs/SECURITY_PRIVACY.md](docs/SECURITY_PRIVACY.md).
