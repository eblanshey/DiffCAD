# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GetCommitsAction orchestration and result contracts.
"""Unit tests for GetCommitsAction."""

from datetime import datetime

from freecad.history_wb.application.actions.get_commits import GetCommitsAction
from freecad.history_wb.domain.git.git_service import GitService
from freecad.history_wb.domain.git.models import GitCommit, GitRepository

from tests.fakes.fake_git_port import FakeGitPort


class TestGetCommitsAction:
    """Tests for GetCommitsAction execute behavior."""

    def test_execute_returns_commits_success(self) -> None:
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/repo")
        fake_port.set_commits(
            "/repo",
            [
                GitCommit(
                    id="c1", message="Fix bug", author="John", timestamp=datetime.fromisoformat("2024-01-15T10:30:00")
                ),
                GitCommit(
                    id="c2",
                    message="Add feature",
                    author="Jane",
                    timestamp=datetime.fromisoformat("2024-01-14T09:00:00"),
                ),
            ],
        )

        service = GitService(fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")
        action = GetCommitsAction(service)

        result = action.execute(repo)

        assert result.is_success is True
        assert len(result.data) == 2
        assert result.message is None

    def test_execute_returns_empty_for_unknown_repo(self) -> None:
        fake_port = FakeGitPort()
        service = GitService(fake_port)
        repo = GitRepository(name="nonexistent", absolute_path="/nonexistent")
        action = GetCommitsAction(service)

        result = action.execute(repo)

        assert result.is_success is True
        assert result.data == []

    def test_execute_forwards_limit_and_skip(self) -> None:
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/repo")
        for i in range(5):
            fake_port.add_commit(
                root_path="/repo",
                commit_id=str(i),
                message=f"C{i}",
                author="A",
                timestamp=f"2024-01-{i + 1:02d}T00:00:00Z",
            )

        service = GitService(fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")
        action = GetCommitsAction(service)

        result = action.execute(repo, limit=2, skip=1)

        assert result.is_success is True
        assert len(result.data) == 2
