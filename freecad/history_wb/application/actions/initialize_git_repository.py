# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Initialize a new git repository in a selected directory
# after validating it is not already inside an existing repository.
"""Application action for git repository initialization."""

from __future__ import annotations

import os

from ...domain.git.git_service import GitService
from .result_models import Result
from .update_gitignore import UpdateGitIgnoreAction


class InitializeGitRepositoryAction:
    """Initialize git repository in selected directory."""

    def __init__(self, git_service: GitService, update_gitignore_action: UpdateGitIgnoreAction) -> None:
        """Initialize dependencies for repository initialization workflow."""
        self._git_service = git_service
        self._update_gitignore_action = update_gitignore_action

    def execute(self, path: str) -> Result:
        """Initialize repository at path and return GitRepository on success."""
        normalized_path = os.path.abspath(path) if path else ""
        if not normalized_path:
            return Result.failure("Repository directory is required")

        if self._git_service.get_repository(normalized_path) is not None:
            return Result.failure("Directory is already inside a git repository")

        repository = self._git_service.initialize_repository(normalized_path)
        if repository is None:
            return Result.failure("Failed to initialize git repository")

        gitignore_result = self._update_gitignore_action.execute(repository)
        if not gitignore_result.is_success:
            return Result.failure(gitignore_result.message or "Failed to update .gitignore")

        return Result.success(repository)
