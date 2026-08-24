# Start here

This project turns timestamped speech, visible text, and visual evidence into a short report that keeps links back to the supporting evidence. The included demonstration is synthetic and deterministic: it uses no private video, internet service, paid API, or AI-provider account.

## Run this project on Windows

1. Install [Python 3.12 or newer](https://www.python.org/downloads/). During installation, enable **Add Python to PATH**.
2. Double-click `SETUP.bat` once.
3. Double-click `RUN.bat`.
4. The result folder opens automatically.

Setup reuses the same `.venv` every time, so running it again is safe. If Node.js 20+ is already installed, setup also prepares the optional Chrome-extension development tools. It does not install system software for you.

## What you should see

Within roughly 30–60 seconds, the demo creates:

```text
artifacts/demo/
├── README.txt
├── analysis.json
└── summary.md
```

Open `summary.md`. It should explain a contradiction between synthetic speech and on-screen evidence. `analysis.json` contains the complete versioned result for developers and integrations.

## Something went wrong?

Double-click `DOCTOR.bat`. It checks Python, the local environment, package installation, writable output, Git, the optional extension tools, FFmpeg, and the local command center. Errors explain the next action without installing or changing anything.

Common actions:

| Action | Windows | Linux/macOS |
| --- | --- | --- |
| First setup | `SETUP.bat` | `sh setup.sh` |
| Run demo | `RUN.bat` | `sh run.sh` |
| Start local service | `START.bat` | `sh command-center.sh start` |
| Open local app | `OPEN_APP.bat` | `sh command-center.sh start` |
| Stop / status | `STOP.bat` / `STATUS.bat` | `sh command-center.sh stop` / `status` |
| Back up local data | `BACKUP.bat` | Advanced CLI only |
| Diagnose | `DOCTOR.bat` | `sh doctor.sh` |
| Full tests | `TEST.bat` | `sh test.sh` |
| Clean outputs | `CLEAN.bat` | `sh clean.sh` |

`CLEAN` removes generated reports, builds, and caches. It preserves `.venv` and `extension/node_modules`, so another setup is normally unnecessary.

## Optional real-media dashboard

The one-click demo does not require FFmpeg. To inspect video files that you own or are authorized to process, install FFmpeg/ffprobe and use the authenticated local command center:

```powershell
COMMAND_CENTER.bat
```

The service binds only to `127.0.0.1` and does not call cloud providers. Imported media, job history, validation reports, and transcripts are stored in a user-scoped local data folder until you explicitly delete a job. Stop it from the dashboard or run:

```powershell
COMMAND_CENTER.bat stop
```

`COMMAND_CENTER.bat status` checks the app without opening it. `COMMAND_CENTER.bat update` checks for source updates but does not modify the checkout; applying an available fast-forward update requires the app to be stopped and the explicit `COMMAND_CENTER.bat update -Apply` command.

Validation works with FFmpeg alone. Real transcription is optional and remains local: run `SETUP.bat -Transcription`, place a compatible Faster-Whisper CTranslate2 model containing `model.bin`, `config.json`, and `tokenizer.json` in a local folder, and set `VIDEO_INTELLIGENCE_WHISPER_MODEL` to that folder before starting the app. A model name such as `tiny` is not accepted, and the project never downloads model or tokenizer assets automatically. `DOCTOR.bat` reports package, model manifest, device, and compute readiness separately; it does not run or claim real inference.

## Advanced and developer usage

Developers should read [README.md](README.md), [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), and [docs/TESTING.md](docs/TESTING.md). The launchers are convenience wrappers; the existing CLI, schemas, Python API, and extension toolchain remain directly available.
