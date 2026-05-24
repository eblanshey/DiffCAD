# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: This module provides git domain models and contracts,
# including repository representations, initialization candidates, git paths,
# the GitPort protocol, and the GitService orchestration helpers.
"""Git domain module."""

from .git_service import GitService
from .models import GitCommit, GitRepository, GitRepositoryInitCandidate
from .paths import git_path_name, is_fcstd_path, relative_git_path, to_git_path
from .ports import GitPort


__all__ = [
    "GitRepository",
    "GitRepositoryInitCandidate",
    "GitCommit",
    "GitPort",
    "GitService",
    "git_path_name",
    "is_fcstd_path",
    "relative_git_path",
    "to_git_path",
]
