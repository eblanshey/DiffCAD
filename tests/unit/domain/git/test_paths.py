# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for Git path normalization helpers.
"""Unit tests for Git path helpers."""

from unittest.mock import patch

import pytest
from freecad.history_wb.domain.git.paths import git_path_name, is_fcstd_path, relative_git_path, to_git_path


def test_to_git_path_normalizes_windows_separators() -> None:
    """Test Windows separators become Git POSIX separators."""
    assert to_git_path("assemblies\\sub\\Widget.FCStd") == "assemblies/sub/Widget.FCStd"


def test_relative_git_path_normalizes_os_relative_path() -> None:
    """Test relative paths are normalized after OS relpath computation."""
    with patch(
        "freecad.history_wb.domain.git.paths.relpath",
        lambda path, root: "assemblies\\sub\\Widget.FCStd",
    ):
        assert relative_git_path("C:\\repo\\assemblies\\sub\\Widget.FCStd", "C:\\repo") == "assemblies/sub/Widget.FCStd"


def test_git_path_name_handles_windows_and_trailing_separator() -> None:
    """Test final name extraction works for Windows-style paths."""
    assert git_path_name("C:\\repo\\project\\") == "project"


@pytest.mark.parametrize("path", ["part.FCStd", "part.fcstd", "part.FCSTD"])
def test_is_fcstd_path_is_case_insensitive(path: str) -> None:
    """Test FCStd extension matching works across case-insensitive filesystems."""
    assert is_fcstd_path(path) is True
