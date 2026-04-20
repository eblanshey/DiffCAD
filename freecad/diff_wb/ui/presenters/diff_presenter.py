"""File responsibility: Diff result presenter for UI."""

from typing import Any

from ...application.actions.create_diff import CreateDiffAction
from ...application.actions.create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
from ...application.actions.create_document_snapshot_working import CreateDocumentSnapshotForWorkingTreeAction
from ...application.actions.get_committed_file_paths import GetCommittedFilePathsAction
from ...application.actions.get_dirty_documents import GetDirtyDocumentsAction
from ...application.actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from ...application.actions.get_staged_file_paths import GetStagedFilePathsAction
from ...application.actions.stage_documents import StageDocumentsAction
from ...domain.diff.engine import DiffResult
from ...domain.diff.models import DiffState, NodeDiff, PropertyDiff
from ...domain.git.models import GitRepository
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
        get_dirty_documents_action: GetDirtyDocumentsAction,
        get_staged_file_paths_action: GetStagedFilePathsAction,
        get_committed_file_paths_action: GetCommittedFilePathsAction,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            view: DiffView implementation to display diff results
            ui_state: UI state holder containing git repository info
            get_eligible_docs_action: Action to get eligible open documents
            create_working_snapshot_action: Action to create working tree snapshots
            create_commit_snapshot_action: Action to create commit snapshots
            create_diff_action: Action to compute diffs between snapshots
            stage_documents_action: Action to stage documents to git
            get_dirty_documents_action: Action to get dirty document paths
            get_staged_file_paths_action: Action to get staged file paths
            get_committed_file_paths_action: Action to get committed file paths
        """
        self._view = view
        self._ui_state = ui_state
        self._get_eligible_docs = get_eligible_docs_action
        self._create_working_tree_snapshot = create_working_snapshot_action
        self._create_commit_snapshot = create_commit_snapshot_action
        self._create_diff = create_diff_action
        self._stage_documents = stage_documents_action
        self._get_dirty_documents = get_dirty_documents_action
        self._get_staged_file_paths = get_staged_file_paths_action
        self._get_committed_file_paths = get_committed_file_paths_action
        self._diff_results_by_path: dict[str, DiffResult] = {}

        # Wire up the callback for history selection
        self._view.set_history_selection_callback(self.on_history_item_selected)

    def present_diff(self, diff_result: DiffResult) -> None:
        """Transform domain data and call view methods to render UI.

        Args:
            diff_result: DiffResult from CompareSnapshotsAction.execute()
        """
        # Store diff result for property lookup (also add to dict for multi-doc support)
        self._diff_result = diff_result
        git_path = diff_result.new_snapshot.git_path or diff_result.new_snapshot.document_name
        if git_path:
            self._diff_results_by_path[git_path] = diff_result

        # Transform domain objects to presentation models
        nodes = [self._format_node(node) for node in diff_result.hierarchy.roots]

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
        3. Get dirty documents (ONE call for all eligible docs)
        4. Collect results, logging warnings for failures
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

        # Get dirty documents (ONE call for all eligible docs - efficient!)
        dirty_result = self._get_dirty_documents.execute(repo, eligible_docs)
        dirty_paths = set(dirty_result.data) if dirty_result.is_success else set()

        # Store diff results keyed by git_path for later use by add button
        self._diff_results_by_path.clear()
        for result in all_diff_results:
            git_path = result.new_snapshot.git_path
            if git_path:
                self._diff_results_by_path[git_path] = result

        if all_diff_results:
            self.present_diffs(all_diff_results, dirty_paths)
        else:
            Log.warning("No diff results to display")

    def _on_staging_selected(self) -> None:
        """Handle Staging item selection.

        For each staged FCStd file:
        1. Get staged snapshot from index (commit=None)
        2. Get snapshot from HEAD
        3. Create diff between HEAD and index

        Displays resulting diffs. For paths where index snapshot is missing,
        creates flat warning items (no tree below).
        """
        repo = self._ui_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return

        # Get list of staged FCStd files
        staged_result = self._get_staged_file_paths.execute(repo)
        if not staged_result.is_success:
            Log.warning(f"Failed to get staged files: {staged_result.message}")
            return

        staged_paths = staged_result.data or []
        if not staged_paths:
            # No staged files - clear the view
            self._view.show_diff_trees([])
            return

        # Compute diffs for all staged paths
        all_diff_results, missing_snapshot_paths = self._compute_staged_diffs(repo, staged_paths)

        # Store diff results keyed by git_path for later use
        self._diff_results_by_path.clear()
        for result in all_diff_results:
            result_git_path = result.new_snapshot.git_path
            if result_git_path:
                self._diff_results_by_path[result_git_path] = result

        if all_diff_results or missing_snapshot_paths:
            # Present with empty dirty_paths since staged files are, by definition, tracked
            self.present_diffs(all_diff_results, set(), missing_snapshot_paths)
        else:
            Log.warning("No diff results to display for staging")

    def _compute_staged_diffs(self, repo: GitRepository, staged_paths: list[str]) -> tuple[list[DiffResult], list[str]]:
        """Compute diffs for staged files.

        For each staged path, retrieves snapshots from index and HEAD,
        then computes the diff between them.

        Args:
            repo: GitRepository containing the documents.
            staged_paths: List of staged git paths.

        Returns:
            Tuple of (list of DiffResult, list of paths with missing index snapshots).
        """
        all_diff_results: list[DiffResult] = []
        missing_snapshot_paths: list[str] = []

        for git_path in staged_paths:
            diff_result, needs_warning = self._compute_diff_for_single_staged_file(repo, git_path)

            if needs_warning:
                missing_snapshot_paths.append(git_path)
            elif diff_result is not None:
                all_diff_results.append(diff_result)

        return all_diff_results, missing_snapshot_paths

    def _compute_diff_for_single_staged_file(
        self, repo: GitRepository, git_path: str
    ) -> tuple[DiffResult | None, bool]:
        """Compute diff for a single staged file.

        Retrieves snapshots from index and HEAD, then computes the diff.

        Args:
            repo: GitRepository containing the documents.
            git_path: The git path of the staged file.

        Returns:
            Tuple of (DiffResult or None, boolean indicating if snapshot is missing in index).
        """
        # Get snapshot from index (staged version)
        index_result = self._create_commit_snapshot.execute(repo, None, git_path)
        index_snapshot = index_result.data if index_result.is_success else None

        if index_snapshot is None:
            # Snapshot missing in index - track for warning display (per MVP spec)
            return None, True

        # Get snapshot from HEAD
        head_result = self._create_commit_snapshot.execute(repo, "HEAD", git_path)
        head_snapshot = head_result.data if head_result.is_success else None

        # Normal case: create diff between HEAD and index
        if head_snapshot is None:
            # HEAD doesn't have this file yet - treat as all new
            diff_result = self._create_diff.execute(None, index_snapshot)
        else:
            diff_result = self._create_diff.execute(head_snapshot, index_snapshot)

        if diff_result.is_success and diff_result.data is not None:
            return diff_result.data, False
        else:
            Log.warning(f"Failed to compute diff for {git_path}: {diff_result.message}")
            return None, False

    def _compute_commit_diffs(self, repo: GitRepository, commit_hash: str) -> tuple[list[DiffResult], list[str]]:
        """Compute diffs for files changed in a commit vs its parent.

        For each FCStd file changed between the commit and its parent:
        1. Extract snapshots from both commits
        2. Compute diff between snapshots
        3. Track paths where parent snapshot is missing

        Args:
            repo: GitRepository containing the documents.
            commit_hash: The commit hash to compute diffs for.

        Returns:
            Tuple of (list of DiffResult, list of paths with missing parent snapshots).
        """
        all_diff_results: list[DiffResult] = []
        missing_snapshot_paths: list[str] = []

        commit_result = self._get_committed_file_paths.execute(repo, commit_hash)
        parent_result = self._get_committed_file_paths.execute(repo, commit_hash + "^")

        commit_paths = set(commit_result.data) if commit_result.is_success else set()
        parent_paths = set(parent_result.data) if parent_result.is_success else set()
        all_paths = commit_paths | parent_paths

        for git_path in all_paths:
            commit_snap_result = self._create_commit_snapshot.execute(repo, commit_hash, git_path)
            parent_snap_result = self._create_commit_snapshot.execute(repo, commit_hash + "^", git_path)

            commit_snapshot = commit_snap_result.data if commit_snap_result.is_success else None
            parent_snapshot = parent_snap_result.data if parent_snap_result.is_success else None

            if commit_snapshot is not None and parent_snapshot is not None:
                # Both snapshots exist - compute diff
                diff_result = self._create_diff.execute(parent_snapshot, commit_snapshot)
                if diff_result.is_success and diff_result.data is not None:
                    all_diff_results.append(diff_result.data)
            elif commit_snapshot is not None and parent_snapshot is None:
                # Parent snapshot missing (extraction failed, no YAML, etc.) - show with warning
                diff_result = self._create_diff.execute(None, commit_snapshot)
                if diff_result.is_success and diff_result.data is not None:
                    all_diff_results.append(diff_result.data)
                missing_snapshot_paths.append(git_path)
            # Skip cases where commit_snapshot is None (no data to compare)

        return all_diff_results, missing_snapshot_paths

    def _on_commit_selected(self, commit_hash: str | None) -> None:
        """Handle commit item selection.

        Delegates per-file diff computation to _compute_commit_diffs(),
        then stores results and presents them to the view.
        """
        if commit_hash is None:
            Log.warning("Commit selection received without commit hash")
            return

        repo = self._ui_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return

        # Compute diffs for all changed files (extracted for testability)
        all_diff_results, missing_paths = self._compute_commit_diffs(repo, commit_hash)

        # Store diff results keyed by git_path for later use
        self._diff_results_by_path.clear()
        for result in all_diff_results:
            git_path = result.new_snapshot.git_path
            if git_path:
                self._diff_results_by_path[git_path] = result

        if all_diff_results or missing_paths:
            self.present_diffs(all_diff_results, set(), missing_paths)
        else:
            Log.info(f"No FCStd files changed in commit {commit_hash}")
            self._view.show_diff_trees([])

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

    def present_diffs(
        self,
        diff_results: list[DiffResult],
        dirty_paths: set[str] | None = None,
        missing_snapshot_paths: list[str] | None = None,
    ) -> None:
        """Transform multiple DiffResults into presentation models and display.

        Args:
            diff_results: List of DiffResult objects to present.
            dirty_paths: Set of git paths that have git-tracked changes.
            missing_snapshot_paths: List of git_paths where snapshot is missing (creates flat warning items).
        """
        dirty_paths = dirty_paths or set()
        missing_snapshot_paths = missing_snapshot_paths or []

        if not diff_results and not missing_snapshot_paths:
            self._view.show_diff_trees([])
            return

        presentations = []
        for diff_result in diff_results:
            nodes = [self._format_node(node) for node in diff_result.hierarchy.roots]
            git_path = diff_result.new_snapshot.git_path or diff_result.new_snapshot.document_name
            warnings = list(diff_result.warnings)

            # Compute has_changes from nodes
            has_changes = any(node.has_changes for node in nodes)

            # Check if this document's git path has git-tracked changes
            is_git_dirty = git_path in dirty_paths

            # Stage button is enabled if there are diff changes OR git-tracked changes
            stage_button_enabled = has_changes or is_git_dirty

            presentations.append(
                DiffTreePresentation(
                    nodes=nodes,
                    git_path=git_path,
                    warnings=warnings,
                    stage_button_enabled=stage_button_enabled,
                )
            )

        # Add flat warning items for missing snapshot paths
        for git_path in missing_snapshot_paths:
            presentations.append(
                DiffTreePresentation(
                    nodes=[],  # Empty - flat item
                    git_path=git_path,
                    warnings=["WARNING_OLD_SNAPSHOT_MISSING"],
                    stage_button_enabled=False,
                )
            )

        # Sort all presentations alphanumerically by git_path
        presentations.sort(key=lambda p: p.git_path)

        self._view.show_diff_trees(presentations)

        # Show summary from first document (for now)
        if diff_results:
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

    def on_node_selected(self, git_path: str, node_path: str) -> None:
        """Handle tree node selection to display property diffs.

        Called by view when user clicks a node in the diff tree.
        Looks up the property diffs for that path and displays them.

        Args:
            git_path: The document path (key in _diff_results_by_path)
            node_path: The path of the selected node within that document
        """
        # Guard: No diff results stored
        if not self._diff_results_by_path:
            self._view.show_properties([])
            return

        # Look up the correct DiffResult for this document
        diff_result = self._diff_results_by_path.get(git_path)
        if diff_result is None:
            Log.debug(f"[PRESENTER] No DiffResult found for git_path: {git_path}")
            self._view.show_properties([])
            return

        # Find NodeDiff by path within this document's hierarchy
        node_diff = diff_result.hierarchy.find_by_path(node_path)

        # If not found, clear properties
        if node_diff is None:
            Log.debug(f"[PRESENTER] NodeDiff not found for path: {node_path} in document {git_path}")
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
