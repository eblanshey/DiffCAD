# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for .gitignore write/stage application action.
"""Unit tests for UpdateGitIgnoreAction."""

from freecad.history_wb.application.actions.get_gitignore_content import GetGitIgnoreContentAction
from freecad.history_wb.application.actions.update_gitignore import UpdateGitIgnoreAction
from freecad.history_wb.domain.git.models import GitRepository
from freecad.history_wb.domain.git.git_service import GitService
from tests.fakes.fake_git_port import FakeGitPort


class TestUpdateGitIgnoreAction:
    """Tests for persisting repository .gitignore."""

    def test_execute_writes_and_stages_gitignore(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        repo_path = tmp_path / "repo"
        repo_path.mkdir(parents=True)
        fake_git = FakeGitPort()
        action = UpdateGitIgnoreAction(
            git_service=GitService(fake_git),
            get_gitignore_content_action=GetGitIgnoreContentAction(),
        )
        repo = GitRepository(name="repo", absolute_path=str(repo_path))

        result = action.execute(repo, "*.FCBak\n")

        assert result.is_success is True
        assert (repo_path / ".gitignore").read_text(encoding="utf-8") == "*.FCBak\n"
        assert fake_git._last_stage_files_call == (str(repo_path), [".gitignore"])

    def test_execute_fails_when_stage_fails(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        repo_path = tmp_path / "repo"
        repo_path.mkdir(parents=True)
        action = UpdateGitIgnoreAction(
            git_service=GitService(FakeGitPort(fail_stage=True)),
            get_gitignore_content_action=GetGitIgnoreContentAction(),
        )
        repo = GitRepository(name="repo", absolute_path=str(repo_path))

        result = action.execute(repo, "*.FCBak\n")

        assert result.is_success is False
        assert result.message == "Failed to stage .gitignore file"
