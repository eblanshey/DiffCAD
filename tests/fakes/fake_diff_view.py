"""File responsibility: Fake implementation of DiffView protocol for testing."""

from typing import Any

from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation, PropertyPresentation


class FakeDiffView:
    """Fake implementation of DiffView for testing DiffPresenter.

    Captures method calls for verification in tests instead of rendering UI.
    """

    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []
        self._last_call: dict[str, Any] | None = None

    def show_loading(self) -> None:
        """Capture loading call instead of showing UI."""
        self._record_call("show_loading")

    def show_diff_tree(self, nodes: list[NodePresentation]) -> None:
        """Capture diff tree call instead of showing UI."""
        self._record_call("show_diff_tree", nodes=nodes)

    def show_summary(self, added: int, deleted: int, modified: int) -> None:
        """Capture summary call instead of showing UI."""
        self._record_call("show_summary", added=added, deleted=deleted, modified=modified)

    def show_error(self, message: str) -> None:
        """Capture error call instead of showing UI."""
        self._record_call("show_error", message=message)

    def show_properties(self, properties: list[PropertyPresentation]) -> None:
        """Capture properties call instead of showing UI."""
        self._record_call("show_properties", properties=properties)

    def _record_call(self, method: str, **kwargs: Any) -> dict[str, Any]:
        """Record a method call for later verification."""
        call: dict[str, Any] = {"method": method, **kwargs}
        self._calls.append(call)
        self._last_call = call
        return call

    def get_call_count(self) -> int:
        """Return number of calls logged."""
        return len(self._calls)

    def get_calls(self) -> list[dict[str, Any]]:
        """Return all logged calls."""
        return self._calls.copy()
