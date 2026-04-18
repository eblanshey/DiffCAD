# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for getting dirty document paths.
# This module provides the GetDirtyDocumentsAction which checks which documents
# have git-tracked changes (modified or untracked).
"""Application action for getting dirty documents."""

from ...domain.freecad_ports import DocumentLike
from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from .result_models import Result


__all__ = ["GetDirtyDocumentsAction"]


class GetDirtyDocumentsAction:
    """Get list of document git paths that have git changes.

    This action checks which of the provided documents have been modified
    or are untracked in the git repository. Only modified and untracked
    files are considered (not staged-only or deleted files).
    """

    def __init__(self, git_service: GitService):
        self._git_service = git_service

    def execute(self, repo: GitRepository, documents: list[DocumentLike]) -> Result:
        """Execute the action to get dirty document paths.

        Args:
            repo: GitRepository to check against.
            documents: List of DocumentLike objects to check.

        Returns:
            Result.success(list of dirty git paths relative to repo root).
        """
        dirty_paths = self._git_service.get_dirty_documents(repo, documents)
        return Result.success(dirty_paths)
