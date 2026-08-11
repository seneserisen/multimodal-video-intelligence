from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from video_intelligence import cli
from video_intelligence.command_center import doctor
from video_intelligence.command_center.controller import command_center_status
from video_intelligence.command_center.dashboard import DASHBOARD_HTML, DASHBOARD_JS
from video_intelligence.command_center.models import (
    CommandCenterStatus,
    DoctorCheck,
    DoctorReport,
    RuntimeState,
    StartResult,
    UpdateReport,
)
from video_intelligence.command_center.state import read_state, remove_state, write_state


def test_runtime_state_round_trip_and_removal(tmp_path: Path) -> None:
    state = RuntimeState(
        pid=123,
        port=4567,
        token="x" * 32,
        started_at=datetime.now(UTC),
        version="0.3.0",
    )
    target = write_state(state, tmp_path)

    assert target.parent == tmp_path
    assert read_state(tmp_path) == state
    assert remove_state(tmp_path, expected_pid=999) is False
    assert target.exists()
    assert remove_state(tmp_path, expected_pid=123) is True
    assert not target.exists()


def test_status_is_stopped_without_runtime_state(tmp_path: Path) -> None:
    status = command_center_status(tmp_path)
    assert status.running is False
    assert "stopped" in status.message.casefold()


def test_dashboard_uses_fragment_token_and_authenticated_api() -> None:
    assert "#token=" in DASHBOARD_JS
    assert "Authorization" in DASHBOARD_JS
    assert "127.0.0.1" in DASHBOARD_HTML
    assert "NO CLOUD CALLS" in DASHBOARD_HTML


def test_doctor_reports_missing_optional_media_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda _binary: None)
    report = doctor.run_doctor(tmp_path)
    assert report.ready is True
    statuses = {check.name: check.status for check in report.checks}
    assert statuses["python"] == "ok"
    assert statuses["ffmpeg"] == "warning"
    assert statuses["ffprobe"] == "warning"
    assert statuses["data_storage"] in {"ok", "warning"}
    assert statuses["transcription"] == "warning"


def test_cli_lifecycle_dispatches_without_real_processes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    running = CommandCenterStatus(
        running=True,
        pid=123,
        port=4567,
        started_at=datetime.now(UTC),
        version="0.3.0",
        message="healthy",
    )
    start = StartResult(status=running, dashboard_url="http://127.0.0.1:4567/#token=hidden")
    monkeypatch.setattr(cli, "command_center_start", lambda **_kwargs: start)
    monkeypatch.setattr(sys, "argv", ["video-intelligence", "start", "--no-open", "--json"])
    assert cli.main() == 0
    json_output = capsys.readouterr().out
    json_result = json.loads(json_output)
    assert json_result["status"]["running"] is True
    assert json_result["dashboard_url"] == "http://127.0.0.1:4567/"
    assert "hidden" not in json_output

    monkeypatch.setattr(sys, "argv", ["video-intelligence", "start", "--no-open"])
    assert cli.main() == 0
    plain_output = capsys.readouterr().out
    assert "Dashboard: http://127.0.0.1:4567/" in plain_output
    assert "Authentication token hidden" in plain_output
    assert "#token=" not in plain_output

    monkeypatch.setattr(cli, "command_center_status", lambda: running)
    monkeypatch.setattr(sys, "argv", ["video-intelligence", "status"])
    assert cli.main() == 0
    assert "Process 123" in capsys.readouterr().out


def test_cli_doctor_and_update_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    doctor_report = DoctorReport(
        ready=True,
        checks=[DoctorCheck(name="python", status="ok", detail="Python")],
    )
    update_report = UpdateReport(
        repository="repo",
        branch="main",
        upstream="origin/main",
        ahead=0,
        behind=0,
        applied=False,
        message="up to date",
    )
    monkeypatch.setattr(cli, "run_doctor", lambda: doctor_report)
    monkeypatch.setattr(sys, "argv", ["video-intelligence", "doctor", "--json"])
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out)["ready"] is True

    monkeypatch.setattr(cli, "update_source", lambda **_kwargs: update_report)
    monkeypatch.setattr(sys, "argv", ["video-intelligence", "update", "--json"])
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out)["upstream"] == "origin/main"
