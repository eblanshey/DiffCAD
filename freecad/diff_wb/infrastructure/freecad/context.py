# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the FreeCadContext wrapper for dependency
# injection and the FreeCadPortAdapter that implements the FreeCadPort interface using
# the real FreeCAD API. It also provides the get_runtime_context() and get_port() helper
# functions for easy access to the runtime context and port.
"""FreeCAD runtime context and port adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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

    def translate(self, context: str, text: str) -> str: ...


class GuiLike(Protocol):
    """Minimal Protocol for the FreeCAD GUI module."""

    pass


@dataclass(frozen=True)
class FreeCadContext:
    """Bundle of runtime bindings for the Diff Workbench.

    This wrapper allows code to be written against Protocols
    and enables unit tests to provide a fake context without importing FreeCAD.
    """

    app: AppLike
    gui: GuiLike | None = None


def get_runtime_context() -> FreeCadContext:
    """Return a context wired to the real FreeCAD runtime modules."""
    import FreeCAD as App

    try:
        import FreeCADGui as Gui
    except Exception:  # pylint: disable=broad-exception-caught
        Gui = None

    return FreeCadContext(app=App, gui=Gui)


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

    def get_object(self, doc: object, name: str) -> object | None:
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


def get_port(ctx: FreeCadContext | None = None) -> FreeCadPort:
    """Get a FreeCadPort instance.

    Factory function that creates and returns a FreeCadPortAdapter
    instance, using the provided context or creating a runtime context if none is given.

    If no context is provided, creates a runtime context.
    """
    if ctx is None:
        ctx = get_runtime_context()
    return FreeCadPortAdapter(ctx)
