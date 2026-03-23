# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Consolidated FreeCAD port interfaces and adapters.

This module provides all port protocols, adapter classes, and factory functions
for FreeCAD integration.

All factory functions require an explicit FreeCadContext parameter - no automatic
context creation. This enforces explicit dependency injection and keeps the domain
and application layers testable without FreeCAD dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ConsoleLike(Protocol):
    """Minimal Protocol for FreeCAD's console output API."""

    def PrintMessage(self, text: str) -> None: ...
    def PrintError(self, text: str) -> None: ...
    def PrintWarning(self, text: str) -> None: ...


class DocumentLike(Protocol):
    """Minimal Protocol for FreeCAD document operations."""

    Objects: list[object]

    def getObject(self, name: str) -> object | None: ...
    def recompute(self) -> None: ...


class AppLike(Protocol):
    """Minimal Protocol for the FreeCAD application module."""

    ActiveDocument: DocumentLike | None
    Console: ConsoleLike

    def ParamGet(self, path: str) -> object: ...
    def translate(self, context: str, text: str) -> str: ...
    def GetString(self, name: str) -> str: ...


class GuiLike(Protocol):
    """Minimal Protocol for the FreeCAD GUI module."""

    def update(self) -> None: ...


@dataclass(frozen=True)
class FreeCadContext:
    """Bundle of runtime bindings for the Diff Workbench.

    This wrapper allows code to be written against Protocols
    and enables unit tests to provide a fake context without importing FreeCAD.

    Attributes:
        app: The FreeCAD application module (AppLike protocol)
        gui: The FreeCAD GUI module if available, None otherwise
    """

    app: AppLike
    gui: GuiLike | None = None


def get_freecad_runtime_context() -> FreeCadContext:
    """Return a context wired to the real FreeCAD runtime modules.

    This function should only be called from the composition root (init_gui.py)
    when FreeCAD is actually running.

    Returns:
        FreeCadContext with real FreeCAD/FreeCADGui modules
    """
    import FreeCAD as App

    try:
        import FreeCADGui as Gui
    except Exception:  # pylint: disable=broad-exception-caught
        Gui = None  # type: ignore[assignment]

    return FreeCadContext(app=App, gui=Gui)  # type: ignore[arg-type]


class FreeCadPort(Protocol):
    """Interface for FreeCAD document operations.

    This Protocol defines the minimal set of FreeCAD operations needed
    by the Diff Workbench, allowing for test doubles in unit tests.
    """

    def get_active_document(self) -> object | None:
        """Get the active document, or None if no document is open."""
        ...

    def get_object(self, doc: object, name: str) -> object | None:
        """Get a document object by name."""
        ...

    def try_recompute_active_document(self) -> None:
        """Recompute the active document if one exists."""
        ...

    def try_update_gui(self) -> None:
        """Trigger a GUI update if the GUI is available."""
        ...

    def log(self, text: str) -> None:
        """Log a message to the FreeCAD console."""
        ...

    def warn(self, text: str) -> None:
        """Show a warning message."""
        ...

    def message(self, text: str) -> None:
        """Show an informational message."""
        ...

    def translate(self, context: str, text: str) -> str:
        """Translate text using FreeCAD's translation system."""
        ...


class FreeCadPortAdapter:
    """Runtime adapter implementing FreeCadPort using real FreeCAD APIs.

    This class adapts the real FreeCAD API to the FreeCadPort interface,
    allowing domain code to work with the port abstraction while infrastructure code
    handles the actual FreeCAD calls.
    """

    def __init__(self, ctx: FreeCadContext) -> None:
        self._ctx = ctx

    def get_active_document(self) -> object | None:
        return self._ctx.app.ActiveDocument

    def get_object(self, doc: DocumentLike, name: str) -> object | None:
        return doc.getObject(name)

    def try_recompute_active_document(self) -> None:
        doc = self._ctx.app.ActiveDocument
        if doc is not None:
            doc.recompute()

    def try_update_gui(self) -> None:
        if self._ctx.gui is not None:
            self._ctx.gui.update()

    def log(self, text: str) -> None:
        self._ctx.app.Console.PrintMessage(text + "\n")

    def warn(self, text: str) -> None:
        self._ctx.app.Console.PrintWarning(text + "\n")

    def message(self, text: str) -> None:
        self._ctx.app.Console.PrintMessage(text + "\n")

    def translate(self, context: str, text: str) -> str:
        return self._ctx.app.translate(context, text)


def get_port(ctx: FreeCadContext) -> FreeCadPort:
    """Get a FreeCadPort instance.

    Factory function that creates and returns a FreeCadPortAdapter
    instance using the provided context.

    Args:
        ctx: FreeCAD runtime context (mandatory)

    Returns:
        FreeCadPortAdapter instance
    """
    return FreeCadPortAdapter(ctx)  # type: ignore[return-value]


class AppPort(Protocol):
    """Interface for application-level operations.

    This Protocol defines operations like translation that are provided
    by the FreeCAD application, allowing for test doubles.
    """

    def translate(self, context: str, text: str) -> str:
        """Translate the given text in the provided translation context."""
        ...


class AppPortAdapter:
    """Runtime adapter implementing AppPort using FreeCAD's translation API."""

    def __init__(self, ctx: FreeCadContext) -> None:
        self._ctx = ctx

    def translate(self, context: str, text: str) -> str:
        return self._ctx.app.translate(context, text)


def get_app_port(ctx: FreeCadContext) -> AppPort:
    """Get an AppPort instance.

    Factory function that creates and returns an AppPortAdapter
    instance using the provided context.

    Args:
        ctx: FreeCAD runtime context (mandatory)

    Returns:
        AppPortAdapter instance
    """
    return AppPortAdapter(ctx)


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

    def get_mdi_area(self) -> Any:
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

    def get_mdi_area(self) -> Any:
        main_window: Any = self.get_main_window()
        return main_window.workspace()

    def add_subwindow(self, *, mdi_area: Any, widget: object) -> object:
        subwindow = mdi_area.addSubWindow(widget)
        widget.setParent(mdi_area)  # type: ignore[attr-defined]
        return subwindow

    def find_subwindow(self, *, mdi_area: Any, title: str) -> Any:
        for sub in mdi_area.subWindowList():
            if sub.windowTitle() == title:
                return sub
        return None


def get_gui_port(ctx: FreeCadContext) -> GuiPort:
    """Get a GuiPort instance.

    Factory function that creates and returns a GuiPortAdapter
    instance using the provided context.

    Args:
        ctx: FreeCAD runtime context (mandatory)

    Returns:
        GuiPortAdapter instance

    Raises:
        RuntimeError: If GUI is not available
    """
    if ctx.gui is None:
        raise RuntimeError("GUI not available")
    return GuiPortAdapter(ctx)


__all__ = [
    "FreeCadContext",
    "get_freecad_runtime_context",
    "get_port",
    "get_app_port",
    "get_gui_port",
    "FreeCadPort",
    "AppPort",
    "GuiPort",
]
