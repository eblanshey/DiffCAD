# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains unit tests for the GitPortAdapter class.
# Tests use subprocess mocking to verify git repository detection without actual
# git commands, ensuring reliable and fast test execution.
"""Unit tests for GitPortAdapter."""

import os
import subprocess
import unittest.mock
from unittest.mock import patch

import pytest

from freecad.diff_wb.infrastructure.git import GitPortAdapter


class TestGitPortAdapter:
    """Tests for the GitPortAdapter class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.adapter = GitPortAdapter()

    @pytest.mark.parametrize(
        "path",
        [
            "/home/user/project",
            "/tmp/test_repo",
            "./relative/path",
            "/absolute/path/to/repo",
        ],
    )
    def test_find_top_level_path_success(self, path: str) -> None:
        """Test successful git root detection.

        When git rev-parse returns exit code 0, the adapter should return
        the stripped stdout value.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout="/home/user/project\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            result = self.adapter.find_top_level_git_path(path)

            # Verify subprocess.run was called with correct arguments
            mock_run.assert_called_once_with(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Verify the result is the stripped stdout
            assert result == "/home/user/project"

    def test_find_top_level_path_success_with_extra_whitespace(self) -> None:
        """Test that leading/trailing whitespace is properly stripped."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout="  /home/user/project  \n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.find_top_level_git_path("/some/path")

            assert result == "/home/user/project"

    @patch.object(os.path, "dirname", return_value="/parent/directory")
    @patch.object(os.path, "isfile", return_value=True)
    def test_find_top_level_path_with_file_path(
        self, mock_isfile: unittest.mock.Mock, mock_dirname: unittest.mock.Mock
    ) -> None:
        """Test that file paths are handled correctly by using parent directory as cwd.

        When the input path is a file (not a directory), the adapter should:
        1. Detect that the input is a file using os.path.isfile()
        2. Extract the parent directory using os.path.dirname()
        3. Pass the parent directory to subprocess.run() as cwd

        This ensures git commands work correctly when given a file path.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout="/home/user/project\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            result = self.adapter.find_top_level_git_path("/parent/directory/file.py")

            # Verify os.path.isfile was called with the original path
            mock_isfile.assert_called_once_with("/parent/directory/file.py")

            # Verify os.path.dirname was called with the original path
            mock_dirname.assert_called_once_with("/parent/directory/file.py")

            # Verify subprocess.run was called with parent directory as cwd
            mock_run.assert_called_once_with(
                ["git", "rev-parse", "--show-toplevel"],
                cwd="/parent/directory",
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Verify the result is returned correctly
            assert result == "/home/user/project"

    def test_find_top_level_path_not_in_git_repo(self) -> None:
        """Test handling of path not in a git repository.

        When git rev-parse returns non-zero exit code (not in git repo),
        the adapter should return None.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.find_top_level_git_path("/non/git/path")

            assert result is None

    def test_find_top_level_path_timeout(self) -> None:
        """Test handling of subprocess timeout.

        When git command times out, the adapter should return None.
        """
        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=5)):
            result = self.adapter.find_top_level_git_path("/some/path")

            assert result is None

    def test_find_top_level_path_git_not_found(self) -> None:
        """Test handling of git command not found.

        When git executable is not found, the adapter should return None.
        """
        with patch.object(subprocess, "run", side_effect=FileNotFoundError("git")):
            result = self.adapter.find_top_level_git_path("/some/path")

            assert result is None

    def test_find_top_level_path_empty_stdout_success(self) -> None:
        """Test handling of empty stdout with success exit code.

        Edge case: git returns 0 but empty output (shouldn't happen normally).
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.find_top_level_git_path("/some/path")

            # Empty string stripped is still empty string
            assert result == ""

    @pytest.mark.parametrize(
        "returncode",
        [1, 2, 128],
    )
    def test_find_top_level_path_various_error_codes(self, returncode: int) -> None:
        """Test handling of various non-zero exit codes.

        Any non-zero exit code should result in None being returned.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=returncode,
            stdout="",
            stderr=f"error {returncode}",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.find_top_level_git_path("/some/path")

            assert result is None


class TestGitPortAdapterProtocol:
    """Tests to verify GitPortAdapter implements GitPort protocol."""

    def test_adapter_implements_gitport_protocol(self) -> None:
        """Test that GitPortAdapter has the required find_top_level_git_path method.

        This verifies the adapter correctly implements the GitPort protocol.
        """
        adapter = GitPortAdapter()

        # Verify the method exists and is callable
        assert hasattr(adapter, "find_top_level_git_path")
        assert callable(adapter.find_top_level_git_path)
