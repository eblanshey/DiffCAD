# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains unit tests for the GitPortAdapter.get_committed_files()
# method. Tests use subprocess mocking to verify git diff-tree output parsing without
# actual git commands, ensuring reliable and fast test execution.
"""Unit tests for GitPortAdapter.get_committed_files()."""

import subprocess
from unittest.mock import patch

import pytest
from freecad.history_wb.infrastructure.git import GitPortAdapter


class TestGitPortAdapterGetCommittedFiles:
    """Tests for the get_committed_files method of GitPortAdapter."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.adapter = GitPortAdapter()
        self.adapter._git_executable = "git"

    def test_get_committed_files_success(self) -> None:
        """Test successful parsing of git diff-tree output returning FCStd files.

        Given a valid git repo with FCStd files changed in a commit, when
        get_committed_files is called, then it returns the list of relative
        paths to those FCStd files.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-z", "-r", "abc123"],
            returncode=0,
            stdout="path/to/document.FCStd\x00path/to/another.FCStd\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            result = self.adapter.get_committed_files("/path/to/repo", "abc123")

            mock_run.assert_called_once_with(
                ["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-z", "-r", "abc123"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            assert result == ["path/to/document.FCStd", "path/to/another.FCStd"]

    def test_get_committed_files_filters_non_fcstd(self) -> None:
        """Test filtering: only .FCStd files returned.

        Given a git commit with mixed file types, when get_committed_files is called,
        then only .FCStd files are returned.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "abc123"],
            returncode=0,
            stdout="README.md\x00path/to/document.FCStd\x00src/main.py\x00path/to/model.FCStd\x00config.yaml\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_committed_files("/path/to/repo", "abc123")

            assert result == ["path/to/document.FCStd", "path/to/model.FCStd"]

    @pytest.mark.parametrize(
        "commit_ref",
        [
            "HEAD",
            "HEAD~1",
            "abc123def456",
            "abc123",
            "refs/heads/main",
        ],
    )
    def test_get_committed_files_various_commit_refs(self, commit_ref: str) -> None:
        """Test with HEAD, HEAD~1, short hash formats.

        Given various commit reference formats, when get_committed_files is called,
        then the correct command with the commit reference is passed to git.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit_ref],
            returncode=0,
            stdout="path/to/document.FCStd\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            result = self.adapter.get_committed_files("/path/to/repo", commit_ref)

            mock_run.assert_called_once_with(
                ["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-z", "-r", commit_ref],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            assert result == ["path/to/document.FCStd"]

    def test_get_committed_files_root_commit(self) -> None:
        """Test with --root flag for root commit.

        Given a root commit (first commit in repo), when get_committed_files is called,
        then all FCStd files in the root commit are returned (diff-tree with --root
        diff against empty tree).
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "root_hash"],
            returncode=0,
            stdout="initial.FCStd\x00project.FCStd\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_committed_files("/path/to/repo", "root_hash")

            assert result == ["initial.FCStd", "project.FCStd"]

    def test_get_committed_files_empty_result(self) -> None:
        """Test empty result when commit has no FCStd changes.

        Given a commit with only non-FCStd files, when get_committed_files is called,
        then an empty list is returned.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "abc123"],
            returncode=0,
            stdout="README.md\x00src/main.py\x00config.yaml\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_committed_files("/path/to/repo", "abc123")

            assert result == []

    def test_get_committed_files_empty_output(self) -> None:
        """Test empty output from git diff-tree.

        Given a commit with no files (empty output), when get_committed_files is called,
        then an empty list is returned.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "abc123"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_committed_files("/path/to/repo", "abc123")

            assert result == []

    @pytest.mark.parametrize(
        ("side_effect",),
        [
            (subprocess.TimeoutExpired(cmd="git", timeout=30),),
            (FileNotFoundError("git"),),
        ],
    )
    def test_get_committed_files_handles_errors(self, side_effect: Exception) -> None:
        """Test timeout and git-not-found return empty list."""
        with patch.object(subprocess, "run", side_effect=side_effect):
            result = self.adapter.get_committed_files("/path/to/repo", "abc123")

            assert result == []

    def test_get_committed_files_non_zero_exit_code(self) -> None:
        """Test non-zero exit code returns empty list."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "invalid"],
            returncode=128,
            stdout="",
            stderr="fatal: Not a valid commit name",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_committed_files("/path/to/repo", "invalid")

            assert result == []

    def test_get_committed_files_with_trailing_nuls(self) -> None:
        """Test handling of output with trailing NULs.

        Given git diff-tree output with trailing NULs, when get_committed_files
        is called, then empty lines are filtered out and only valid paths returned.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "abc123"],
            returncode=0,
            stdout="path/to/document.FCStd\x00path/to/another.FCStd\x00\x00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_committed_files("/path/to/repo", "abc123")

            assert result == ["path/to/document.FCStd", "path/to/another.FCStd"]

    def test_get_committed_files_handles_filename_with_newline(self) -> None:
        """Given NUL-delimited output, filenames containing newlines remain intact."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-z", "-r", "abc123"],
            returncode=0,
            stdout="path/with\nnewline.FCStd\x00README.md\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.get_committed_files("/path/to/repo", "abc123")

            assert result == ["path/with\nnewline.FCStd"]
