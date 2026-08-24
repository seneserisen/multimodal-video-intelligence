# Troubleshooting

Start with `DOCTOR.bat` on Windows or `sh doctor.sh` on Linux/macOS.

## Python was not found

Install Python 3.12 or newer. On Windows, enable **Add Python to PATH**, open a new terminal, and run `SETUP.bat` again. Setup never installs Python or requests administrator access.

## `.venv` or the package is missing

Run `SETUP.bat` or `sh setup.sh`. The command reuses an existing environment and repairs the editable installation.

## Extension tests cannot run

Install Node.js 20 or newer, then run:

```powershell
.\SETUP.bat -RequireExtension
```

The synthetic evidence demo does not require Node.js.

## FFmpeg or ffprobe is unavailable

The basic demo still works. Real-media inspection and dashboard upload validation require a local FFmpeg installation. Restart the terminal or Codex after installation so the updated `PATH` is visible.

## The demo result looks unchanged

That is expected: the bundled demo is deterministic. It intentionally overwrites `artifacts/demo` with the same evidence-backed contradiction result so visitors can reproduce it.

## Transcription is unavailable

Validation-only jobs still work. Run `SETUP.bat -Transcription`, set `VIDEO_INTELLIGENCE_WHISPER_MODEL` to an existing compatible local model directory, then restart the command center. `DOCTOR.bat` reports whether the package and model are ready. The application never downloads a model automatically.

## Local jobs use too much disk space

Imported source media is retained for durable history, retry, and recovery. Use **Delete job + media** in the dashboard to remove an individual source. Run `BACKUP.bat` before deleting anything you may need later. `OPEN_RESULTS.bat` opens the exact local data folder.

## Restore is refused

Stop the command center first and pass both the archive and explicit confirmation: `RESTORE.bat -BackupPath "C:\path\backup.zip" -Confirm`. Unsafe, oversized, unsupported, or corrupt archives are rejected without replacing current data.

## The command center is already running

Open the existing dashboard or run `video-intelligence status`. Stop it through the dashboard or with `video-intelligence stop`; the project never kills an arbitrary process.

## GitHub does not show local edits

Saving files changes only the local clone. Review the changes in GitHub Desktop or Git, commit the intended files, and explicitly push. The project does not auto-commit or auto-push.
