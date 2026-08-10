from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from video_intelligence.command_center.controller import command_center_status
from video_intelligence.command_center.models import UpdateReport
from video_intelligence.errors import ErrorCode, StructuredError, VideoIntelligenceError


@dataclass(frozen=True)
class GitResult:
    returncode: int
    stdout: str
    stderr: str


class GitRunner(Protocol):
    def run(self, arguments: Sequence[str], *, cwd: Path) -> GitResult: ...


class SubprocessGitRunner:
    def run(self, arguments: Sequence[str], *, cwd: Path) -> GitResult:
        try:
            completed = subprocess.run(
                list(arguments),
                cwd=cwd,
                check=False,
                capture_output=True,
                shell=False,
                text=True,
                timeout=60,
            )
        except FileNotFoundError:
            return GitResult(127, "", "Git is not installed or available on PATH.")
        except subprocess.TimeoutExpired:
            return GitResult(124, "", "Git did not finish within the configured timeout.")
        return GitResult(completed.returncode, completed.stdout.strip(), completed.stderr.strip())


def _failure(message: str, recovery: str) -> VideoIntelligenceError:
    return VideoIntelligenceError(
        StructuredError(
            code=ErrorCode.UPDATE_UNAVAILABLE,
            message=message,
            safe_recovery_action=recovery,
        )
    )


def _git(runner: GitRunner, repository: Path, *arguments: str) -> str:
    result = runner.run(["git", *arguments], cwd=repository)
    if result.returncode != 0:
        raise _failure(
            "The source update command could not inspect the Git repository.",
            "Verify the checkout has an accessible upstream remote.",
        )
    return result.stdout


def update_source(
    *,
    repository: Path,
    apply: bool = False,
    runner: GitRunner | None = None,
    state_dir: Path | None = None,
) -> UpdateReport:
    runner = runner or SubprocessGitRunner()
    root_text = _git(runner, repository, "rev-parse", "--show-toplevel")
    root = Path(root_text).resolve()
    branch = _git(runner, root, "branch", "--show-current")
    upstream = _git(runner, root, "rev-parse", "--abbrev-ref", "@{upstream}")
    remote, separator, _remote_branch = upstream.partition("/")
    if not separator or not remote:
        raise _failure(
            "The configured upstream does not identify a remote branch.",
            "Configure the current branch to track a remote branch.",
        )
    if apply and command_center_status(state_dir).running:
        raise _failure(
            "The command center must be stopped before applying a source update.",
            "Run video-intelligence stop, then retry update --apply.",
        )
    if apply and _git(runner, root, "status", "--porcelain"):
        raise VideoIntelligenceError(
            StructuredError(
                code=ErrorCode.DIRTY_WORKTREE,
                message="The source checkout has uncommitted changes.",
                safe_recovery_action="Commit or stash local changes before updating.",
            )
        )
    _git(runner, root, "fetch", "--prune", remote)
    counts = _git(runner, root, "rev-list", "--left-right", "--count", f"HEAD...{upstream}")
    try:
        ahead_text, behind_text = counts.split()
        ahead, behind = int(ahead_text), int(behind_text)
    except (ValueError, TypeError) as exc:
        raise _failure(
            "Git returned an unexpected update status.",
            "Inspect the repository and upstream configuration manually.",
        ) from exc
    applied = False
    if apply and behind:
        if ahead:
            raise _failure(
                "The local and upstream branches have diverged.",
                "Resolve the divergence manually; automatic updates are fast-forward only.",
            )
        _git(runner, root, "merge", "--ff-only", upstream)
        applied = True
        behind = 0
    if applied:
        message = "Source checkout updated with a fast-forward merge."
    elif behind:
        message = f"{behind} upstream commit(s) are available."
    else:
        message = "Source checkout is up to date."
    return UpdateReport(
        repository=str(root),
        branch=branch,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        applied=applied,
        message=message,
    )
