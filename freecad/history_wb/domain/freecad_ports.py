# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Port interfaces for the Diff Workbench.
# This module defines all Protocol interfaces (contracts) for external system
# interactions. These interfaces belong in the domain layer so that application
# and domain code can depend on abstractions without importing infrastructure.
"""Port interfaces for external system interactions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .git.models import GitRepository


class DocumentObjectLike(Protocol):
    """Minimal Protocol for FreeCAD document objects used by extraction.

    This protocol intentionally includes only members needed by the snapshot
    extractor and related link-handling logic.
    """

    Name: str
    TypeId: str
    PropertiesList: list[str]

    def isDerivedFrom(self, type_id: str) -> bool: ...
    def isLink(self) -> bool: ...
    def getTypeIdOfProperty(self, name: str) -> str: ...


class ConsoleLike(Protocol):
    """Minimal Protocol for FreeCAD's console output API."""

    def PrintMessage(self, text: str) -> None: ...
    def PrintError(self, text: str) -> None: ...
    def PrintWarning(self, text: str) -> None: ...
    def PrintDebug(self, text: str) -> None: ...


class DocumentLike(Protocol):
    """Minimal Protocol for FreeCAD document operations."""

    FileName: str  # Path to the document file (empty string if unsaved)
    Name: str
    Objects: list[DocumentObjectLike]

    def getObject(self, name: str) -> DocumentObjectLike | None: ...
    def addObject(self, type_id: str, name: str) -> DocumentObjectLike: ...
    def recompute(self) -> None: ...
    def save(self) -> None: ...


class QtModule(Protocol):
    """Protocol for FreeCAD.Qt module which provides translation."""

    def translate(self, context: str, text: str) -> str: ...


class AppLike(Protocol):
    """Minimal Protocol for the FreeCAD application module."""

    ActiveDocument: DocumentLike | None
    Console: ConsoleLike

    def ParamGet(self, path: str) -> object: ...
    def translate(self, context: str, text: str) -> str: ...
    def GetString(self, name: str) -> str: ...
    def listDocuments(self) -> dict[str, DocumentLike]: ...
    def openDocument(self, filename: str) -> DocumentLike: ...
    def newDocument(self, name: str) -> DocumentLike: ...

    @property
    def Qt(self) -> QtModule: ...


class GuiDocumentLike(Protocol):
    """Minimal Protocol for FreeCAD GUI document operations."""

    @property
    def Modified(self) -> bool: ...
    def getViewProvider(self, obj: object) -> object | None: ...


class GuiLike(Protocol):
    """Minimal Protocol for the FreeCAD GUI module."""

    def getDocument(self, doc_name: str) -> GuiDocumentLike | None: ...
    def getMainWindow(self) -> object | None: ...


@dataclass(frozen=True)
class FreeCadContext:
    """Bundle of runtime bindings for the Diff Workbench.

    This wrapper allows code to be written against Protocols
    and enables unit tests to provide a fake context without importing FreeCAD.

    Attributes:
        app: The FreeCAD application module (AppLike protocol)
        gui: The FreeCAD GUI module (GuiLike protocol)
    """

    app: AppLike
    gui: GuiLike


class FreeCadPort(Protocol):
    """Interface for FreeCAD document operations.

    This Protocol defines the minimal set of FreeCAD operations needed
    by the Diff Workbench, allowing for test doubles in unit tests.
    """

    def get_active_document(self) -> DocumentLike | None:
        """Get the active document, or None if no document is open."""
        ...

    def get_all_open_documents(self) -> list[DocumentLike]:
        """Get all open documents.

        Returns:
            A list of DocumentLike objects representing all open documents.
            Returns an empty list if no documents are open.
        """
        ...

    def open_document(self, path: str) -> DocumentLike:
        """Open a document from disk in FreeCAD."""
        ...

    def get_object(self, doc: DocumentLike, name: str) -> DocumentObjectLike | None:
        """Get a document object by name."""
        ...

    def save_document(self, doc: DocumentLike) -> None:
        """Persist an open document to disk."""
        ...

    def save_document_if_modified(self, doc: DocumentLike) -> bool:
        """Persist an open document only when GUI marks it modified."""
        ...

    def try_recompute_active_document(self) -> None:
        """Recompute the active document if one exists."""
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

    def debug(self, text: str) -> None:
        """Log a debug message to the FreeCAD console."""
        ...

    def get_main_window(self) -> object | None:
        """Get the FreeCAD main window widget, or None if not available."""
        ...


class AppPort(Protocol):
    """Interface for application-level operations.

    This Protocol defines operations like translation that are provided
    by the FreeCAD application, allowing for test doubles.
    """

    def translate(self, context: str, text: str) -> str:
        """Translate the given text in the provided translation context."""
        ...


class FreeCadFileManagerPort(Protocol):
    """Interface for FreeCAD file materialization and content lookup.

    This Protocol defines the contract for preparing FreeCAD document revisions
    from git commits, staging, or working tree files. Internal storage layout,
    archive reuse, and extraction are implementation details of the adapter.

    Attributes:
        prepare_document_revision: Materialize and extract document revision.
        find_extracted_file: Find file by name inside extracted document tree.
    """

    def prepare_document_revision(
        self,
        repo: GitRepository,
        git_path: str,
        revision: str,
    ) -> Path | None:
        """Materialize and extract requested revision; return extraction root path.

        Args:
            repo: Git repository model.
            git_path: Relative path to FCStd file within repository.
            revision: "working", "staging", or commit reference.

        Returns:
            Path to extraction root directory, or None if preparation fails.

        Notes:
            Internal implementation handles source selection (staging/working/commit),
            storage layout, archive reuse, and safe extraction.
        """
        ...

    def find_extracted_file(self, extract_root: Path, file_name: str) -> Path | None:
        """Find file by name inside extracted document tree.

        Args:
            extract_root: Root directory of extracted FCStd archive.
            file_name: Name of file to find (e.g., "Pad.Shape.brp").

        Returns:
            Path to BREP file if found, None otherwise.
        """
        ...


__all__ = [
    "FreeCadContext",
    "FreeCadPort",
    "AppPort",
    "FreeCadFileManagerPort",
    "DocumentLike",
    "DocumentObjectLike",
    "ConsoleLike",
    "QtModule",
    "AppLike",
    "GuiLike",
    "GuiDocumentLike",
]
