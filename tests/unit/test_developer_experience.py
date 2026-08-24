from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_portfolio_entry_points_are_present_and_documented() -> None:
    expected = {
        "START_HERE.md",
        "SETUP.bat",
        "RUN.bat",
        "COMMAND_CENTER.bat",
        "TEST.bat",
        "DOCTOR.bat",
        "CLEAN.bat",
        "setup.sh",
        "run.sh",
        "command-center.sh",
        "test.sh",
        "doctor.sh",
        "clean.sh",
    }
    assert expected <= {path.name for path in ROOT.iterdir()}
    guide = text("START_HERE.md")
    assert "artifacts/demo" in guide
    assert "DOCTOR.bat" in guide
    assert "no private video" in guide


def test_low_tech_operator_controls_are_present() -> None:
    expected = {
        "SETUP.bat",
        "START.bat",
        "STOP.bat",
        "RESTART.bat",
        "STATUS.bat",
        "DOCTOR.bat",
        "TEST.bat",
        "OPEN_APP.bat",
        "OPEN_FOLDER.bat",
        "OPEN_RESULTS.bat",
        "OPEN_LOGS.bat",
        "BACKUP.bat",
        "RESTORE.bat",
        "UPDATE.bat",
    }
    assert expected <= {path.name for path in ROOT.iterdir()}
    for launcher in expected - {"SETUP.bat", "DOCTOR.bat", "TEST.bat"}:
        assert "scripts\\control.ps1" in text(launcher)


def test_root_launchers_are_thin_wrappers() -> None:
    mapping = {
        "SETUP.bat": "scripts\\setup.ps1",
        "RUN.bat": "scripts\\run.ps1",
        "COMMAND_CENTER.bat": "scripts\\command-center.ps1",
        "TEST.bat": "scripts\\test.ps1",
        "DOCTOR.bat": "scripts\\doctor.ps1",
        "CLEAN.bat": "scripts\\clean.ps1",
        "setup.sh": "scripts/setup.sh",
        "run.sh": "scripts/run.sh",
        "command-center.sh": "scripts/command-center.sh",
        "test.sh": "scripts/test.sh",
        "doctor.sh": "scripts/doctor.sh",
        "clean.sh": "scripts/clean.sh",
    }
    for launcher, target in mapping.items():
        content = text(launcher)
        assert target in content
        assert len(content.splitlines()) <= 7


def test_launchers_do_not_publish_or_stage_changes() -> None:
    mutating_git = re.compile(r"\bgit\s+(?:add|commit|push|pull|merge|reset)\b", re.IGNORECASE)
    for name in (
        "setup.ps1",
        "run.ps1",
        "command-center.ps1",
        "test.ps1",
        "clean.ps1",
        "setup.sh",
        "run.sh",
        "command-center.sh",
        "test.sh",
        "clean.sh",
    ):
        assert mutating_git.search(text(f"scripts/{name}")) is None


def test_demo_uses_existing_cli_and_ignored_artifact_directory() -> None:
    powershell = text("scripts/run.ps1")
    shell = text("scripts/run.sh")
    for content in (powershell, shell):
        assert "video_intelligence.cli analyze-evidence" in content
        assert "contradiction_case.json" in content
        assert "validate_example.py" in content
    assert "artifacts/" in text(".gitignore").splitlines()


def test_command_center_launcher_exposes_explicit_safe_actions() -> None:
    powershell = text("scripts/command-center.ps1")
    shell = text("scripts/command-center.sh")
    for content in (powershell, shell):
        assert "video_intelligence.cli" in content
        for action in ("start", "status", "stop", "update"):
            assert action in content
    assert 'if ($Action -eq "update" -and $Apply)' in powershell
    assert "--apply" in powershell


def test_cleanup_targets_only_generated_repository_paths() -> None:
    powershell = text("scripts/clean.ps1")
    shell = text("scripts/clean.sh")
    for content in (powershell, shell):
        assert "artifacts" in content
        assert "extension" in content and "dist" in content
        assert re.search(r"(?:Remove-Item|rm\s+-rf)[^\n]*\.venv", content) is None
        assert re.search(r"(?:Remove-Item|rm\s+-rf)[^\n]*node_modules", content) is None


def test_ci_is_read_only_and_pins_official_actions() -> None:
    workflow = text(".github/workflows/portfolio-verification.yml")
    assert "contents: read" in workflow
    assert "pull_request:" in workflow
    assert "windows-latest" in workflow and "ubuntu-latest" in workflow
    uses = re.findall(r"uses:\s+(actions/[^@\s]+)@([^\s]+)", workflow)
    assert {name for name, _ref in uses} == {
        "actions/checkout",
        "actions/setup-node",
        "actions/setup-python",
    }
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for _name, ref in uses)
