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

from typing import Protocol

from ..presenters.presentation_models import NodePresentation, PropertyPresentation


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

    def show_diff_tree(self, nodes: list[NodePresentation]) -> None:
        """Display the diff tree.

        Args:
            nodes: List of node presentation models to display.
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
