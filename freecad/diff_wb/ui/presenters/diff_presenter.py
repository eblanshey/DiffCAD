"""File responsibility: Diff result presenter for UI."""

from typing import Any

from ...application.actions.create_diff import CreateDiffAction
from ...application.actions.create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
from ...application.actions.create_document_snapshot_working import CreateDocumentSnapshotForWorkingTreeAction
from ...application.actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from ...application.actions.stage_documents import StageDocumentsAction
from ...domain.diff.engine import DiffResult
from ...domain.diff.models import DiffState, NodeDiff, PropertyDiff
from ...domain.tree import Property
from ...utils import Log
from ..protocols.diff_view import DiffView
from ..state import UIState
from ..views.models import HistorySelection
from .presentation_models import DiffTreePresentation, NodePresentation, PropertyPresentation


class DiffPresenter:
    """Transform DiffResult into presentation models and call view methods.

    This presenter transforms domain-level diff results into UI-friendly
    presentation models, then calls view protocol methods to trigger
    the actual UI rendering.

    Dependencies are injected for testability.
    """

    def __init__(
        self,
        view: DiffView,
        ui_state: UIState,
        get_eligible_docs_action: GetOpenEligibleDocumentsAction,
        create_working_snapshot_action: CreateDocumentSnapshotForWorkingTreeAction,
        create_commit_snapshot_action: CreateDocumentSnapshotForCommitAction,
        create_diff_action: CreateDiffAction,
        stage_documents_action: StageDocumentsAction,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            view: DiffView implementation to display diff results
            ui_state: UI state holder containing git repository info
            get_eligible_docs_action: Action to get eligible open documents
            create_working_snapshot_action: Action to create working tree snapshots
            create_commit_snapshot_action: Action to create commit snapshots (stub)
            create_diff_action: Action to compute diffs between snapshots
            stage_documents_action: Action to stage documents to git
        """
        self._view = view
        self._ui_state = ui_state
        self._get_eligible_docs = get_eligible_docs_action
        self._create_working_tree_snapshot = create_working_snapshot_action
        self._create_commit_snapshot = create_commit_snapshot_action
        self._create_diff = create_diff_action
        self._stage_documents = stage_documents_action
        self._diff_results_by_path: dict[str, DiffResult] = {}

        # Wire up the callback for history selection
        self._view.set_history_selection_callback(self.on_history_item_selected)

    def present_diff(self, diff_result: DiffResult) -> None:
        """Transform domain data and call view methods to render UI.

        Args:
            diff_result: DiffResult from CompareSnapshotsAction.execute()
        """
        # Store diff result for property lookup
        self._diff_result = diff_result

        # Transform domain objects to presentation models
        nodes = [self._format_node(node) for node in diff_result.hierarchy.roots]

        # Get git_path for top-level item (use document_name as fallback)
        git_path = diff_result.new_snapshot.git_path or diff_result.new_snapshot.document_name

        # Call view methods to trigger UI rendering
        self._view.show_diff_tree(nodes, git_path)
        # Pass raw integers - view handles translation and formatting using
        # individual labels (DIFF_SUMMARY_ADDED_LABEL, etc.) per user decision
        # Use explicit counts from DiffResult
        self._view.show_summary(
            added=diff_result.added_count,
            deleted=diff_result.deleted_count,
            modified=diff_result.modified_count,
        )

    def on_history_item_selected(self, selection: HistorySelection) -> None:
        """Handle single item selection from history list.

        Args:
            selection: HistorySelection containing item_kind and optional commit_hash
        """
        if selection.item_kind == "WORKING_TREE":
            self._on_working_tree_selected()
        elif selection.item_kind == "STAGING":
            self._on_staging_selected()
        elif selection.item_kind == "COMMIT":
            self._on_commit_selected(selection.commit_hash)

    def _on_working_tree_selected(self) -> None:
        """Handle Working Tree item selection.

        For each eligible document:
        1. Create working tree snapshot
        2. Create diff against None (old snapshot)
        3. Collect results, logging warnings for failures
        """
        repo = self._ui_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return

        docs_result = self._get_eligible_docs.execute(repo)
        if not docs_result.is_success or not docs_result.data:
            Log.warning(f"No eligible documents: {docs_result.message}")
            return

        eligible_docs = docs_result.data
        all_diff_results: list[DiffResult] = []

        for doc in eligible_docs:
            working_result = self._create_working_tree_snapshot.execute(repo, doc)
            if not working_result.is_success or working_result.data is None:
                Log.warning(f"Failed to create working snapshot: {working_result.message}")
                continue

            working_snapshot = working_result.data

            commit_result = self._create_commit_snapshot.execute(repo, None, working_snapshot.git_path)
            commit_snapshot = commit_result.data if commit_result.is_success else None

            diff_result = self._create_diff.execute(commit_snapshot, working_snapshot)
            if diff_result.is_success and diff_result.data is not None:
                all_diff_results.append(diff_result.data)
            else:
                Log.warning(f"Failed to compute diff: {diff_result.message}")

        # Store diff results keyed by git_path for later use by add button
        self._diff_results_by_path.clear()
        for result in all_diff_results:
            git_path = result.new_snapshot.git_path
            if git_path:
                self._diff_results_by_path[git_path] = result

        if all_diff_results:
            self.present_diffs(all_diff_results)
        else:
            Log.warning("No diff results to display")

    def _on_staging_selected(self) -> None:
        """Handle Staging item selection. STUB: For now, does nothing."""
        pass

    def _on_commit_selected(self, commit_hash: str | None) -> None:
        """Handle commit item selection. STUB: For now, does nothing."""
        pass

    def on_add_button_clicked(self, git_path: str) -> None:
        """Handle '+ Stage' button click for staging.

        Args:
            git_path: The git_path of the document to stage.
        """
        repo = self._ui_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return

        # Look up the DiffResult for this git_path
        diff_result = self._diff_results_by_path.get(git_path)
        if not diff_result:
            Log.warning(f"No diff result found for {git_path}")
            return

        # Get the working tree snapshot (new_snapshot) from the diff
        # Since we're in working tree view, old_snapshot may be None
        working_snapshot = diff_result.new_snapshot

        # Stage the document
        result = self._stage_documents.execute(repo, [working_snapshot])
        if not result.is_success:
            Log.warning(f"Failed to stage document: {result.message}")
            return

        Log.info(f"Successfully staged {git_path}")

        # Recalculate diff (Working Tree -> Commit None means same snapshot)
        # This will refresh the view to show no changes
        self._on_working_tree_selected()

    def present_diffs(self, diff_results: list[DiffResult]) -> None:
        """Transform multiple DiffResults into presentation models and display."""
        if not diff_results:
            self._view.show_diff_trees([])
            return

        presentations = []
        for diff_result in diff_results:
            nodes = [self._format_node(node) for node in diff_result.hierarchy.roots]
            git_path = diff_result.new_snapshot.git_path or diff_result.new_snapshot.document_name
            warnings = list(diff_result.warnings)

            presentations.append(DiffTreePresentation(nodes=nodes, git_path=git_path, warnings=warnings))

        self._view.show_diff_trees(presentations)

        # Show summary from first document (for now)
        first = diff_results[0]
        self._view.show_summary(
            added=first.added_count,
            deleted=first.deleted_count,
            modified=first.modified_count,
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
            state=node_diff.state,
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

        # Find NodeDiff by path using hierarchy lookup
        node_diff = self._diff_result.hierarchy.find_by_path(path)

        # If not found, clear properties
        if node_diff is None:
            Log.debug(f"[PRESENTER] NodeDiff not found for path: {path}")
            self._view.show_properties([])
            return

        # Transform property diffs to presentations
        properties = self._transform_property_diffs(node_diff)
        Log.debug(f"[PRESENTER] Transformed to {len(properties)} PropertyPresentation")
        self._view.show_properties(properties)

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
            # Determine group from the property value
            # Use new_value's group if available, otherwise old_value's group
            group = self._extract_property_group(
                prop_diff.new_value if prop_diff.new_value is not None else prop_diff.old_value
            )

            # Extract old_value and new_value for expandable properties
            old_value = self._extract_property_value(prop_diff.old_value)
            new_value = self._extract_property_value(prop_diff.new_value)

            # Transform children recursively from domain PropertyDiff
            children = self._transform_children(prop_diff.children)

            # Create main property row
            presentations.append(
                PropertyPresentation(
                    name=prop_diff.property_name,
                    state=prop_diff.state,
                    old_value=old_value,
                    new_value=new_value,
                    children=children,
                    group=group,
                )
            )

            # Handle expression as separate row
            old_expr = getattr(prop_diff.old_value, "expression", None) if prop_diff.old_value else None
            new_expr = getattr(prop_diff.new_value, "expression", None) if prop_diff.new_value else None

            if old_expr or new_expr:
                # Determine expression state using DiffState enum
                if old_expr and not new_expr:
                    expr_state = DiffState.DELETED
                elif not old_expr and new_expr:
                    expr_state = DiffState.ADDED
                elif old_expr == new_expr:
                    expr_state = DiffState.UNCHANGED
                else:
                    expr_state = DiffState.MODIFIED

                presentations.append(
                    PropertyPresentation(
                        name="-> Expression",
                        state=expr_state,
                        old_value=old_expr,
                        new_value=new_expr,
                        group=group,  # Inherit group from parent property
                    )
                )

        return presentations

    def _extract_property_value(self, prop: Property | None) -> Any:
        """Extract the underlying value from a Property object."""
        return prop.value if prop is not None else None

    def _extract_property_group(self, prop: Property | None) -> str | None:
        """Extract the group attribute from a Property object."""
        return getattr(prop, "group", None) if prop is not None else None

    def _transform_children(self, child_diffs: list[PropertyDiff]) -> list[PropertyPresentation]:
        """Recursively transform child property diffs to presentation format.

        Args:
            child_diffs: List of PropertyDiff children from domain

        Returns:
            List of PropertyPresentation for UI display
        """
        return [
            PropertyPresentation(
                name=child_diff.property_name,
                state=child_diff.state,
                old_value=self._extract_property_value(child_diff.old_value),
                new_value=self._extract_property_value(child_diff.new_value),
                children=self._transform_children(child_diff.children),
                # No group for children
            )
            for child_diff in child_diffs
        ]
