# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Global registry for UI components.
# Provides thread-safe access to presenters from entry points without
# tight coupling to the composition root.
"""Global registry for UI components."""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .presenters.diff_presenter import DiffPresenter
    from .presenters.git_repository_presenter import GitRepositoryPresenter
    from .state import UIState


class UIRegistry:
    """Registry for UI components.

    Provides centralized access to presenters from entry points without
    tight coupling to the composition root. Note: This is designed for
    FreeCAD's single-threaded Python interpreter; thread safety is not
    guaranteed for multi-threaded scenarios.
    """

    def __init__(self) -> None:
        self._diff_presenter: DiffPresenter | None = None
        self._git_repository_presenter: GitRepositoryPresenter | None = None
        self._ui_state: UIState | None = None

    @property
    def diff_presenter(self) -> "DiffPresenter | None":
        """Get diff presenter (may be None)."""
        return self._diff_presenter

    @property
    def ui_state(self) -> "UIState":
        """Get UI state.

        Raises:
            RuntimeError: If not initialized
        """
        if self._ui_state is None:
            raise RuntimeError("UI state not initialized. Workbench must be activated first.")
        return self._ui_state

    @property
    def git_repository_presenter(self) -> "GitRepositoryPresenter":
        """Get git repository presenter.

        Raises:
            RuntimeError: If not initialized
        """
        if self._git_repository_presenter is None:
            raise RuntimeError("Git repository presenter not initialized.")
        return self._git_repository_presenter

    def register_ui_state(self, state: "UIState") -> None:
        """Register UI state."""
        self._ui_state = state

    def register_git_repository_presenter(self, presenter: "GitRepositoryPresenter") -> None:
        """Register git repository presenter."""
        self._git_repository_presenter = presenter

    def register_diff_presenter(self, presenter: "DiffPresenter") -> None:
        """Register diff presenter."""
        self._diff_presenter = presenter

    def clear(self) -> None:
        """Clear registry (for testing)."""
        self._diff_presenter = None
        self._git_repository_presenter = None
        self._ui_state = None


# Global instance
ui_registry = UIRegistry()


__all__ = ["UIRegistry", "ui_registry"]
