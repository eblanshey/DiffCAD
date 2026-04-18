# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the GitService class which combines
# GitPort interface with GitRepository model creation. It is responsible for
# providing a convenient method to get GitRepository objects from file or
# directory paths using dependency injection. It has no external dependencies.
"""Git domain service."""

import os

from ...utils import Log
from ..freecad_ports import DocumentLike
from .models import GitCommit, GitRepository
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
        name = os.path.basename(git_root)
        return GitRepository(name=name, absolute_path=git_root)

    def get_commits(self, repo: GitRepository, limit: int = 20) -> list[GitCommit]:
        """Get recent commits from git repository.

        Args:
            repo: GitRepository to get commits from.
            limit: Maximum number of commits to return.

        Returns:
            List of GitCommit objects in DESC order.
        """
        return self._git_port.get_commits(repo.absolute_path, limit)

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
                    rel_path = os.path.relpath(doc_path, repo.absolute_path)
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
