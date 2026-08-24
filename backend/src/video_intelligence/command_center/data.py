from __future__ import annotations

import os
import sys
from contextlib import suppress
from pathlib import Path


def default_data_dir() -> Path:
    override = os.environ.get("VIDEO_INTELLIGENCE_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve(strict=False)
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "MultimodalVideoIntelligence"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "MultimodalVideoIntelligence"
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "multimodal-video-intelligence"


def prepare_data_dir(data_dir: Path | None = None) -> Path:
    directory = (data_dir or default_data_dir()).resolve(strict=False)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with suppress(OSError):
        directory.chmod(0o700)
    (directory / "media").mkdir(mode=0o700, exist_ok=True)
    (directory / "work").mkdir(mode=0o700, exist_ok=True)
    return directory
