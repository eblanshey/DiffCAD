# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the GitService class which combines
# GitPort interface with GitRepository model creation. It is responsible for
# providing a convenient method to get GitRepository objects from file or
# directory paths using dependency injection, including commit listing, file
# staging, committed file queries, and commit creation. It has no external
# dependencies.
"""Git domain service."""

from ...utils import Log
from ..freecad_ports import DocumentLike
from .models import GitCommit, GitIdentity, GitRepository
from .paths import git_path_name, relative_git_path
from .ports import GitPort


class GitService:
    """Service for git repository operations.

    This class provides a high-level interface for working with git repositories.
    It uses a GitPort for low-level git operations and creates GitRepository
    objects from the results.

    Attributes:
        _git_port: The GitPort instance used for git operations.
    """

    def __init__(self, git_port: GitPort) -> None:
        """Initialize the GitService with a GitPort.

        Args:
            git_port: The GitPort implementation to use for git operations.
        """
        self._git_port = git_port

    def get_repository(self, path: str) -> GitRepository | None:
        """Get GitRepository for path.

        This method determines if a given path is within a git repository and,
        if so, returns a GitRepository object representing that repository.

        Args:
            path: File or directory path to check.

        Returns:
            GitRepository if path is in a git repo, None otherwise.
        """
        git_root = self._git_port.find_top_level_git_path(path)
        if git_root is None:
            return None
        name = git_path_name(git_root)
        return GitRepository(name=name, absolute_path=git_root)

    def get_commits(self, repo: GitRepository, limit: int = 20, skip: int = 0) -> list[GitCommit]:
        """Get recent commits from git repository.

        Args:
            repo: GitRepository to get commits from.
            limit: Maximum number of commits to return.
            skip: Number of newest commits to skip before returning results.

        Returns:
            List of GitCommit objects in DESC order.
        """
        return self._git_port.get_commits(repo.absolute_path, limit, skip)

    def get_eligible_docs(self, repo: GitRepository, documents: list[DocumentLike]) -> list[DocumentLike]:
        """Filter documents to those within the git repository.

        This method filters a list of documents (DocumentLike objects) to only
        include those whose file paths are within the given git repository.

        Args:
            repo: GitRepository to check documents against.
            documents: List of DocumentLike objects to filter.

        Returns:
            List of documents that are within the git repository.
        """
        eligible = []
        for doc in documents:
            doc_path = getattr(doc, "FileName", "")
            if doc_path and self._git_port.is_path_in_repository(repo.absolute_path, doc_path):
                eligible.append(doc)
        return eligible

    def get_dirty_documents(self, repo: GitRepository, documents: list[DocumentLike]) -> list[str]:
        """Get git paths of documents that have git changes.

        This method checks which of the provided documents have been modified
        or are untracked in the git repository.

        Args:
            repo: GitRepository to check against.
            documents: List of DocumentLike objects to check.

        Returns:
            List of git paths (relative from repo root) that are dirty.
        """
        try:
            dirty_paths = self._git_port.get_dirty_paths(repo.absolute_path)

            # Filter to only documents we care about
            dirty_doc_paths = []
            for doc in documents:
                doc_path = getattr(doc, "FileName", "")
                if doc_path and self._git_port.is_path_in_repository(repo.absolute_path, doc_path):
                    # Get relative path from git root
                    rel_path = relative_git_path(doc_path, repo.absolute_path)
                    if rel_path in dirty_paths:
                        dirty_doc_paths.append(rel_path)

            return dirty_doc_paths
        except (OSError, ValueError) as e:
            Log.warning(f"Error getting dirty documents: {e}")
            return []

    def stage_files(self, repo: GitRepository, paths: list[str]) -> bool:
        """Stage files in the git repository.

        Args:
            repo: GitRepository to stage files in.
            paths: List of relative paths (from git root) to stage.

        Returns:
            True if staging succeeded, False otherwise.
        """
        return self._git_port.stage_files(repo.absolute_path, paths)

    def get_staged_files(self, repo: GitRepository) -> list[str]:
        """Get list of staged FCStd file paths.

        Args:
            repo: GitRepository to check.

        Returns:
            List of relative paths (from git root) of staged FCStd files.
        """
        return self._git_port.get_staged_paths(repo.absolute_path)

    def get_file_contents(self, repo: GitRepository, commit: str | None, git_path: str) -> str | None:
        """Get file contents from git at a specific commit or index.

        Args:
            repo: GitRepository to get file from.
            commit: Commit reference or None for index.
            git_path: Relative path within repository.

        Returns:
            File contents as string, or None if not found.
        """
        return self._git_port.get_file_contents(repo.absolute_path, commit, git_path)

    def write_file_from_ref(self, repo: GitRepository, commit: str | None, git_path: str, destination: str) -> bool:
        """Write file bytes from git ref/index to destination path."""
        return self._git_port.write_file_from_ref(repo.absolute_path, commit, git_path, destination)

    def resolve_ref(self, repo: GitRepository, ref: str) -> str | None:
        """Resolve git ref to full commit hash."""
        return self._git_port.resolve_ref(repo.absolute_path, ref)

    def file_exists(self, repo: GitRepository, commit: str | None, git_path: str) -> bool:
        """Check whether a file exists at commit or index.

        Args:
            repo: GitRepository to query.
            commit: Commit reference or None for index.
            git_path: Relative path within repository.

        Returns:
            True if file exists at the specified ref/index.
        """
        return self._git_port.file_exists(repo.absolute_path, commit, git_path)

    def commit(self, repo: GitRepository, message: str) -> bool:
        """Commit staged changes in the repository.

        Args:
            repo: GitRepository to commit in.
            message: Commit message text.

        Returns:
            True if commit succeeded, False otherwise.
        """
        return self._git_port.commit(repo.absolute_path, message)

    def get_identity(self, repo: GitRepository) -> GitIdentity | None:
        """Get configured git author identity for repository context."""
        return self._git_port.get_identity(repo.absolute_path)

    def save_identity(self, repo: GitRepository, identity: GitIdentity, should_save_globally: bool) -> bool:
        """Save git author identity locally or globally."""
        return self._git_port.save_identity(repo.absolute_path, identity, should_save_globally)

    def can_write_global_identity(self) -> bool:
        """Return whether global git identity config can be written."""
        return self._git_port.can_write_global_identity()

    def get_committed_files(self, repo: GitRepository, commit: str) -> list[str]:
        """Get list of FCStd file paths changed in a specific commit.

        Args:
            repo: GitRepository to check.
            commit: Commit reference (hash, "HEAD", "HEAD~1", etc.)

        Returns:
            List of relative paths (from git root) of .FCStd files changed in the commit.
        """
        return self._git_port.get_committed_files(repo.absolute_path, commit)

    def initialize_repository(self, path: str) -> GitRepository | None:
        """Initialize git repository in directory and return repository model.

        Args:
            path: Directory path where git init should run.

        Returns:
            GitRepository if initialization succeeded, None otherwise.
        """
        if not path:
            return None
        if not self._git_port.initialize_repository(path):
            return None
        return self.get_repository(path)
