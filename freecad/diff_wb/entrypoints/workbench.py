# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Defines the DiffWorkbench class that integrates
# the workbench into FreeCAD's GUI with menus and toolbars.
"""FreeCAD workbench registration for Diff Workbench.

Defines the Gui.Workbench subclass used by FreeCAD to create menus/toolbars
and activate the workbench.
"""

import os

from ..infrastructure.freecad.context import get_port
from ..resources import ICONPATH


def _translate(context: str, text: str) -> str:
    return get_port().translate(context, text)


try:
    import FreeCADGui as Gui  # pylint: disable=import-error
except Exception:  # pylint: disable=broad-exception-caught
    Gui = None


if Gui is not None:

    class DiffWorkbench(Gui.Workbench):
        """Workbench class for the Diff Workbench addon."""

        MenuText = _translate("Workbench", "Diff Workbench")
        ToolTip = _translate("Workbench", "Compare document snapshots")
        Icon = os.path.join(ICONPATH, "Logo.svg")
        toolbox = [
            "DiffTakeSnapshot",
            "DiffCompare",
            "DiffSwapColumns",
        ]

        def GetClassName(self) -> str:
            """Return the class name of the workbench."""
            return "Gui::PythonWorkbench"

        def Initialize(self) -> None:
            """Called at first activation; import all commands."""
            import FreeCAD as App  # pylint: disable=import-error

            get_port().message(_translate("Log", "Switching to diff_wb") + "\n")

            qt_translate_noop = App.Qt.QT_TRANSLATE_NOOP

            # NOTE: Context for these commands must be "Workbench"
            self.appendToolbar(qt_translate_noop("Workbench", "Diff Workbench"), self.toolbox)
            self.appendMenu(qt_translate_noop("Workbench", "Diff Workbench"), self.toolbox)

        def Activated(self) -> None:
            """Called when user switches to this workbench."""
            get_port().message(_translate("Log", "Workbench diff_wb activated.") + "\n")

        def Deactivated(self) -> None:
            """Called when this workbench is deactivated."""
            get_port().message(_translate("Log", "Workbench diff_wb de-activated.") + "\n")
