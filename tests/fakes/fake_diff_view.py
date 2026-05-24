"""File responsibility: Fake implementation of DiffView protocol for testing."""

from collections.abc import Callable
from typing import Any

from freecad.history_wb.domain.git.models import GitCommit, GitRepository
from freecad.history_wb.ui.presenters.presentation_models import (
    DiffTreePresentation,
    NodePresentation,
    PropertyPresentation,
)
from freecad.history_wb.ui.views.models import HistorySelection


class FakeDiffView:
    """Fake implementation of DiffView protocol for testing DiffPresenter.

    Captures method calls for verification in tests instead of rendering UI.
    """

    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []
        self._last_call: dict[str, Any] | None = None
        self._refresh_callback: Callable[[], None] | None = None
        self._history_selection_callback: Callable[[Any], None] | None = None
        self._history_scroll_bottom_callback: Callable[[], None] | None = None
        self._add_button_callback: Callable[[str], None] | None = None
        self._stage_all_callback: Callable[[], None] | None = None
        self._visual_diff_callback: Callable[[str, str], None] | None = None
        self._current_selection: Any = None

    def show_loading(self) -> None:
        """Capture loading call instead of showing UI."""
        self._record_call("show_loading")

    def show_doc_diff(self, nodes: list[NodePresentation], git_path: str = "") -> None:
        """Capture diff tree call instead of showing UI."""
        self._record_call("show_doc_diff", nodes=nodes, git_path=git_path)

    def show_doc_diffs(self, diff_trees: list[DiffTreePresentation]) -> None:
        """Capture multiple diff trees call instead of showing UI.

        Args:
            diff_trees: List of DiffTreePresentation objects to display.
                       Each represents a diff tree for one document.
        """
        self._record_call("show_doc_diffs", diff_trees=diff_trees)

    def show_summary(self, changed_docs: int) -> None:
        """Capture summary call instead of showing UI."""
        self._record_call("show_summary", changed_docs=changed_docs)

    def show_error(self, message: str) -> None:
        """Capture error call instead of showing UI."""
        self._record_call("show_error", message=message)

    def show_property_diff(self, properties: list[PropertyPresentation]) -> None:
        """Capture properties call instead of showing UI."""
        self._record_call("show_property_diff", properties=properties)

    def clear_property_diff(self) -> None:
        """Capture property-diff clear call."""
        self._record_call("clear_property_diff")

    def clear_doc_diffs(self) -> None:
        """Capture document-diff clear call."""
        self._record_call("clear_doc_diffs")

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

    def set_history_scroll_bottom_callback(self, callback: Callable[[], None]) -> None:
        """Capture bottom-scroll callback registration for infinite scroll."""
        self._record_call("set_history_scroll_bottom_callback", callback=callback)
        self._history_scroll_bottom_callback = callback

    def append_commits(self, commits: list[GitCommit]) -> None:
        """Capture append commits call for incremental history loading."""
        self._record_call("append_commits", commits=commits)

    def set_add_button_callback(self, callback: Callable[[str], None]) -> None:
        """Capture add button callback registration instead of connecting to button.

        Args:
            callback: A callable that takes a git_path string to invoke when add button is clicked.
        """
        self._record_call("set_add_button_callback", callback=callback)
        self._add_button_callback = callback

    def set_visual_diff_callback(self, callback: Callable[[str, str], None]) -> None:
        """Capture visual diff callback registration."""
        self._record_call("set_visual_diff_callback", callback=callback)
        self._visual_diff_callback = callback

    def trigger_visual_diff_callback(self, git_path: str, node_path: str) -> None:
        """Trigger visual diff callback for tests."""
        if self._visual_diff_callback is not None:
            self._visual_diff_callback(git_path, node_path)

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

    def collapse_tree_item(self, git_path: str) -> None:
        """Capture collapse_tree_item call instead of collapsing UI.

        Args:
            git_path: The git_path of the tree item to collapse.
        """
        self._record_call("collapse_tree_item", git_path=git_path)

    def set_stage_button_enabled(self, git_path: str, enabled: bool) -> None:
        """Capture set_stage_button_enabled call instead of updating UI.

        Args:
            git_path: The git_path of the document whose button to update.
            enabled: Whether the stage button should be enabled.
        """
        self._record_call("set_stage_button_enabled", git_path=git_path, enabled=enabled)

    def set_stage_all_callback(self, callback: Callable[[], None]) -> None:
        """Capture Stage All callback registration instead of connecting to button.

        Args:
            callback: A no-argument callable to invoke on Stage All click.
        """
        self._record_call("set_stage_all_callback", callback=callback)
        self._stage_all_callback = callback

    def trigger_stage_all_callback(self) -> None:
        """Trigger the registered Stage All callback if one exists."""
        if self._stage_all_callback is not None:
            self._stage_all_callback()

    def set_stage_all_button_visible(self, visible: bool) -> None:
        """Capture Stage All button visibility call.

        Args:
            visible: Whether the Stage All button should be visible.
        """
        self._record_call("set_stage_all_button_visible", visible=visible)

    def set_stage_all_button_enabled(self, enabled: bool) -> None:
        """Capture Stage All button enabled call.

        Args:
            enabled: Whether the Stage All button should be enabled.
        """
        self._record_call("set_stage_all_button_enabled", enabled=enabled)

    def get_current_history_selection(self) -> HistorySelection | None:
        """Return currently selected history entry for presenter logic."""
        return self._current_selection

    def set_current_history_selection(self, selection: HistorySelection | None) -> None:
        """Test helper to set current history selection."""
        self._current_selection = selection
