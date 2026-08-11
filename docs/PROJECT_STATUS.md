# Project status

## Implemented

- Deterministic, schema-validated evidence fusion and Markdown/JSON export.
- Safe local media metadata validation through ffprobe.
- Authenticated loopback command center with durable local processing jobs.
- Durable SQLite jobs, retained authorized media, restart recovery, duplicate detection, retry, and explicit deletion.
- Optional local Faster-Whisper provider with FFmpeg audio extraction, timestamped speech evidence, detected language, strict no-download model validation, lazy-generator safety, model/device/compute/VAD provenance, and edit metadata. This path is automated-tested; real inference is not yet locally validated.
- Chrome Manifest V3 platform-detection scaffold without provider secrets.
- Windows one-click setup, demo, doctor, tests, and generated-output cleanup.
- Linux/macOS shell equivalents with the same user-facing vocabulary.

## Demonstration boundary

`RUN.bat` and `sh run.sh` analyze checked-in synthetic evidence and write `artifacts/demo`. This proves the evidence, fusion, export, and schema contracts without private media, network calls, or nondeterministic providers.

## Not implemented

- Browser media acquisition or recording.
- OCR, adaptive frame extraction, visual-action analysis, or audio-event analysis.
- Live AI-provider integrations.
- Full resumable stage caching after restart; interrupted jobs currently restart their requested pipeline safely.
- Production deployment, public hosting, telemetry, or automated GitHub publishing.
- Real Faster-Whisper acceptance, CPU/GPU performance measurements, and real-provider persistence/backup evidence; no compatible local model was available during Milestone 4B.

The repository is an engineering foundation and reproducible portfolio demonstration, not a production-ready video-analysis product.
