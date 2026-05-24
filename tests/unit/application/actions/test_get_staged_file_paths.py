# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GetStagedFilePathsAction application action.
"""Unit tests for GetStagedFilePathsAction."""

from unittest.mock import MagicMock

import pytest
from freecad.history_wb.application.actions.get_staged_file_paths import GetStagedFilePathsAction
from freecad.history_wb.domain.git.git_service import GitService
from freecad.history_wb.domain.git.models import GitRepository


class TestGetStagedFilePathsAction:
    """Tests for GetStagedFilePathsAction class."""

    def test_execute_returns_staged_paths(self) -> None:
        """Test: Execute returns list of staged FCStd file paths."""
        # Given a mock GitService that returns ["path/to/doc.FCStd"]
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.get_staged_files.return_value = ["path/to/doc.FCStd", "another/doc.FCStd"]

        action = GetStagedFilePathsAction(git_service=mock_git_service)
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called with a repo
        result = action.execute(repo)

        # Then Result.success with staged paths is returned
        assert result.is_success is True
        assert result.data == ["path/to/doc.FCStd", "another/doc.FCStd"]

    def test_execute_returns_empty_list_when_nothing_staged(self) -> None:
        """Test: Execute returns empty list when no files are staged."""
        # Given a mock GitService that returns []
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.get_staged_files.return_value = []

        action = GetStagedFilePathsAction(git_service=mock_git_service)
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called
        result = action.execute(repo)

        # Then Result.success([]) is returned
        assert result.is_success is True
        assert result.data == []

    def test_execute_raises_exception_on_error(self) -> None:
        """Test: Execute raises exception when git service raises."""
        # Given a mock GitService that raises
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.get_staged_files.side_effect = Exception("Git error")

        action = GetStagedFilePathsAction(git_service=mock_git_service)
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called
        # Then exception propagates (actions don't catch exceptions)
        with pytest.raises(Exception, match="Git error"):
            action.execute(repo)
