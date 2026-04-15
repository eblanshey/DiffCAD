# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains the GitRepository frozen dataclass which
# represents a git repository with its name (directory name) and absolute path.
# It is a core domain model with no external dependencies.
"""Git domain models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GitRepository:
    """A git repository representation.

    This immutable dataclass represents a git repository with its name
    (the directory name of the git root) and its absolute path.

    Attributes:
        name: Directory name of git root (e.g., "my_project")
        absolute_path: Absolute path to git root (e.g., "/home/user/my_project")
    """

    name: str
    absolute_path: str

    def __str__(self) -> str:
        """Return a string representation of the repository.

        Returns:
            String in format "name (absolute_path)"
        """
        return f"{self.name} ({self.absolute_path})"
