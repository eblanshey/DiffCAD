# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for loading repository .gitignore content action.
"""Unit tests for GetGitIgnoreContentAction."""

from freecad.history_wb.application.actions.get_gitignore_content import (
    DEFAULT_GITIGNORE_CONTENT,
    GetGitIgnoreContentAction,
)
from freecad.history_wb.domain.git.models import GitRepository


class TestGetGitIgnoreContentAction:
    """Tests for loading repository .gitignore content."""

    def test_returns_default_when_gitignore_missing(self) -> None:
        action = GetGitIgnoreContentAction()
        repo = GitRepository(name="repo", absolute_path="/home/user/repo")

        result = action.execute(repo)

        assert result.is_success is True
        assert result.data == DEFAULT_GITIGNORE_CONTENT

    def test_reads_existing_gitignore_content(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        repo_path = tmp_path / "repo"
        repo_path.mkdir(parents=True)
        (repo_path / ".gitignore").write_text("*.bak\n", encoding="utf-8")
        action = GetGitIgnoreContentAction()
        repo = GitRepository(name="repo", absolute_path=str(repo_path))

        result = action.execute(repo)

        assert result.is_success is True
        assert result.data == "*.bak\n"
