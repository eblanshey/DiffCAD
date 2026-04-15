# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the GitPortAdapter class that implements
# the GitPort protocol using git CLI via subprocess. It handles git repository
# detection by running 'git rev-parse --show-toplevel' and returning the root path
# or None if the path is not in a git repository.
"""GitPort adapter implementation using git CLI."""

import os
import subprocess

from freecad.diff_wb.domain.git.ports import GitPort


class GitPortAdapter(GitPort):
    """Adapter that implements GitPort protocol using git CLI.

    This class provides a concrete implementation of the GitPort protocol
    by invoking git commands via subprocess. It is responsible for detecting
    whether a given path is within a git repository and returning the root
    path of that repository.

    Attributes:
        No public attributes.
    """

    def find_top_level_git_path(self, path: str) -> str | None:
        """Find git root using git CLI.

        Uses 'git rev-parse --show-toplevel' to find the root of the git
        repository containing the given path. Returns None if the path is
        not within a git repository or if git is unavailable.

        Args:
            path: The path (file or directory) to check for git repository.

        Returns:
            Absolute path to git root as string if path is in a git repo,
            or None if not in a git repo or if an error occurred.
        """
        # Normalize path: if path is a file, use its parent directory as cwd
        cwd_path = path
        if path and os.path.isfile(path):
            cwd_path = os.path.dirname(path)

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=cwd_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError, OSError):
            return None
