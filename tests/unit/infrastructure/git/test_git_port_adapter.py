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
from freecad.diff_wb.utils import Log


class TestGitPortAdapter:
    """Tests for the GitPortAdapter class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.adapter = GitPortAdapter()
        self.adapter._git_executable = "git"

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
                encoding="utf-8",
                errors="replace",
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
                encoding="utf-8",
                errors="replace",
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

        with (
            patch.object(subprocess, "run", return_value=mock_result),
            patch.object(Log, "warning") as mock_warning,
        ):
            result = self.adapter.find_top_level_git_path("/non/git/path")

            assert result is None
            mock_warning.assert_not_called()

    def test_find_top_level_path_warns_for_git_error(self) -> None:
        """Test git errors are logged separately from non-repository paths."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=128,
            stdout="",
            stderr="fatal: detected dubious ownership in repository at '//server/share/repo'",
        )

        with (
            patch.object(subprocess, "run", return_value=mock_result),
            patch.object(Log, "warning") as mock_warning,
        ):
            result = self.adapter.find_top_level_git_path("//server/share/repo/file.FCStd")

        assert result is None
        mock_warning.assert_called_once()
        assert "Git repository detection failed due to git error" in mock_warning.call_args[0][0]
        assert "dubious ownership" in mock_warning.call_args[0][0]

    @pytest.mark.parametrize(
        ("side_effect",),
        [
            (subprocess.TimeoutExpired(cmd="git", timeout=5),),
            (FileNotFoundError("git"),),
        ],
    )
    def test_find_top_level_path_handles_errors(self, side_effect: Exception) -> None:
        """Test timeout and git-not-found return None."""
        with patch.object(subprocess, "run", side_effect=side_effect):
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

    def test_run_git_suppresses_windows_console_window(self) -> None:
        """Test Windows git commands run without opening a console window."""

        class FakeStartupInfo:
            """Minimal STARTUPINFO test double."""

            def __init__(self) -> None:
                self.dwFlags = 0
                self.wShowWindow = 1

        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout="C:/repo\n",
            stderr="",
        )

        with (
            patch.object(os, "name", "nt"),
            patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True),
            patch.object(subprocess, "STARTF_USESHOWWINDOW", 1, create=True),
            patch.object(subprocess, "SW_HIDE", 0, create=True),
            patch.object(subprocess, "STARTUPINFO", FakeStartupInfo, create=True),
            patch.object(subprocess, "run", return_value=mock_result) as mock_run,
        ):
            result = self.adapter.find_top_level_git_path("C:/repo")

        assert result == "C:/repo"
        kwargs = mock_run.call_args.kwargs
        assert kwargs["creationflags"] == 0x08000000
        startupinfo = kwargs["startupinfo"]
        assert startupinfo.dwFlags == 1
        assert startupinfo.wShowWindow == 0

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

    def test_initialize_repository_success(self) -> None:
        """Test successful git init returns True."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "init"],
            returncode=0,
            stdout="Initialized empty Git repository\n",
            stderr="",
        )

        with (
            patch.object(os.path, "isdir", return_value=True),
            patch.object(subprocess, "run", return_value=mock_result) as mock_run,
        ):
            result = self.adapter.initialize_repository("/path/to/project")

        assert result is True
        mock_run.assert_called_once_with(
            ["git", "init"],
            cwd="/path/to/project",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

    def test_initialize_repository_returns_false_for_missing_directory(self) -> None:
        """Test missing directory short-circuits with False."""
        with patch.object(os.path, "isdir", return_value=False):
            result = self.adapter.initialize_repository("/missing/path")

        assert result is False

    def test_initialize_repository_returns_false_on_non_zero_exit(self) -> None:
        """Test git init failure return code returns False."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "init"],
            returncode=1,
            stdout="",
            stderr="fatal: init failed",
        )

        with (
            patch.object(os.path, "isdir", return_value=True),
            patch.object(subprocess, "run", return_value=mock_result),
        ):
            result = self.adapter.initialize_repository("/path/to/project")

        assert result is False


