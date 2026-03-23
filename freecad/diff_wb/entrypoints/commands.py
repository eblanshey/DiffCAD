# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: FreeCAD command entry points for the Diff Workbench.

This module defines the FreeCAD commands that bridge user interactions
(toolbar/menu clicks) with application layer actions and UI presenters.
"""

import os

from .._container import _container
from ..application.actions.commands.compare_snapshots import CompareSnapshotsAction
from ..application.actions.commands.take_snapshot import TakeSnapshotAction
from ..application.di.container import ApplicationContainer
from ..resources import ICONPATH
from ..ui.presenters.diff_presenter import DiffPresenter
from ..ui.presenters.snapshot_presenter import SnapshotPresenter


class _TakeSnapshotCommand:
    """Command to take a new snapshot of the active document."""

    def __init__(self, action: TakeSnapshotAction, presenter: SnapshotPresenter) -> None:
        """Initialize with wired action and presenter.

        Args:
            action: TakeSnapshotAction to execute snapshot creation
            presenter: SnapshotPresenter to display results
        """
        self._action = action
        self._presenter = presenter

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": _container.translate("Workbench", "Take Snapshot"),
            "ToolTip": _container.translate("Workbench", "Create a snapshot of the current document"),
            "Pixmap": os.path.join(ICONPATH, "TakeSnapshot.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        result = self._action.execute()
        self._presenter.present_result(result)


class _CompareCommand:
    """Command to compare against a selected snapshot."""

    def __init__(
        self,
        action: CompareSnapshotsAction,
        presenter: DiffPresenter | None,
    ) -> None:
        """Initialize with wired action and optional presenter.

        Args:
            action: CompareSnapshotsAction to execute comparison
            presenter: Optional DiffPresenter to display diff results
        """
        self._action = action
        self._presenter = presenter

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": _container.translate("Workbench", "Compare"),
            "ToolTip": _container.translate("Workbench", "Compare snapshots"),
            "Pixmap": os.path.join(ICONPATH, "Compare.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        # Phase 8: Get snapshot IDs from UI selection
        # TODO: Phase 8 - Implement UI dialog for snapshot selection
        old_id = self._get_selected_old_snapshot()
        new_id = self._get_selected_new_snapshot()

        result = self._action.execute(old_id, new_id)
        if result.success and self._presenter and result.diff_result is not None:
            self._presenter.present_diff(result.diff_result)

    def _get_selected_old_snapshot(self) -> str:
        """Get the selected old snapshot ID from UI.

        Returns:
            The ID of the snapshot selected as the "old" snapshot.

        Raises:
            NotImplementedError: Phase 8 - UI selection not yet implemented.
        """
        raise NotImplementedError("Phase 8 - UI selection not yet implemented")

    def _get_selected_new_snapshot(self) -> str:
        """Get the selected new snapshot ID from UI.

        Returns:
            The ID of the snapshot selected as the "new" snapshot.

        Raises:
            NotImplementedError: Phase 8 - UI selection not yet implemented.
        """
        raise NotImplementedError("Phase 8 - UI selection not yet implemented")


class _SwapColumnsCommand:
    """Command to swap left/right columns in the diff view."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": _container.translate("Workbench", "Swap Columns"),
            "ToolTip": _container.translate("Workbench", "Swap the left and right columns"),
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


def register_commands(container: ApplicationContainer) -> None:
    """Register the Diff Workbench commands with FreeCAD.

    Args:
        container: Application container with wired actions and presenters
    """
    import FreeCADGui as Gui  # pylint: disable=import-error

    Gui.addCommand(
        "DiffTakeSnapshot",
        _TakeSnapshotCommand(
            action=container.take_snapshot_action,
            presenter=container.snapshot_presenter,
        ),
    )
    Gui.addCommand(
        "DiffCompare",
        _CompareCommand(
            action=container.compare_snapshots_action,
            presenter=container.diff_presenter,
        ),
    )
    Gui.addCommand("DiffSwapColumns", _SwapColumnsCommand())
