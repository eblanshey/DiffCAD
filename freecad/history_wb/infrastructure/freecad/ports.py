# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: FreeCAD port adapters and factory functions.

This module provides adapter classes and factory functions that implement
the port interfaces defined in domain.ports. It adapts the real FreeCAD API
to the port abstractions, allowing domain/application code to remain independent
of FreeCAD-specific implementations.

All factory functions require an explicit FreeCadContext parameter - no automatic
context creation. This enforces explicit dependency injection and keeps the domain
and application layers testable without FreeCAD dependencies.
"""

from __future__ import annotations

from ...domain.freecad_ports import (
    AppPort,
    DocumentLike,
    FreeCadContext,
    FreeCadPort,
)
from ...utils import Log


def get_freecad_runtime_context() -> FreeCadContext:
    """Return a context wired to the real FreeCAD runtime modules.

    This function should only be called from the composition root (init_gui.py)
    when FreeCAD is actually running.

    Returns:
        FreeCadContext with real FreeCAD module
    """
    import FreeCAD as App
    import FreeCADGui as Gui

    return FreeCadContext(app=App, gui=Gui)  # type: ignore[arg-type]


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

    def get_all_open_documents(self) -> list[DocumentLike]:
        docs_dict = self._ctx.app.listDocuments()
        return list(docs_dict.values())

    def open_document(self, path: str) -> DocumentLike:
        return self._ctx.app.openDocument(path)

    def get_object(self, doc: DocumentLike, name: str) -> object | None:
        return doc.getObject(name)

    def save_document(self, doc: DocumentLike) -> None:
        doc.save()

    def _get_gui_doc_modified(self, doc: DocumentLike) -> bool:
        doc_name = getattr(doc, "Name", "")
        if not doc_name:
            return False
        try:
            gui_doc = self._ctx.gui.getDocument(doc_name)
        except (AttributeError, RuntimeError, ReferenceError, ValueError, TypeError) as exc:
            Log.warning(f"Failed to get GUI document '{doc_name}': {exc}")
            return False
        if gui_doc is None:
            return False
        gui_doc_typed = gui_doc
        try:
            return bool(gui_doc_typed.Modified)
        except (AttributeError, RuntimeError, ReferenceError, ValueError, TypeError) as exc:
            Log.warning(f"Failed to check modified state for GUI document '{doc_name}': {exc}")
            return False

    def save_document_if_modified(self, doc: DocumentLike) -> bool:
        if not self._get_gui_doc_modified(doc):
            return False
        doc.save()
        return True

    def try_recompute_active_document(self) -> None:
        doc = self._ctx.app.ActiveDocument
        if doc is not None:
            doc.recompute()

    def log(self, text: str) -> None:
        self._ctx.app.Console.PrintMessage(text + "\n")

    def warn(self, text: str) -> None:
        self._ctx.app.Console.PrintWarning(text + "\n")

    def message(self, text: str) -> None:
        self._ctx.app.Console.PrintMessage(text + "\n")

    def debug(self, text: str) -> None:
        self._ctx.app.Console.PrintDebug(text + "\n")

    def translate(self, context: str, text: str) -> str:
        try:
            qt_obj = self._ctx.app.Qt
        except AttributeError:
            # Fall back to simple translation if Qt not available
            return text.replace(" ", "_").lower()
        result = qt_obj.translate(context, text)
        return result

    def get_main_window(self) -> object | None:
        return self._ctx.gui.getMainWindow()


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


class AppPortAdapter:
    """Runtime adapter implementing AppPort using FreeCAD's translation API."""

    def __init__(self, ctx: FreeCadContext) -> None:
        self._ctx = ctx

    def translate(self, context: str, text: str) -> str:
        try:
            qt_obj = self._ctx.app.Qt
        except AttributeError:
            # Fall back to simple translation if Qt not available
            return text.replace(" ", "_").lower()
        result = qt_obj.translate(context, text)
        return result


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


__all__ = [
    "FreeCadContext",
    "get_freecad_runtime_context",
    "get_port",
    "get_app_port",
    "FreeCadPort",
    "AppPort",
    "FreeCadPortAdapter",
    "AppPortAdapter",
]
