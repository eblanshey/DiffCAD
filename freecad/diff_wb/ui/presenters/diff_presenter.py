"""File responsibility: Diff result presenter for UI."""

from ...domain.diff.engine import DiffResult
from ...domain.diff.models import NodeDiff
from ..protocols.diff_view import DiffView
from .presentation_models import NodePresentation


class DiffPresenter:
    """Transform DiffResult into presentation models and call view methods.

    This presenter transforms domain-level diff results into UI-friendly
    presentation models, then calls view protocol methods to trigger
    the actual UI rendering.

    Dependencies are injected for testability.
    """

    def __init__(self, view: DiffView) -> None:
        """Initialize with required dependencies.

        Args:
            view: DiffView implementation to display diff results
        """
        self._view = view

    def present_diff(self, diff_result: DiffResult) -> None:
        """Transform domain data and call view methods to render UI.

        Args:
            diff_result: DiffResult from CompareSnapshotsAction.execute()
        """
        # Transform domain objects to presentation models
        nodes = [self._format_node(node) for node in diff_result.node_diffs]

        # Call view methods to trigger UI rendering
        self._view.show_diff_tree(nodes)
        # Pass raw integers - view handles translation and formatting using
        # individual labels (DIFF_SUMMARY_ADDED_LABEL, etc.) per user decision
        self._view.show_summary(
            added=diff_result.summary.added_nodes,
            deleted=diff_result.summary.deleted_nodes,
            modified=diff_result.summary.modified_nodes,
        )

    def _format_node(self, node_diff: NodeDiff) -> NodePresentation:
        """Transform domain NodeDiff to presentation model.

        Args:
            node_diff: Domain NodeDiff from diff engine

        Returns:
            NodePresentation suitable for UI display
        """
        return NodePresentation(
            path=node_diff.path,
            type_id=node_diff.type_id,
            state=node_diff.state.name,
            has_changes=node_diff.has_changes,
            children=[self._format_node(child) for child in node_diff.children],
        )
