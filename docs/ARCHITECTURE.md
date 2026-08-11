# Architecture

The architecture is a pipeline with explicit boundaries:

```text
acquisition -> media validation -> modality providers -> evidence validation
            -> temporal fusion -> summarization -> verification -> export
```

Domain models are provider-neutral. Provider protocols return evidence only; fusion does not import provider implementations. Exporters consume a validated `AnalysisResult`. The extension discovers browser state but does not hold secrets or call cloud providers. The extension is not yet connected to the loopback command center.

Milestone 1 starts at validated synthetic evidence. Milestone 2A adds a local media-validation boundary backed by a safe `ffprobe` argument-array wrapper. Milestone 2B adds a standard-library command-center service bound to authenticated loopback only. Milestone 3A adds bounded ephemeral validation jobs. Milestone 4 replaces ephemeral job metadata with a user-scoped SQLite repository, retains authorized source media until explicit deletion, recovers interrupted work, extracts audio through cancellable FFmpeg, and emits timestamped speech evidence through an optional local Faster-Whisper provider. OCR, visual/audio intelligence, search, Q&A, and generalized library behavior remain later boundaries.
