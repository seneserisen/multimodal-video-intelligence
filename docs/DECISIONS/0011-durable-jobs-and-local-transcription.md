# ADR 0011: Durable jobs and explicit local transcription

## Context

The next product milestone requires real speech transcription and job history that survives a command-center restart. ADR 0010 intentionally kept validation jobs and uploaded media ephemeral, which cannot support restart recovery, transcript editing, or durable provenance.

## Decision

Store job records in a user-scoped SQLite database and retain each authorized source file in a user-scoped data directory until the user deletes its job. SQLite access stays behind a small repository with parameterized statements, a schema-version table, WAL journaling, and indexes derived from job-list and duplicate-hash queries. The repository never stores bearer tokens or provider credentials.

Interrupted queued or running jobs are recovered as queued when their retained source exists. Incomplete uploads are failed safely and their partial bytes are removed. Deleting a job removes its retained media and transcript. Backups are explicit, run only while the service is stopped, and contain the database plus retained authorized media.

Real transcription uses a provider-neutral protocol. The first implementation extracts mono 16 kHz PCM audio with a cancellable `ffmpeg` argument array and invokes an optional local Faster-Whisper installation with an explicit, complete local CTranslate2 model path. MVI rejects model names and incomplete manifests, requires a local tokenizer, and initializes Faster-Whisper with `local_files_only=True`; automatic model/tokenizer downloads, cloud transcription, and provider secrets are not enabled. Transcript segments become speech evidence with monotonic timestamps, detected language, confidence when supported, provider/method/model and device/compute/VAD metadata, processing version, and source provenance. User edits retain original text, extraction provenance, timestamps, edit count, and last-edit time.

## Consequences

Authorized media is no longer deleted automatically after successful processing; users must delete the job or clear/restore local data deliberately. Disk use and privacy exposure therefore increase and must be visible in the UI and operator documentation. SQLite is local application state, not a public service or multi-user database. OCR, visual/audio intelligence, search, Q&A, and generalized video-library behavior remain later milestones.
