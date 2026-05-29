# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Write and stage repository .gitignore contents.
"""Application action for persisting repository .gitignore content."""

from __future__ import annotations

from pathlib import Path

from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ...utils import Log
from .get_gitignore_content import GetGitIgnoreContentAction
from .result_models import Result


class UpdateGitIgnoreAction:
    """Persist repository .gitignore with staging."""

    def __init__(self, git_service: GitService, get_gitignore_content_action: GetGitIgnoreContentAction) -> None:
        """Initialize action with git service dependency."""
        self._git_service = git_service
        self._get_gitignore_content_action = get_gitignore_content_action

    def execute(self, repo: GitRepository, content: str | None = None) -> Result:
        """Write .gitignore content and stage it in repository index."""
        target_content = content
        if target_content is None:
            content_result = self._get_gitignore_content_action.execute(repo)
            if not content_result.is_success:
                return content_result
            target_content = str(content_result.data)

        gitignore_path = self._gitignore_path(repo)
        try:
            gitignore_path.write_text(target_content, encoding="utf-8")
        except OSError as error:
            Log.exception(f"Failed writing .gitignore at {gitignore_path}: {error}")
            return Result.failure("Failed to write .gitignore file")

        staged = self._git_service.stage_files(repo, [".gitignore"])
        if not staged:
            return Result.failure("Failed to stage .gitignore file")
        return Result.success(True)

    def _gitignore_path(self, repo: GitRepository) -> Path:
        """Return absolute path to repository .gitignore file."""
        return Path(repo.absolute_path) / ".gitignore"
