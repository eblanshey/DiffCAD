"""File responsibility: Commit staging action orchestration."""

from freecad.history_wb.domain.git.git_service import GitService
from freecad.history_wb.domain.git.models import GitRepository

from .result_models import Result


class CommitStagingAction:
    """Action to commit staged changes to git repository.

    This action orchestrates the commit workflow by calling GitService
    to perform the actual git commit operation.
    """

    def __init__(self, git_service: GitService) -> None:
        """Initialize with required dependencies.

        Args:
            git_service: Service for git operations.
        """
        self._git_service = git_service

    def execute(self, repo: GitRepository, message: str) -> Result:
        """Commit staged changes.

        Args:
            repo: GitRepository to commit in. Must have staged files.
            message: Commit message text.

        Returns:
            Result with success status and optional error message.
        """
        success = self._git_service.commit(repo, message)

        if success:
            return Result.success(True)
        return Result.failure("Git commit failed")