class TestGitPortAdapterGetCommits:
    """Tests for the get_commits method of GitPortAdapter."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.adapter = GitPortAdapter()
        self.adapter._git_executable = "git"

    def test_get_commits_success_single_commit(self) -> None:
        """Test successful commit retrieval with a single commit."""
        # Using null byte (\x00) as separator - format: hash\x00message\x00author\x00timestamp\x00
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="abc123def456\x00Initial commit\x00Author Name\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            commits = self.adapter.get_commits("/path/to/repo")

            # Verify subprocess.run was called with correct arguments
            mock_run.assert_called_once_with(
                ["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )

            # Verify result
            assert len(commits) == 1
            assert commits[0].id == "abc123def456"
            assert commits[0].message == "Initial commit"
            assert commits[0].author == "Author Name"
            assert commits[0].timestamp.isoformat() == "2024-01-01T10:00:00+00:00"

    def test_get_commits_parsing_full_message(self) -> None:
        """Test parsing commit with full message (subject + body)."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="abc123def456\x00Fix bug in module\n\nThis is the body of the commit.\nIt has multiple lines.\x00John Doe\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            assert len(commits) == 1
            assert commits[0].id == "abc123def456"
            assert commits[0].message == "Fix bug in module\n\nThis is the body of the commit.\nIt has multiple lines."
            assert commits[0].author == "John Doe"
            assert commits[0].timestamp.isoformat() == "2024-01-01T10:00:00+00:00"

    def test_get_commits_multiple_commits(self) -> None:
        """Test retrieving multiple commits."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="hash3\x00Third commit\x00Alice\x002024-01-03T10:00:00+00:00\x00hash2\x00Second commit\x00Bob\x002024-01-02T10:00:00+00:00\x00hash1\x00First commit\x00Charlie\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            assert len(commits) == 3
            assert commits[0].id == "hash3"
            assert commits[0].author == "Alice"
            assert commits[0].timestamp.isoformat() == "2024-01-03T10:00:00+00:00"
            assert commits[1].id == "hash2"
            assert commits[1].author == "Bob"
            assert commits[1].timestamp.isoformat() == "2024-01-02T10:00:00+00:00"
            assert commits[2].id == "hash1"
            assert commits[2].author == "Charlie"
            assert commits[2].timestamp.isoformat() == "2024-01-01T10:00:00+00:00"

    def test_get_commits_trims_newline_prefixed_hashes(self) -> None:
        """Test parsing commits when git log inserts newline between records."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout=(
                "hash3\x00Third commit\x00Alice\x002024-01-03T10:00:00+00:00\x00"
                "\nhash2\x00Second commit\x00Bob\x002024-01-02T10:00:00+00:00\x00"
                "\nhash1\x00First commit\x00Charlie\x002024-01-01T10:00:00+00:00\x00"
            ),
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            assert len(commits) == 3
            assert commits[0].id == "hash3"
            assert commits[1].id == "hash2"
            assert commits[2].id == "hash1"

    def test_get_commits_limit_parameter(self) -> None:
        """Test that limit parameter is passed correctly to git log."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n5", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="hash1\x00Commit 1\x00Author\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            self.adapter.get_commits("/path/to/repo", limit=5)

            mock_run.assert_called_once_with(
                ["git", "log", "-n5", "--format=%H%x00%B%x00%an%x00%aI%x00"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )

    def test_get_commits_skip_parameter(self) -> None:
        """Test that skip parameter is passed correctly to git log."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "--skip=10", "-n5", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="hash1\x00Commit 1\x00Author\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            self.adapter.get_commits("/path/to/repo", limit=5, skip=10)

            mock_run.assert_called_once_with(
                ["git", "log", "--skip=10", "-n5", "--format=%H%x00%B%x00%an%x00%aI%x00"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )

    def test_get_commits_empty_repository(self) -> None:
        """Test handling of empty repository (no commits)."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            assert commits == []

    @pytest.mark.parametrize(
        ("side_effect",),
        [
            (subprocess.TimeoutExpired(cmd="git", timeout=10),),
            (FileNotFoundError("git"),),
        ],
    )
    def test_get_commits_handles_errors(self, side_effect: Exception) -> None:
        """Test timeout and git-not-found return empty list."""
        with patch.object(subprocess, "run", side_effect=side_effect):
            commits = self.adapter.get_commits("/path/to/repo")

            assert commits == []

    def test_get_commits_non_zero_exit_code(self) -> None:
        """Test handling of non-zero exit code from git."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            assert commits == []

    def test_get_commits_non_zero_exit_code_logs_warning(self) -> None:
        """Test non-zero git log errors are logged when unexpected."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )

        with (
            patch.object(subprocess, "run", return_value=mock_result),
            patch.object(Log, "warning") as mock_warning,
        ):
            commits = self.adapter.get_commits("/path/to/repo")

        assert commits == []
        mock_warning.assert_called_once_with("Git log failed with return code 128: fatal: not a git repository")

    def test_get_commits_no_commits_yet_does_not_log_warning(self) -> None:
        """Test unborn-branch git log error is treated as expected and not logged."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=128,
            stdout="",
            stderr="fatal: your current branch 'master' does not have any commits yet",
        )

        with (
            patch.object(subprocess, "run", return_value=mock_result),
            patch.object(Log, "warning") as mock_warning,
        ):
            commits = self.adapter.get_commits("/path/to/repo")

        assert commits == []
        mock_warning.assert_not_called()

    @patch.object(os.path, "dirname", return_value="/parent/directory")
    @patch.object(os.path, "isfile", return_value=True)
    def test_get_commits_with_file_path(
        self, mock_isfile: unittest.mock.Mock, mock_dirname: unittest.mock.Mock
    ) -> None:
        """Test that file paths use parent directory as cwd.

        When the input path is a file (not a directory), the adapter should:
        1. Detect that the input is a file using os.path.isfile()
        2. Extract the parent directory using os.path.dirname()
        3. Pass the parent directory to subprocess.run() as cwd
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="hash1\x00Commit message\x00Author\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            self.adapter.get_commits("/parent/directory/file.py")

            # Verify os.path.isfile was called with the original path
            mock_isfile.assert_called_once_with("/parent/directory/file.py")

            # Verify os.path.dirname was called with the original path
            mock_dirname.assert_called_once_with("/parent/directory/file.py")

            # Verify subprocess.run was called with parent directory as cwd
            mock_run.assert_called_once_with(
                ["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
                cwd="/parent/directory",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )

    def test_get_commits_message_with_pipe_characters(self) -> None:
        """Test parsing commit message containing pipe characters."""
        # Null byte separator handles pipe characters in messages correctly
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="abc123def456\x00Fix: update | value in config\x00John Doe\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            assert len(commits) == 1
            assert commits[0].id == "abc123def456"
            assert commits[0].message == "Fix: update | value in config"
            assert commits[0].author == "John Doe"
            assert commits[0].timestamp.isoformat() == "2024-01-01T10:00:00+00:00"

    def test_get_commits_multiline_message_with_body(self) -> None:
        """Test parsing commit with multiline message including body."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="hash123\x00Add new feature\n\nThis is a detailed description of the feature.\n\n- Feature 1\n- Feature 2\x00Developer Name\x002024-01-01T12:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            assert len(commits) == 1
            assert commits[0].id == "hash123"
            # Message includes subject and body (before author field)
            assert "Add new feature" in commits[0].message
            assert "This is a detailed description" in commits[0].message
            assert commits[0].author == "Developer Name"
            assert commits[0].timestamp.isoformat() == "2024-01-01T12:00:00+00:00"

    def test_get_commits_desc_order_newest_first(self) -> None:
        """Test that commits are returned in DESC order (newest first)."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="latest_hash\x00Latest commit\x00Author\x002024-01-15T10:00:00+00:00\x00oldest_hash\x00Oldest commit\x00Author\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            # git log returns newest first by default
            assert len(commits) == 2
            assert commits[0].id == "latest_hash"
            assert commits[0].timestamp.isoformat() == "2024-01-15T10:00:00+00:00"
            assert commits[1].id == "oldest_hash"
            assert commits[1].timestamp.isoformat() == "2024-01-01T10:00:00+00:00"

    def test_get_commits_malformed_data_returns_empty_list(self) -> None:
        """Test handling of malformed commit data (incomplete fields)."""
        # Incomplete data - only has hash and message, missing author and timestamp
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="hash1\x00Commit message\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            # Incomplete data (less than 4 fields per commit) should be skipped
            assert commits == []


class TestGitPortAdapterIsPathInRepository:
    """Tests for the is_path_in_repository method of GitPortAdapter."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.adapter = GitPortAdapter()
        self.adapter._git_executable = "git"

    @pytest.mark.parametrize(
        "git_root,path,expected",
        [
            # Normal paths - file within repo
            ("/home/user/project", "/home/user/project/src/file.py", True),
            ("/home/user/project", "/home/user/project/doc.md", True),
            # Nested paths
            ("/home/user/project", "/home/user/project/src/subdir/deep/file.py", True),
            ("/home/user/project", "/home/user/project/a/b/c/d/e/f.py", True),
            # Directory paths within repo
            ("/home/user/project", "/home/user/project/src", True),
            ("/home/user/project", "/home/user/project/src/nested/dir", True),
            # Path exactly at git root
            ("/home/user/project", "/home/user/project", True),
            # Paths outside repo
            ("/home/user/project", "/home/user/other/file.py", False),
            ("/home/user/project", "/tmp/file.py", False),
            ("/home/user/project", "/home/user/project-sibling/file.py", False),
            # Trailing slashes
            ("/home/user/project/", "/home/user/project/src/file.py", True),
            ("/home/user/project", "/home/user/project/src/file.py/", True),
            # Empty or invalid paths
            ("", "/home/user/project/file.py", False),
            ("/home/user/project", "", False),
            ("", "", False),
        ],
    )
    def test_is_path_in_repository_various_scenarios(self, git_root: str, path: str, expected: bool) -> None:
        """Test is_path_in_repository with various path scenarios.

        This verifies that the method correctly handles:
        - Normal file and directory paths
        - Nested paths
        - Paths exactly at git root
        - Paths outside the repository
        - Trailing slashes
        - Different path separators
        - Empty or invalid paths
        """
        result = self.adapter.is_path_in_repository(git_root, path)
        assert result == expected

    def test_is_path_in_repository_with_relative_paths_normalized(self) -> None:
        """Test that relative path components are properly normalized.

        The method should handle paths with .. and . components correctly.
        """
        # Path with parent directory reference that still resolves inside repo
        result = self.adapter.is_path_in_repository("/home/user/project", "/home/user/project/src/../docs/file.md")
        assert result is True

        # Path with parent directory reference that goes outside repo
        result = self.adapter.is_path_in_repository("/home/user/project", "/home/user/project/../other/file.md")
        assert result is False

    def test_is_path_in_repository_case_sensitive(self) -> None:
        """Test that path matching is case-sensitive.

        On Linux, paths should be case-sensitive.
        """
        # Different case should not match
        result = self.adapter.is_path_in_repository("/home/user/Project", "/home/user/project/file.py")
        assert result is False

        result = self.adapter.is_path_in_repository("/home/user/project", "/home/user/Project/file.py")
        assert result is False


