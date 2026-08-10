# ADR 0009: Authenticated loopback command center

## Context

The local-first application needs one place to inspect prerequisites, start and stop its local process, view health, and explicitly update a source checkout. Adding a general web framework or unauthenticated local endpoint would expand the dependency and attack surface.

## Decision

Implement the command center with Python's standard-library HTTP server, bound only to `127.0.0.1` on a random port by default. Generate a cryptographically random token for every run, store it in a user-only temporary state file, and require it as a bearer token for every API endpoint. Serve the static dashboard shell without credentials; pass the token in the browser URL fragment so it is not included in the initial HTTP request.

Lifecycle commands are `doctor`, `start`, `status`, and `stop`. `update` operates only on a clean source checkout with a configured upstream, fetches explicitly, and applies changes only with `--apply` using a fast-forward-only merge while the service is stopped. There is no background updater, database, telemetry, or externally bound listener.

## Consequences

The service remains small and local, and third-party websites cannot call authenticated operations without the per-run token. The state file and process lifecycle require platform-aware handling. Source update is intentionally not a package manager and cannot resolve divergent branches or local changes.
