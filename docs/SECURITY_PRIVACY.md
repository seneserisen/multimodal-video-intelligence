# Security and privacy

## Threat model

Untrusted URLs, filenames, media, provider/model output, transcripts, browser messages, databases, and backup archives may attempt path traversal, command injection, resource exhaustion, secret extraction, XSS, SQL injection, prompt injection, malformed-schema attacks, or unsafe restoration. Private media may be exposed by cloud processing or excessive retention.

## Controls

The command center binds only to `127.0.0.1` and generates a random bearer token per run. The user-only temporary state file is never committed. Direct browser handoff uses a URL fragment that is removed from history; CLI text and JSON expose only a token-free URL. Browser API mutations require the exact loopback origin.

Uploads require authorization confirmation, a supported filename, exact positive content length, size and concurrency limits, and a random server-owned path. Filenames never become paths. SHA-256 identifies duplicates. SQLite statements are parameterized. Transcript edits are length-bounded, keep provenance, and render through `textContent`. Extracted video text is evidence, never an application instruction.

FFmpeg and ffprobe use argument arrays with `shell=False`, time limits, and cooperative process termination. The local Faster-Whisper provider requires an explicit existing model directory; there is no automatic model download, cloud upload, or secret in extension JavaScript. Provider identifiers and local/cloud boundaries remain configuration.

Authorized source media, reports, and transcripts persist in a user-scoped local data directory until explicit deletion. Incomplete uploads are removed during recovery. Backup restore rejects traversal paths, links, excessive file counts/expanded size, unsupported manifests, and corrupt SQLite databases. Restore and backup require the service to be stopped. Source update is explicit, refuses dirty/divergent checkouts, and uses fast-forward-only merges.

## Remaining risks

Browser capture, signal-level media validation, immediate cancellation during a single in-flight model inference step, hostile decoder/model behavior, GPU-memory preflight, and encrypted local transport are not implemented or validated. Retained media increases privacy and disk exposure until explicit deletion. FFmpeg, ffprobe, Faster-Whisper, and model files should be trusted and patched. Users must confirm ownership or authorization before processing.
