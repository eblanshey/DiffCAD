"""File responsibility: Diff result presenter for UI."""

from ...domain.diff.engine import DiffResult
from ...domain.diff.models import NodeDiff
from ...domain.tree import Property
from ..protocols.diff_view import DiffView
from .presentation_models import NodePresentation, PropertyPresentation


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
        # Store diff result for property lookup
        self._diff_result = diff_result

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

    def on_node_selected(self, path: str) -> None:
        """Handle tree node selection to display property diffs.

        Called by view when user clicks a node in the diff tree.
        Looks up the property diffs for that path and displays them.

        Args:
            path: The path of the selected node (from QTreeWidgetItem.UserRole)
        """
        # Guard: No diff result stored
        if not hasattr(self, "_diff_result") or self._diff_result is None:
            self._view.show_properties([])
            return

        # Find NodeDiff by path
        node_diff = self._find_node_diff_by_path(path, self._diff_result.node_diffs)

        # If not found, clear properties
        if node_diff is None:
            self._view.show_properties([])
            return

        # Transform property diffs to presentations
        properties = self._transform_property_diffs(node_diff)
        self._view.show_properties(properties)

    def _find_node_diff_by_path(self, path: str, node_diffs: list[NodeDiff]) -> NodeDiff | None:
        """Recursively find NodeDiff by path."""
        for node in node_diffs:
            if node.path == path:
                return node
            # Search children recursively
            if node.children:
                found = self._find_node_diff_by_path(path, node.children)
                if found:
                    return found
        return None

    def _transform_property_diffs(self, node_diff: NodeDiff) -> list[PropertyPresentation]:
        """Transform domain PropertyDiff to presentation format.

        Expression changes appear as separate rows.

        Args:
            node_diff: Domain NodeDiff with property_diffs

        Returns:
            List of PropertyPresentation for UI display
        """
        presentations = []

        for prop_diff in node_diff.property_diffs:
            # Process all properties (including unchanged)

            # Format display strings
            old_display = self._format_property_value(prop_diff.old_value)
            new_display = self._format_property_value(prop_diff.new_value)

            # Create main property row
            presentations.append(
                PropertyPresentation(
                    name=prop_diff.property_name,
                    old_display=old_display,
                    new_display=new_display,
                    state=prop_diff.state.name,
                )
            )

            # Handle expression as separate row
            old_expr = getattr(prop_diff.old_value, "expression", None) if prop_diff.old_value else None
            new_expr = getattr(prop_diff.new_value, "expression", None) if prop_diff.new_value else None

            if old_expr or new_expr:
                # Expression changed - add second row
                old_expr_display = f"+{old_expr}" if old_expr else "(none)"
                new_expr_display = f"+{new_expr}" if new_expr else "(none)"

                # Determine expression state
                expr_state = "MODIFIED"
                if old_expr and not new_expr:
                    expr_state = "DELETED"
                elif not old_expr and new_expr:
                    expr_state = "ADDED"

                presentations.append(
                    PropertyPresentation(
                        name=f"{prop_diff.property_name} (expr)",
                        old_display=old_expr_display,
                        new_display=new_expr_display,
                        state=expr_state,
                    )
                )

        return presentations

    def _format_property_value(self, prop: Property | None) -> str:
        """Format property value for display.

        Args:
            prop: Property object or None

        Returns:
            Formatted string suitable for display
        """
        if prop is None:
            return ""
        return str(prop)
