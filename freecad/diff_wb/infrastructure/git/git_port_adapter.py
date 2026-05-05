# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the GitPortAdapter class that implements
# the GitPort protocol using git CLI via subprocess. It handles git repository
# detection, commit listing, file staging, commit creation, and committed file path
# queries. All git operations use subprocess with proper error handling.
"""GitPort adapter implementation using git CLI."""

import os
import shutil
import subprocess
from codecs import decode as codecs_decode
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

    def __init__(self) -> None:
        """Initialize adapter with cached git executable path."""
        self._git_executable = shutil.which("git")

    def _run_git(
        self,
        args: list[str],
        *,
        cwd: str,
        timeout: int,
    ) -> subprocess.CompletedProcess[str] | None:
        """Run git command with consistent encoding and error handling."""
        if self._git_executable is None:
            Log.warning("Git command not found - git may not be installed or not in PATH")
            return None

        return subprocess.run(
            [self._git_executable, *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

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
            result = self._run_git(["rev-parse", "--show-toplevel"], cwd=cwd_path, timeout=5)
            if result is None:
                return None
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError, OSError):
            return None

    def get_commits(self, path: str, limit: int = 20, skip: int = 0) -> list[GitCommit]:
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
            skip: Number of newest commits to skip before returning results.

        Returns:
            List of GitCommit objects in DESC order (newest first).
        """
        output = self._get_commits_output(path=path, limit=limit, skip=skip)
        if not output:
            return []

        # Split by null byte to get all fields
        # Each commit has 4 fields: hash, message, author, timestamp
        # The trailing %x00 after timestamp creates an extra empty element
        parts = output.split("\x00")

        commits = []
        # Process in groups of 4 (hash, message, author, timestamp)
        for i in range(0, len(parts) - 3, 4):
            # Git inserts a newline between pretty-format entries. When using
            # null-byte field delimiters this can prefix the next commit hash
            # with "\n". Strip whitespace from scalar fields to keep values valid.
            commit_hash = parts[i].strip()
            full_message = parts[i + 1]
            author = parts[i + 2].strip()
            timestamp = parts[i + 3].strip()

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

    def _get_commits_output(self, path: str, limit: int, skip: int) -> str:
        """Run git log command and return stripped output."""
        cwd_path = path
        if path and os.path.isfile(path):
            cwd_path = os.path.dirname(path)

        log_args = ["log"]
        if skip > 0:
            log_args.append(f"--skip={skip}")
        log_args.extend([f"-n{limit}", "--format=%H%x00%B%x00%an%x00%aI%x00"])

        try:
            result = self._run_git(log_args, cwd=cwd_path, timeout=10)
        except subprocess.TimeoutExpired:
            Log.warning(f"Git log command timed out for path: {path}")
            return ""
        except FileNotFoundError:
            Log.warning("Git command not found - git may not be installed or not in PATH")
            return ""
        except (NotADirectoryError, OSError) as e:
            Log.warning(f"Git error for path {path}: {e}")
            return ""

        if result is None:
            return ""

        if result.returncode != 0:
            Log.warning(f"Git log failed with return code {result.returncode}: {result.stderr.strip()}")
            return ""

        return result.stdout.strip()

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

        normalized_git_root = os.path.normcase(os.path.abspath(git_root))
        normalized_path = os.path.normcase(os.path.abspath(path))

        try:
            return os.path.commonpath([normalized_git_root, normalized_path]) == normalized_git_root
        except ValueError:
            # Different drives on Windows cannot share common path.
            return False

    def get_dirty_paths(self, git_root: str) -> list[str]:
        """Get dirty paths using git status --porcelain -z.

        Filters for modified (M) and untracked (??) files only, as these are
        the only ones that can be staged via `git add`.

        Args:
            git_root: Absolute path to git repository root.

        Returns:
            List of relative paths (from git root) that are modified or untracked.
            Empty list if repo is clean or not a git repo.
        """
        try:
            # Use NUL-delimited porcelain output.
            # Why: newline-delimited output cannot safely represent filenames
            # containing embedded newlines, and quoted-path parsing is trickier.
            # With -z, git uses ASCII NUL as record separator and raw paths.
            # NUL is represented in Python string literals as "\x00".
            result = self._run_git(["status", "--porcelain", "-z"], cwd=git_root, timeout=30)
            if result is None or result.returncode != 0:
                return []

            status_entries = self._parse_status_output_entries(result.stdout)
            return [
                str(entry["rel_path"])
                for entry in status_entries
                if self._is_dirty_status(str(entry["wt_status"]), str(entry["rel_path"]))
            ]
        except subprocess.TimeoutExpired:
            Log.warning("Git status command timed out")
            return []
        except FileNotFoundError:
            Log.warning("Git command not found - may not be installed")
            return []
        except (NotADirectoryError, OSError) as e:
            Log.warning(f"Git status failed: {e}")
            return []

    def _parse_status_output_entries(self, stdout: str) -> list[dict[str, str | int]]:
        """Parse git status porcelain output into normalized status entries."""
        parsed_entries: list[dict[str, str | int]] = []
        if "\x00" in stdout:
            # NUL-delimited mode (-z): each entry ends with NUL ('\x00').
            # Split by NUL and ignore final empty fragment if present.
            entries = [entry for entry in stdout.split("\x00") if entry]
            index = 0
            while index < len(entries):
                parsed = self._parse_git_status_entry_z(entries, index)
                if parsed is None:
                    index += 1
                    continue
                parsed_entries.append(parsed)
                index += int(parsed["consumed"])
            return parsed_entries

        for line in stdout.split("\n"):
            line = line.rstrip()
            if not line:
                continue
            parsed_line = self._parse_git_status_line(line)
            if parsed_line is not None:
                parsed_entries.append(
                    {
                        "index_status": line[0],
                        "wt_status": parsed_line["status"],
                        "rel_path": parsed_line["rel_path"],
                        "consumed": 1,
                    }
                )
        return parsed_entries

    def _parse_git_status_line(self, line: str) -> dict[str, str] | None:
        """Parse a git status porcelain line into status and path components.

        Git porcelain line format: "<index_status><wt_status> <path>"
        - Position 0: index/staging area status
        - Position 1: working tree status (drives dirty detection)
        - Position 2: space separator
        - Position 3+: repository-relative path

        Examples:
            " M file.txt" -> index=space, wt=M (modified, not staged)
            "M  file.txt" -> index=M, wt=space (staged only)
            "MM file.txt" -> index=M, wt=M (staged + modified again)
            "?? file.txt" -> untracked
        """
        if len(line) < 4:
            return None

        wt_status = line[1]
        rel_path = self._normalize_porcelain_path(line[3:])

        valid_statuses = ("M", "?", "A", "D", "R", "U", "T", "C", " ")
        if wt_status not in valid_statuses:
            return None

        return {"status": wt_status, "rel_path": rel_path}

    def _parse_git_status_entry_z(self, entries: list[str], index: int) -> dict[str, str | int] | None:
        """Parse one NUL-delimited porcelain v1 entry from git status -z.

        Git porcelain format with ``-z`` emits NUL-separated entries:
        - Normal entries: ``<index_status><wt_status> <path>\0``
        - Rename/copy entries: ``<index_status><wt_status> <new_path>\0<old_path>\0``

        Examples:
            " M file.txt" → index=space, wt=M → modified but NOT yet staged
            "M  file.txt" → index=M, wt=space → already staged (NOT dirty)
            "MM file.txt" → index=M, wt=M → modified after staging (dirty)
            "?? file.txt" → index=?, wt=? → untracked

        Args:
            entries: NUL-delimited output entries from git status.
            index: Entry index to parse.

        Returns:
            Dictionary with parsed statuses/path and consumed entry count,
            or None if parsing fails.
        """
        entry = entries[index]
        if len(entry) < 3:
            return None

        index_status = entry[0]
        wt_status = entry[1]
        rel_path = entry[3:] if len(entry) > 3 else ""
        consumed = 1

        if index_status in ("R", "C"):
            # For rename/copy in -z mode, git emits two NUL-separated path fields:
            # new path in current entry, old path in next entry. We care about
            # target/new path for downstream matching/staging logic.
            if index + 1 >= len(entries):
                return None
            consumed = 2

        # Only process lines with valid status characters
        valid_statuses = ("M", "?", "A", "D", "R", "U", "T", "C", " ")
        if wt_status not in valid_statuses:
            return None

        return {
            "index_status": index_status,
            "wt_status": wt_status,
            "rel_path": rel_path,
            "consumed": consumed,
        }

    def _normalize_porcelain_path(self, path: str) -> str:
        """Normalize porcelain path by decoding git-quoted paths.

        Git porcelain output may quote paths that contain whitespace or special
        characters, e.g. ``"path/with spaces/file.FCStd"``. This helper strips
        surrounding quotes and decodes C-style escapes so callers always receive
        the real relative path.

        Args:
            path: Raw path fragment from porcelain output.

        Returns:
            Normalized relative path.
        """
        normalized = path.strip()

        if len(normalized) >= 2 and normalized[0] == '"' and normalized[-1] == '"':
            quoted_content = normalized[1:-1]
            try:
                return codecs_decode(quoted_content, "unicode_escape")
            except UnicodeDecodeError:
                return quoted_content

        return normalized

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

        # Use git add with -v for verbose output
        try:
            result = self._run_git(["add", "-v", "--", *paths], cwd=git_root, timeout=30)
            if result is None:
                return False

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
        except (NotADirectoryError, OSError) as e:
            Log.warning(f"Git add failed: {e}")
            return False

    def get_staged_paths(self, git_root: str) -> list[str]:
        """Get staged FCStd file paths using git status --porcelain -z.

        Filters for files that are staged in the index (position 0 status is not space).
        Only returns files with .FCStd extension.

        Args:
            git_root: Absolute path to git repository root.

        Returns:
            List of relative paths (from git root) that are staged and are FCStd files.
        """
        try:
            result = self._run_git(["status", "--porcelain", "-z"], cwd=git_root, timeout=30)
            if result is None or result.returncode != 0:
                return []

            status_entries = self._parse_status_output_entries(result.stdout)
            return [
                str(entry["rel_path"])
                for entry in status_entries
                if str(entry["index_status"]) not in (" ", "?") and str(entry["rel_path"]).endswith(".FCStd")
            ]
        except subprocess.TimeoutExpired:
            Log.warning("Git status command timed out")
            return []
        except FileNotFoundError:
            Log.warning("Git command not found")
            return []
        except (NotADirectoryError, OSError) as e:
            Log.warning(f"Git status failed: {e}")
            return []

    def get_file_contents(self, git_root: str, commit: str | None, git_path: str) -> str | None:
        """Get file contents using git show.

        Args:
            git_root: Absolute path to git repository root.
            commit: Commit reference or None for index.
            git_path: Relative path within repository.

        Returns:
            File contents as string, or None if not found or error.
        """
        # Get from index using :<path> syntax, or from specific commit
        try:
            args = ["show", f":{git_path}"] if commit is None else ["show", f"{commit}:{git_path}"]
            result = self._run_git(args, cwd=git_root, timeout=30)
            if result is None:
                return None

            if result.returncode == 0:
                return result.stdout
            return None
        except subprocess.TimeoutExpired:
            Log.warning(f"Git show command timed out for {git_path}")
            return None
        except FileNotFoundError:
            Log.warning("Git command not found")
            return None
        except (NotADirectoryError, OSError) as e:
            Log.warning(f"Git show failed for {git_path}: {e}")
            return None

    def file_exists(self, git_root: str, commit: str | None, git_path: str) -> bool:
        """Check file existence at commit or index via git cat-file.

        Args:
            git_root: Absolute path to git repository root.
            commit: Commit reference or None for index.
            git_path: Relative path within repository.

        Returns:
            True if path exists, False otherwise.
        """
        try:
            target = f":{git_path}" if commit is None else f"{commit}:{git_path}"
            result = self._run_git(["cat-file", "-e", target], cwd=git_root, timeout=30)
            if result is None:
                return False
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError, OSError):
            return False

    def commit(self, git_root: str, message: str) -> bool:
        """Commit staged changes using git CLI.

        Uses 'git commit -m <message>' command.

        Args:
            git_root: Absolute path to git repository root.
            message: Commit message text.

        Returns:
            True if git commit succeeded, False otherwise.
        """
        try:
            result = self._run_git(["commit", "-m", message], cwd=git_root, timeout=30)
            if result is None:
                return False

            if result.returncode == 0:
                Log.debug(f"Commit successful: {result.stdout.strip()}")
                return True

            Log.warning(f"Git commit failed: {result.stderr.strip()}")
            return False
        except subprocess.TimeoutExpired:
            Log.warning("Git commit command timed out")
            return False
        except FileNotFoundError:
            Log.warning("Git command not found")
            return False
        except (NotADirectoryError, OSError) as e:
            Log.warning(f"Git error: {e}")
            return False

    def get_committed_files(self, git_root: str, commit: str) -> list[str]:
        """Get FCStd file paths changed in a specific commit using git diff-tree.

        Uses `git diff-tree --root --no-commit-id --name-only -r <commit>` to list
        all files changed in the given commit. The `--root` flag ensures root commits
        also return their files. Results are filtered to only include .FCStd files.

        Args:
            git_root: Absolute path to git repository root.
            commit: Commit reference (hash, "HEAD", "HEAD~1", etc.)

        Returns:
            List of relative paths (from git root) of .FCStd files changed in the commit.
            Empty list if no FCStd files changed or error occurred.
        """
        try:
            result = self._run_git(
                [
                    "diff-tree",
                    "--root",
                    "--no-commit-id",
                    "--name-only",
                    "-z",
                    "-r",
                    commit,
                ],
                cwd=git_root,
                timeout=30,
            )
            if result is None or result.returncode != 0:
                return []
            return [path for path in result.stdout.split("\x00") if path and path.endswith(".FCStd")]
        except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError, OSError):
            return []
