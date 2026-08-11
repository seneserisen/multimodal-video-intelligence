# Local command center

The command center is an authenticated local service for durable media-processing jobs. It binds only to `127.0.0.1`, uses a random port by default, keeps its per-run bearer token in a user-only temporary state file, and keeps jobs in a separate user-scoped application-data directory. It is not a public website or remote processing API.

## Low-tech controls

From the repository root:

```powershell
START.bat
STOP.bat
RESTART.bat
STATUS.bat
OPEN_APP.bat
OPEN_RESULTS.bat
OPEN_LOGS.bat
BACKUP.bat
RESTORE.bat -BackupPath "C:\path\mvi-backup-YYYYMMDDTHHMMSSZ.zip" -Confirm
UPDATE.bat
```

`COMMAND_CENTER.bat start|status|stop|update` remains available, as do the underlying `video-intelligence` CLI commands. No launcher stages, commits, pushes, downloads models, or runs an updater in the background.

## Durable jobs

The dashboard accepts authorized `.avi`, `.m4v`, `.mkv`, `.mov`, `.mp4`, and `.webm` files. The default upload limit is 512 MiB and can be lowered with `start --max-upload-mb SIZE`. At most two jobs may be active and one local job runs at a time.

Authorized source bytes are retained under a random per-job directory in the local data folder. Job state, content hashes, validation reports, and transcripts are stored in SQLite. Duplicate imports are rejected. Terminal jobs can be retried, and interrupted queued/running jobs with retained media are recovered after restart. Incomplete uploads are failed and removed during recovery.

Cancellation stops cancellable FFmpeg/ffprobe work and is checked between transcription segments. Cancelling or stopping does not silently delete retained source media. **Delete job + media** explicitly removes the record, transcript, report, and source.

## Optional real local transcription

Install the optional provider only when needed:

```powershell
SETUP.bat -Transcription
$env:VIDEO_INTELLIGENCE_WHISPER_MODEL = "C:\models\faster-whisper-small"
OPEN_APP.bat
```

The value must be an existing local Faster-Whisper model directory. `VIDEO_INTELLIGENCE_WHISPER_DEVICE` may be `cpu`, `cuda`, or `auto`; `VIDEO_INTELLIGENCE_WHISPER_COMPUTE_TYPE` defaults to `int8`. The application never downloads a model automatically.

A transcription job validates media, extracts mono 16 kHz PCM with cancellable FFmpeg, invokes the explicitly configured local model, and stores timestamped speech evidence with detected language, confidence where supported, provider/method, processing version, and source provenance. User edits change segment text only and retain the original extracted text in provenance attributes.

## Backups

Stop the service before backup or restore. Backups are written beside the application-data folder, not into the Git repository. Restore validates archive paths, link types, file count, expanded size, manifest version, and SQLite integrity before replacing current data.

## Source updates

`UPDATE.bat` fetches and reports ahead/behind counts without changing source files. `UPDATE.bat -Apply` requires a stopped service and clean worktree, refuses divergence, and performs only `git merge --ff-only` against the configured upstream.

## Dashboard security

The static dashboard shell contains no credentials. Start places the random token in the URL fragment for direct browser handoff; JavaScript moves it to session storage, removes the fragment from history, and uses an Authorization header for API calls. Browser mutations require the exact loopback origin. Uploads require a separate authorization-confirmation header. Responses disable caching and set restrictive content-security, framing, MIME-sniffing, and referrer headers. Extracted and user-edited text is rendered with `textContent`, not HTML.
