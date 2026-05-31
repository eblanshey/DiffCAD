# File responsibility: Diff result presenter for UI.
#
# Transforms domain-level diff results into UI-friendly presentation models.
# Builds nested sub-path trees from PropertyPathDiff and maps them to
# PropertyPresentation objects for view rendering.
"""Diff result presenter for UI.

This module provides the DiffPresenter class that transforms domain-level
diff results into UI-friendly presentation models.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ...application.actions.create_document_diffs import CreateDocumentDiffsAction
from ...application.actions.get_committed_file_paths import GetCommittedFilePathsAction
from ...application.actions.get_dirty_documents import GetDirtyDocumentsAction
from ...application.actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from ...application.actions.get_staged_file_paths import GetStagedFilePathsAction
from ...application.actions.open_document import OpenDocumentAction
from ...application.actions.open_visual_diff import (
    OpenVisualDiffAction,
    OpenVisualDiffRequest,
    VisualDiffRequestType,
)
from ...application.actions.restore_documents import (
    RestoreDocumentsAction,
    RestoreDocumentsRequest,
    RestoreScope,
    RestoreSource,
)
from ...application.actions.result_models import (
    CreateDocumentDiffsRequest,
    DiffIssues,
    DocumentDiffMode,
    DocumentDiffResult,
    GeneralDiffIssue,
    SnapshotIssue,
)
from ...application.actions.stage_documents import StageDocumentsAction
from ...application.actions.unstage_documents import UnstageDocumentsAction
from ...domain.diff.engine import DiffResult
from ...domain.diff.models import DiffState, NodeDiff, PropertyDiff, PropertyPathDiff
from ...domain.freecad_ports import DocumentLike
from ...domain.git.models import GitRepository
from ...domain.settings import SettingsRepository
from ...domain.tree import Property
from ...domain.tree.data_path import PropertyPathType
from ...utils import Log, format_float, translate
from ..protocols.diff_view import DiffView
from ..state import UIState
from ..views.models import HistorySelection
from .presentation_models import (
    DiffComputationFailedIndicator,
    DiffTreePresentation,
    DocumentStatusIndicator,
    FileChangedOnlyIndicator,
    NewInvalidSnapshotIndicator,
    NewSnapshotMissingIndicator,
    NodePresentation,
    OldInvalidSnapshotIndicator,
    OldSnapshotMissingIndicator,
    PropertyPresentation,
    WorkingTreeDocumentClosedIndicator,
)


if TYPE_CHECKING:
    pass


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


def _format_pv(pv: Any, precision: int) -> Any:
    """Format a PropertyPathValue for UI display.

    FLOAT and QUANTITY types use precision-based float formatting.
    QUANTITY returns bracketed string like "[10.00 mm]".
    Non-PropertyPathValue inputs (strings from container summaries or
    expression rows) are returned unchanged.

    Args:
        pv: A PropertyPathValue instance, a pre-formatted string, or None.
        precision: Number of decimal places for float formatting.

    Returns:
        Formatted display value, or the input unchanged if not a PropertyPathValue.
    """
    if pv is None:
        return None
    if getattr(pv, "type_", None) == PropertyPathType.FLOAT:
        return format_float(float(pv.value), precision)
    if getattr(pv, "type_", None) == PropertyPathType.QUANTITY:
        num = format_float(float(pv.value), precision)
        unit = pv.unit if pv.unit else ""
        return num + " " + unit
    if hasattr(pv, "value"):
        return pv.value
    return pv


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

    # Leaf value row (store PropertyPathValue for type-aware formatting later)
    node.old_value = pd.old_value
    node.new_value = pd.new_value
    node.state = pd.value_state

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


def _set_subtree_state(node: _PathTreeNode, state: DiffState) -> None:
    """Set one state on a whole path tree."""
    node.state = state
    for child in node.children.values():
        _set_subtree_state(child, state)


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


def _derive_container_summary(values: list[Any], precision: int) -> str | None:
    """Create a bracketed summary string from child values.

    Used for container rows (e.g. Placement) where no direct value
    exists but children do. Produces output like "[0.00 0.00 0.00]".

    Accepts PropertyPathValue instances and formats them with the given
    precision. QUANTITY types are formatted as "10.00 mm" within the
    summary brackets.

    Args:
        values: List of PropertyPathValue or raw values from child nodes.
        precision: Number of decimal places for float formatting.

    Returns:
        A bracketed string like "[0.00 0.00 0.00]", or None if no values.
    """
    non_null_values = [v for v in values if v is not None]
    non_null = [_format_pv(v, precision) for v in non_null_values]
    non_null = [str(v) for v in non_null if v is not None]
    if not non_null:
        return None
    return "[" + " ".join(non_null) + "]"


def _child_sort_key(name: str) -> tuple:
    """Return a sort key for deterministic child ordering.

    Names sort before indices, indices sort numerically.
    This keeps [2] before [10] and prevents lexicographic jitter.

    Args:
        name: A child node name (e.g. "Base", "[0]", "Value", "Unit").

    Returns:
        A tuple suitable for sorting.
    """
    if name.startswith("[") and name.endswith("]"):
        try:
            return (1, int(name[1:-1]))
        except ValueError:
            return (0, name)
    return (0, name)


def _path_tree_to_presentations(node: _PathTreeNode, precision: int) -> list[PropertyPresentation]:
    """Convert internal tree nodes to UI presentation rows.

    Value policy:
    - If a node has direct old/new values, show them.
    - If it has no direct value but has children, derive FreeCAD-style
      bracket summary from child values for collapsed display.

    Child rows still carry full per-path detail when expanded.

    Args:
        node: The root node to convert (typically the root of a path tree).
        precision: Number of decimal places for float formatting.

    Returns:
        A list of ``PropertyPresentation`` objects.
    """
    out: list[PropertyPresentation] = []
    for key in sorted(node.children.keys(), key=_child_sort_key):
        child = node.children[key]
        grandchildren = _path_tree_to_presentations(child, precision)

        old_value = child.old_value
        new_value = child.new_value
        if old_value is None and new_value is None and grandchildren:
            # FreeCAD-like container summary when there is no direct value row.
            old_value = _derive_container_summary([gc.old_value for gc in grandchildren], precision)
            new_value = _derive_container_summary([gc.new_value for gc in grandchildren], precision)

        # Format PropertyPathValue to display values
        old_value = _format_pv(old_value, precision)
        new_value = _format_pv(new_value, precision)

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


def _build_property_presentation(
    prop_diff: PropertyDiff,
    precision: int,
    group: str | None,
) -> PropertyPresentation:
    """Build UI presentation for one property diff."""
    root_path = next((pd for pd in prop_diff.path_diffs if pd.path == "."), None)
    root_state = _property_root_state(prop_diff, root_path)
    root = _PathTreeNode(name=prop_diff.property_name, state=root_state)
    for pd in prop_diff.path_diffs:
        _insert_path_diff(root, pd)

    if prop_diff.state in (DiffState.ADDED, DiffState.DELETED):
        _set_subtree_state(root, prop_diff.state)

    prop_old_value, prop_new_value = _property_root_values(root, precision)
    return PropertyPresentation(
        name=prop_diff.property_name,
        state=root.state,
        old_value=prop_old_value,
        new_value=prop_new_value,
        children=_path_tree_to_presentations(root, precision),
        group=group,
    )


def _property_root_state(prop_diff: PropertyDiff, root_path: PropertyPathDiff | None) -> DiffState:
    """Return state for property root without inheriting child path changes."""
    if prop_diff.state in (DiffState.ADDED, DiffState.DELETED):
        return prop_diff.state
    return root_path.value_state if root_path else DiffState.UNCHANGED


def _property_root_values(root: _PathTreeNode, precision: int) -> tuple[Any, Any]:
    """Return formatted old and new values for a property root row."""
    old_value = root.old_value
    new_value = root.new_value
    if old_value is None and new_value is None and root.children:
        old_leaf_values, new_leaf_values = _collect_leaf_values(root, include_expr=False)
        old_value = _derive_container_summary(old_leaf_values, precision)
        new_value = _derive_container_summary(new_leaf_values, precision)
    return _format_pv(old_value, precision), _format_pv(new_value, precision)


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
        create_document_diffs_action: CreateDocumentDiffsAction,
        stage_documents_action: StageDocumentsAction,
        unstage_documents_action: UnstageDocumentsAction,
        get_dirty_documents_action: GetDirtyDocumentsAction,
        get_staged_file_paths_action: GetStagedFilePathsAction,
        get_committed_file_paths_action: GetCommittedFilePathsAction,
        open_visual_feature_diff_action: OpenVisualDiffAction,
        open_document_action: OpenDocumentAction,
        restore_documents_action: RestoreDocumentsAction,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            view: DiffView implementation to display diff results
            ui_state: UI state holder containing git repository info
            get_eligible_docs_action: Action to get eligible open documents
            create_document_diffs_action: Action to orchestrate document diffs by mode
            stage_documents_action: Action to stage documents to git
            get_dirty_documents_action: Action to get dirty documents
            settings_repo: Settings repository for runtime precision (optional, uses default if None)
        """
        from ...domain.config import FLOAT_PRECISION as DEFAULT_FLOAT_PRECISION

        self._view = view
        self._ui_state = ui_state
        self._get_eligible_docs = get_eligible_docs_action
        self._create_document_diffs = create_document_diffs_action
        self._stage_documents = stage_documents_action
        self._unstage_documents = unstage_documents_action
        self._get_dirty_documents = get_dirty_documents_action
        self._open_visual_feature_diff = open_visual_feature_diff_action
        self._open_document = open_document_action
        self._restore_documents = restore_documents_action
        self._get_staged_file_paths = get_staged_file_paths_action
        self._get_committed_file_paths = get_committed_file_paths_action
        self._settings_repo = settings_repo
        self._default_precision = DEFAULT_FLOAT_PRECISION
        self._diff_results_by_path: dict[str, DiffResult] = {}
        self._document_results_by_path: dict[str, DocumentDiffResult] = {}
        self._current_history_selection: HistorySelection | None = None
        self._focus_history_window_callback: Callable[[], None] | None = None

        # Wire up the callback for history selection
        self._view.set_history_selection_callback(self.on_history_item_selected)

        # Wire Stage All callback
        self._view.set_stage_all_callback(self.on_stage_all_clicked)
        self._view.set_remove_all_button_callback(self.on_remove_all_from_reviewed_clicked)
        self._view.set_remove_from_reviewed_button_callback(self.on_remove_from_reviewed_button_clicked)
        self._view.set_remove_all_from_reviewed_callback(self.on_remove_all_from_reviewed_clicked)
        self._view.set_mark_all_reviewed_from_in_progress_callback(self.on_stage_all_clicked)
        self._view.set_restore_button_callback(self.on_restore_document_clicked)
        self._view.set_restore_all_button_callback(self.on_restore_all_clicked)
        self._view.set_restore_all_from_history_context_callback(self.on_restore_all_from_history_context)
        self._view.set_open_document_for_comparison_callback(self.on_open_document_for_comparison_clicked)
        self._view.set_force_diff_callback(self.force_working_tree_diffs)

    def on_open_document_for_comparison_clicked(self, git_path: str) -> None:
        """Open missing working-tree document in FreeCAD, then recompute Current Files diff."""
        repo = self._ui_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return
        document_path = str(Path(repo.absolute_path) / git_path)
        result = self._open_document.execute(document_path)
        if not result.is_success:
            if result.message:
                Log.warning(result.message)
            return
        self._on_working_tree_selected()
        if self._focus_history_window_callback is not None:
            self._focus_history_window_callback()

    def set_focus_history_window_callback(self, callback: Callable[[], None]) -> None:
        """Set callback that focuses history host window after async FreeCAD actions."""
        self._focus_history_window_callback = callback

    def _get_precision(self) -> int:
        """Get the current float precision from settings or use default.

        Returns:
            The float precision value (decimal places) from settings,
            or the default if settings repo is not available.
        """
        if self._settings_repo is not None:
            try:
                settings = self._settings_repo.get_settings()
                return settings.float_precision
            except (AttributeError, RuntimeError):
                # If settings retrieval fails, fall back to default
                pass
        return self._default_precision

    def on_history_item_selected(self, selection: HistorySelection) -> None:
        """Handle single item selection from history list.

        Args:
            selection: HistorySelection containing item_kind and optional commit_hash
        """
        self._current_history_selection = selection
        if selection.item_kind == "WORKING_TREE":
            self._on_working_tree_selected()
        elif selection.item_kind == "STAGING":
            self._on_staging_selected()
        elif selection.item_kind == "COMMIT":
            self._on_commit_selected(selection.commit_hash)

    def clear_property_diff(self) -> None:
        """Clear property diff panel content."""
        self._view.clear_property_diff()

    def clear_doc_diff(self) -> None:
        """Clear document diff data and document/property diff panels."""
        self._diff_results_by_path.clear()
        self._view.clear_doc_diffs()

    def _on_working_tree_selected(self) -> None:
        """Handle Working Tree item selection.

        For each eligible document:
        1. Create working tree snapshot
        2. Create diff against None (old snapshot)
        3. Get dirty documents (ONE call for all eligible docs)
        4. Collect results, logging failures
        """
        repo = self._ui_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            self.clear_doc_diff()
            return

        eligible_docs = self._get_eligible_documents(repo)
        if not eligible_docs:
            self.clear_doc_diff()
            return

        document_results = self._compute_working_tree_diffs(repo, eligible_docs)
        self._store_results(document_results)

        if document_results:
            self.present_diffs(document_results)
        else:
            Log.info("No diff results to display")
            self.clear_doc_diff()

    def _get_eligible_documents(self, repo: GitRepository) -> list[DocumentLike] | None:
        """Get eligible documents for the repository."""
        docs_result = self._get_eligible_docs.execute(repo)
        if not docs_result.is_success or not docs_result.data:
            Log.warning(f"No eligible documents: {docs_result.message}")
            return None
        return docs_result.data

    def _compute_working_tree_diffs(
        self, repo: GitRepository, eligible_docs: list[DocumentLike], force_all: bool = False
    ) -> list[DocumentDiffResult]:
        """Compute diffs for working tree mode."""
        doc_diff_results_result = self._create_document_diffs.execute(
            CreateDocumentDiffsRequest(
                mode=DocumentDiffMode.WORKING_TREE, repo=repo, eligible_docs=eligible_docs, force_all=force_all
            )
        )
        if doc_diff_results_result.is_success and doc_diff_results_result.data:
            return doc_diff_results_result.data
        return []

    def force_working_tree_diffs(self) -> None:
        """Force diff computation for all eligible documents, including unchanged ones."""
        repo = self._ui_state.git_repository
        if repo is None:
            return

        eligible_docs = self._get_eligible_documents(repo)
        if not eligible_docs:
            return

        document_results = self._compute_working_tree_diffs(repo, eligible_docs, force_all=True)
        self._store_results(document_results)

        if document_results:
            self.present_diffs(document_results)
        else:
            self.clear_doc_diff()

        self._view.show_info_message(
            translate("History", "Force Refresh"),
            translate("History", "Force refreshed comparisons for all open files."),
        )

    def _store_results(self, document_results: list[DocumentDiffResult]) -> None:
        """Store action results and diff payloads for later use."""
        self._diff_results_by_path.clear()
        self._document_results_by_path = {result.git_path: result for result in document_results}
        for result in document_results:
            if result.snapshot_diff is not None:
                self._diff_results_by_path[result.git_path] = result.snapshot_diff

    def _on_staging_selected(self) -> None:
        """Handle Staging item selection.

        For each staged FCStd file:
        1. Get staged snapshot from index (commit=None)
        2. Get snapshot from HEAD
        3. Create diff between HEAD and index

        Displays resulting diffs. For paths where index snapshot is missing,
        creates flat warning items (no tree below).
        """
        self._view.set_stage_all_button_visible(False)
        self._view.set_remove_all_button_visible(False)

        repo = self._ui_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            self.clear_doc_diff()
            return

        document_results = self._compute_staging_diffs(repo)
        self._store_results(document_results)

        if document_results:
            self.present_diffs(document_results)
        else:
            Log.info("No diff results to display for staging")
            self.clear_doc_diff()

    def _compute_staging_diffs(self, repo: GitRepository) -> list[DocumentDiffResult]:
        """Compute diffs for staging mode."""
        doc_diff_results_result = self._create_document_diffs.execute(
            CreateDocumentDiffsRequest(mode=DocumentDiffMode.STAGING, repo=repo)
        )
        if doc_diff_results_result.is_success and doc_diff_results_result.data:
            return doc_diff_results_result.data
        return []

    def _on_commit_selected(self, commit_hash: str | None) -> None:
        """Handle commit item selection.

        Requests document-level commit diffs via CreateDocumentDiffsAction,
        then stores results and presents them to the view.
        """
        self._view.set_stage_all_button_visible(False)
        self._view.set_remove_all_button_visible(False)

        if commit_hash is None:
            Log.warning("Commit selection received without commit hash")
            self.clear_doc_diff()
            return

        repo = self._ui_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            self.clear_doc_diff()
            return

        document_results = self._compute_commit_diffs(repo, commit_hash)
        self._store_results(document_results)

        if document_results:
            self.present_diffs(document_results)
        else:
            Log.info(f"No FCStd files changed in commit {commit_hash}")
            self.clear_doc_diff()

    def _compute_commit_diffs(self, repo: GitRepository, commit_hash: str) -> list[DocumentDiffResult]:
        """Compute diffs for commit mode."""
        doc_diff_results_result = self._create_document_diffs.execute(
            CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash=commit_hash)
        )
        if doc_diff_results_result.is_success and doc_diff_results_result.data:
            return doc_diff_results_result.data
        return []

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

        # Clear stale property view tied to prior node selection
        self.clear_property_diff()

        # Remove staged path from cached Current Files results and re-present remainder.
        self._remove_path_from_cached_working_tree_results(git_path)

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

        # Collect snapshots that keep working-tree stage button enabled.
        snapshots = [
            result.new_snapshot
            for result in self._diff_results_by_path.values()
            if result.new_snapshot is not None
            and self._compute_stage_button_state(self._document_results_by_path.get(result.new_snapshot.git_path), True)
        ]

        if not snapshots:
            # Normal no-op case (for example, Current Files context action with nothing to stage).
            return

        # Stage all documents
        result = self._stage_documents.execute(repo, snapshots)
        if not result.is_success:
            Log.warning(f"Failed to stage documents: {result.message}")
            return

        Log.info(f"Successfully staged {len(snapshots)} documents")

        # Clear current doc/property selection before reloading trees
        self.clear_doc_diff()

        # Refresh the working tree view to reflect staged state
        self._on_working_tree_selected()

    def _remove_path_from_cached_working_tree_results(self, git_path: str) -> None:
        """Remove one path from cached working-tree results and refresh view from cache."""
        self._diff_results_by_path.pop(git_path, None)
        self._document_results_by_path.pop(git_path, None)

        if not self._document_results_by_path:
            self.clear_doc_diff()
            return

        remaining_results = sorted(self._document_results_by_path.values(), key=lambda result: result.git_path)
        self.present_diffs(remaining_results)

    def on_remove_from_reviewed_button_clicked(self, git_path: str) -> None:
        """Unstage one reviewed document unit (FCStd + snapshot yaml)."""
        repo = self._ui_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return

        result = self._unstage_documents.execute(repo, [git_path])
        if not result.is_success:
            Log.warning(f"Failed to remove document from reviewed: {result.message}")
            return

        Log.info(f"Removed reviewed document: {git_path}")
        self.clear_property_diff()
        self._on_staging_selected()

    def on_remove_all_from_reviewed_clicked(self) -> None:
        """Unstage all reviewed staged paths from index."""
        repo = self._ui_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return

        result = self._unstage_documents.execute(repo, None)
        if not result.is_success:
            Log.warning(f"Failed to remove all reviewed files: {result.message}")
            return

        Log.info("Removed all reviewed files")
        self.clear_property_diff()
        current_selection = self._view.get_current_history_selection()
        if current_selection is None:
            return
        if current_selection.item_kind == "STAGING":
            self._on_staging_selected()
        elif current_selection.item_kind == "WORKING_TREE":
            self._on_working_tree_selected()

    def on_restore_document_clicked(self, git_path: str) -> None:
        """Restore one document for current staging/commit source."""
        current = self._current_history_selection
        repo = self._ui_state.git_repository
        if current is None or repo is None:
            return
        if current.item_kind not in ("STAGING", "COMMIT"):
            return
        source, commit_hash = self._restore_source_from_selection(current)
        if not self._view.show_restore_file_confirmation_dialog(git_path):
            return
        request = RestoreDocumentsRequest(
            repo=repo,
            source=source,
            scope=RestoreScope.SINGLE_PATH,
            commit_hash=commit_hash,
            paths=[git_path],
        )
        self._execute_restore(request)

    def on_restore_all_clicked(self) -> None:
        """Restore listed/all files for current staging/commit source."""
        current = self._current_history_selection
        if current is None:
            return
        self.on_restore_all_from_history_context(current)

    def on_restore_all_from_history_context(self, selection: HistorySelection) -> None:
        """Restore from history context selection without changing selected row."""
        repo = self._ui_state.git_repository
        if repo is None:
            return
        if selection.item_kind not in ("STAGING", "COMMIT"):
            return
        scope_text = self._view.show_restore_scope_dialog()
        if scope_text is None:
            return
        if not self._view.show_restore_file_confirmation_dialog(""):
            return

        source, commit_hash = self._restore_source_from_selection(selection)
        listed_paths = self._listed_paths_for_selection(repo, selection)
        scope = RestoreScope.LISTED_FCSTD if scope_text == "listed_fcstd" else RestoreScope.ALL_FCSTD
        request = RestoreDocumentsRequest(
            repo=repo,
            source=source,
            scope=scope,
            commit_hash=commit_hash,
            paths=listed_paths,
        )
        self._execute_restore(request)

    def _restore_source_from_selection(self, selection: HistorySelection) -> tuple[RestoreSource, str | None]:
        if selection.item_kind == "COMMIT":
            return RestoreSource.COMMIT, selection.commit_hash
        return RestoreSource.INDEX, None

    def _listed_paths_for_selection(self, repo: GitRepository, selection: HistorySelection) -> list[str]:
        if selection.item_kind == "COMMIT" and selection.commit_hash:
            result = self._get_committed_file_paths.execute(repo, selection.commit_hash)
            return result.data if result.is_success and result.data else []
        result = self._get_staged_file_paths.execute(repo)
        return result.data if result.is_success and result.data else []

    def _execute_restore(self, request: RestoreDocumentsRequest) -> None:
        result = self._restore_documents.execute(request)
        self.clear_property_diff()
        if not result.is_success:
            self._view.show_error_message(translate("History", "Restore"), result.message or "Restore failed")
            return
        self._view.show_info_message(translate("History", "Restore"), translate("History", "Restoration complete."))
        current = self._current_history_selection
        if current is not None and current.item_kind == "WORKING_TREE":
            self._on_working_tree_selected()

    def present_diffs(
        self,
        document_results: list[DocumentDiffResult],
    ) -> None:
        """Transform multiple DiffResults into presentation models and display.

        Args:
            document_results: Action-level document diff results.
        """
        if not document_results:
            self.clear_doc_diff()
            return

        self.clear_property_diff()

        is_working_tree = (
            self._current_history_selection is not None and self._current_history_selection.item_kind == "WORKING_TREE"
        )

        presentations = self._build_presentations(
            document_results,
            is_working_tree,
        )

        presentations.sort(key=lambda p: p.git_path)

        self._view.show_doc_diffs(presentations)
        self._configure_summary_buttons(presentations)
        self._show_summary(document_results)

    def _build_presentations(
        self,
        document_results: list[DocumentDiffResult],
        is_working_tree: bool,
    ) -> list[DiffTreePresentation]:
        """Build document presentations from diff results."""
        presentations: list[DiffTreePresentation] = []
        for document_result in document_results:
            if not self._should_display_document_result(document_result):
                continue
            git_path = document_result.git_path
            indicators = self._get_document_indicators(document_result.issues)
            nodes: list[NodePresentation] = []
            if document_result.snapshot_diff is not None:
                nodes = [self._format_node(node) for node in document_result.snapshot_diff.hierarchy.roots]
            stage_button_enabled = self._compute_stage_button_state(document_result, is_working_tree)

            presentations.append(
                DiffTreePresentation(
                    nodes=nodes,
                    git_path=git_path,
                    indicators=indicators,
                    document_state=document_result.document_state,
                    stage_button_enabled=stage_button_enabled,
                )
            )
        return presentations

    def _should_display_document_result(self, document_result: DocumentDiffResult) -> bool:
        """Return whether one document result should be shown in the document tree."""
        if document_result.document_state != DiffState.UNCHANGED:
            return True
        if document_result.snapshot_diff is not None and document_result.snapshot_diff.has_changes:
            return True
        return document_result.issues.has_any()

    def _compute_stage_button_state(
        self,
        document_result: DocumentDiffResult | None,
        is_working_tree: bool,
    ) -> bool:
        """Compute whether stage button should be enabled.

        Stage writes new-side snapshot. Enabled when:
        - document has changes (not UNCHANGED), OR old snapshot is missing (first snapshot needed)
        - new-side snapshot has no issue (dirty-not-open files block staging)
        """
        if not is_working_tree or document_result is None:
            return False
        has_changes = document_result.document_state != DiffState.UNCHANGED
        needs_snapshot = document_result.issues.old_snapshot is not None
        return (has_changes or needs_snapshot) and document_result.issues.new_snapshot is None

    def _configure_summary_buttons(self, presentations: list[DiffTreePresentation]) -> None:
        """Configure summary-bar bulk action buttons by current history selection."""
        current = self._current_history_selection
        is_working_tree = current is not None and current.item_kind == "WORKING_TREE"
        is_staging = current is not None and current.item_kind == "STAGING"
        is_commit = current is not None and current.item_kind == "COMMIT"

        if is_working_tree:
            any_staggable = any(p.stage_button_enabled for p in presentations)
            self._view.set_stage_all_button_visible(True)
            self._view.set_stage_all_button_enabled(any_staggable)
            self._view.set_remove_all_button_visible(False)
            self._view.set_remove_all_button_enabled(False)
            self._view.set_restore_all_button_visible(False)
            self._view.set_restore_all_button_enabled(False)
            return

        if is_staging:
            self._view.set_stage_all_button_visible(False)
            self._view.set_stage_all_button_enabled(False)
            self._view.set_remove_all_button_visible(True)
            self._view.set_remove_all_button_enabled(bool(presentations))
            self._view.set_restore_all_button_visible(bool(presentations))
            self._view.set_restore_all_button_enabled(bool(presentations))
            return

        if is_commit:
            self._view.set_stage_all_button_visible(False)
            self._view.set_stage_all_button_enabled(False)
            self._view.set_remove_all_button_visible(False)
            self._view.set_remove_all_button_enabled(False)
            self._view.set_restore_all_button_visible(bool(presentations))
            self._view.set_restore_all_button_enabled(bool(presentations))
            return

        self._view.set_stage_all_button_visible(False)
        self._view.set_stage_all_button_enabled(False)
        self._view.set_remove_all_button_visible(False)
        self._view.set_remove_all_button_enabled(False)
        self._view.set_restore_all_button_visible(False)
        self._view.set_restore_all_button_enabled(False)

    def _show_summary(self, document_results: list[DocumentDiffResult]) -> None:
        """Show per-status summary counts derived from document status."""
        modified_docs = 0
        deleted_docs = 0
        added_docs = 0
        for document_result in document_results:
            if document_result.document_state == DiffState.MODIFIED:
                modified_docs += 1
            elif document_result.document_state == DiffState.DELETED:
                deleted_docs += 1
            elif document_result.document_state == DiffState.ADDED:
                added_docs += 1
        self._view.show_summary(modified_docs=modified_docs, deleted_docs=deleted_docs, added_docs=added_docs)

    def _get_document_indicators(self, issues: DiffIssues) -> list[DocumentStatusIndicator]:
        """Build UI indicators for categorized document issues."""
        indicators: list[DocumentStatusIndicator] = []
        if issues.old_snapshot == SnapshotIssue.MISSING:
            indicators.append(OldSnapshotMissingIndicator())
        elif issues.old_snapshot == SnapshotIssue.INVALID:
            indicators.append(OldInvalidSnapshotIndicator())

        if issues.new_snapshot == SnapshotIssue.MISSING:
            if (
                self._current_history_selection is not None
                and self._current_history_selection.item_kind == "WORKING_TREE"
            ):
                indicators.append(WorkingTreeDocumentClosedIndicator())
            else:
                indicators.append(NewSnapshotMissingIndicator())
        elif issues.new_snapshot == SnapshotIssue.INVALID:
            indicators.append(NewInvalidSnapshotIndicator())

        for issue in issues.general:
            if issue == GeneralDiffIssue.DIFF_COMPUTATION_FAILED:
                indicators.append(DiffComputationFailedIndicator())
            elif issue == GeneralDiffIssue.GIT_CHANGED_NO_PARAMETRIC_DIFF:
                indicators.append(FileChangedOnlyIndicator())
        return indicators

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
            has_changes=node_diff.has_deep_changes,
            visual_diff_enabled=self._is_visual_diff_enabled(node_diff.type_id),
            children=[self._format_node(child) for child in node_diff.children],
        )

    def _is_visual_diff_enabled(self, type_id: str) -> bool:
        """Return True when node type is eligible for visual diff."""
        return type_id.startswith("Part::") or type_id.startswith("PartDesign::") or type_id == "Sketcher::SketchObject"

    def on_visual_diff_clicked(self, git_path: str, node_path: str) -> None:
        """Open visual diff for one node in current history mode."""
        current_selection = self._current_history_selection
        if current_selection is None:
            return

        repo = self._ui_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return

        request = self._build_visual_diff_request(current_selection, repo, git_path, node_path)
        if request is None:
            return

        result = self._open_visual_feature_diff.execute(request)
        if not result.is_success and result.message:
            Log.warning(result.message)

    def _build_visual_diff_request(
        self,
        selection: HistorySelection,
        repo: GitRepository,
        git_path: str,
        node_path: str,
    ) -> OpenVisualDiffRequest | None:
        """Build visual diff request for current history mode."""
        if selection.item_kind == "WORKING_TREE":
            return OpenVisualDiffRequest(
                repo=repo,
                git_path=git_path,
                node_path=node_path,
                type=VisualDiffRequestType.WORKING,
            )

        if selection.item_kind == "STAGING":
            return OpenVisualDiffRequest(
                repo=repo,
                git_path=git_path,
                node_path=node_path,
                type=VisualDiffRequestType.STAGING,
            )

        if selection.item_kind == "COMMIT" and selection.commit_hash:
            return OpenVisualDiffRequest(
                repo=repo,
                git_path=git_path,
                node_path=node_path,
                type=VisualDiffRequestType.COMMIT,
                old_commit=f"{selection.commit_hash}~1",
                new_commit=selection.commit_hash,
            )

        Log.warning("Commit selection missing commit hash for visual diff")
        return None

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
            self.clear_property_diff()
            return

        # Look up the correct DiffResult for this document
        diff_result = self._diff_results_by_path.get(git_path)
        if diff_result is None:
            Log.debug(f"[PRESENTER] No DiffResult found for git_path: {git_path}")
            self.clear_property_diff()
            return

        # Find NodeDiff by path within this document's hierarchy
        node_diff = diff_result.hierarchy.find_by_path(node_path)

        # If not found, clear properties
        if node_diff is None:
            Log.debug(f"[PRESENTER] NodeDiff not found for path: {node_path} in document {git_path}")
            self.clear_property_diff()
            return

        # Transform property diffs to presentations
        properties = self._transform_property_diffs(node_diff)
        Log.debug(f"[PRESENTER] Transformed to {len(properties)} PropertyPresentation")
        self._view.show_property_diff(properties)

    def _transform_property_diffs(self, node_diff: NodeDiff) -> list[PropertyPresentation]:
        """Transform domain PropertyDiff to presentation format.

        Uses ``prop_diff.path_diffs`` to build a nested sub-path tree.
        Root "." path values are mapped to the property top row.
        Expression rows are nested under their corresponding path row.
        Each node's state reflects only its own value changes — expression
        and child path changes do not propagate upward.

        Args:
            node_diff: Domain NodeDiff with property_diffs

        Returns:
            List of PropertyPresentation for UI display
        """
        precision = self._get_precision()
        presentations: list[PropertyPresentation] = []

        for prop_diff in node_diff.property_diffs:
            # Determine group from the property value
            group = self._extract_property_group(
                prop_diff.new_value if prop_diff.new_value is not None else prop_diff.old_value
            )

            presentations.append(_build_property_presentation(prop_diff, precision, group))

        return presentations

    def _extract_property_group(self, prop: Property | None) -> str | None:
        """Extract the group attribute from a Property object."""
        return getattr(prop, "group", None) if prop is not None else None
