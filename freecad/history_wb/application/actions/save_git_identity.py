"""File responsibility: Action for saving git commit author identity."""

from freecad.history_wb.domain.git.git_service import GitService
from freecad.history_wb.domain.git.models import GitIdentity, GitRepository

from .result_models import Result


class SaveGitIdentityAction:
    """Action to save git author identity locally or globally."""

    def __init__(self, git_service: GitService) -> None:
        """Initialize with git service dependency."""
        self._git_service = git_service

    def execute(self, repo: GitRepository, identity: GitIdentity, should_save_globally: bool) -> Result:
        """Save git author identity.

        Args:
            repo: Git repository to configure.
            identity: Identity to save.
            should_save_globally: True to save globally, False to save locally.

        Returns:
            Result containing True when save succeeds.
        """
        if self._git_service.save_identity(repo, identity, should_save_globally):
            return Result.success(True)
        return Result.failure("Git identity save failed")
