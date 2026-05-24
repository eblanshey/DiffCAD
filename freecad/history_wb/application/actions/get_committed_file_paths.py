# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for getting FCStd file paths changed in a commit.
"""Application action for getting FCStd file paths changed in a commit."""

from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from .result_models import Result


__all__ = ["GetCommittedFilePathsAction"]


class GetCommittedFilePathsAction:
    """Get list of FCStd file paths changed in a specific commit."""

    def __init__(self, git_service: GitService) -> None:
        """Initialize with GitService.

        Args:
            git_service: GitService for git operations.
        """
        self._git_service = git_service

    def execute(self, repo: GitRepository, commit: str) -> Result:
        """Get FCStd file paths changed in a commit.

        Args:
            repo: GitRepository to get committed files from.
            commit: Commit reference (hash, "HEAD", "HEAD~1", etc.)

        Returns:
            Result containing list of FCStd git_paths on success.
        """
        committed_paths = self._git_service.get_committed_files(repo, commit)
        return Result.success(committed_paths)
