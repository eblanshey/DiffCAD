# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for initializing git repositories via application action.
"""Unit tests for InitializeGitRepositoryAction."""

from freecad.history_wb.application.actions.get_gitignore_content import GetGitIgnoreContentAction
from freecad.history_wb.application.actions.initialize_git_repository import InitializeGitRepositoryAction
from freecad.history_wb.application.actions.update_gitignore import UpdateGitIgnoreAction
from freecad.history_wb.domain.git import GitRepository, GitService
from tests.fakes.fake_git_port import FakeGitPort


class TestInitializeGitRepositoryAction:
    """Tests for repository initialization action behavior."""

    def test_initializes_repository_for_available_directory(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        fake_git = FakeGitPort()
        git_service = GitService(fake_git)
        action = InitializeGitRepositoryAction(
            git_service=git_service,
            update_gitignore_action=UpdateGitIgnoreAction(
                git_service=git_service,
                get_gitignore_content_action=GetGitIgnoreContentAction(),
            ),
        )
        target_repo = tmp_path / "project"
        target_repo.mkdir(parents=True)

        result = action.execute(str(target_repo))

        assert result.is_success is True
        assert isinstance(result.data, GitRepository)
        assert result.data.absolute_path == str(target_repo)
        assert result.data.name == "project"
        assert fake_git._last_stage_files_call == (str(target_repo), [".gitignore"])

    def test_rejects_empty_path(self) -> None:
        git_service = GitService(FakeGitPort())
        action = InitializeGitRepositoryAction(
            git_service=git_service,
            update_gitignore_action=UpdateGitIgnoreAction(
                git_service=git_service,
                get_gitignore_content_action=GetGitIgnoreContentAction(),
            ),
        )

        result = action.execute("")

        assert result.is_success is False
        assert result.message == "Repository directory is required"

    def test_rejects_path_already_inside_git_repository(self) -> None:
        fake_git = FakeGitPort()
        fake_git.add_git_repo("/home/user/repo")
        git_service = GitService(fake_git)
        action = InitializeGitRepositoryAction(
            git_service=git_service,
            update_gitignore_action=UpdateGitIgnoreAction(
                git_service=git_service,
                get_gitignore_content_action=GetGitIgnoreContentAction(),
            ),
        )

        result = action.execute("/home/user/repo/sub")

        assert result.is_success is False
        assert result.message == "Directory is already inside a git repository"

    def test_returns_failure_when_git_init_fails(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        git_service = GitService(FakeGitPort(fail_init=True))
        action = InitializeGitRepositoryAction(
            git_service=git_service,
            update_gitignore_action=UpdateGitIgnoreAction(
                git_service=git_service,
                get_gitignore_content_action=GetGitIgnoreContentAction(),
            ),
        )
        target_repo = tmp_path / "project"
        target_repo.mkdir(parents=True)

        result = action.execute(str(target_repo))

        assert result.is_success is False
        assert result.message == "Failed to initialize git repository"

    def test_returns_failure_when_gitignore_stage_fails(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        git_service = GitService(FakeGitPort(fail_stage=True))
        action = InitializeGitRepositoryAction(
            git_service=git_service,
            update_gitignore_action=UpdateGitIgnoreAction(
                git_service=git_service,
                get_gitignore_content_action=GetGitIgnoreContentAction(),
            ),
        )
        target_repo = tmp_path / "project"
        target_repo.mkdir(parents=True)

        result = action.execute(str(target_repo))

        assert result.is_success is False
        assert result.message == "Failed to stage .gitignore file"
