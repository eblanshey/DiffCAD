# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the GitPortAdapter class that implements
# the GitPort protocol using git CLI via subprocess. It handles git repository
# detection by running 'git rev-parse --show-toplevel' and returning the root path
# or None if the path is not in a git repository. It also retrieves recent commits
# using 'git log' with proper parsing of commit data.
"""GitPort adapter implementation using git CLI."""

import os
import subprocess
from datetime import datetime

from freecad.diff_wb.domain.git.models import GitCommit
from freecad.diff_wb.domain.git.ports import GitPort
from freecad.diff_wb.utils import Log


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

    def get_commits(self, path: str, limit: int = 20) -> list[GitCommit]:
        """Get recent commits using git CLI.

        Uses 'git log' with null-byte separators to handle multiline messages
        and special characters safely. Format uses %x00 (null byte) as delimiter:
        %H%x00%B%x00%an%x00%aI%x00
        - %H: full commit hash
        - %B: full message (subject + body)
        - %an: author name
        - %aI: author date in ISO 8601 format
        - %x00: null byte separator

        Returns commits in DESC order (newest first).

        Args:
            path: Absolute path to git repository root.
            limit: Maximum number of commits to return (default 20).

        Returns:
            List of GitCommit objects in DESC order (newest first).
        """
        # Normalize path: if path is a file, use its parent directory as cwd
        cwd_path = path
        if path and os.path.isfile(path):
            cwd_path = os.path.dirname(path)

        try:
            result = subprocess.run(
                ["git", "log", f"-n{limit}", "--format=%H%x00%B%x00%an%x00%aI%x00"],
                cwd=cwd_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                Log.warning(f"Git log failed with return code {result.returncode}: {result.stderr.strip()}")
                return []

            output = result.stdout.strip()
            if not output:
                return []

            # Split by null byte to get all fields
            # Each commit has 4 fields: hash, message, author, timestamp
            # The trailing %x00 after timestamp creates an extra empty element
            parts = output.split("\x00")

            commits = []
            # Process in groups of 4 (hash, message, author, timestamp)
            for i in range(0, len(parts) - 3, 4):
                commit_hash = parts[i]
                full_message = parts[i + 1]
                author = parts[i + 2]
                timestamp = parts[i + 3]

                if commit_hash:  # Skip empty entries
                    # Parse ISO format timestamp into datetime instance
                    timestamp_dt = datetime.fromisoformat(timestamp)
                    commits.append(
                        GitCommit(
                            id=commit_hash,
                            message=full_message,
                            author=author,
                            timestamp=timestamp_dt,
                        )
                    )

            return commits
        except subprocess.TimeoutExpired:
            Log.warning(f"Git log command timed out for path: {path}")
            return []
        except FileNotFoundError:
            Log.warning("Git command not found - git may not be installed or not in PATH")
            return []
        except (NotADirectoryError, OSError) as e:
            Log.warning(f"Git error for path {path}: {e}")
            return []

    def is_path_in_repository(self, git_root: str, path: str) -> bool:
        """Check if a path is within the git repository.

        This method normalizes both paths and checks if the given path starts
        with the git repository root path.

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

    def get_dirty_paths(self, git_root: str) -> list[str]:
        """Get dirty paths using git status --porcelain.

        Filters for modified (M) and untracked (??) files only, as these are
        the only ones that can be staged via `git add`.

        Args:
            git_root: Absolute path to git repository root.

        Returns:
            List of relative paths (from git root) that are modified or untracked.
            Empty list if repo is clean or not a git repo.
        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=git_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return []

            dirty_paths = []
            # Don't use .strip() on the whole output - it removes leading spaces
            # from lines like " M file.txt" which are valid porcelain format.
            # Instead, strip each line individually when checking if empty.
            for line in result.stdout.split("\n"):
                line = line.rstrip()  # Only strip trailing whitespace
                if not line:
                    continue

                parsed = self._parse_git_status_line(line)
                if parsed and self._is_dirty_status(parsed["status"], parsed["rel_path"]):
                    dirty_paths.append(parsed["rel_path"])

            return dirty_paths

        except subprocess.TimeoutExpired:
            Log.warning("Git status command timed out")
            return []
        except FileNotFoundError:
            Log.warning("Git command not found - may not be installed")
            return []

    def _parse_git_status_line(self, line: str) -> dict[str, str] | None:
        """Parse a git status porcelain line into status and path components.

        Git porcelain format: "<index_status><wt_status> <path>"
        - Position 0: Index/staging area status
        - Position 1: Working tree status (what determines if file can be staged)
        - Position 2: Space separator
        - Position 3+: File path relative to git root

        Examples:
            " M file.txt" → index=space, wt=M → modified but NOT yet staged
            "M  file.txt" → index=M, wt=space → already staged (NOT dirty)
            "MM file.txt" → index=M, wt=M → modified after staging (dirty)
            "?? file.txt" → index=?, wt=? → untracked

        Args:
            line: A single line from git status --porcelain output.

        Returns:
            Dictionary with 'status' and 'rel_path' keys, or None if parsing fails.
            The 'status' field contains the working tree status character.
        """
        if len(line) < 4:
            return None

        # Extract working tree status (position 1) and path (position 3+)
        wt_status = line[1]
        rel_path = line[3:]

        # Only process lines with valid status characters
        valid_statuses = ("M", "?", "A", "D", "R", "U", "T", "C", " ")
        if wt_status not in valid_statuses:
            return None

        return {"status": wt_status, "rel_path": rel_path}

    def _is_dirty_status(self, status: str, rel_path: str) -> bool:
        """Check if a git status code represents a dirty (staggable) file.

        A file is considered dirty if it has changes in the working tree that
        can be staged via `git add`. This includes:
        - Modified files (M): Changes not yet staged
        - Untracked files (?): New files not in git

        Files that are already staged (A without M), deleted (D), or have other
        statuses are NOT considered dirty.

        Args:
            status: The git status character (working tree position).
            rel_path: The relative file path (used to ensure non-empty).

        Returns:
            True if the file is dirty and can be staged, False otherwise.
        """
        # Only M (modified) and ? (untracked) are dirty
        # Staged-only (A), deleted (D), and others are NOT dirty
        return (status == "M" or status == "?") and bool(rel_path)

    def stage_files(self, git_root: str, paths: list[str]) -> bool:
        """Stage files using git add.

        Args:
            git_root: Absolute path to git repository root.
            paths: List of relative paths to stage.

        Returns:
            True if git add succeeded for all files, False otherwise.
        """
        if not paths:
            return True

        try:
            # Use git add with -v for verbose output
            result = subprocess.run(
                ["git", "add", "-v"] + paths,
                cwd=git_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        Log.debug(f"Staged: {line}")
                return True
            Log.warning(f"Git add failed: {result.stderr.strip()}")
            return False
        except subprocess.TimeoutExpired:
            Log.warning("Git add command timed out")
            return False
        except FileNotFoundError:
            Log.warning("Git command not found")
            return False
