# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module defines the GitPort protocol interface for git
# repository operations. It provides a contract for git port implementations that
# can be used by the domain layer without coupling to specific infrastructure.
# The protocol has no external dependencies beyond the standard library.
"""Git domain ports (protocol interfaces)."""

from typing import Protocol


class GitPort(Protocol):
    """Protocol defining the interface for git repository operations.

    This protocol specifies the contract that any git port implementation must follow.
    It allows the domain layer to interact with git functionality without depending
    on specific implementations, enabling dependency injection and testability.

    Attributes:
        find_top_level_path: Method to find the git root path from a given path.
    """

    def find_top_level_git_path(self, path: str) -> str | None:
        """Find git root by traversing up from path.

        This method determines if a given path is within a git repository and,
        if so, returns the absolute path to the repository root.

        Args:
            path: Starting path (file or directory) to check.

        Returns:
            Absolute path to git root as string if path is in a git repo,
            or None if not in a git repo.
        """
        ...
