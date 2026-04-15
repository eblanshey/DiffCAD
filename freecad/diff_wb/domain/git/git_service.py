# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the GitService class which combines
# GitPort interface with GitRepository model creation. It is responsible for
# providing a convenient method to get GitRepository objects from file or
# directory paths using dependency injection. It has no external dependencies.
"""Git domain service."""

import os

from .models import GitRepository
from .ports import GitPort


class GitService:
    """Service for git repository operations.

    This class provides a high-level interface for working with git repositories.
    It uses a GitPort for low-level git operations and creates GitRepository
    objects from the results.

    Attributes:
        _git_port: The GitPort instance used for git operations.
    """

    def __init__(self, git_port: GitPort) -> None:
        """Initialize the GitService with a GitPort.

        Args:
            git_port: The GitPort implementation to use for git operations.
        """
        self._git_port = git_port

    def get_repository(self, path: str) -> GitRepository | None:
        """Get GitRepository for path.

        This method determines if a given path is within a git repository and,
        if so, returns a GitRepository object representing that repository.

        Args:
            path: File or directory path to check.

        Returns:
            GitRepository if path is in a git repo, None otherwise.
        """
        git_root = self._git_port.find_top_level_git_path(path)
        if git_root is None:
            return None
        name = os.path.basename(git_root)
        return GitRepository(name=name, absolute_path=git_root)
