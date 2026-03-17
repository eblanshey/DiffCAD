# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the GuiPortAdapter that implements the GuiPort
# interface using FreeCAD's Qt API. It handles loading UI files and managing MDI subwindows.
"""GUI port adapter for FreeCAD Qt operations."""

from __future__ import annotations

from typing import Protocol

from ..freecad.context import FreeCadContext, get_runtime_context


class GuiPort(Protocol):
    """Interface for FreeCAD GUI operations.

    This Protocol defines operations for loading Qt UI files and
    managing MDI subwindows, allowing for test doubles.
    """

    def load_ui(self, ui_path: str) -> object:
        """Load a Qt UI file and return the widget."""
        ...

    def get_main_window(self) -> object:
        """Get the main application window."""
        ...

    def get_mdi_area(self) -> object | None:
        """Get the MDI area for subwindows, or None if not available."""
        ...

    def add_subwindow(self, *, mdi_area: object, widget: object) -> object:
        """Add a widget as an MDI subwindow and return the QMdiSubWindow."""
        ...

    def find_subwindow(self, *, mdi_area: object, title: str) -> object | None:
        """Find an existing subwindow by title, or None if not found."""
        ...


class GuiPortAdapter:
    """Runtime adapter implementing GuiPort using FreeCAD's Qt API.

    This class adapts FreeCAD's Qt API to the GuiPort interface,
    allowing domain code to work with the port abstraction while infrastructure code
    handles the actual Qt calls.
    """

    def __init__(self, ctx: FreeCadContext) -> None:
        self._ctx = ctx

    def load_ui(self, ui_path: str) -> object:
        from PySide6.QtCore import QFile
        from PySide6.QtUiTools import QUiLoader

        loader = QUiLoader()
        file = QFile(ui_path)
        if not file.open(QFile.ReadOnly):
            raise RuntimeError(f"Cannot open UI file: {ui_path}")
        widget = loader.load(file)
        file.close()
        return widget

    def get_main_window(self) -> object:
        from FreeCADGui import getMainWindow

        return getMainWindow()

    def get_mdi_area(self) -> object | None:
        main_window = self.get_main_window()
        return main_window.workspace()

    def add_subwindow(self, *, mdi_area: object, widget: object) -> object:
        subwindow = mdi_area.addSubWindow(widget)
        widget.setParent(mdi_area)
        return subwindow

    def find_subwindow(self, *, mdi_area: object, title: str) -> object | None:
        for sub in mdi_area.subWindowList():
            if sub.windowTitle() == title:
                return sub
        return None


def get_gui_port(ctx: FreeCadContext | None = None) -> GuiPort:
    """Get a GuiPort instance.

    Factory function that creates and returns a GuiPortAdapter
    instance, using the provided context or creating a runtime context if none is given.

    If no context is provided, creates a runtime context.
    Returns None if GUI is not available.
    """
    if ctx is None:
        ctx = get_runtime_context()
    if ctx.gui is None:
        raise RuntimeError("GUI not available")
    return GuiPortAdapter(ctx)
