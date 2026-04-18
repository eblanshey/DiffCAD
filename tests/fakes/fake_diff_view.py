"""File responsibility: Fake implementation of DiffView protocol for testing."""

from collections.abc import Callable
from typing import Any

from freecad.diff_wb.domain.git.models import GitRepository
from freecad.diff_wb.ui.presenters.presentation_models import (
    DiffTreePresentation,
    NodePresentation,
    PropertyPresentation,
)


class FakeDiffView:
    """Fake implementation of DiffView protocol for testing DiffPresenter.

    Captures method calls for verification in tests instead of rendering UI.
    """

    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []
        self._last_call: dict[str, Any] | None = None
        self._refresh_callback: Callable[[], None] | None = None
        self._history_selection_callback: Callable[[Any], None] | None = None
        self._add_button_callback: Callable[[str], None] | None = None

    def show_loading(self) -> None:
        """Capture loading call instead of showing UI."""
        self._record_call("show_loading")

    def show_diff_tree(self, nodes: list[NodePresentation], git_path: str = "") -> None:
        """Capture diff tree call instead of showing UI."""
        self._record_call("show_diff_tree", nodes=nodes, git_path=git_path)

    def show_diff_trees(self, diff_trees: list[DiffTreePresentation]) -> None:
        """Capture multiple diff trees call instead of showing UI.

        Args:
            diff_trees: List of DiffTreePresentation objects to display.
                       Each represents a diff tree for one document.
        """
        self._record_call("show_diff_trees", diff_trees=diff_trees)

    def show_summary(self, added: int, deleted: int, modified: int) -> None:
        """Capture summary call instead of showing UI."""
        self._record_call("show_summary", added=added, deleted=deleted, modified=modified)

    def show_error(self, message: str) -> None:
        """Capture error call instead of showing UI."""
        self._record_call("show_error", message=message)

    def show_properties(self, properties: list[PropertyPresentation]) -> None:
        """Capture properties call instead of showing UI."""
        self._record_call("show_properties", properties=properties)

    def show_repository(self, repo: GitRepository | None) -> None:
        """Capture repository display call instead of showing UI."""
        self._record_call("show_repository", repo=repo)

    def set_refresh_callback(self, callback: Callable[[], None]) -> None:
        """Capture refresh callback registration instead of connecting to button.

        Args:
            callback: A no-argument callable to invoke on refresh.
        """
        self._record_call("set_refresh_callback", callback=callback)
        self._refresh_callback = callback

    def set_history_selection_callback(self, callback: Callable[[Any], None]) -> None:
        """Capture history selection callback registration instead of connecting to view.

        Args:
            callback: A callable that takes a HistorySelection argument to invoke on selection.
        """
        self._record_call("set_history_selection_callback", callback=callback)
        self._history_selection_callback = callback

    def set_add_button_callback(self, callback: Callable[[str], None]) -> None:
        """Capture add button callback registration instead of connecting to button.

        Args:
            callback: A callable that takes a git_path string to invoke when add button is clicked.
        """
        self._record_call("set_add_button_callback", callback=callback)
        self._add_button_callback = callback

    def trigger_add_button_callback(self, git_path: str) -> None:
        """Trigger the registered add button callback if one exists.

        This is useful for testing that the callback was properly registered
        and can be invoked with a git_path argument.

        Args:
            git_path: The git_path to pass to the callback.
        """
        if self._add_button_callback is not None:
            self._add_button_callback(git_path)

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

    def trigger_refresh(self) -> None:
        """Trigger the registered refresh callback if one exists.

        This is useful for testing that the callback was properly registered
        and can be invoked.
        """
        if self._refresh_callback is not None:
            self._refresh_callback()
