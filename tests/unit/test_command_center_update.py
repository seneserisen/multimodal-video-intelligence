from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest
from video_intelligence.command_center.update import GitResult, update_source
from video_intelligence.errors import ErrorCode, VideoIntelligenceError


class FakeGitRunner:
    def __init__(
        self,
        root: Path,
        *,
        status: str = "",
        counts: str = "0 0",
        upstream: str = "origin/agent/command-center",
    ) -> None:
        self.root = root
        self.status = status
        self.counts = counts
        self.upstream = upstream
        self.calls: list[tuple[str, ...]] = []

    def run(self, arguments: Sequence[str], *, cwd: Path) -> GitResult:
        assert arguments[0] == "git"
        command = tuple(arguments[1:])
        self.calls.append(command)
        remote = self.upstream.partition("/")[0]
        outputs = {
            ("rev-parse", "--show-toplevel"): str(self.root),
            ("branch", "--show-current"): "agent/command-center",
            ("rev-parse", "--abbrev-ref", "@{upstream}"): self.upstream,
            ("status", "--porcelain"): self.status,
            ("fetch", "--prune", remote): "",
            (
                "rev-list",
                "--left-right",
                "--count",
                f"HEAD...{self.upstream}",
            ): self.counts,
            ("merge", "--ff-only", self.upstream): "updated",
        }
        return GitResult(0, outputs[command], "")


def test_update_check_reports_available_commits(tmp_path: Path) -> None:
    runner = FakeGitRunner(tmp_path, counts="0 2")
    report = update_source(repository=tmp_path, runner=runner)
    assert report.behind == 2
    assert report.applied is False
    assert ("merge", "--ff-only", "origin/agent/command-center") not in runner.calls


def test_update_apply_is_fast_forward_only(tmp_path: Path) -> None:
    runner = FakeGitRunner(tmp_path, counts="0 2")
    report = update_source(repository=tmp_path, apply=True, runner=runner, state_dir=tmp_path)
    assert report.applied is True
    assert report.behind == 0
    assert ("merge", "--ff-only", "origin/agent/command-center") in runner.calls


def test_update_refuses_dirty_worktree(tmp_path: Path) -> None:
    runner = FakeGitRunner(tmp_path, status="M important.py", counts="0 2")
    with pytest.raises(VideoIntelligenceError) as caught:
        update_source(repository=tmp_path, apply=True, runner=runner, state_dir=tmp_path)
    assert caught.value.detail.code == ErrorCode.DIRTY_WORKTREE
    assert ("fetch", "--prune", "origin") not in runner.calls


def test_update_refuses_diverged_branch(tmp_path: Path) -> None:
    runner = FakeGitRunner(tmp_path, counts="1 2")
    with pytest.raises(VideoIntelligenceError, match="diverged"):
        update_source(repository=tmp_path, apply=True, runner=runner, state_dir=tmp_path)


def test_update_fetches_the_configured_remote(tmp_path: Path) -> None:
    runner = FakeGitRunner(tmp_path, upstream="upstream/main")
    report = update_source(repository=tmp_path, runner=runner)
    assert report.upstream == "upstream/main"
    assert ("fetch", "--prune", "upstream") in runner.calls
