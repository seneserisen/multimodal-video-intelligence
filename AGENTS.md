# Repository instructions

## Scope and layout

This repository is the local-first Multimodal Video Intelligence monorepo.

- `backend/src/video_intelligence`: Python domain, provider, fusion, export, and CLI code.
- `extension`: Chrome Manifest V3 TypeScript scaffold. It never receives provider secrets.
- `schemas`: stable JSON interchange contracts.
- `tests`: deterministic unit, integration, contract, fixture, and synthetic-media tests.
- `docs`: product, architecture, privacy, state-machine, evidence, testing, roadmap, and decisions.

Keep acquisition, media validation, modality extraction, fusion, summarization, export, and session cleanup separate. Domain models may be shared inward; provider-specific models must remain behind provider interfaces. Do not add a database or web server without an accepted decision record.

## Commands

From the repository root (PowerShell):

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy backend/src
python -m video_intelligence.cli analyze-evidence --input tests/fixtures/contradiction_case.json --profile balanced --output-dir build/example
python scripts/validate_example.py build/example/analysis.json schemas/analysis-result.schema.json
# Requires local ffprobe and user-authorised media:
python -m video_intelligence.cli inspect-media --input <video.mp4> --output build/media-report.json --confirm-authorized
```

From `extension`:

```powershell
npm install
npm test
npm run lint
npm run build
```

## Security, privacy, and cost

- Local services must bind only to loopback and must be authenticated if added.
- Never log or commit secrets, cookies, authorization headers, private media, or real credentials.
- Secrets come from environment variables or an OS secret store and never enter extension JavaScript.
- Use argument arrays for subprocesses, validate paths and filenames, enforce size/duration limits, and clean temporary session directories on every exit path.
- No telemetry, analytics, cookie export, DRM/access-control circumvention, CAPTCHA bypass, or paid infrastructure.
- Provider interfaces must declare local/cloud processing and keep model identifiers in configuration.
- Tests use deterministic fake providers and must never call live APIs or the network.
- Do not push, publish, deploy, release, open a PR, enable billing, or modify external accounts without explicit user approval.

## Definition of done

A change is done when public interfaces are typed and documented, schema versions are maintained, evidence references validate, security implications are addressed, deterministic tests cover success and failure paths, generated artifacts are isolated, and all relevant commands above have actually run. Report unavailable tools and failed checks exactly; never weaken tests or claim production readiness.
