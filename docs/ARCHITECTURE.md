# Architecture

The architecture is a pipeline with explicit boundaries:

```text
acquisition -> media validation -> modality providers -> evidence validation
            -> temporal fusion -> summarization -> verification -> export
```

Domain models are provider-neutral. Provider protocols return evidence only; fusion does not import provider implementations. Exporters consume a validated `AnalysisResult`. The extension discovers browser state but does not hold secrets or call cloud providers. The extension is not yet connected to the loopback command center.

Milestone 1 starts at validated synthetic evidence. Milestone 2A adds a local media-validation boundary backed by a safe `ffprobe` argument-array wrapper. Milestone 2B adds a standard-library command-center service bound to authenticated loopback only. Milestone 3A adds a bounded in-memory job manager and raw upload endpoint around that existing validator. Uploaded media has one owner—the job manager—and is removed before a job settles; only its typed report stays in memory. Acquisition, recording, frame/audio signal analysis, durable job storage, and live AI integrations remain design-only.
