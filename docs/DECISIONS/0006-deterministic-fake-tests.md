# ADR 0006: Deterministic fake providers in tests

Automated tests use deterministic fakes so failures remain reproducible, cost-free, offline, and independent of external-provider drift. Network access is disabled during Python tests.
