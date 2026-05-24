# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GitPortAdapter.get_dirty_paths method.
# This module verifies that get_dirty_paths correctly identifies modified and
# untracked files while filtering out staged-only, deleted, and other change types.
"""Unit tests for GitPortAdapter.get_dirty_paths."""

import subprocess
from unittest.mock import patch

import pytest
from freecad.history_wb.infrastructure.git.git_port_adapter import GitPortAdapter


def test_get_dirty_paths_returns_modified_and_untracked():
    """Given modified and untracked files in git status output, returns their paths."""
    # Git porcelain format: "<index_status><wt_status> <path>"
    # " M" = modified in working tree (not yet staged)
    # "??" = untracked file
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=0,
        stdout=" M src/file.py\n?? new.txt\n",
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")

        assert set(result) == {"src/file.py", "new.txt"}


def test_get_dirty_paths_empty_for_clean_repo():
    """Given empty git status output (clean repo), returns empty list."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=0,
        stdout="",
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")

        assert result == []


def test_get_dirty_paths_filters_staged_only_changes():
    """Given staged-only changes (A without M), they should NOT be included."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=0,
        stdout="A staged_file.py\n",
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")

        assert result == []  # Staged-only not considered dirty


def test_get_dirty_paths_filters_deleted_files():
    """Given deleted files (D), they should NOT be included."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=0,
        stdout="D deleted_file.py\n",
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")

        assert result == []  # Deleted not considered dirty


def test_get_dirty_paths_handles_git_error():
    """Given git command failure, returns empty list."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=128,
        stdout="",
        stderr="fatal: not a git repository",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/not/a/repo")

        assert result == []


@pytest.mark.parametrize(
    ("side_effect",),
    [
        (subprocess.TimeoutExpired(cmd="git", timeout=30),),
        (OSError("bad cwd"),),
    ],
)
def test_get_dirty_paths_handles_errors(side_effect: Exception):
    """Given timeout or OS error, returns empty list."""
    with patch.object(subprocess, "run", side_effect=side_effect):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")

        assert result == []


def test_get_dirty_paths_handles_filenames_with_spaces():
    """Given filenames with spaces, correctly extracts the full path."""
    # Git porcelain format: "<index_status><wt_status> <path>"
    # " M" = modified in working tree (not yet staged)
    # "??" = untracked file
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=0,
        stdout=" M path/with spaces/file.txt\n?? new file.txt\n",
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")

        assert set(result) == {"path/with spaces/file.txt", "new file.txt"}


def test_get_dirty_paths_handles_git_quoted_paths_with_spaces():
    """Given git-quoted paths, returns unquoted relative paths."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=0,
        stdout=' M "path/with spaces/file.txt"\n?? "new file.txt"\n',
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")

        assert set(result) == {"path/with spaces/file.txt", "new file.txt"}


def test_get_dirty_paths_handles_mixed_status_codes():
    """Given mixed index/working tree status codes (e.g., MM), includes only dirty ones."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=0,
        stdout="MM modified_twice.py\nM  staged_only.py\n M unstaged_modified.py\n?? untracked.txt\n",
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")

        # Only files with working tree changes should be dirty:
        # - MM: both staged AND modified in WT (dirty)
        # - M : staged only, no WT changes (NOT dirty)
        # -  M: modified in WT but not staged (dirty)
        # - ??: untracked (dirty)
        assert set(result) == {"modified_twice.py", "unstaged_modified.py", "untracked.txt"}


def test_get_dirty_paths_handles_z_paths_with_newlines():
    """Given NUL-delimited porcelain output, embedded newlines are preserved."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain", "-z"],
        returncode=0,
        stdout=" M path/with\nnewline.FCStd\x00?? new\nfile.FCStd\x00",
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")

        assert set(result) == {"path/with\nnewline.FCStd", "new\nfile.FCStd"}


def test_get_dirty_paths_preserves_z_path_spaces():
    """Given NUL-delimited porcelain output, raw path spaces are preserved."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain", "-z"],
        returncode=0,
        stdout=" M  leading and trailing .FCStd \x00",
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")

        assert result == [" leading and trailing .FCStd "]
