# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GetCommittedFilePathsAction application action.
"""Unit tests for GetCommittedFilePathsAction."""

from unittest.mock import MagicMock

import pytest
from freecad.history_wb.application.actions.get_committed_file_paths import GetCommittedFilePathsAction
from freecad.history_wb.domain.git.git_service import GitService
from freecad.history_wb.domain.git.models import GitRepository


class TestGetCommittedFilePathsAction:
    """Tests for GetCommittedFilePathsAction class."""

    def test_execute_returns_committed_file_paths(self) -> None:
        """Test: Execute returns list of FCStd file paths changed in a commit."""
        # Given a mock GitService that returns paths for a commit
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.get_committed_files.return_value = [
            "path/to/doc.FCStd",
            "another/doc.FCStd",
        ]

        action = GetCommittedFilePathsAction(git_service=mock_git_service)
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called with a repo and commit hash
        result = action.execute(repo, "abc123")

        # Then Result.success with committed file paths is returned
        assert result.is_success is True
        assert result.data == ["path/to/doc.FCStd", "another/doc.FCStd"]

    def test_execute_returns_empty_list_when_no_fcstd_changes(self) -> None:
        """Test: Execute returns empty list when commit has no FCStd changes."""
        # Given a mock GitService that returns []
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.get_committed_files.return_value = []

        action = GetCommittedFilePathsAction(git_service=mock_git_service)
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called
        result = action.execute(repo, "abc123")

        # Then Result.success([]) is returned
        assert result.is_success is True
        assert result.data == []

    def test_execute_raises_exception_on_error(self) -> None:
        """Test: Execute raises exception when git service raises."""
        # Given a mock GitService that raises
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.get_committed_files.side_effect = Exception("Git error")

        action = GetCommittedFilePathsAction(git_service=mock_git_service)
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called
        # Then exception propagates (actions don't catch exceptions)
        with pytest.raises(Exception, match="Git error"):
            action.execute(repo, "abc123")
