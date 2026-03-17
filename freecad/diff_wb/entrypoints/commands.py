# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Registers FreeCAD commands for snapshot management
# and diff comparison operations in the workbench toolbar.
"""FreeCAD command registrations for the Diff Workbench.

This module defines the toolbar/menu commands for snapshot management
and diff comparison operations.
"""

import os

from ..infrastructure.freecad.app_port import get_app_port
from ..resources import ICONPATH


_translate = get_app_port().translate


class _TakeSnapshotCommand:
    """Command to take a new snapshot of the active document."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": _translate("Workbench", "Take Snapshot"),
            "ToolTip": _translate("Workbench", "Create a snapshot of the current document"),
            "Pixmap": os.path.join(ICONPATH, "TakeSnapshot.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """Execute the take snapshot action."""
        pass


class _CompareCommand:
    """Command to compare against a selected snapshot."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": _translate("Workbench", "Compare"),
            "ToolTip": _translate("Workbench", "Compare snapshots"),
            "Pixmap": os.path.join(ICONPATH, "Compare.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """Execute the compare action."""
        pass


class _SwapColumnsCommand:
    """Command to swap left/right columns in the diff view."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": _translate("Workbench", "Swap Columns"),
            "ToolTip": _translate("Workbench", "Swap the left and right columns"),
            "Pixmap": os.path.join(ICONPATH, "SwapColumns.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """Execute the swap columns action."""
        pass


def register_commands() -> None:
    """Register the Diff Workbench commands with FreeCAD."""
    import FreeCADGui as Gui  # pylint: disable=import-error

    Gui.addCommand("DiffTakeSnapshot", _TakeSnapshotCommand())
    Gui.addCommand("DiffCompare", _CompareCommand())
    Gui.addCommand("DiffSwapColumns", _SwapColumnsCommand())
