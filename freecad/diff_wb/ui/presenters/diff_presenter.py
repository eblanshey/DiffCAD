# File responsibility: Diff result presenter for UI.
#
# Transforms domain-level diff results into UI-friendly presentation models.
# Builds nested sub-path trees from PropertyPathDiff and maps them to
# PropertyPresentation objects for view rendering.
"""Diff result presenter for UI.

This module provides the DiffPresenter class that transforms domain-level
diff results into UI-friendly presentation models.
"""

from dataclasses import dataclass, field
from typing import Any

from ...application.actions.create_diff import CreateDiffAction
from ...application.actions.create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
from ...application.actions.create_document_snapshot_working import (
    CreateDocumentSnapshotForWorkingTreeAction,
)
from ...application.actions.get_committed_file_paths import GetCommittedFilePathsAction
from ...application.actions.get_dirty_documents import GetDirtyDocumentsAction
from ...application.actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from ...application.actions.get_staged_file_paths import GetStagedFilePathsAction
from ...application.actions.stage_documents import StageDocumentsAction
from ...config import FLOAT_PRECISION
from ...domain.diff.engine import DiffResult
from ...domain.diff.models import WARNING_OLD_SNAPSHOT_MISSING, DiffState, NodeDiff, PropertyPathDiff
from ...domain.git.models import GitRepository
from ...domain.tree import Property
from ...utils import Log, format_float
from ..protocols.diff_view import DiffView
from ..state import UIState
from ..views.models import HistorySelection
from .presentation_models import DiffTreePresentation, NodePresentation, PropertyPresentation


@dataclass
class _PathTreeNode:
    """Internal tree node for building hierarchical path diffs.

    Attributes:
        name: The path segment name (e.g. "Base", "[0]", "Value", "Expression").
        state: Aggregated diff state for this node and its descendants.
        old_value: Old value at this path, or None if not present.
        new_value: New value at this path, or None if not present.
        children: Child nodes keyed by segment name.
    """

    name: str
    state: DiffState = DiffState.UNCHANGED
    old_value: Any = None
    new_value: Any = None
    children: dict[str, "_PathTreeNode"] = field(default_factory=dict)


def _split_rel_path(path: str) -> list[str]:
    """Convert flattened path strings into hierarchical segments.

    Rules:
    - "." means property-root (no extra segments).
    - Dot separators split named segments ("Base.x" -> ["Base", "x"]).
    - Bracket indices are standalone segments and preserve numeric identity
      ("Constraints[10].Value" -> ["Constraints", "[10]", "Value"]).

    Why this parser exists:
    - A naive split('.') loses index structure.
    - Treating "Constraints[0]" as one segment prevents desired nesting.

    Args:
        path: A flattened path string from ``PropertyPathDiff.path``.

    Returns:
        A list of hierarchical segment names.
    """
    if path == ".":
        return []
    if not path:
        return []
    tokens: list[str] = []
    segment_buf: list[str] = []
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if segment_buf:
                tokens.append("".join(segment_buf))
                segment_buf = []
            i += 1
            continue
        if ch == "[":
            if segment_buf:
                tokens.append("".join(segment_buf))
                segment_buf = []
            j = path.find("]", i)
            if j == -1:
                # Malformed bracket - treat as regular text
                segment_buf.append(ch)
                i += 1
                continue
            tokens.append(path[i : j + 1])
            i = j + 1
            continue
        segment_buf.append(ch)
        i += 1
    if segment_buf:
        tokens.append("".join(segment_buf))
    return tokens


def _aggregate_states(states: list[DiffState]) -> DiffState:
    """Roll up child states to a parent state.

    Rules:
    - No changed descendants -> UNCHANGED
    - All changed descendants are ADDED -> ADDED
    - All changed descendants are DELETED -> DELETED
    - Mixed changes -> MODIFIED

    Args:
        states: List of DiffState values to aggregate.

    Returns:
        The aggregated DiffState.
    """
    changed = [s for s in states if s != DiffState.UNCHANGED]
    if not changed:
        return DiffState.UNCHANGED
    if all(s == DiffState.ADDED for s in changed):
        return DiffState.ADDED
    if all(s == DiffState.DELETED for s in changed):
        return DiffState.DELETED
    return DiffState.MODIFIED