class TestGitPortAdapterStageFiles:
    """Tests for the stage_files method of GitPortAdapter."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.adapter = GitPortAdapter()
        self.adapter._git_executable = "git"

    def test_stage_files_uses_pathspec_separator(self) -> None:
        """Given paths that look like options, git add receives -- separator."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "add", "-v", "--", "-weird.FCStd"],
            returncode=0,
            stdout="add '-weird.FCStd'\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            result = self.adapter.stage_files("/path/to/repo", ["-weird.FCStd"])

            assert result is True
            mock_run.assert_called_once_with(
                ["git", "add", "-v", "--", "-weird.FCStd"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

    def test_stage_files_handles_bad_cwd_os_error(self) -> None:
        """Given subprocess raises OSError, returns False."""
        with patch.object(subprocess, "run", side_effect=OSError("bad cwd")):
            result = self.adapter.stage_files("/path/to/repo", ["file.FCStd"])

            assert result is False


class TestGitPortAdapterGetStagedPaths:
    """Tests for the get_staged_paths method of GitPortAdapter."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.adapter = GitPortAdapter()
        self.adapter._git_executable = "git"

    def test_get_staged_paths_returns_staged_fcstd_files(self) -> None:
        """Test that staged .FCStd files are returned correctly.

        Given a git repo with a staged .FCStd file, when get_staged_paths is called,
        then it returns the relative path of the staged file.
        """
        # Simulate git status --porcelain output with staged .FCStd file
        # Format: "<index_status><wt_status> <path>"
        # "A " means added/staged
        mock_result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain"],
            returncode=0,
            stdout="A  path/to/document.FCStd\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            result = self.adapter.get_staged_paths("/path/to/repo")

            mock_run.assert_called_once_with(
                ["git", "status", "--porcelain", "-z"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            assert result == ["path/to/document.FCStd"]

    def test_get_staged_paths_filters_non_fcstd_files(self) -> None:
        """Test that non-.FCStd files are filtered out.

        Given a git repo with staged .txt and .FCStd files, when get_staged_paths is called,
        then only .FCStd files are returned.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain"],
            returncode=0,
            stdout="A  readme.txt\nA  document.FCStd\nM  notes.md\nA  another.FCStd\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_staged_paths("/path/to/repo")

            assert result == ["document.FCStd", "another.FCStd"]

    def test_get_staged_paths_returns_empty_when_nothing_staged(self) -> None:
        """Test that empty list is returned when nothing is staged.

        Given a git repo with no staged files, when get_staged_paths is called,
        then it returns an empty list.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_staged_paths("/path/to/repo")

            assert result == []

    def test_get_staged_paths_ignores_modified_not_staged(self) -> None:
        """Test that modified but unstaged files are ignored.

        Given a git repo with modified but unstaged files, when get_staged_paths is called,
        then those files are not returned.

        In porcelain format, " M file" means modified in working tree but NOT staged
        (index position is space). Only files where index position is not space are staged.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain"],
            returncode=0,
            stdout=" M path/to/modified.FCStd\n?? untracked.FCStd\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_staged_paths("/path/to/repo")

            # " M" means modified but NOT staged (index is space)
            # "??" means untracked (not staged)
            # Both should be filtered out
            assert result == []

    def test_get_staged_paths_handles_mixed_staged_and_unstaged(self) -> None:
        """Test handling of mixed staged and unstaged files.

        Given a mix of staged and unstaged files, only staged .FCStd files should be returned.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain"],
            returncode=0,
            stdout="M  staged.FCStd\n M modified.FCStd\nA  added.FCStd\n?? new.FCStd\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_staged_paths("/path/to/repo")

            # "M " and "A " are staged, " M" and "??" are not
            assert result == ["staged.FCStd", "added.FCStd"]

    def test_get_staged_paths_decodes_git_quoted_paths(self) -> None:
        """Test that git-quoted staged paths are decoded before filtering."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain"],
            returncode=0,
            stdout='A  "path/with spaces/document.FCStd"\nA  "notes file.txt"\n',
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_staged_paths("/path/to/repo")

            assert result == ["path/with spaces/document.FCStd"]

    def test_get_staged_paths_handles_z_renamed_fcstd_target(self) -> None:
        """Given status -z rename output, returns renamed FCStd target path."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain", "-z"],
            returncode=0,
            stdout="R  new/path/document.FCStd\x00old/path/document.FCStd\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_staged_paths("/path/to/repo")

            assert result == ["new/path/document.FCStd"]

    def test_get_staged_paths_preserves_z_leading_path_space(self) -> None:
        """Given status -z raw paths, leading spaces are preserved."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain", "-z"],
            returncode=0,
            stdout="A   leading.FCStd\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_staged_paths("/path/to/repo")

            assert result == [" leading.FCStd"]

    def test_get_staged_paths_handles_z_path_with_newline(self) -> None:
        """Given status -z raw paths, embedded newlines are preserved."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain", "-z"],
            returncode=0,
            stdout="A  path/with\nnewline.FCStd\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_staged_paths("/path/to/repo")

            assert result == ["path/with\nnewline.FCStd"]

    @pytest.mark.parametrize(
        ("side_effect",),
        [
            (subprocess.TimeoutExpired(cmd="git", timeout=30),),
            (FileNotFoundError("git"),),
        ],
    )
    def test_get_staged_paths_handles_errors(self, side_effect: Exception) -> None:
        """Test timeout and git-not-found return empty list."""
        with patch.object(subprocess, "run", side_effect=side_effect):
            result = self.adapter.get_staged_paths("/path/to/repo")

            assert result == []

    def test_get_staged_paths_non_zero_exit_code(self) -> None:
        """Test handling of non-zero exit code from git."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain"],
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_staged_paths("/path/to/repo")

            assert result == []


