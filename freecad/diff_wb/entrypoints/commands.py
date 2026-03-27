# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: FreeCAD command entry points for the Diff Workbench.

This module defines the FreeCAD commands that bridge user interactions
(toolbar/menu clicks) with application layer actions and UI presenters.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ..resources import ICONPATH


if TYPE_CHECKING:
    from ..ui.views.diff_panel_view import DiffPanelView


class _TakeSnapshotCommand:
    """Command to take a new snapshot of the active document."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Take Snapshot",
            "ToolTip": "Create a snapshot of the current document",
            "Pixmap": os.path.join(ICONPATH, "TakeSnapshot.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from .._container import get_container

        container = get_container()
        result = container.take_snapshot_action.execute()
        container.snapshot_presenter.present_result(result)


class _CompareCommand:
    """Command to compare against a selected snapshot."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Compare",
            "ToolTip": "Compare snapshots",
            "Pixmap": os.path.join(ICONPATH, "Compare.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from PySide6.QtWidgets import QMessageBox  # pylint: disable=import-error

        from .._container import get_container

        container = get_container()

        # Get the diff panel view from FreeCADGui
        # The view is accessed via the workbench's main window
        view = self._get_view()
        if view is None:
            QMessageBox.critical(None, "Error", "Diff panel view not found.")
            return

        # Get selected snapshot IDs from the view
        selected_ids = view.get_selected_snapshot_ids()

        # Validate: require at least 2 snapshots (use first 2 if more selected)
        # Selection order: first selected = old/from, second selected = new/to
        if len(selected_ids) < 2:
            QMessageBox.warning(
                None,
                "Selection Required",
                "Please select at least 2 snapshots to compare.",
            )
            return

        # Use only the first 2 if more than 2 are selected
        old_id = selected_ids[0]
        new_id = selected_ids[1]

        result = container.compare_snapshots_action.execute(old_id, new_id)
        if result.success and container.diff_presenter and result.diff_result is not None:
            container.diff_presenter.present_diff(result.diff_result)

    def _get_view(self) -> DiffPanelView | None:
        """Get the DiffPanelView from FreeCADGui.

        Returns:
            The DiffPanelView instance if found, None otherwise.
        """
        import FreeCADGui as Gui  # pylint: disable=import-error

        from ..ui.views.diff_panel_view import DiffPanelView

        # Get the diff panel view from FreeCADGui
        # The view is accessed via the workbench's main window
        mw = Gui.getMainWindow()
        if mw is None:
            return None

        # Find the DiffPanelView widget (assumed to be in the main window)
        for widget in mw.findChildren(DiffPanelView):
            return widget

        return None


class _SwapColumnsCommand:
    """Command to swap left/right columns in the diff view."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Swap Columns",
            "ToolTip": "Swap the left and right columns",
            "Pixmap": os.path.join(ICONPATH, "SwapColumns.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """Execute the swap columns action.

        TODO: Phase 8 - Implement when UI view exists.
        """
        # Phase 8: Will call view method to swap columns when UI is implemented
        pass


def register_commands() -> None:
    """Register the Diff Workbench commands with FreeCAD."""
    import FreeCADGui as Gui  # pylint: disable=import-error

    Gui.addCommand("DiffTakeSnapshot", _TakeSnapshotCommand())
    Gui.addCommand("DiffCompare", _CompareCommand())
    Gui.addCommand("DiffSwapColumns", _SwapColumnsCommand())
