"""File responsibility: Diff view interface definition.

This protocol defines the interface for diff views. Views handle both
translation of templates (from translation_strings.py) AND parameter
substitution using Qt-style placeholders (%1, %2, etc.). Presenters pass
raw data only - they never format user-facing messages.

Translation Strategy for Summary:
    The show_summary method passes raw integers. The view should translate
    individual labels and combine them with values:

        def show_summary(self, added: int, deleted: int, modified: int) -> None:
            added_label = QCoreApplication.translate("DiffView", DIFF_SUMMARY_ADDED_LABEL)
            deleted_label = QCoreApplication.translate("DiffView", DIFF_SUMMARY_DELETED_LABEL)
            modified_label = QCoreApplication.translate("DiffView", DIFF_SUMMARY_MODIFIED_LABEL)

            self._addedLabel.setText(f"{added_label} {added}")
            self._deletedLabel.setText(f"{deleted_label} {deleted}")
            self._modifiedLabel.setText(f"{modified_label} {modified}")
"""

from collections.abc import Callable
from typing import Protocol

from ...domain.git.models import GitRepository
from ..presenters.presentation_models import (
    DiffTreePresentation,
    NodePresentation,
    PropertyPresentation,
)
from ..views.models import HistorySelection


__all__ = ["DiffView"]


class DiffView(Protocol):
    """Interface that any diff display component must implement.

    Implemented by Qt implementations in the UI views layer.

    The view is responsible for translating messages and substituting
    parameters. Presenters pass raw data only.
    """

    def show_loading(self) -> None:
        """Display loading indicator while diff is being computed.

        Use DIFF_LOADING_MESSAGE from translation_strings.py for the message.
        """

    def show_diff_tree(self, nodes: list[NodePresentation], git_path: str = "") -> None:
        """Display the diff tree.

        Args:
            nodes: List of node presentation models to display.
            git_path: The git path to display as top-level item (falls back to document name).
        """

    def show_summary(self, added: int, deleted: int, modified: int) -> None:
        """Display the diff summary counts.

        Args:
            added: Number of added nodes.
            deleted: Number of deleted nodes.
            modified: Number of modified nodes.

        The view should use individual labels (DIFF_SUMMARY_ADDED_LABEL,
        DIFF_SUMMARY_DELETED_LABEL, DIFF_SUMMARY_MODIFIED_LABEL) and
        append the counts after each label.
        """

    def show_error(self, message: str) -> None:
        """Display error message.

        Args:
            error_message: The error message to display.
        """

    def show_properties(self, properties: list[PropertyPresentation]) -> None:
        """Display property diffs in the properties column.

        Args:
            properties: List of PropertyPresentation objects to display.
                       Each row shows: Property Name | Old Value → New Value
                       Color coding: green=added, red=deleted, blue=modified
                       Expression changes appear as separate rows after their value row.
        """

    def show_repository(self, repo: GitRepository | None) -> None:
        """Display git repository info above snapshot list.

        Args:
            repo: GitRepository object if detected, or None if no repository found.
                  The view should display repository name and path when available,
                  or a "no repository" message when None.
        """

    def set_refresh_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to invoke when refresh button is clicked.

        Args:
            callback: A no-argument callable to invoke on refresh.
        """

    def set_history_selection_callback(self, callback: Callable[[HistorySelection], None]) -> None:
        """Set the callback for history list selection.

        Args:
            callback: A callable that receives HistorySelection with item_kind and commit_hash
        """

    def show_diff_trees(self, diffs: list[DiffTreePresentation]) -> None:
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
