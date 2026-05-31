# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Fake GitPort implementation for testing git repository detection
# and commit retrieval. This provides an in-memory simulation of git operations
# without requiring actual git repositories or subprocess calls.
"""Fake GitPort implementation for testing."""

import os
from datetime import datetime
from pathlib import Path

from freecad.history_wb.domain.git.models import DirtyFile, GitCommit, GitIdentity


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

    def __init__(
        self,
        fail_stage: bool = False,
        fail_commit: bool = False,
        fail_init: bool = False,
        fail_unstage: bool = False,
    ) -> None:
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
        # Flag to simulate git init failures
        self._fail_init = fail_init
        self._fail_unstage = fail_unstage
        # Staged paths for get_staged_paths
        self._staged_paths: list[str] = []
        self._dirty_files: list[DirtyFile] = []
        # File contents mapping: (commit, git_path) -> content
        self._file_contents: dict[tuple[str | None, str], str] = {}
        self._file_bytes: dict[tuple[str | None, str], bytes] = {}
        # Existing files mapping: (commit, git_path) -> exists
        self._file_exists: dict[tuple[str | None, str], bool] = {}
        self._resolved_refs: dict[str, str] = {}
        # Tracks the last commit() call for argument verification
        self._last_commit_call: tuple[str, str] | None = None
        # Maps (git_root, commit) tuples to lists of FCStd file paths
        self._committed_files: dict[tuple[str, str], list[str]] = {}
        # Tracks last initialize_repository path call
        self._last_init_path: str | None = None
        self._identity: GitIdentity | None = None
        self._last_save_identity_call: tuple[str, GitIdentity, bool] | None = None
        self._can_write_global_identity = True
        self._last_unstage_files_call: tuple[str, list[str]] | None = None
        self._last_unstage_all_call: str | None = None
        self._last_restore_call: tuple[str, str | None, list[str]] | None = None
        self._all_fcstd_paths: dict[tuple[str, str | None], list[str]] = {}
        self._current_saved_fcstd_paths: dict[str, list[str]] = {}
        self._last_stage_files_call: tuple[str, list[str]] | None = None

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

    def get_commits(self, path: str, limit: int = 20, skip: int = 0) -> list[GitCommit]:
        """Get recent commits from the fake git repository.

        This implementation returns the configured commits sorted by timestamp
        in DESC order (newest first), limited by the specified limit parameter.

        Args:
            path: Starting path (file or directory) to check.
            limit: Maximum number of commits to return (default 20).
            skip: Number of newest commits to skip before returning results.

        Returns:
            List of GitCommit objects sorted by timestamp in DESC order (newest first).
        """
        # Find the git root for this path
        git_root = self.find_top_level_git_path(path)

        if git_root is None or git_root not in self._commits:
            return []

        # Get all commits for this repository
        all_commits = self._commits[git_root]

        # Sort by timestamp in DESC order (newest first), apply skip then limit
        sorted_commits = sorted(all_commits, key=lambda c: c.timestamp, reverse=True)
        return sorted_commits[skip : skip + limit]

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
        self._last_stage_files_call = (git_root, paths)
        return not self._fail_stage

    def get_dirty_files(self, git_root: str) -> list[DirtyFile]:
        """Fake implementation of get_dirty_files for testing.

        This fake implementation returns an empty list by default. Tests can
        override this behavior by subclassing or using a different fake.

        Args:
            git_root: Absolute path to git repository root.

        Returns:
            Configured dirty files, or empty list (simulating a clean repository).
        """
        return self._dirty_files

    def set_dirty_files(self, files: list[DirtyFile]) -> None:
        """Set dirty files returned by get_dirty_files."""
        self._dirty_files = files

    def unstage_files(self, git_root: str, paths: list[str]) -> bool:
        """Fake implementation of unstage_files for testing."""
        self._last_unstage_files_call = (git_root, paths)
        return not self._fail_unstage

    def unstage_all(self, git_root: str) -> bool:
        """Fake implementation of unstage_all for testing."""
        self._last_unstage_all_call = git_root
        return not self._fail_unstage

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

    def file_exists(self, git_root: str, commit: str | None, git_path: str) -> bool:
        """Fake implementation of file_exists for testing."""
        key = (commit, git_path)
        if key in self._file_exists:
            return self._file_exists[key]
        return key in self._file_contents or key in self._file_bytes

    def write_file_from_ref(self, git_root: str, commit: str | None, git_path: str, destination: str) -> bool:
        """Write configured fake file bytes to destination path."""
        key = (commit, git_path)
        content = self._file_bytes.get(key)
        if content is None:
            text_content = self._file_contents.get(key)
            if text_content is None:
                return False
            content = text_content.encode("utf-8")
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(content)
        return True

    def restore_paths_from_ref(self, git_root: str, commit: str | None, paths: list[str]) -> bool:
        """Record restore call and succeed."""
        self._last_restore_call = (git_root, commit, paths)
        return True

    def get_all_fcstd_paths(self, git_root: str, commit: str | None) -> list[str]:
        """Return configured FCStd path set for source."""
        return self._all_fcstd_paths.get((git_root, commit), [])

    def get_current_saved_fcstd_paths(self, git_root: str) -> list[str]:
        """Return configured current saved FCStd paths."""
        return self._current_saved_fcstd_paths.get(git_root, [])

    def set_all_fcstd_paths(self, root_path: str, commit: str | None, paths: list[str]) -> None:
        """Set FCStd path set returned for commit/index source."""
        self._all_fcstd_paths[(root_path, commit)] = paths

    def set_current_saved_fcstd_paths(self, root_path: str, paths: list[str]) -> None:
        """Set FCStd paths returned for current saved history set."""
        self._current_saved_fcstd_paths[root_path] = paths

    def get_last_restore_call(self) -> tuple[str, str | None, list[str]] | None:
        """Return last restore_paths_from_ref call args."""
        return self._last_restore_call

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

    def set_staged_paths(self, paths: list[str]) -> None:
        """Set the staged paths returned by get_staged_paths.

        Args:
            paths: List of relative file paths to return as staged.
        """
        self._staged_paths = paths

    def set_file_contents(self, commit: str | None, git_path: str, content: str) -> None:
        """Set file contents for a specific commit and path.

        Args:
            commit: Commit reference or None for index.
            git_path: Relative path within repository.
            content: File content string to return.
        """
        self._file_contents[(commit, git_path)] = content

    def set_file_bytes(self, commit: str | None, git_path: str, content: bytes) -> None:
        """Set binary file contents for a specific commit and path."""
        self._file_bytes[(commit, git_path)] = content

    def set_resolved_ref(self, ref: str, resolved_hash: str) -> None:
        """Set resolved commit hash for a ref."""
        self._resolved_refs[ref] = resolved_hash

    def resolve_ref(self, git_root: str, ref: str) -> str | None:
        """Resolve fake git ref to configured full hash or None if not configured."""
        return self._resolved_refs.get(ref)

    def get_last_commit_call(self) -> tuple[str, str] | None:
        """Get the arguments from the last commit() call.

        Returns:
            Tuple of (git_root, message) from the last commit() call, or None if not called.
        """
        return self._last_commit_call

    def get_last_unstage_files_call(self) -> tuple[str, list[str]] | None:
        """Return last unstage_files call args."""
        return self._last_unstage_files_call

    def get_last_unstage_all_call(self) -> str | None:
        """Return last unstage_all call arg."""
        return self._last_unstage_all_call

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

    def initialize_repository(self, path: str) -> bool:
        """Initialize a fake git repository at path."""
        self._last_init_path = path
        if self._fail_init or not path:
            return False
        self.add_git_repo(path)
        return True

    def get_last_init_path(self) -> str | None:
        """Return last path passed to initialize_repository."""
        return self._last_init_path

    def get_identity(self, git_root: str) -> GitIdentity | None:
        """Return configured fake git identity."""
        return self._identity

    def save_identity(self, git_root: str, identity: GitIdentity, should_save_globally: bool) -> bool:
        """Save fake git identity."""
        self._last_save_identity_call = (git_root, identity, should_save_globally)
        self._identity = identity
        return True

    def set_can_write_global_identity(self, can_write: bool) -> None:
        """Set global git identity writability result."""
        self._can_write_global_identity = can_write

    def can_write_global_identity(self) -> bool:
        """Return configured fake global git identity writability."""
        return self._can_write_global_identity

    def reset_file_bytes(self) -> None:
        """Clear all configured file bytes."""
        self._file_bytes.clear()
