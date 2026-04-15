# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains the ApplicationState dataclass which
# serves as an in-memory state holder for the UI layer only. It stores the
# currently detected GitRepository and is created once at startup, reused across
# all git-related actions. Domain layer must NOT depend on this class.
"""Application state holder for UI layer."""

from dataclasses import dataclass

from freecad.diff_wb.domain.git.models import GitRepository


@dataclass
class ApplicationState:
    """In-memory state holder for UI layer only.

    This class is for UI/presentation layer use ONLY.
    It stores the currently detected GitRepository.
    Created once at startup and reused across all git-related actions.

    Architecture note: Domain layer must NOT depend on this class.
    Future enhancements may add observable properties using Qt signals.
    """

    git_repository: GitRepository | None = None
