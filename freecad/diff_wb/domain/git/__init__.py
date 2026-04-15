# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: This module provides the GitRepository model representing
# a git repository with its name and absolute path, the GitPort protocol
# interface for git repository operations, and the GitService class that
# combines these to provide convenient repository detection. It is part of the
# domain layer and has no external dependencies.
"""Git domain module."""

from .git_service import GitService
from .models import GitRepository
from .ports import GitPort


__all__ = ["GitRepository", "GitPort", "GitService"]
