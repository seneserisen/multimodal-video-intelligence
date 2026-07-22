# Local command center

The command center is a small authenticated service for operating a source checkout. It is not a public website or processing API. It binds only to `127.0.0.1`, chooses a random port unless one is requested, and stores per-run state in the current user's temporary directory.

```powershell
python -m video_intelligence.cli doctor
python -m video_intelligence.cli start
python -m video_intelligence.cli status --json
python -m video_intelligence.cli stop
```

`start` opens the dashboard unless `--no-open` is supplied. Starting twice reuses the healthy process. `stop` sends an authenticated loopback request and never kills an arbitrary PID. Runtime logs and the token-bearing state file remain outside the repository.

## Source updates

```powershell
python -m video_intelligence.cli update
python -m video_intelligence.cli update --apply
```

The first command fetches and reports ahead/behind counts without changing source files. `--apply` requires the command center to be stopped and the worktree to be clean. It refuses divergent histories and performs only `git merge --ff-only` against the configured upstream. It does not update global tools, install dependencies, merge pull requests, or run in the background.

## Dashboard security

The static dashboard shell is public only to the local machine and contains no credentials. The start command places the random token in the URL fragment; browser JavaScript moves it to session storage, removes the fragment from history, and uses an Authorization header for status and stop calls. API responses disable caching and set restrictive content-security, framing, MIME-sniffing, and referrer headers.
