# Roadmap

## Milestone 1 — foundation

Validated evidence models, fake providers, deterministic fusion, CLI/export, schemas, synthetic tests, and a non-recording MV3 scaffold.

## Milestone 2A — local media probing

Safe local `ffprobe` execution, typed stream/container metadata, configurable file and duration limits, codec/stream diagnostics, explicit authorization confirmation, JSON export, and deterministic fake-runner tests. Signal-level silence, black-frame, frozen-playback, and completeness checks remain future work.

## Milestone 2B — local command center

Authenticated loopback dashboard, user-scoped runtime state, prerequisite diagnostics, clean start/status/stop lifecycle, and explicit fast-forward-only source update checks.

## Milestone 3A — ephemeral local jobs

Authenticated, size-bounded dashboard uploads for authorized media; a single local validation worker; in-memory progress and reports; cooperative cancellation; and temporary-media cleanup on every terminal path. Durable history, resume, signal analysis, and multimodal providers remain future work.

## Milestone 3B — developer experience and reproducibility

Idempotent local setup, thin Windows and Unix launchers, a deterministic 60-second demo, actionable workspace diagnostics, isolated artifacts, safe cleanup, developer documentation, and an explicit local-review/commit/push boundary. Fresh Windows setup is exercised locally; Linux/macOS runtime validation remains platform-dependent.

## Milestone 4 — real local transcription and durable jobs

User-scoped SQLite job history, retained authorized source media, restart recovery, content hashing and duplicate detection, explicit deletion, cancellation/retry, backup/restore, cancellable FFmpeg audio extraction, optional local Faster-Whisper transcription, detected language, timestamped speech evidence, confidence where supported, and provenance-preserving transcript edits are implemented and deterministic-tested. Complete local model manifests are required, network fallback is disabled, lazy segment failures/cancellation are handled, and model/device/compute/VAD provenance is retained. Real Faster-Whisper inference, CPU performance, and GPU execution remain unverified because no local model was available for Milestone 4B acceptance; Milestone 4 must not yet be labelled real-transcription validated.

## Future milestones

The roadmap covers authorised YouTube/Instagram/TikTok URL input, the acquisition fallback ladder, tab capture, OCR, adaptive frames and scene/slide changes, visual/action and relevant audio analysis, evidence timelines, contradiction detection, screenshots, multimodal search and QA, confidence-driven reprocessing, stage caching, long-video resume, Markdown/JSON export, local/hybrid modes, secure cleanup, engineering mode, and transparent coverage. Live providers remain optional and replaceable.
