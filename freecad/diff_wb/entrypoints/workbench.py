# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Defines the DiffWorkbench class that integrates
# the workbench into FreeCAD's GUI with menus and toolbars.
"""FreeCAD workbench registration for Diff Workbench.

Defines the Gui.Workbench subclass used by FreeCAD to create menus/toolbars
and activate the workbench.
"""

import os
import traceback
from typing import TYPE_CHECKING

from ..resources import ICONPATH
from ..utils import Log, set_logger


if TYPE_CHECKING:
    pass


_PREFERENCES_REGISTRY_ATTR = "_diff_wb_preference_pages"
_PREFERENCES_PAGE_ID = "freecad.diff_wb.ui.views.settings_preferences_page.DiffSettingsPreferencesPage"


try:
    import FreeCADGui as Gui  # pylint: disable=import-error
    from FreeCADGui import getMainWindow  # noqa: N813
except Exception as e:
    Log.exception(f"Failed to import FreeCADGui: {e}")
    Gui = None  # type: ignore[assignment]
    getMainWindow = None  # type: ignore[assignment]  # noqa: N816


if Gui is not None:

    class DiffWorkbench(Gui.Workbench):
        """Workbench class for the Diff Workbench addon."""

        _preferences_page_registered = False

        Icon = os.path.join(ICONPATH, "Logo.svg")
        toolbox = [
            "DiffOpenDiffWindow",
            "DiffRefreshRepository",
            "DiffRecomputeActiveDocument",
            "DiffRecomputeAllOpenDocuments",
            "DiffOpenAllDocumentsInRepository",
            "DiffCommit",
            # "DiffTakeSnapshot",
            # "DiffCompare",
            # "DiffSwapColumns",
        ]

        def __init__(self):
            super().__init__()
            self.MenuText = "Diff"
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
            from ..entrypoints.commands import register_commands
            from ..infrastructure.freecad.logger import FreeCADLogger
            from ..infrastructure.freecad.ports import get_freecad_runtime_context

            # Create runtime context
            ctx = get_freecad_runtime_context()

            # Create container (wires all actions/presenters)
            container = create_application_container(ctx)

            # Initialize global logger with FreeCAD logger
            set_logger(FreeCADLogger(container._freecad_port))

            # Make container globally available
            set_container(container)

            # Register commands
            register_commands()

            # Configure preferences page action dependencies for FreeCAD no-arg construction
            from ..ui.views.settings_preferences_page import DiffSettingsPreferencesPage

            DiffSettingsPreferencesPage.configure_actions(
                container.get_diff_settings_action,
                container.save_diff_settings_action,
            )

            # Register preferences page once
            self._register_preferences_page()

            # Setup toolbar and menu
            Log.info("Switching to diff_wb")
            qt_translate_noop = App.Qt.QT_TRANSLATE_NOOP
            self.appendToolbar(qt_translate_noop("Workbench", "Diff Workbench"), self.toolbox)
            self.appendMenu(qt_translate_noop("Workbench", "Diff Workbench"), self.toolbox)

        @classmethod
        def _register_preferences_page(cls) -> None:
            if cls._preferences_page_registered:
                return
            if Gui is None:
                return

            registry = getattr(Gui, _PREFERENCES_REGISTRY_ATTR, None)
            if not isinstance(registry, set):
                registry = set()
                setattr(Gui, _PREFERENCES_REGISTRY_ATTR, registry)
            if _PREFERENCES_PAGE_ID in registry:
                cls._preferences_page_registered = True
                return

            from ..ui.views.settings_preferences_page import DiffSettingsPreferencesPage

            Gui.addPreferencePage(DiffSettingsPreferencesPage, "Diff")
            registry.add(_PREFERENCES_PAGE_ID)
            cls._preferences_page_registered = True

        def Activated(self) -> None:
            """Called when user switches to this workbench."""
            Log.info("Workbench diff_wb activated.")
            self.create_or_show_diff_panel()

        def create_or_show_diff_panel(self) -> None:
            """Create the diff panel if it doesn't exist, or show/focus it if it does."""
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
            """Create UI components and register them."""
            if getMainWindow is None:
                Log.warning("FreeCADGui not available")
                return

            try:
                from PySide6.QtCore import Qt
                from PySide6.QtGui import QIcon
                from PySide6.QtWidgets import QMdiArea

                from .._container import _container
                from ..ui.composer import compose_and_register_ui

                # Get MDI area
                main_window = getMainWindow()
                mdi_area = main_window.findChild(QMdiArea)

                if mdi_area is None:
                    Log.warning("Could not get MDI area")
                    return

                # Compose UI and register presenters globally
                view = compose_and_register_ui(_container)

                # Add as MDI subwindow
                self._subwindow = mdi_area.addSubWindow(view)
                self._subwindow.setWindowTitle("Diff View")
                self._subwindow.setWindowIcon(QIcon(os.path.join(ICONPATH, "Logo.svg")))
                self._subwindow.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
                self._subwindow.resize(900, 600)
                self._subwindow.show()

                # Note: Snapshots are loaded automatically after creation via SnapshotPresenter.present_result()
                # No need to load on panel creation - commits are shown by GitRepositoryPresenter instead

                # Connect window close cleanup
                self._subwindow.destroyed.connect(self._on_subwindow_closed)

            except Exception as e:
                Log.exception(f"ERROR creating diff panel: {e} traceback: {traceback.format_exc()}")

        def _on_subwindow_closed(self) -> None:
            """Called when the diff panel subwindow is closed."""
            Log.info("Diff panel closed.")
            self._subwindow = None  # Reset reference so new one will be created on next activation
