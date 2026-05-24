"""File responsibility: Action for checking global git identity config writability."""

from freecad.history_wb.domain.git.git_service import GitService

from .result_models import Result


class CanWriteGlobalGitIdentityAction:
    """Action to check whether global git identity can be saved."""

    def __init__(self, git_service: GitService) -> None:
        """Initialize with git service dependency."""
        self._git_service = git_service

    def execute(self) -> Result:
        """Return whether global git identity can be saved."""
        return Result.success(self._git_service.can_write_global_identity())
