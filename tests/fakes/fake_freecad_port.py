"""File responsibility: Fake FreeCAD port for testing."""

from typing import cast

from freecad.diff_wb.domain.freecad_ports import DocumentLike, FreeCadPort


class FakeFreeCadPort(FreeCadPort):
    """Fake implementation of FreeCADPort for unit testing."""

    def __init__(
        self,
        active_document: object | None = None,
        open_documents: list[object] | None = None,
    ) -> None:
        """Initialize with optional active document and open documents.

        Args:
            active_document: Mock document object or None
            open_documents: List of mock document objects or empty list
        """
        self._active_document: object | None = active_document
        self._open_documents: list[DocumentLike] = (
            cast(list[DocumentLike], open_documents) if open_documents is not None else []
        )
        self._call_log: list[str] = []  # Track method calls for verification

    def get_active_document(self) -> DocumentLike | None:
        """Return the configured active document."""
        self._call_log.append("get_active_document")
        return self._active_document  # type: ignore[return-value]

    def get_all_open_documents(self) -> list[DocumentLike]:
        """Return the configured open documents."""
        self._call_log.append("get_all_open_documents")
        return self._open_documents

    def get_object(self, doc: object, name: str) -> object | None:
        """Return None (not implemented in fake)."""
        self._call_log.append(f"get_object:{name}")
        return None

    def save_document(self, doc: DocumentLike) -> None:
        """Call save on the provided document."""
        self._call_log.append("save_document")
        doc.save()

    def try_recompute_active_document(self) -> None:
        """Log the call (not actually recomputing)."""
        self._call_log.append("try_recompute_active_document")

    def log(self, text: str) -> None:
        """Log the call (not actually logging)."""
        self._call_log.append(f"log:{text}")

    def warn(self, text: str) -> None:
        """Log the call (not actually warning)."""
        self._call_log.append(f"warn:{text}")

    def message(self, text: str) -> None:
        """Log the call (not actually messaging)."""
        self._call_log.append(f"message:{text}")

    def translate(self, context: str, text: str) -> str:
        """Return text unchanged (not implementing translation)."""
        self._call_log.append(f"translate:{context}:{text}")
        return text
