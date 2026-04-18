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
