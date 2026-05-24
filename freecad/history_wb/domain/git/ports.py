# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module defines the GitPort protocol interface for git
# repository operations. It provides a contract for git port implementations that
# can be used by the domain layer without coupling to specific implementations.
# The protocol supports repository detection, commit listing, file staging, commit
# creation, and committed file path queries. The protocol has no external dependencies
# beyond the standard library.
"""Git domain ports (protocol interfaces)."""

from typing import Protocol

from freecad.history_wb.domain.git.models import GitCommit, GitIdentity


__all__ = ["GitPort"]


class GitPort(Protocol):
    """Protocol defining the interface for git repository operations.

    This protocol specifies the contract that any git port implementation must follow.
    It allows the domain layer to interact with git functionality without depending
    on specific implementations, enabling dependency injection and testability.

    Attributes:
        find_top_level_path: Method to find the git root path from a given path.
        get_commits: Method to get recent commits from a git repository.
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

    def get_commits(self, path: str, limit: int = 20, skip: int = 0) -> list[GitCommit]:
        """Get recent commits from git repository.

        Args:
            path: Absolute path to git repository root.
            limit: Maximum number of commits to return (default 20 for MVP).
            skip: Number of newest commits to skip before returning results.

        Returns:
            List of GitCommit objects in DESC order (newest first).
        """
        ...

    def is_path_in_repository(self, git_root: str, path: str) -> bool:
        """Check if a path is within the git repository.

        This method normalizes both paths to handle different path separators
        and relative components (like .. and .), then checks if the given path
        starts with the git repository root path at a directory boundary.

        Args:
            git_root: Absolute path to git repository root.
            path: Path to check (file or directory).

        Returns:
            True if path is within git_root (including the root itself),
            False otherwise (including empty paths).
        """
        ...

    def stage_files(self, git_root: str, paths: list[str]) -> bool:
        """Stage files in the git repository.

        Args:
            git_root: Absolute path to git repository root.
            paths: List of relative paths (from git root) to stage.

        Returns:
            True if staging succeeded, False otherwise.
        """
        ...

    def get_dirty_paths(self, git_root: str) -> list[str]:
        """Get list of dirty file paths (modified or untracked).

        This method runs `git status --porcelain` and filters for files that are
        modified in the working tree or untracked. These are the only files that
        can be staged via `git add`.

        Args:
            git_root: Absolute path to git repository root.

        Returns:
            List of relative paths (from git root) that are modified or untracked.
            Empty list if repo is clean or not a git repo.
        """
        ...

    def get_staged_paths(self, git_root: str) -> list[str]:
        """Get list of staged file paths (relative from git root).

        Filters for FCStd files only (files with .FCStd extension).

        Args:
            git_root: Absolute path to git repository root.

        Returns:
            List of relative paths (from git root) that are staged.
            Empty list if no FCStd files are staged or not a git repo.
        """
        ...

    def get_file_contents(self, git_root: str, commit: str | None, git_path: str) -> str | None:
        """Get file contents from git at a specific commit or index.

        Uses `git show` command to retrieve file contents.
        If commit is None, retrieves from the index (staged version).

        Args:
            git_root: Absolute path to git repository root.
            commit: Commit reference (hash, "HEAD", "HEAD~2", etc.) or None for index.
            git_path: Relative path of the file within the repository.

        Returns:
            File contents as string, or None if file doesn't exist or error.
        """
        ...

    def write_file_from_ref(self, git_root: str, commit: str | None, git_path: str, destination: str) -> bool:
        """Write file bytes from git ref/index to destination path.

        Args:
            git_root: Absolute path to git repository root.
            commit: Commit reference or None for index.
            git_path: Relative path within repository.
            destination: Absolute output file path.

        Returns:
            True if write succeeded, False otherwise.
        """
        ...

    def resolve_ref(self, git_root: str, ref: str) -> str | None:
        """Resolve git ref to full commit hash.

        Args:
            git_root: Absolute path to git repository root.
            ref: Commit reference such as HEAD, a hash, or HEAD~1.

        Returns:
            Full commit hash if ref resolves to a commit, None otherwise.
        """
        ...

    def file_exists(self, git_root: str, commit: str | None, git_path: str) -> bool:
        """Check whether a file path exists at commit or index.

        Args:
            git_root: Absolute path to git repository root.
            commit: Commit reference or None for index.
            git_path: Relative path within repository.

        Returns:
            True if the path exists at given ref/index, False otherwise.
        """
        ...

    def commit(self, git_root: str, message: str) -> bool:
        """Commit staged changes in the git repository.

        Args:
            git_root: Absolute path to git repository root.
            message: Commit message text.

        Returns:
            True if commit succeeded, False otherwise.
        """
        ...

    def get_identity(self, git_root: str) -> GitIdentity | None:
        """Get configured git author identity for repository context.

        Args:
            git_root: Absolute path to git repository root.

        Returns:
            GitIdentity if both name and email are configured, None otherwise.
        """
        ...

    def save_identity(self, git_root: str, identity: GitIdentity, should_save_globally: bool) -> bool:
        """Save git author identity locally or globally.

        Args:
            git_root: Absolute path to git repository root.
            identity: Git identity to save.
            should_save_globally: True for global config, False for local repo config.

        Returns:
            True if identity was saved, False otherwise.
        """
        ...

    def can_write_global_identity(self) -> bool:
        """Return whether global git identity config can be written.

        Returns:
            True if global git config is writable, False otherwise.
        """
        ...

    def get_committed_files(self, git_root: str, commit: str) -> list[str]:
        """Get list of FCStd file paths changed in a specific commit.

        Args:
            git_root: Absolute path to git repository root.
            commit: Commit reference (hash, "HEAD", "HEAD~1", etc.)

        Returns:
            List of relative paths (from git root) of .FCStd files changed in the commit.
            Empty list if no FCStd files changed or error occurred.
        """
        ...

    def initialize_repository(self, path: str) -> bool:
        """Initialize a git repository in the given directory.

        Args:
            path: Absolute directory path where git init should run.

        Returns:
            True if initialization succeeded, False otherwise.
        """
        ...
