# Multimodal Video Intelligence

A local-first foundation for turning speech, visible text, visual events, and relevant audio events into a timestamped evidence timeline and evidence-backed analysis.

Milestone 1 accepts deterministic evidence JSON rather than acquiring real media. It validates evidence, groups it temporally, removes duplicated speech/subtitles, identifies simple confirmations and contradictions, scores importance, and exports schema-valid JSON plus Markdown. It also includes a non-recording Chrome MV3 scaffold that detects supported platforms and visible video metadata.

## Quick start

Requires Python 3.12+ and Node.js 20+. FFmpeg is a future acquisition dependency and is not required for this milestone.

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m video_intelligence.cli analyze-evidence --input tests/fixtures/contradiction_case.json --profile balanced --output-dir build/example
cd extension
npm install
npm test
npm run build
```

No live AI service is called. See [docs/TESTING.md](docs/TESTING.md) and [docs/SECURITY_PRIVACY.md](docs/SECURITY_PRIVACY.md).
