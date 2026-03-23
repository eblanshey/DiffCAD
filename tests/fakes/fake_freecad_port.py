"""File responsibility: Fake FreeCAD port for testing."""

from freecad.diff_wb.infrastructure.freecad.ports import FreeCadPort


class FakeFreeCadPort(FreeCadPort):
    """Fake implementation of FreeCADPort for unit testing."""

    def __init__(self, active_document: object = None) -> None:
        """Initialize with optional active document.

        Args:
            active_document: Mock document object or None
        """
        self._active_document: object | None = active_document
        self._call_log: list[str] = []  # Track method calls for verification

    def get_active_document(self) -> object | None:
        """Return the configured active document."""
        self._call_log.append("get_active_document")
        return self._active_document

    def get_object(self, doc: object, name: str) -> object | None:
        """Return None (not implemented in fake)."""
        self._call_log.append(f"get_object:{name}")
        return None

    def try_recompute_active_document(self) -> None:
        """Log the call (not actually recomputing)."""
        self._call_log.append("try_recompute_active_document")

    def try_update_gui(self) -> None:
        """Log the call (not actually updating GUI)."""
        self._call_log.append("try_update_gui")

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