class TestGitPortAdapterGetFileContents:
    """Tests for the get_file_contents method of GitPortAdapter."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.adapter = GitPortAdapter()
        self.adapter._git_executable = "git"

    def test_get_file_contents_from_index(self) -> None:
        """Test getting file contents from the index (staged version).

        Given a git repo with a staged file, when get_file_contents is called with commit=None,
        then it returns the file contents from the index.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "show", ":path/to/file.FCStd"],
            returncode=0,
            stdout="yaml content here\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            result = self.adapter.get_file_contents("/path/to/repo", None, "path/to/file.FCStd")

            mock_run.assert_called_once_with(
                ["git", "show", ":path/to/file.FCStd"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            assert result == "yaml content here\n"

    def test_get_file_contents_from_commit(self) -> None:
        """Test getting file contents from a specific commit.

        Given a git repo with a committed file, when get_file_contents is called with a valid commit hash,
        then it returns the file contents from that commit.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "show", "abc123:path/to/file.FCStd"],
            returncode=0,
            stdout="commit content here\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            result = self.adapter.get_file_contents("/path/to/repo", "abc123", "path/to/file.FCStd")

            mock_run.assert_called_once_with(
                ["git", "show", "abc123:path/to/file.FCStd"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            assert result == "commit content here\n"

    def test_get_file_contents_returns_none_for_nonexistent_file(self) -> None:
        """Test that None is returned for nonexistent file.

        Given a valid git repo, when get_file_contents is called for a nonexistent file,
        then it returns None.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "show", ":nonexistent.FCStd"],
            returncode=128,
            stdout="",
            stderr="fatal: path 'nonexistent.FCStd' does not exist in index",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_file_contents("/path/to/repo", None, "nonexistent.FCStd")

            assert result is None

    def test_get_file_contents_returns_none_for_invalid_commit(self) -> None:
        """Test that None is returned for invalid commit.

        Given a valid git repo, when get_file_contents is called with an invalid commit,
        then it returns None.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "show", "invalid_commit:path/to/file.FCStd"],
            returncode=128,
            stdout="",
            stderr="fatal: Invalid revision name",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_file_contents("/path/to/repo", "invalid_commit", "path/to/file.FCStd")

            assert result is None

    @pytest.mark.parametrize(
        ("side_effect",),
        [
            (subprocess.TimeoutExpired(cmd="git", timeout=30),),
            (FileNotFoundError("git"),),
        ],
    )
    def test_get_file_contents_handles_errors(self, side_effect: Exception) -> None:
        """Test timeout and git-not-found return None."""
        with patch.object(subprocess, "run", side_effect=side_effect):
            result = self.adapter.get_file_contents("/path/to/repo", None, "path/to/file.FCStd")

            assert result is None

    def test_get_file_contents_with_head_commit(self) -> None:
        """Test getting file contents from HEAD commit."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "show", "HEAD:path/to/file.FCStd"],
            returncode=0,
            stdout="head content\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_file_contents("/path/to/repo", "HEAD", "path/to/file.FCStd")

            assert result == "head content\n"
