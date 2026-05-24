# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains git domain dataclasses that represent
# repositories, identities, initialization candidates, and commits. These are core domain
# models with no external dependencies.
"""Git domain models."""

from dataclasses import dataclass
from datetime import datetime


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


@dataclass(frozen=True)
class GitCommit:
    """A git commit representation.

    This immutable dataclass represents a git commit with its id, message,
    author, and timestamp.

    Attributes:
        id: The commit hash (full hash, caller can truncate for display)
        message: Full commit message (subject + body)
        author: Author name
        timestamp: datetime instance representing commit time
    """

    id: str
    message: str  # Full message, not just subject line
    author: str
    timestamp: datetime  # datetime instance

    def __str__(self) -> str:
        """Return a string representation of the commit.

        Returns:
            String in format "id | author | timestamp | message"
        """
        return f"{self.id} | {self.author} | {self.timestamp.isoformat()} | {self.message}"


@dataclass(frozen=True)
class GitIdentity:
    """Git author identity used when creating commits."""

    name: str
    email: str


@dataclass(frozen=True)
class GitRepositoryInitCandidate:
    """Directory candidate for repository initialization.

    Attributes:
        path: Absolute directory path to display/select.
        is_available: True when this directory can be initialized.
        existing_repository_path: Existing repository root that contains path.
    """

    path: str
    is_available: bool
    existing_repository_path: str | None = None
