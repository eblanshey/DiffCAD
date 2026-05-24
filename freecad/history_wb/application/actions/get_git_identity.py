"""File responsibility: Action for reading git commit author identity."""

from freecad.history_wb.domain.git.git_service import GitService
from freecad.history_wb.domain.git.models import GitRepository

from .result_models import Result


class GetGitIdentityAction:
    """Action to read configured git author identity for a repository."""

    def __init__(self, git_service: GitService) -> None:
        """Initialize with git service dependency."""
        self._git_service = git_service

    def execute(self, repo: GitRepository) -> Result:
        """Read git author identity.

        Args:
            repo: Git repository to query.

        Returns:
            Result containing GitIdentity or None when not configured.
        """
        return Result.success(self._git_service.get_identity(repo))
