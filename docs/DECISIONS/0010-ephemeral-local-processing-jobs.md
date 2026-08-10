# ADR 0010: Ephemeral local processing jobs

## Context

The command center needs to accept user-selected media and expose useful progress and results before real transcription, OCR, and visual providers exist. Retaining uploads or adding a database would create unnecessary privacy and lifecycle risk.

## Decision

Accept raw authenticated uploads only over the loopback command-center API. Require an exact content length, an explicit authorization-confirmation header, a supported media extension, and a configurable upload-size limit. Stream bytes into a randomly named, user-scoped temporary job directory without trusting the supplied filename as a path.

Keep job metadata and completed media-probe reports in memory. Accept at most two active jobs, process one job at a time, and terminate an active `ffprobe` subprocess when cancellation is requested. Delete the uploaded file and job directory on success, failure, cancellation, removal, and service shutdown. Retain only non-sensitive in-memory results until the command center stops.

## Consequences

There is no resume across service restarts and no durable history. Cancellation is checked at short intervals while `ffprobe` runs; future multi-process providers will need equivalent cancellation contracts. The two-active-job limit bounds temporary disk exposure to twice the configured per-upload limit. This design provides a secure first workflow without committing to database or retention architecture.
