# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for initializing git repositories via application action.
"""Unit tests for InitializeGitRepositoryAction."""

from freecad.history_wb.application.actions.initialize_git_repository import InitializeGitRepositoryAction
from freecad.history_wb.domain.git import GitRepository, GitService

from tests.fakes.fake_git_port import FakeGitPort


class TestInitializeGitRepositoryAction:
    """Tests for repository initialization action behavior."""

    def test_initializes_repository_for_available_directory(self) -> None:
        action = InitializeGitRepositoryAction(git_service=GitService(FakeGitPort()))

        result = action.execute("/home/user/project")

        assert result.is_success is True
        assert isinstance(result.data, GitRepository)
        assert result.data.absolute_path == "/home/user/project"
        assert result.data.name == "project"

    def test_rejects_empty_path(self) -> None:
        action = InitializeGitRepositoryAction(git_service=GitService(FakeGitPort()))

        result = action.execute("")

        assert result.is_success is False
        assert result.message == "Repository directory is required"

    def test_rejects_path_already_inside_git_repository(self) -> None:
        fake_git = FakeGitPort()
        fake_git.add_git_repo("/home/user/repo")
        action = InitializeGitRepositoryAction(git_service=GitService(fake_git))

        result = action.execute("/home/user/repo/sub")

        assert result.is_success is False
        assert result.message == "Directory is already inside a git repository"

    def test_returns_failure_when_git_init_fails(self) -> None:
        action = InitializeGitRepositoryAction(git_service=GitService(FakeGitPort(fail_init=True)))

        result = action.execute("/home/user/project")

        assert result.is_success is False
        assert result.message == "Failed to initialize git repository"
