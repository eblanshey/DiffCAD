# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GitPortAdapter.get_dirty_files method.
# This module verifies dirty FCStd classification into DirtyFile records and
# filtering of staged-only and non-FCStd entries.
"""Unit tests for GitPortAdapter.get_dirty_files."""

import subprocess
from unittest.mock import patch

import pytest

from freecad.history_wb.domain.git.models import DirtyFile, DirtyFileStatus
from freecad.history_wb.infrastructure.git.git_port_adapter import GitPortAdapter


def test_get_dirty_files_returns_fcstd_modified_untracked_deleted() -> None:
    """Given mixed dirty files, returns FCStd DirtyFile records only."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain", "-z"],
        returncode=0,
        stdout=(" M doc.FCStd\x00?? new.FCStd\x00 D removed.FCStd\x00 M src/file.py\x00?? new.txt\x00"),
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_files("/path/to/repo")

    assert result == [
        DirtyFile(git_path="doc.FCStd", status=DirtyFileStatus.MODIFIED),
        DirtyFile(git_path="new.FCStd", status=DirtyFileStatus.ADDED),
        DirtyFile(git_path="removed.FCStd", status=DirtyFileStatus.DELETED),
    ]


def test_get_dirty_files_accepts_lowercase_fcstd_extension() -> None:
    """Lowercase .fcstd treated as FCStd file."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain", "-z"],
        returncode=0,
        stdout=" M lower.fcstd\x00",
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_files("/path/to/repo")

    assert result == [DirtyFile(git_path="lower.fcstd", status=DirtyFileStatus.MODIFIED)]


def test_get_dirty_files_empty_for_clean_repo() -> None:
    """Given empty git status output (clean repo), returns empty list."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain", "-z"],
        returncode=0,
        stdout="",
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_files("/path/to/repo")

    assert result == []


def test_get_dirty_files_filters_staged_only_changes() -> None:
    """Staged-only entries excluded when wt-status is blank."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain", "-z"],
        returncode=0,
        stdout="M  staged_only.FCStd\x00",
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_files("/path/to/repo")

    assert result == []


def test_get_dirty_files_handles_git_error() -> None:
    """Given git command failure, returns empty list."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain", "-z"],
        returncode=128,
        stdout="",
        stderr="fatal: not a git repository",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_files("/path/to/not/a/repo")

    assert result == []


@pytest.mark.parametrize(
    ("side_effect",),
    [
        (subprocess.TimeoutExpired(cmd="git", timeout=30),),
        (OSError("bad cwd"),),
    ],
)
def test_get_dirty_files_handles_errors(side_effect: Exception) -> None:
    """Given timeout or OS error, returns empty list."""
    with patch.object(subprocess, "run", side_effect=side_effect):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_files("/path/to/repo")

    assert result == []


def test_get_dirty_files_handles_mixed_status_codes() -> None:
    """Mixed index/working-tree status classify correctly."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain", "-z"],
        returncode=0,
        stdout=(
            "MM modified_twice.FCStd\x00"
            "M  staged_only.FCStd\x00"
            " M unstaged_modified.FCStd\x00"
            "?? untracked.FCStd\x00"
            " D deleted.FCStd\x00"
        ),
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_files("/path/to/repo")

    assert result == [
        DirtyFile(git_path="modified_twice.FCStd", status=DirtyFileStatus.MODIFIED),
        DirtyFile(git_path="unstaged_modified.FCStd", status=DirtyFileStatus.MODIFIED),
        DirtyFile(git_path="untracked.FCStd", status=DirtyFileStatus.ADDED),
        DirtyFile(git_path="deleted.FCStd", status=DirtyFileStatus.DELETED),
    ]


def test_get_dirty_files_handles_z_paths_with_newlines() -> None:
    """NUL-delimited paths preserve embedded newlines."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain", "-z"],
        returncode=0,
        stdout=" M path/with\nnewline.FCStd\x00?? new\nfile.FCStd\x00",
        stderr="",
    )

    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_files("/path/to/repo")

    assert result == [
        DirtyFile(git_path="path/with\nnewline.FCStd", status=DirtyFileStatus.MODIFIED),
        DirtyFile(git_path="new\nfile.FCStd", status=DirtyFileStatus.ADDED),
    ]
