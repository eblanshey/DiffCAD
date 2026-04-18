# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Global registry for UI components.
# Provides thread-safe access to presenters from entry points without
# tight coupling to the composition root.
"""Global registry for UI components."""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .presenters.diff_presenter import DiffPresenter
    from .presenters.snapshot_presenter import SnapshotPresenter


class UIRegistry:
    """Registry for UI components.

    Provides centralized access to presenters from entry points without
    tight coupling to the composition root. Note: This is designed for
    FreeCAD's single-threaded Python interpreter; thread safety is not
    guaranteed for multi-threaded scenarios.
    """

    def __init__(self) -> None:
        self._snapshot_presenter: SnapshotPresenter | None = None
        self._diff_presenter: DiffPresenter | None = None

    @property
    def snapshot_presenter(self) -> "SnapshotPresenter":
        """Get snapshot presenter.

        Raises:
            RuntimeError: If not initialized (workbench not activated)
        """
        if self._snapshot_presenter is None:
            raise RuntimeError("Snapshot presenter not initialized. Workbench must be activated first.")
        return self._snapshot_presenter

    @property
    def diff_presenter(self) -> "DiffPresenter | None":
        """Get diff presenter (may be None)."""
        return self._diff_presenter

    def register_snapshot_presenter(self, presenter: "SnapshotPresenter") -> None:
        """Register snapshot presenter."""
        self._snapshot_presenter = presenter

    def register_diff_presenter(self, presenter: "DiffPresenter") -> None:
        """Register diff presenter."""
        self._diff_presenter = presenter

    def clear(self) -> None:
        """Clear registry (for testing)."""
        self._snapshot_presenter = None
        self._diff_presenter = None


# Global instance
ui_registry = UIRegistry()


__all__ = ["UIRegistry", "ui_registry"]