def _insert_path_diff(root: _PathTreeNode, pd: PropertyPathDiff) -> None:
    """Insert a single path diff into the tree at the correct position.

    Walks the path segments to find/create the leaf node, then sets
    its value and expression state. If an expression exists on either
    side, a nested "Expression" child is created.

    Args:
        root: The root node of the tree.
        pd: A ``PropertyPathDiff`` to insert.
    """
    segments = _split_rel_path(pd.path)
    node = root
    for seg in segments:
        node = node.children.setdefault(seg, _PathTreeNode(name=seg))

    # Leaf value row (show all rows, including unchanged)
    node.old_value = pd.old_value.value if pd.old_value is not None else None
    node.new_value = pd.new_value.value if pd.new_value is not None else None
    leaf_states = [pd.value_state]

    # Nested expression row under leaf, if expression exists on either side
    if pd.old_value is not None or pd.new_value is not None:
        old_expr = pd.old_value.expression if pd.old_value is not None else None
        new_expr = pd.new_value.expression if pd.new_value is not None else None
        if old_expr is not None or new_expr is not None:
            expr_node = _PathTreeNode(
                name="Expression",
                state=pd.expression_state,
                old_value=old_expr,
                new_value=new_expr,
            )
            node.children["__expr__"] = expr_node
            leaf_states.append(pd.expression_state)

    node.state = _aggregate_states(leaf_states)


def _rollup_states(node: _PathTreeNode) -> DiffState:
    """Recursively roll up states from leaves to root.

    Each node's state is updated to include the aggregated state of
    all its descendants.

    Args:
        node: The node to start rolling up from.

    Returns:
        The aggregated state for this node.
    """
    child_states = [_rollup_states(c) for c in node.children.values()]
    combined = _aggregate_states([node.state, *child_states])
    node.state = combined
    return combined


def _collect_leaf_values(node: _PathTreeNode, include_expr: bool = False) -> tuple[list[Any], list[Any]]:
    """Recursively collect leaf values from all descendants.

    Excludes expression rows (names starting with '__') by default.
    Only leaf nodes (nodes with direct old_value or new_value) contribute.

    Args:
        node: The node to collect values from.
        include_expr: Whether to include expression row values.

    Returns:
        Tuple of (old_values, new_values) from leaf nodes.
    """
    old_values: list[Any] = []
    new_values: list[Any] = []
    for name, child in node.children.items():
        if not include_expr and name.startswith("__"):
            continue
        # If this node has a direct value, it's a leaf - collect it
        if child.old_value is not None:
            old_values.append(child.old_value)
        if child.new_value is not None:
            new_values.append(child.new_value)
        # Recurse into children regardless (intermediate nodes may have no value)
        child_old, child_new = _collect_leaf_values(child, include_expr)
        old_values.extend(child_old)
        new_values.extend(child_new)
    return old_values, new_values


def _derive_container_summary(values: list[Any]) -> str | None:
    """Create a bracketed summary string from child values.

    Used for container rows (e.g. Placement) where no direct value
    exists but children do. Produces output like "[0.00 0.00 0.00]".

    Float values are formatted with the configured precision.

    Args:
        values: List of old or new values from child presentations.

    Returns:
        A bracketed string like "[0.00 0.00 0.00]", or None if no values.
    """
    non_null = [format_float(v, FLOAT_PRECISION) if isinstance(v, float) else str(v) for v in values if v is not None]
    if not non_null:
        return None
    return "[" + " ".join(non_null) + "]"


def _child_sort_key(name: str) -> tuple:
    """Return a sort key for deterministic child ordering.

    Names sort before indices, indices sort numerically.
    This keeps [2] before [10] and prevents lexicographic jitter.

    Args:
        name: A child node name (e.g. "Base", "[0]", "Expression").

    Returns:
        A tuple suitable for sorting.
    """
    if name.startswith("[") and name.endswith("]"):
        try:
            return (1, int(name[1:-1]))
        except ValueError:
            return (0, name)
    return (0, name)


