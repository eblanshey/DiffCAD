# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Defines the DiffWorkbench class that integrates
# the workbench into FreeCAD's GUI with menus and toolbars.
"""FreeCAD workbench registration for Diff Workbench.

Defines the Gui.Workbench subclass used by FreeCAD to create menus/toolbars
and activate the workbench.
"""

import os

from ..resources import ICONPATH
from ..utils import Log, set_logger


try:
    import FreeCADGui as Gui  # pylint: disable=import-error
    from FreeCADGui import getMainWindow  # noqa: N813
except Exception:  # pylint: disable=broad-exception-caught
    Gui = None
    getMainWindow = None  # noqa: N816


if Gui is not None:

    class DiffWorkbench(Gui.Workbench):
        """Workbench class for the Diff Workbench addon."""

        Icon = os.path.join(ICONPATH, "Logo.svg")
        toolbox = [
            "DiffTakeSnapshot",
            "DiffCompare",
            "DiffSwapColumns",
        ]

        def __init__(self):
            super().__init__()
            self.MenuText = "Diff Workbench"
            self.ToolTip = "Compare document snapshots"
            self._subwindow = None  # Store reference to MDI subwindow

        def GetClassName(self) -> str:
            """Return the class name of the workbench."""
            return "Gui::PythonWorkbench"

        def Initialize(self) -> None:
            """Called at first activation; create container and register commands."""
            import FreeCAD as App  # pylint: disable=import-error

            from .._container import set_container
            from ..application.di.container import create_application_container
            from ..domain.snapshots.repository import InMemorySnapshotRepository
            from ..entrypoints.commands import register_commands
            from ..infrastructure.freecad.logger import FreeCADLogger
            from ..infrastructure.freecad.ports import get_freecad_runtime_context

            # Create runtime context
            ctx = get_freecad_runtime_context()

            # Create snapshot repository
            snapshot_repo = InMemorySnapshotRepository()

            # Create container (wires all actions/presenters)
            container = create_application_container(ctx, snapshot_repo=snapshot_repo)

            # Initialize global logger with FreeCAD logger
            set_logger(FreeCADLogger(container._freecad_port))

            # Make container globally available
            set_container(container)

            # Register commands
            register_commands()

            # Setup toolbar and menu
            Log.info("Switching to diff_wb")
            qt_translate_noop = App.Qt.QT_TRANSLATE_NOOP
            self.appendToolbar(qt_translate_noop("Workbench", "Diff Workbench"), self.toolbox)
            self.appendMenu(qt_translate_noop("Workbench", "Diff Workbench"), self.toolbox)

        def Activated(self) -> None:
            """Called when user switches to this workbench."""
            Log.info("Workbench diff_wb activated.")

            # Create subwindow if it doesn't exist (was closed or never created)
            if self._subwindow is None:
                self._create_diff_panel()
            else:
                # Show existing subwindow and bring to front
                self._subwindow.show()
                self._subwindow.raise_()
                self._subwindow.setFocus()

        def Deactivated(self) -> None:
            """Called when this workbench is deactivated."""
            Log.info("Workbench diff_wb de-activated.")

            # Don't hide the subwindow - let it stay visible like other FreeCAD panels
            # This prevents interference with FreeCAD's default view management
            # Presenter reference is kept alive; cleaned up by _on_subwindow_closed if window closes

        def _create_diff_panel(self) -> None:
            """Create the 3-column diff panel as an MDI subwindow."""
            if getMainWindow is None:
                Log.warning("FreeCADGui not available")
                return

            try:
                from PySide6.QtCore import Qt
                from PySide6.QtWidgets import QMdiArea

                from .._container import _container  # By now _container is set
                from ..ui import DiffPanelView
                from ..ui.presenters.snapshot_presenter import SnapshotPresenter

                # Get MDI area from FreeCAD's main window
                main_window = getMainWindow()
                mdi_area = main_window.findChild(QMdiArea)

                if mdi_area is None:
                    Log.warning("Could not get MDI area")
                    return

                # Create panel
                panel = DiffPanelView()

                # Update container's snapshot_presenter to use the real DiffPanelView
                # This fixes the bug where commands were using NullSnapshotView instead of the actual UI
                _container.snapshot_presenter = SnapshotPresenter(
                    view=panel,
                    list_snapshots_action=_container.list_snapshots_action,
                )

                # Update container's diff_presenter to use the real DiffPanelView
                # This fixes the bug where compare command couldn't display diff results
                from ..ui.presenters.diff_presenter import DiffPresenter

                _container.diff_presenter = DiffPresenter(view=panel)

                # Add as subwindow (QMdiSubWindow created automatically)
                # Do NOT call setParent - let FreeCAD handle it
                self._subwindow = mdi_area.addSubWindow(panel)

                # Configure subwindow
                self._subwindow.setWindowTitle("Diff View")

                # Set proper cleanup attribute
                self._subwindow.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

                # Set a reasonable default size that doesn't interfere with other views
                self._subwindow.resize(900, 600)

                # Show normally (not maximized) to coexist with other MDI views
                self._subwindow.show()

                # Load snapshots after showing the panel
                _container.snapshot_presenter.load_snapshots()

                # Connect destroyed signal to reset reference when window is closed
                # QMdiSubWindow inherits from QWidget which inherits from QObject
                self._subwindow.destroyed.connect(self._on_subwindow_closed)
            except Exception as e:
                import traceback

                Log.error(f"ERROR creating diff panel: {e}")
                Log.error(traceback.format_exc())

        def _on_subwindow_closed(self) -> None:
            """Called when the diff panel subwindow is closed."""
            Log.info("Diff panel closed.")
            self._subwindow = None  # Reset reference so new one will be created on next activation
