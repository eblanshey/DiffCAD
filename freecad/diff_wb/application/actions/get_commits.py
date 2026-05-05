# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the GetCommitsAction class which is
# responsible for retrieving git commits from a repository. It uses GitService
# to fetch commits and returns them as a Result.
"""Application action for getting git commits."""

from ...domain.git.git_service import GitService
from ...domain.git.models import GitCommit, GitRepository
from .result_models import Result


class GetCommitsAction:
    """Get recent git commits from a repository."""

    def __init__(
        self,
        git_service: GitService,
    ) -> None:
        """Initialize the action with required dependencies.

        Args:
            git_service: Service for git operations.
        """
        self._git_service = git_service

    def execute(self, repo: GitRepository, limit: int = 20, skip: int = 0) -> Result:
        """Get recent commits.

        Args:
            repo: GitRepository to get commits from. Must be a valid repository.
            limit: Maximum number of commits to return (default 20).
            skip: Number of newest commits to skip before returning results.

        Returns:
            Result with list of GitCommit on success, or failure result.
        """
        commits: list[GitCommit] = self._git_service.get_commits(repo, limit, skip)
        return Result.success(commits)
