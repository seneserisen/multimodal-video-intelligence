# Security and privacy

## Threat model

Untrusted URLs, filenames, media, provider output, and browser messages may attempt path traversal, command injection, oversized input, secret extraction, or malformed-schema attacks. Private media may be exposed by cloud processing or retained temporary files.

## Controls

Use typed validation, resolved paths constrained to intended roots, subprocess argument arrays with `shell=False`, loopback-only authenticated services, environment/OS secret storage, explicit size and duration limits, and per-session temporary directories cleaned on success and failure. Local media inspection requires explicit authorization confirmation. The extension requests only `activeTab` and `sidePanel`; it does not read cookies or transmit media. Cloud processing must be labelled and requires an explicit privacy warning.

The command center binds only to `127.0.0.1` and generates a cryptographically random bearer token for each run. Its user-scoped temporary state file contains the token and is never committed. The dashboard receives the token through a URL fragment during the direct browser handoff, which is removed from browser history and sent only in authenticated API headers. CLI text and JSON output show only the token-free dashboard URL. Browser API requests must have the exact loopback origin. Uploads additionally require an authorization confirmation, a supported filename, an exact positive content length, and a configured size limit. The service accepts no more than two active jobs, processes one at a time, and terminates an active `ffprobe` process on cancellation. A bounded worker writes to random user-scoped temporary directories and removes media after success, failure, cancellation, removal, and shutdown. Job reports exist in memory only. Stop never force-kills a PID. Source updates require an explicit command, refuse dirty or divergent checkouts, and use fast-forward-only merges.

## Remaining risks

Browser capture, signal-level media validation, cleanup after forced process termination or power loss, hostile decoder behavior, provider retention, and encrypted local transport are not implemented or validated. `ffprobe` remains an external parser and should be kept patched. Users must confirm ownership or authorisation before media processing.
