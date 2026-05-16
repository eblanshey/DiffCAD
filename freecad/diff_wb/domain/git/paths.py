# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Git path helpers that normalize repository-relative paths
# across operating systems while preserving Git's POSIX-style path convention.
"""Git path normalization helpers."""

from os.path import relpath
from pathlib import PurePosixPath


def to_git_path(path: str) -> str:
    """Convert OS path separators to Git's POSIX-style separators."""
    return path.replace("\\", "/")


def relative_git_path(path: str, root: str) -> str:
    """Return a repository-relative Git path for an OS filesystem path."""
    return to_git_path(relpath(path, root))


def git_path_name(path: str) -> str:
    """Return final path component from an OS or Git-style path."""
    return PurePosixPath(to_git_path(path).rstrip("/")).name


def is_fcstd_path(path: str) -> bool:
    """Return True when path has a FreeCAD document extension."""
    return path.lower().endswith(".fcstd")
