# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Fake GitPort implementation for testing git repository detection
# and commit retrieval. This provides an in-memory simulation of git operations
# without requiring actual git repositories or subprocess calls.
"""Fake GitPort implementation for testing."""

import os
from datetime import datetime

from freecad.diff_wb.domain.git.models import GitCommit


class FakeGitPort:
    """Fake implementation of GitPort for testing purposes.

    This fake implementation simulates git repository detection and commit retrieval
    without requiring actual git repositories or subprocess calls. It uses an
    in-memory mapping of paths to their git roots and commits.

    Attributes:
        _git_roots: Dictionary mapping paths to their git root paths.
        _commits: Dictionary mapping repo paths to lists of GitCommit objects.
        _staged_paths: List of staged paths for get_staged_paths.
        _file_contents: Mapping of (commit, git_path) to file contents.
        _last_commit_call: Tuple of (git_root, message) from the last commit() call, or None.
        _committed_files: Mapping of (git_root, commit) tuples to lists of FCStd file paths.
    """

    def __init__(self, fail_stage: bool = False, fail_commit: bool = False) -> None:
        """Initialize the fake git port with empty mappings.

        Args:
            fail_stage: If True, stage_files will return False (for testing failure cases).
            fail_commit: If True, commit will return False (for testing failure cases).
        """
        # Maps paths to their git root paths
        self._git_roots: dict[str, str] = {}
        # Maps git root paths to lists of commits
        self._commits: dict[str, list[GitCommit]] = {}
        # Flag to simulate staging failures
        self._fail_stage = fail_stage
        # Flag to simulate commit failures
        self._fail_commit = fail_commit
        # Staged paths for get_staged_paths
        self._staged_paths: list[str] = []
        # File contents mapping: (commit, git_path) -> content
        self._file_contents: dict[tuple[str | None, str], str] = {}
        # Tracks the last commit() call for argument verification
        self._last_commit_call: tuple[str, str] | None = None
        # Maps (git_root, commit) tuples to lists of FCStd file paths
        self._committed_files: dict[tuple[str, str], list[str]] = {}

    def add_git_repo(self, root_path: str) -> None:
        """Add a simulated git repository root.

        Args:
            root_path: The absolute path to the git repository root.
        """
        self._git_roots[root_path] = root_path
        # Initialize empty commit list for this repo
        self._commits[root_path] = []

    def add_commit(
        self,
        root_path: str,
        commit_id: str,
        message: str,
        author: str,
        timestamp: str | datetime,
    ) -> None:
        """Add a simulated commit to a repository.

        Commits are added in order (oldest first). The get_commits method
        will return them in DESC order (newest first).

        Args:
            root_path: The absolute path to the git repository root.
            commit_id: The commit hash.
            message: The commit message.
            author: The author name.
            timestamp: ISO format timestamp string or datetime instance.
        """
        if root_path not in self._commits:
            self._commits[root_path] = []

        # Convert string timestamp to datetime if needed
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        commit = GitCommit(
            id=commit_id,
            message=message,
            author=author,
            timestamp=timestamp,
        )
        self._commits[root_path].append(commit)

    def set_commits(self, root_path: str, commits: list[GitCommit]) -> None:
        """Set commits for a simulated git repository.

        Args:
            root_path: The absolute path to the git repository root.
            commits: List of GitCommit objects to return for this repo.
        """
        self._commits[root_path] = commits

    def find_top_level_git_path(self, path: str) -> str | None:
        """Find git root by checking if path is within a known git repo.

        This implementation checks if the given path or any of its parent
        directories match a known git root.

        Args:
            path: Starting path (file or directory) to check.

        Returns:
            Absolute path to git root as string if path is in a known git repo,
            or None if not in a known git repo.
        """
        # Normalize the path
        normalized_path = path.rstrip("/")

        # Check if the path itself is a git root
        if normalized_path in self._git_roots:
            return self._git_roots[normalized_path]

        # Traverse up the directory tree to find a git root
        current_path = normalized_path
        while True:
            # Get parent directory
            parent_path = "/".join(current_path.split("/")[:-1])

            # If we've reached the root, stop searching
            if parent_path == "" or parent_path == "/":
                # Check root explicitly
                if "/" in self._git_roots:
                    return self._git_roots["/"]
                break

            # Check if parent is a git root
            if parent_path in self._git_roots:
                return self._git_roots[parent_path]

            current_path = parent_path

        return None

    def get_commits(self, path: str, limit: int = 20) -> list[GitCommit]:
        """Get recent commits from the fake git repository.

        This implementation returns the configured commits sorted by timestamp
        in DESC order (newest first), limited by the specified limit parameter.

        Args:
            path: Starting path (file or directory) to check.
            limit: Maximum number of commits to return (default 20).

        Returns:
            List of GitCommit objects sorted by timestamp in DESC order (newest first).
        """
        # Find the git root for this path
        git_root = self.find_top_level_git_path(path)

        if git_root is None or git_root not in self._commits:
            return []

        # Get all commits for this repository
        all_commits = self._commits[git_root]

        # Sort by timestamp in DESC order (newest first) and apply the limit
        sorted_commits = sorted(all_commits, key=lambda c: c.timestamp, reverse=True)
        return sorted_commits[:limit]

    def is_path_in_repository(self, git_root: str, path: str) -> bool:
        """Check if a path is within the git repository.

        This implementation normalizes both paths and checks if the given path
        starts with the git repository root path.

        Args:
            git_root: Absolute path to git repository root.
            path: Path to check (file or directory).

        Returns:
            True if path is within git_root, False otherwise.
        """
        if not git_root or not path:
            return False

        # Normalize paths to handle different separators and relative components
        normalized_git_root = os.path.normpath(git_root).rstrip(os.sep)
        normalized_path = os.path.normpath(path)

        # Check if path starts with git_root
        # We need to ensure we're matching at a directory boundary
        if normalized_path == normalized_git_root:
            return True

        # Check if path is a subdirectory/file within git_root
        return normalized_path.startswith(normalized_git_root + os.sep)

    def stage_files(self, git_root: str, paths: list[str]) -> bool:
        """Fake implementation of stage_files for testing.

        This fake implementation returns True by default, or False if configured
        to fail (via fail_stage parameter in __init__).

        Args:
            git_root: Absolute path to git repository root.
            paths: List of relative paths to stage.

        Returns:
            True if not configured to fail, False otherwise.
        """
        return not self._fail_stage

    def get_dirty_paths(self, git_root: str) -> list[str]:
        """Fake implementation of get_dirty_paths for testing.

        This fake implementation returns an empty list by default. Tests can
        override this behavior by subclassing or using a different fake.

        Args:
            git_root: Absolute path to git repository root.

        Returns:
            Empty list (simulating a clean repository).
        """
        return []

    def get_staged_paths(self, git_root: str) -> list[str]:
        """Fake implementation of get_staged_paths for testing.

        Args:
            git_root: Absolute path to git repository root.

        Returns:
            List of staged paths configured via _staged_paths.
        """
        return self._staged_paths

    def get_file_contents(self, git_root: str, commit: str | None, git_path: str) -> str | None:
        """Fake implementation of get_file_contents for testing.

        Args:
            git_root: Absolute path to git repository root.
            commit: Commit reference or None for index.
            git_path: Relative path within repository.

        Returns:
            File contents if configured, None otherwise.
        """
        key = (commit, git_path)
        if key in self._file_contents:
            return self._file_contents[key]
        return None

    def commit(self, git_root: str, message: str) -> bool:
        """Fake implementation of commit for testing.

        This fake implementation returns True by default, or False if configured
        to fail (via fail_commit parameter in __init__). Tracks the last call
        arguments in _last_commit_call for test verification.

        Args:
            git_root: Absolute path to git repository root.
            message: Commit message text.

        Returns:
            True if not configured to fail, False otherwise.
        """
        self._last_commit_call = (git_root, message)
        return not self._fail_commit

    def set_committed_files(self, root_path: str, commit: str, paths: list[str]) -> None:
        """Set committed file paths for a specific commit in a repo.

        Args:
            root_path: The absolute path to the git repository root.
            commit: The commit reference (hash, "HEAD", etc.).
            paths: List of relative FCStd file paths changed in the commit.
        """
        self._committed_files[(root_path, commit)] = paths

    def get_committed_files(self, git_root: str, commit: str) -> list[str]:
        """Get FCStd file paths changed in a specific commit.

        Args:
            git_root: Absolute path to git repository root.
            commit: Commit reference (hash, "HEAD", "HEAD~1", etc.)

        Returns:
            List of relative paths (from git root) of .FCStd files changed in the commit.
            Empty list if no FCStd files changed or not configured.
        """
        return self._committed_files.get((git_root, commit), [])
