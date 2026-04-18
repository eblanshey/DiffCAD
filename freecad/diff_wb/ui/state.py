# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: UI layer state holder (frontend state, like Pinia/Redux).
# This module contains the UIState dataclass which serves as an in-memory state
# holder for the UI layer only. It stores the currently detected GitRepository
# and is created once at startup, reused across all git-related actions.
# Domain layer must NOT depend on this class.
"""UI layer state holder (frontend state, like Pinia/Redux)."""

from dataclasses import dataclass

from freecad.diff_wb.domain.git.models import GitRepository


@dataclass
class UIState:
    """In-memory state holder for UI layer only.

    This class is for UI/presentation layer state ONLY.
    It is analogous to frontend state management solutions like Pinia (Vue)
    or Redux (React) - it holds application-wide UI state that is accessed
    by presenters but never by domain or application layer components.

    This class stores the currently detected GitRepository.
    Created once at startup and reused across all git-related actions.

    Architecture note: Domain layer must NOT depend on this class.
    Future enhancements may add observable properties using Qt signals.
    """

    git_repository: GitRepository | None = None


__all__ = ["UIState"]
