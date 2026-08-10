# Local media validation

Milestone 2A validates user-authorised local files before evidence extraction. The CLI resolves the selected path, optionally constrains it to an allowed root, permits a small media-extension allowlist, applies configurable byte and duration limits, and invokes `ffprobe` with an argument array and `shell=False`.

The versioned report records container names, duration when reliable, video/audio/other streams, codecs, dimensions, frame rate, sample rate, channels, warnings, and structured errors. Missing duration stays null. Missing audio is a warning unless the caller requires it; missing video and unsupported codecs are errors.

This stage reads metadata only. It does not yet prove that frames are visually meaningful, audio is audible, playback is unfrozen, or recording is complete. Those checks require bounded decoding and signal analysis in a later milestone.

```powershell
python -m video_intelligence.cli inspect-media `
  --input video.mp4 `
  --output build/media-report.json `
  --confirm-authorized
```
