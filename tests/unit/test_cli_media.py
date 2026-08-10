from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from video_intelligence import cli
from video_intelligence.media.models import MediaProbeResult, MediaStream


def test_inspect_media_cli_writes_versioned_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    media = tmp_path / "input.mp4"
    media.write_bytes(b"placeholder")
    output = tmp_path / "report.json"
    report = MediaProbeResult(
        path=str(media),
        file_size_bytes=media.stat().st_size,
        format_names=["mp4"],
        duration_ms=1000,
        streams=[
            MediaStream(
                index=0,
                stream_type="video",
                codec_name="h264",
                width=640,
                height=360,
                frame_rate=30,
            )
        ],
    )
    monkeypatch.setattr(cli, "probe_media", lambda *_args, **_kwargs: report)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "video-intelligence",
            "inspect-media",
            "--input",
            str(media),
            "--output",
            str(output),
            "--confirm-authorized",
        ],
    )

    assert cli.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0.0"
    assert payload["valid"] is True
    schema_path = Path(__file__).parents[2] / "schemas" / "media-probe-result.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_inspect_media_cli_requires_authorization_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "video-intelligence",
            "inspect-media",
            "--input",
            str(tmp_path / "input.mp4"),
            "--output",
            str(tmp_path / "report.json"),
        ],
    )
    assert cli.main() == 2


def test_inspect_media_cli_does_not_overwrite_without_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "report.json"
    output.write_text("preserve me", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "video-intelligence",
            "inspect-media",
            "--input",
            str(tmp_path / "input.mp4"),
            "--output",
            str(output),
            "--confirm-authorized",
        ],
    )
    assert cli.main() == 2
    assert output.read_text(encoding="utf-8") == "preserve me"
