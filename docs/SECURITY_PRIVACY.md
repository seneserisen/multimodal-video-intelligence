# Security and privacy

## Threat model

Untrusted URLs, filenames, media, provider output, and browser messages may attempt path traversal, command injection, oversized input, secret extraction, or malformed-schema attacks. Private media may be exposed by cloud processing or retained temporary files.

## Controls

Use typed validation, resolved paths constrained to intended roots, subprocess argument arrays, loopback-only authenticated services, environment/OS secret storage, explicit size and duration limits, and per-session temporary directories cleaned on success and failure. The extension requests only `activeTab`, `scripting`, and `sidePanel`; it does not read cookies or transmit media. Cloud processing must be labelled and requires an explicit privacy warning.

## Remaining risks

Browser capture, cleanup under process termination, hostile codecs, provider retention, and secure local transport are not implemented or validated in Milestone 1. Users must confirm ownership or authorisation before future media processing.
