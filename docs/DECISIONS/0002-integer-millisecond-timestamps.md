# ADR 0002: Integer millisecond timestamps

All reliable timing uses integer milliseconds from media start. Milliseconds are precise enough for navigation, language-neutral, JSON-safe, and avoid floating-point drift. Missing timing remains null and is never fabricated.
