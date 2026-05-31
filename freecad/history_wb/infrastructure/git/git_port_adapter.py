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
from pathlib import PurePosixPath
from typing import Any

from freecad.history_wb.domain.git.models import GitCommit, GitIdentity
from freecad.history_wb.domain.git.paths import is_fcstd_path
from freecad.history_wb.domain.git.ports import GitPort
from freecad.history_wb.utils import Log


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
        Log.info(f"Git executable detected: {self._git_executable or '<not found>'}")

    def _windows_no_console_kwargs(self) -> dict[str, Any]:
        """Return subprocess options that suppress console windows on Windows."""
        if os.name != "nt":
            return {}

        kwargs: dict[str, Any] = {}
        create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if create_no_window:
            kwargs["creationflags"] = create_no_window

        startup_info_type = getattr(subprocess, "STARTUPINFO", None)
        startf_use_show_window = getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        if startup_info_type is not None and startf_use_show_window:
            startup_info = startup_info_type()
            startup_info.dwFlags |= startf_use_show_window
            startup_info.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
            kwargs["startupinfo"] = startup_info

        return kwargs

    def _run_git(
        self,
        args: list[str],
        *,
        cwd: str,
        timeout: int,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str] | None:
        """Run git command with consistent encoding and error handling."""
        if self._git_executable is None:
            Log.warning("Git command not found - git may not be installed or not in PATH")
            return None

        run_kwargs: dict[str, Any] = {
            "cwd": cwd,
            "shell": False,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": timeout,
        }
        env_overrides = self._default_git_env()
        if extra_env:
            env_overrides |= extra_env
        if env_overrides:
            run_kwargs["env"] = os.environ | env_overrides
        run_kwargs.update(self._windows_no_console_kwargs())

        return subprocess.run([self._git_executable, *args], **run_kwargs)

    def _global_git_config_home_path(self) -> str:
        """Return home path used for global git config in current runtime."""
        return os.environ.get("SNAP_REAL_HOME") or os.path.expanduser("~")

    def _global_git_config_path(self) -> str:
        """Return global git config path for current runtime."""
        return os.path.join(self._global_git_config_home_path(), ".gitconfig")

    def _default_git_env(self) -> dict[str, str]:
        """Return default git environment overrides for current runtime."""
        if "SNAP_REAL_HOME" not in os.environ:
            return {}
        return {"GIT_CONFIG_GLOBAL": self._global_git_config_path()}

    def _global_git_config_env(self, config_path: str) -> dict[str, str]:
        """Return env that makes git use a specific global config path."""
        return {"GIT_CONFIG_GLOBAL": config_path}

    def _writable_global_git_config_path(self) -> str | None:
        """Return global git config path when writable."""
        config_path = self._global_git_config_path()
        if self._can_write_config_file(config_path):
            return config_path
        return None

    def _can_write_config_file(self, path: str) -> bool:
        """Return True when config file can be opened or created for writing."""
        try:
            with open(path, "a", encoding="utf-8"):
                return True
        except OSError as e:
            Log.info(f"Global git config path is not writable: {path}: {e}")
            return False

    def _read_git_config_value(
        self,
        git_root: str,
        args: list[str],
        *,
        extra_env: dict[str, str] | None = None,
    ) -> str | None:
        """Read one git config value."""
        try:
            result = self._run_git(args, cwd=git_root, timeout=5, extra_env=extra_env)
        except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError, OSError) as e:
            Log.warning(f"Git config read failed: {e}")
            return None

        if result is None or result.returncode != 0:
            return None
        value = result.stdout.strip()
        return value or None

    def _save_git_config_value(
        self,
        git_root: str,
        args: list[str],
        *,
        extra_env: dict[str, str] | None = None,
    ) -> bool:
        """Save one git config value."""
        try:
            result = self._run_git(args, cwd=git_root, timeout=5, extra_env=extra_env)
        except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError, OSError) as e:
            Log.warning(f"Git config save failed: {e}")
            return False

        if result is None or result.returncode != 0:
            stderr = "" if result is None else result.stderr.strip()
            Log.warning(f"Git config save failed: {stderr}")
            return False
        return True

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
            if not self._is_not_git_repository_error(result.stderr):
                Log.warning(
                    "Git repository detection failed due to git error: "
                    f"path={path}, cwd={cwd_path}, returncode={result.returncode}, stderr={result.stderr.strip()}"
                )
            return None
        except subprocess.TimeoutExpired:
            Log.warning(f"Git repository detection timed out for path: {path} (cwd={cwd_path})")
            return None
        except FileNotFoundError:
            Log.warning(f"Git executable disappeared before repository detection for path: {path}")
            return None
        except (NotADirectoryError, OSError) as e:
            Log.warning(f"Git repository detection error for path {path} (cwd={cwd_path}): {e}")
            return None

    def _is_not_git_repository_error(self, stderr: str) -> bool:
        """Return True when git reports the path is not inside a repository."""
        normalized_stderr = stderr.lower()
        return "not a git repository" in normalized_stderr

    def _is_no_commits_yet_error(self, stderr: str) -> bool:
        """Return True when git log fails because repository has no commits yet."""
        normalized_stderr = stderr.lower()
        return "does not have any commits yet" in normalized_stderr

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
            if not self._is_no_commits_yet_error(result.stderr):
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
            List of relative .FCStd paths (from git root) that are modified
            or untracked. Empty list if repo is clean or not a git repo.
        """
        try:
            status_entries = self._get_status_entries(git_root)
            return [
                str(entry["rel_path"])
                for entry in status_entries
                if self._is_dirty_status(str(entry["wt_status"]), str(entry["rel_path"]))
                and str(entry["rel_path"]).endswith(".FCStd")
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

    def _get_staged_status_entries(self, git_root: str) -> list[dict[str, str | int]]:
        """Return parsed porcelain entries that are currently staged."""
        status_entries = self._get_status_entries(git_root)
        return [entry for entry in status_entries if str(entry["index_status"]) not in (" ", "?")]

    def _get_status_entries(self, git_root: str) -> list[dict[str, str | int]]:
        """Return parsed entries from git status --porcelain -z output."""
        # Use NUL-delimited porcelain output.
        # Why: newline-delimited output cannot safely represent filenames
        # containing embedded newlines, and quoted-path parsing is trickier.
        # With -z, git uses ASCII NUL as record separator and raw paths.
        # NUL is represented in Python string literals as "\x00".
        result = self._run_git(["status", "--porcelain", "-z"], cwd=git_root, timeout=30)
        if result is None or result.returncode != 0:
            return []
        return self._parse_status_output_entries(result.stdout)

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
            if parsed_line is None:
                continue
            parsed_entries.append(
                {
                    "index_status": line[0],
                    "wt_status": parsed_line["status"],
                    "rel_path": parsed_line["rel_path"],
                    "consumed": 1,
                }
            )
        return parsed_entries

    def _has_head_commit(self, git_root: str) -> bool:
        """Return True when repository has at least one commit."""
        result = self._run_git(["rev-parse", "--verify", "HEAD"], cwd=git_root, timeout=10)
        return result is not None and result.returncode == 0

    def _run_unstage_with_restore(self, git_root: str, paths: list[str]) -> bool:
        """Run index-only unstage for repositories with HEAD."""
        result = self._run_git(["restore", "--staged", "--", *paths], cwd=git_root, timeout=30)
        if result is None:
            return False
        if result.returncode == 0:
            return True
        Log.warning(f"Git restore --staged failed: {result.stderr.strip()}")
        return False

    def _run_unstage_with_rm_cached(self, git_root: str, paths: list[str]) -> bool:
        """Run index-only unstage fallback for repositories without HEAD."""
        result = self._run_git(["rm", "--cached", "--", *paths], cwd=git_root, timeout=30)
        if result is None:
            return False
        if result.returncode == 0:
            return True
        Log.warning(f"Git rm --cached failed: {result.stderr.strip()}")
        return False

    def unstage_files(self, git_root: str, paths: list[str]) -> bool:
        """Unstage selected paths from index while leaving working tree untouched."""
        if not paths:
            return True

        try:
            staged_entries = self._get_staged_status_entries(git_root)
            staged_paths = {str(entry["rel_path"]) for entry in staged_entries}
            target_paths = [path for path in paths if path in staged_paths]
            if not target_paths:
                return True

            if self._has_head_commit(git_root):
                return self._run_unstage_with_restore(git_root, target_paths)
            return self._run_unstage_with_rm_cached(git_root, target_paths)
        except subprocess.TimeoutExpired:
            Log.warning("Git unstage command timed out")
            return False
        except FileNotFoundError:
            Log.warning("Git command not found")
            return False
        except (NotADirectoryError, OSError) as e:
            Log.warning(f"Git unstage failed: {e}")
            return False

    def unstage_all(self, git_root: str) -> bool:
        """Unstage all currently staged repository paths from index only."""
        try:
            staged_entries = self._get_staged_status_entries(git_root)
            target_paths = [str(entry["rel_path"]) for entry in staged_entries]
            if not target_paths:
                return True

            if self._has_head_commit(git_root):
                return self._run_unstage_with_restore(git_root, target_paths)
            return self._run_unstage_with_rm_cached(git_root, target_paths)
        except subprocess.TimeoutExpired:
            Log.warning("Git unstage all command timed out")
            return False
        except FileNotFoundError:
            Log.warning("Git command not found")
            return False
        except (NotADirectoryError, OSError) as e:
            Log.warning(f"Git unstage all failed: {e}")
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
            status_entries = self._get_status_entries(git_root)
            staged_document_paths: list[str] = []
            seen_paths: set[str] = set()
            for entry in status_entries:
                if str(entry["index_status"]) in (" ", "?"):
                    continue
                rel_path = str(entry["rel_path"])
                fcstd_path = self._document_path_for_staged_entry(rel_path)
                if fcstd_path is None or fcstd_path in seen_paths:
                    continue
                seen_paths.add(fcstd_path)
                staged_document_paths.append(fcstd_path)
            return staged_document_paths
        except subprocess.TimeoutExpired:
            Log.warning("Git status command timed out")
            return []
        except FileNotFoundError:
            Log.warning("Git command not found")
            return []
        except (NotADirectoryError, OSError) as e:
            Log.warning(f"Git status failed: {e}")
            return []

    def _document_path_for_staged_entry(self, rel_path: str) -> str | None:
        """Map staged path to its reviewed FCStd document path when applicable."""
        if is_fcstd_path(rel_path):
            return rel_path

        normalized_path = rel_path.replace("\\", "/")
        yaml_path = PurePosixPath(normalized_path)
        if yaml_path.suffix != ".yaml":
            return None
        if yaml_path.parent.name != ".snapshots":
            return None

        document_name = f"{yaml_path.stem}.FCStd"
        mapped = yaml_path.parent.parent / document_name
        return str(mapped)

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
            args = ["show", self._show_target(commit, git_path)]
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

    def write_file_from_ref(self, git_root: str, commit: str | None, git_path: str, destination: str) -> bool:
        """Write file bytes from git ref/index to destination path."""
        if self._git_executable is None:
            Log.warning("Git command not found - git may not be installed or not in PATH")
            return False
        try:
            target = self._show_target(commit, git_path)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            run_kwargs: dict[str, Any] = {"cwd": git_root, "shell": False, "stderr": subprocess.PIPE}
            env_overrides = self._default_git_env()
            if env_overrides:
                run_kwargs["env"] = os.environ | env_overrides
            run_kwargs.update(self._windows_no_console_kwargs())
            with open(destination, "wb") as output:
                process = subprocess.Popen([self._git_executable, "show", target], stdout=output, **run_kwargs)
                return_code = process.wait(timeout=30)
                return return_code == 0
        except subprocess.TimeoutExpired:
            Log.warning(f"Git show command timed out for {git_path}")
            return False
        except FileNotFoundError as e:
            Log.exception(f"File not found: {e}")
            return False
        except (NotADirectoryError, OSError) as e:
            Log.warning(f"Git show failed for {git_path}: {e}")
            return False

    def _show_target(self, commit: str | None, git_path: str) -> str:
        """Build git show target for commit or index."""
        return f":{git_path}" if commit is None else f"{commit}:{git_path}"

    def resolve_ref(self, git_root: str, ref: str) -> str | None:
        """Resolve git ref to full commit hash via git rev-parse."""
        try:
            result = self._run_git(["rev-parse", "--verify", f"{ref}^{{commit}}"], cwd=git_root, timeout=30)
            if result is None or result.returncode != 0:
                return None
            resolved = result.stdout.strip()
            return resolved or None
        except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError, OSError) as e:
            Log.warning(f"Git ref resolution failed for {ref}: {e}")
            return None

    def restore_paths_from_ref(self, git_root: str, commit: str | None, paths: list[str]) -> bool:
        """Restore selected paths into worktree from commit or index."""
        if not paths:
            Log.debug("Git restore skipped: no paths provided")
            return True
        try:
            args = ["restore", "--worktree"]
            if commit is not None:
                args.append(f"--source={commit}")
            args.extend(["--", *paths])
            result = self._run_git(args, cwd=git_root, timeout=30)
            if result is None:
                Log.warning("Git restore failed: git executable unavailable")
                return False
            if result.returncode != 0:
                Log.warning(f"Git restore failed: {result.stderr.strip()}")
                return False
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError, OSError) as e:
            Log.warning(f"Git restore command failed: {e}")
            return False

    def get_all_fcstd_paths(self, git_root: str, commit: str | None) -> list[str]:
        """Return all FCStd paths available in selected commit or index."""
        try:
            args = ["ls-files", "-z"] if commit is None else ["ls-tree", "-r", "-z", "--name-only", commit]
            result = self._run_git(args, cwd=git_root, timeout=30)
            if result is None:
                Log.warning("Git path listing failed: git executable unavailable")
                return []
            if result.returncode != 0:
                source_name = "index" if commit is None else f"commit {commit}"
                Log.warning(f"Git path listing failed for {source_name}: {result.stderr.strip()}")
                return []
            return [path for path in result.stdout.split("\x00") if path and is_fcstd_path(path)]
        except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError, OSError) as e:
            source_name = "index" if commit is None else f"commit {commit}"
            Log.warning(f"Git path listing failed for {source_name}: {e}")
            return []

    def get_current_saved_fcstd_paths(self, git_root: str) -> list[str]:
        """Return current FCStd paths saved in history (ls-files)."""
        return self.get_all_fcstd_paths(git_root, None)

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

    def get_identity(self, git_root: str) -> GitIdentity | None:
        """Get configured git author identity from repository context."""
        name = self._read_git_config_value(git_root, ["config", "--get", "user.name"])
        email = self._read_git_config_value(git_root, ["config", "--get", "user.email"])
        if name and email:
            return GitIdentity(name=name, email=email)
        return None

    def save_identity(self, git_root: str, identity: GitIdentity, should_save_globally: bool) -> bool:
        """Save git author identity to local or global config."""
        if should_save_globally:
            config_path = self._writable_global_git_config_path()
            if config_path is None:
                Log.warning("Cannot save global git identity because no writable global git config path is available")
                return False
            args_prefix = ["config", "--global"]
            extra_env = self._global_git_config_env(config_path)
        else:
            args_prefix = ["config", "--local"]
            extra_env = None

        name_saved = self._save_git_config_value(
            git_root,
            [*args_prefix, "user.name", identity.name],
            extra_env=extra_env,
        )
        email_saved = self._save_git_config_value(
            git_root,
            [*args_prefix, "user.email", identity.email],
            extra_env=extra_env,
        )
        return name_saved and email_saved

    def can_write_global_identity(self) -> bool:
        """Return whether global git identity config can be written."""
        return self._writable_global_git_config_path() is not None

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
            return [path for path in result.stdout.split("\x00") if path and is_fcstd_path(path)]
        except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError, OSError):
            return []

    def initialize_repository(self, path: str) -> bool:
        """Initialize git repository in directory using git init.

        Args:
            path: Directory path where git init should run.

        Returns:
            True if initialization succeeded, False otherwise.
        """
        if not path or not os.path.isdir(path):
            Log.warning(f"Cannot initialize git repository because directory does not exist: {path}")
            return False

        try:
            result = self._run_git(["init"], cwd=path, timeout=30)
            if result is None:
                return False
            if result.returncode == 0:
                Log.info(f"Initialized git repository: {path}")
                return True
            Log.warning(f"Git init failed: {result.stderr.strip()}")
            return False
        except subprocess.TimeoutExpired:
            Log.warning(f"Git init timed out for path: {path}")
            return False
        except FileNotFoundError:
            Log.warning("Git command not found")
            return False
        except (NotADirectoryError, OSError) as e:
            Log.warning(f"Git init failed for path {path}: {e}")
            return False
