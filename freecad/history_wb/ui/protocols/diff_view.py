"""File responsibility: Diff view interface definition.

This protocol defines the interface for diff views. Views handle both
translation of UI templates/literals AND parameter
substitution using Qt-style placeholders (%1, %2, etc.). Presenters pass
raw data only - they never format user-facing messages.

Translation Strategy for Summary:
    The show_summary method passes per-status document counts.
    The view should translate each label and combine with values.
"""

from collections.abc import Callable
from typing import Protocol

from ...domain.git.models import GitCommit, GitRepository
from ..presenters.presentation_models import (
    DiffTreePresentation,
    NodePresentation,
    PropertyPresentation,
)
from ..views.models import GitConfigDialogResult, HistorySelection


__all__ = ["DiffView"]


class DiffView(Protocol):
    """Interface that any diff display component must implement.

    Implemented by Qt implementations in the UI views layer.

    The view is responsible for translating messages and substituting
    parameters. Presenters pass raw data only.
    """

    def show_doc_diff(self, nodes: list[NodePresentation], git_path: str = "") -> None:
        """Display the diff tree.

        Args:
            nodes: List of node presentation models to display.
            git_path: The git path to display as top-level item (falls back to document name).
        """

    def show_summary(self, modified_docs: int, deleted_docs: int, added_docs: int) -> None:
        """Display per-status document counts.

        Args:
            modified_docs: Number of modified documents.
            deleted_docs: Number of deleted documents.
            added_docs: Number of added documents.
        """

    def show_property_diff(self, properties: list[PropertyPresentation]) -> None:
        """Display property diffs in the properties column.

        Args:
            properties: List of PropertyPresentation objects to display.
                       Each row shows: Property Name | Old Value → New Value
                       Color coding: green=added, red=deleted, blue=modified
                       Expression changes appear as separate rows after their value row.
        """

    def clear_property_diff(self) -> None:
        """Clear property diff panel content."""

    def clear_doc_diffs(self) -> None:
        """Clear document diff tree and related controls.

        This method must also clear the property diff panel.
        """

    def show_repository(self, repo: GitRepository | None) -> None:
        """Display git repository info above snapshot list.

        Args:
            repo: GitRepository object if detected, or None if no repository found.
                  The view should display repository name and path when available,
                  or a "no repository" message when None.
        """

    def show_commits(self, commits: list[GitCommit], show_special_items: bool = True) -> None:
        """Display git commits in the history list.

        Args:
            commits: List of GitCommit objects to display.
            show_special_items: Whether to include top "Current Files" and
                "Reviewed" rows before commit rows.
        """

    def set_force_diff_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to invoke when force diff button is clicked.

        Args:
            callback: A no-argument callable to invoke on force diff.
        """

    def set_refresh_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to invoke when refresh button is clicked.

        Args:
            callback: A no-argument callable to invoke on refresh.
        """

    def set_save_iteration_callback(self, callback: Callable[[], None]) -> None:
        """Set callback fired by Save Iteration panel button."""

    def set_history_selection_callback(self, callback: Callable[[HistorySelection], None]) -> None:
        """Set the callback for history list selection.

        Args:
            callback: A callable that receives HistorySelection with item_kind and commit_hash
        """

    def set_history_scroll_bottom_callback(self, callback: Callable[[], None]) -> None:
        """Set callback fired when history list scroll reaches bottom area.

        Args:
            callback: A no-argument callable for infinite-scroll loading.
        """

    def append_commits(self, commits: list[GitCommit]) -> None:
        """Append commit rows to existing history list without clearing it.

        Args:
            commits: Commit rows to append after existing items.
        """

    def show_doc_diffs(self, diffs: list[DiffTreePresentation]) -> None:
        """Display multiple diff trees (one per document).

        Args:
            diffs: List of DiffTreePresentation objects, each representing
                  a diff tree for one document with its metadata.
        """

    def set_add_button_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback for when the '+ Stage' button is clicked.

        Args:
            callback: A callable that receives the git_path (str) of the
                      document whose '+ Stage' button was clicked.
        """

    def set_remove_from_reviewed_button_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for per-file remove from Reviewed button."""

    def set_visual_diff_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for visual diff click with (git_path, node_path)."""

    def set_open_document_for_comparison_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for document-open indicator click with git_path."""

    def focus_window(self) -> None:
        """Bring history panel window to foreground and focus it."""

    def collapse_tree_item(self, git_path: str) -> None:
        """Collapse the root tree item for the given git_path.

        Args:
            git_path: The git_path of the root tree item to collapse.
        """

    def set_stage_button_enabled(self, git_path: str, enabled: bool) -> None:
        """Enable or disable the '+ Stage' button for a given git_path.

        Args:
            git_path: The git_path of the document whose button to update.
            enabled: Whether the stage button should be enabled.
        """

    def set_stage_all_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback for when the 'Stage All' button is clicked.

        Args:
            callback: A no-argument callable to invoke on Stage All click.
        """

    def set_remove_all_from_reviewed_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for Remove All from Reviewed action."""

    def set_mark_all_reviewed_from_in_progress_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for Mark All Reviewed action from Current Files context menu."""

    def set_stage_all_button_visible(self, visible: bool) -> None:
        """Show or hide the 'Stage All' button.

        Args:
            visible: Whether the Stage All button should be visible.
        """

    def set_stage_all_button_enabled(self, enabled: bool) -> None:
        """Enable or disable the 'Stage All' button.

        Args:
            enabled: Whether the Stage All button should be enabled.
        """

    def set_remove_all_button_visible(self, visible: bool) -> None:
        """Show or hide the 'Remove All' button for Reviewed selection."""

    def set_remove_all_button_enabled(self, enabled: bool) -> None:
        """Enable or disable the 'Remove All' button for Reviewed selection."""

    def set_remove_all_button_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for summary-bar Remove All button."""

    def set_restore_button_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for per-file Restore button."""

    def set_restore_all_button_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for summary-bar Restore All button."""

    def set_restore_all_from_history_context_callback(self, callback: Callable[[HistorySelection], None]) -> None:
        """Set callback for history-list context restore actions."""

    def set_restore_all_button_visible(self, visible: bool) -> None:
        """Show or hide summary-bar Restore All button."""

    def set_restore_all_button_enabled(self, enabled: bool) -> None:
        """Enable or disable summary-bar Restore All button."""

    def get_current_history_selection(self) -> HistorySelection | None:
        """Return currently selected history entry, if any."""

    def show_warning_message(self, title: str, message: str) -> None:
        """Show warning dialog/message to user."""

    def show_info_message(self, title: str, message: str) -> None:
        """Show informational dialog/message to user."""

    def show_error_message(self, title: str, message: str) -> None:
        """Show error dialog/message to user."""

    def show_save_iteration_dialog(self) -> str | None:
        """Show Save Iteration dialog and return commit notes or None."""

    def show_configure_author_dialog(
        self,
        *,
        message: str | None = None,
        initial_values: GitConfigDialogResult | None = None,
        global_config_writable: bool = True,
    ) -> GitConfigDialogResult | None:
        """Show configure-author dialog and return entered values or None."""

    def show_restore_file_confirmation_dialog(self, git_path: str) -> bool:
        """Show destructive confirmation for one file restore."""

    def show_restore_scope_dialog(self) -> str | None:
        """Show bulk restore scope picker. Returns listed_fcstd, all_fcstd, or None."""
