# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Initialize a new git repository in a selected directory
# after validating it is not already inside an existing repository.
"""Application action for git repository initialization."""

from __future__ import annotations

import os

from ...domain.git.git_service import GitService
from .result_models import Result


class InitializeGitRepositoryAction:
    """Initialize git repository in selected directory."""

    def __init__(self, git_service: GitService) -> None:
        self._git_service = git_service

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

        return Result.success(repository)