def _path_tree_to_presentations(node: _PathTreeNode) -> list[PropertyPresentation]:
    """Convert internal tree nodes to UI presentation rows.

    Value policy:
    - If a node has direct old/new values, show them.
    - If it has no direct value but has children, derive FreeCAD-style
      bracket summary from child values for collapsed display.

    Child rows still carry full per-path detail when expanded.

    Args:
        node: The root node to convert (typically the root of a path tree).

    Returns:
        A list of ``PropertyPresentation`` objects.
    """
    out: list[PropertyPresentation] = []
    for key in sorted(node.children.keys(), key=_child_sort_key):
        child = node.children[key]
        grandchildren = _path_tree_to_presentations(child)

        old_value = child.old_value
        new_value = child.new_value
        if old_value is None and new_value is None and grandchildren:
            # FreeCAD-like container summary when there is no direct value row for this segment.
            old_value = _derive_container_summary([gc.old_value for gc in grandchildren])
            new_value = _derive_container_summary([gc.new_value for gc in grandchildren])

        out.append(
            PropertyPresentation(
                name=child.name,
                state=child.state,
                old_value=old_value,
                new_value=new_value,
                children=grandchildren,
            )
        )
    return out


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
        self._dirty_paths: set[str] = set()

        # Wire up the callback for history selection
        self._view.set_history_selection_callback(self.on_history_item_selected)

        # Wire Stage All callback
        self._view.set_stage_all_callback(self.on_stage_all_clicked)

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
            self._diff_results_by_path.clear()
            self._view.show_diff_trees([])
            self._view.set_stage_all_button_visible(False)
            return

        docs_result = self._get_eligible_docs.execute(repo)
        if not docs_result.is_success or not docs_result.data:
            Log.warning(f"No eligible documents: {docs_result.message}")
            # Clear any stale state from prior selection
            self._diff_results_by_path.clear()
            self._view.show_diff_trees([])
            self._view.set_stage_all_button_visible(False)
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

        # Store dirty paths for Stage All button staggability check
        self._dirty_paths = dirty_paths

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
            self._diff_results_by_path.clear()
            self._view.show_diff_trees([])
            self._view.set_stage_all_button_visible(False)

    def _on_staging_selected(self) -> None:
        """Handle Staging item selection.

        For each staged FCStd file:
        1. Get staged snapshot from index (commit=None)
        2. Get snapshot from HEAD
        3. Create diff between HEAD and index

        Displays resulting diffs. For paths where index snapshot is missing,
        creates flat warning items (no tree below).
        """
        # Stage All button is only shown in Working Tree view
        self._view.set_stage_all_button_visible(False)

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
            self._view.show_diff_trees([])

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
        3. Track paths where the selected commit snapshot is missing

        Args:
            repo: GitRepository containing the documents.
            commit_hash: The commit hash to compute diffs for.

        Returns:
            Tuple of (list of DiffResult, list of paths with missing commit snapshots).
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
                # Parent snapshot missing - compare against None and rely on diff warnings.
                diff_result = self._create_diff.execute(None, commit_snapshot)
                if diff_result.is_success and diff_result.data is not None:
                    all_diff_results.append(diff_result.data)
            elif commit_snapshot is None and parent_snapshot is not None:
                # Commit snapshot missing for a changed path - show flat warning row.
                missing_snapshot_paths.append(git_path)
            # Skip cases where both snapshots are None (no data to compare)

        return all_diff_results, missing_snapshot_paths

    def _on_commit_selected(self, commit_hash: str | None) -> None:
        """Handle commit item selection.

        Delegates per-file diff computation to _compute_commit_diffs(),
        then stores results and presents them to the view.
        """
        # Stage All button is only shown in Working Tree view
        self._view.set_stage_all_button_visible(False)

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

        # Remove staged file from dirty paths
        self._dirty_paths.discard(git_path)

        # Collapse the root tree item and disable the stage button
        self._view.collapse_tree_item(git_path)
        self._view.set_stage_button_enabled(git_path, enabled=False)

    def on_stage_all_clicked(self) -> None:
        """Handle 'Stage All' button click.

        Collects all working tree snapshots from _diff_results_by_path that have
        changes (matching the staggability criteria for individual + Stage buttons),
        stages them via StageDocumentsAction, then refreshes the view.
        """
        repo = self._ui_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return

        # Collect snapshots for documents that have diff changes OR are git-dirty
        # (matching individual "+ Stage" button staggability: has_changes or is_git_dirty)
        snapshots = [
            result.new_snapshot
            for result in self._diff_results_by_path.values()
            if result.new_snapshot is not None
            and (
                any(node.has_changes for node in result.hierarchy.roots)
                or result.new_snapshot.git_path in self._dirty_paths
            )
        ]

        if not snapshots:
            Log.warning("No documents with changes to stage")
            return

        # Stage all documents
        result = self._stage_documents.execute(repo, snapshots)
        if not result.is_success:
            Log.warning(f"Failed to stage documents: {result.message}")
            return

        Log.info(f"Successfully staged {len(snapshots)} documents")

        # Clear dirty paths since staged files are no longer dirty
        self._dirty_paths.clear()

        # Refresh the working tree view to reflect staged state
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
            # Also hide Stage All button when no data to display
            self._view.set_stage_all_button_visible(False)
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
                    warnings=[WARNING_OLD_SNAPSHOT_MISSING],
                    stage_button_enabled=False,
                )
            )

        # Sort all presentations alphanumerically by git_path
        presentations.sort(key=lambda p: p.git_path)

        self._view.show_diff_trees(presentations)

        # Stage All button: only visible during Working Tree selection
        is_working_tree = (
            self._view._current_selection is not None and self._view._current_selection.item_kind == "WORKING_TREE"
        )
        if is_working_tree:
            # Enable if any presentation has stage_button_enabled
            any_staggable = any(p.stage_button_enabled for p in presentations)
            self._view.set_stage_all_button_visible(True)
            self._view.set_stage_all_button_enabled(any_staggable)
        else:
            self._view.set_stage_all_button_visible(False)

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
            label=node_diff.label,
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

        Uses ``prop_diff.path_diffs`` to build a nested sub-path tree.
        Root "." path values are mapped to the property top row.
        Expression rows are nested under their corresponding path row.
        Parent nodes get their state from descendants (rollup).

        Args:
            node_diff: Domain NodeDiff with property_diffs

        Returns:
            List of PropertyPresentation for UI display
        """
        presentations: list[PropertyPresentation] = []

        for prop_diff in node_diff.property_diffs:
            # Determine group from the property value
            group = self._extract_property_group(
                prop_diff.new_value if prop_diff.new_value is not None else prop_diff.old_value
            )

            # Build nested path tree from path_diffs
            root = _PathTreeNode(name=prop_diff.property_name, state=prop_diff.state)
            for pd in prop_diff.path_diffs:
                _insert_path_diff(root, pd)
            _rollup_states(root)

            # Map root "." values to the property top row
            prop_old_value = root.old_value
            prop_new_value = root.new_value

            if prop_old_value is None and prop_new_value is None and root.children:
                # Derive container summary from descendant leaf values
                old_leaf_values, new_leaf_values = _collect_leaf_values(root, include_expr=False)
                prop_old_value = _derive_container_summary(old_leaf_values)
                prop_new_value = _derive_container_summary(new_leaf_values)

            # Convert path tree to presentations (excludes root itself)
            children = _path_tree_to_presentations(root)

            presentations.append(
                PropertyPresentation(
                    name=prop_diff.property_name,
                    state=root.state,
                    old_value=prop_old_value,
                    new_value=prop_new_value,
                    children=children,
                    group=group,
                )
            )

        return presentations

    def _extract_property_group(self, prop: Property | None) -> str | None:
        """Extract the group attribute from a Property object."""
        return getattr(prop, "group", None) if prop is not None else None
