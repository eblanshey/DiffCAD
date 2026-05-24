# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for getting list of staged FCStd files.
"""Application action for getting staged file paths."""

from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from .result_models import Result


__all__ = ["GetStagedFilePathsAction"]


class GetStagedFilePathsAction:
    """Get list of FCStd files that are staged in the git repository."""

    def __init__(self, git_service: GitService) -> None:
        """Initialize with GitService.

        Args:
            git_service: GitService for git operations.
        """
        self._git_service = git_service

    def execute(self, repo: GitRepository) -> Result:
        """Get staged FCStd file paths.

        Args:
            repo: GitRepository to get staged files from.

        Returns:
            Result containing list of staged FCStd git_paths on success.
        """
        staged_paths = self._git_service.get_staged_files(repo)
        return Result.success(staged_paths)
