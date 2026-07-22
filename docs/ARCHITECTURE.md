# Architecture

The architecture is a pipeline with explicit boundaries:

```text
acquisition -> media validation -> modality providers -> evidence validation
            -> temporal fusion -> summarization -> verification -> export
```

Domain models are provider-neutral. Provider protocols return evidence only; fusion does not import provider implementations. Exporters consume a validated `AnalysisResult`. The extension discovers browser state but does not hold secrets or call cloud providers. A future loopback service will authenticate extension requests.

Milestone 1 starts at validated synthetic evidence. Milestone 2A adds a local media-validation boundary backed by a safe `ffprobe` argument-array wrapper. Milestone 2B adds a standard-library command-center service bound to authenticated loopback only. It manages lifecycle and explicit source-update checks but does not add processing endpoints. Acquisition, recording, frame/audio signal analysis, and live AI integrations remain design-only.
