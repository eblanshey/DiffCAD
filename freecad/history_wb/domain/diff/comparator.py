# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Efficient snapshot occurrence comparison using normalized
# object/occurrence structures. Compares two document snapshots and produces a
# hierarchical structure of NodeDiff objects representing added, deleted, and modified nodes.
#
# The module contains two main classes:
# - TreeComparator: Compares tree structures using path-based indexing
# - PropertyComparator: Compares property values and delegates state calculation
#   to PropertyDiff (which uses path-based diffs internally).
"""Tree and property comparison algorithms."""

from collections import deque
from dataclasses import dataclass

from ..snapshots import Snapshot
from ..snapshots.models import SnapshotObject
from ..tree.property import Property
from .models import DiffHierarchy, DiffResult, DiffState, NodeDiff, PropertyDiff


@dataclass(frozen=True)
class _OccurrenceRow:
    """Internal comparison row materialized from object+occurrence."""

    id: int
    name: str
    type_id: str
    label: str
    path: str
    after: str | None
    properties: dict[str, Property]


def _effective_exclusions(
    global_excluded: list[str],
    by_type: dict[str, list[str]],
    old_type: str | None,
    new_type: str | None,
) -> set[str]:
    """Compute the effective set of excluded property names for a node comparison.

    The effective set is the union of:
    - Global exclusions (always applied)
    - Per-type exclusions for the old node's type (if present)
    - Per-type exclusions for the new node's type (if present)

    This ensures correct behavior when a node's type changes across snapshots.

    Args:
        global_excluded: List of globally excluded property names
        by_type: Dict mapping type IDs to lists of excluded property names
        old_type: Type ID of the old node (None if node only exists in new)
        new_type: Type ID of the new node (None if node only exists in old)

    Returns:
        Set of property names to exclude from comparison
    """
    effective: set[str] = set(global_excluded)
    if old_type is not None:
        effective.update(by_type.get(old_type, []))
    if new_type is not None:
        effective.update(by_type.get(new_type, []))
    return effective


class TreeComparator:
    """Compares two normalized snapshot occurrence structures.

    This class provides instance methods for comparing tree snapshots efficiently
    using path-based indexing to achieve O(n+m) performance. Internal rows contain
    object payload joined with occurrence path/ordering metadata.

    The algorithm:
    1. Sort both snapshots by path length (parents first)
    2. Build path index for old/new occurrences
    3. Process old occurrences to create deleted/modified diffs
    4. Process new occurrences to create added diffs
    5. Build DiffHierarchy using add_node()
    6. Reorder roots and siblings using node ``after`` links
    7. Return DiffResult with DiffHierarchy and counts
    """

    def __init__(self, precision: int = 2) -> None:
        """Initialize TreeComparator with a PropertyComparator instance.

        Args:
            precision: Number of decimal places for float comparison (default: 2)
        """
        self._property_comparator = PropertyComparator(precision=precision)
        self._precision = precision

    def _get_parent_path(self, child_path: str) -> str:
        """Extract the parent path while preserving the leading slash format.

        This method handles both path formats (with or without leading slashes)
        and returns the parent path in the same format as the input.

        Args:
            child_path: The child path string (e.g., "/Body/Pad" or "Body/Pad")

        Returns:
            The parent path string, or empty string if child_path is a root node

        Examples:
            >>> _get_parent_path("/Body/Pad")
            '/Body'
            >>> _get_parent_path("Body/Pad")
            'Body'
            >>> _get_parent_path("/Part")
            ''
            >>> _get_parent_path("Part")
            ''
            >>> _get_parent_path("/Body/Pad/Sketch")
            '/Body/Pad'
        """
        has_leading_slash = child_path.startswith("/")
        parts = [p for p in child_path.split("/") if p]  # Remove empty segments
        if len(parts) <= 1:
            return ""  # Root node, no parent
        parent_parts = parts[:-1]
        parent_path = "/".join(parent_parts)
        return "/" + parent_path if has_leading_slash else parent_path

    def _sort_rows_by_path_depth(self, rows: list[_OccurrenceRow]) -> list[_OccurrenceRow]:
        """Sort occurrence rows by path depth (parents before children).

        This ensures parents are processed before children for proper exclusion logic.

        Args:
            rows: List of occurrence rows to sort

        Returns:
            List of rows sorted by path depth (shallowest first)
        """
        return sorted(rows, key=lambda row: (row.path.count("/") if row.path else 0, row.path))

    def _node_name_from_path(self, path: str) -> str:
        """Extract node name from path using final segment."""
        if not path:
            return ""
        segments = [segment for segment in path.split("/") if segment]
        return segments[-1] if segments else ""

    def _preferred_after(self, node_diff: NodeDiff) -> str | None:
        """Choose ordering source: new snapshot when available, else old snapshot.

        Nodes present in the new snapshot (UNCHANGED/MODIFIED/ADDED) are ordered
        by ``new_after``. Deleted nodes are ordered by ``old_after``.
        """
        after = node_diff.new_after if node_diff.new_path is not None else node_diff.old_after
        if after is None:
            return None
        # after may be stored as occurrence path; ordering graph is sibling-name keyed.
        return self._node_name_from_path(after)

    def _order_nodes_by_after(self, nodes: list[NodeDiff]) -> list[NodeDiff]:
        """Order sibling nodes using ``after`` links in linear time.

        The ``after`` metadata encodes a predecessor constraint among siblings:
        for a node ``B`` with ``after='A'``, ``A`` must appear before ``B``.
        We model this as a directed edge ``A -> B`` and then compute a stable
        topological ordering with Kahn's algorithm:

        1. Build a sibling-name map in original insertion order.
           - If duplicate sibling names are detected, return input order as a
             safe fallback (name-based constraints would be ambiguous).
        2. Build a graph from valid in-group ``after`` edges and an indegree map.
           - Ignore ``after`` references that point outside the group.
           - Ignore self-references.
        3. Initialize a queue with indegree-0 nodes in original order.
        4. Repeatedly emit queue head, decrement successor indegrees, enqueue
           successors that reach indegree 0.
        5. If unresolved nodes remain (cycle/broken chain), append them in
           original order for deterministic behavior.

        Complexity:
            O(n + e) time and O(n + e) space, where ``n`` is sibling count and
            ``e`` is number of valid in-group ``after`` edges (``e <= n`` here).
        """
        if len(nodes) <= 1:
            return nodes

        named_siblings = self._extract_named_siblings(nodes)
        if named_siblings is None:
            return nodes

        name_to_node, node_names = named_siblings
        adjacency, indegree = self._build_after_graph(nodes, node_names)
        ordered_names = self._topologically_order_names(node_names, adjacency, indegree)
        self._append_unresolved_names(nodes, indegree, ordered_names)
        return [name_to_node[name] for name in ordered_names]

    def _extract_named_siblings(self, nodes: list[NodeDiff]) -> tuple[dict[str, NodeDiff], list[str]] | None:
        """Map sibling names to nodes while preserving insertion order.

        Returns ``None`` when duplicate sibling names are detected.
        """
        name_to_node: dict[str, NodeDiff] = {}
        node_names: list[str] = []
        for node in nodes:
            node_name = self._node_name_from_path(node.path)
            if not node_name:
                continue
            if node_name in name_to_node:
                return None
            name_to_node[node_name] = node
            node_names.append(node_name)
        return name_to_node, node_names

    def _build_after_graph(
        self,
        nodes: list[NodeDiff],
        node_names: list[str],
    ) -> tuple[dict[str, list[str]], dict[str, int]]:
        """Build predecessor graph and indegree map from sibling after-links."""
        adjacency: dict[str, list[str]] = {name: [] for name in node_names}
        indegree: dict[str, int] = dict.fromkeys(node_names, 0)

        for node in nodes:
            node_name = self._node_name_from_path(node.path)
            if node_name not in indegree:
                continue

            after = self._preferred_after(node)
            if after is None or after not in indegree or after == node_name:
                continue

            adjacency[after].append(node_name)
            indegree[node_name] += 1

        return adjacency, indegree

    def _topologically_order_names(
        self,
        node_names: list[str],
        adjacency: dict[str, list[str]],
        indegree: dict[str, int],
    ) -> list[str]:
        """Produce stable topological ordering using Kahn's algorithm."""
        ready: deque[str] = deque(name for name in node_names if indegree[name] == 0)
        ordered_names: list[str] = []

        while ready:
            name = ready.popleft()
            ordered_names.append(name)
            for successor in adjacency[name]:
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    ready.append(successor)

        return ordered_names

    def _append_unresolved_names(
        self,
        nodes: list[NodeDiff],
        indegree: dict[str, int],
        ordered_names: list[str],
    ) -> None:
        """Append nodes that remain unresolved (cycles/invalid chains)."""
        if len(ordered_names) >= len(indegree):
            return

        ordered_set = set(ordered_names)
        for node in nodes:
            node_name = self._node_name_from_path(node.path)
            if node_name in indegree and node_name not in ordered_set:
                ordered_names.append(node_name)
                ordered_set.add(node_name)

    def _order_hierarchy_by_after(self, node_diffs: list[NodeDiff]) -> None:
        """Recursively order roots/children using each node's ``after`` metadata."""
        ordered = self._order_nodes_by_after(node_diffs)
        node_diffs[:] = ordered
        for node_diff in node_diffs:
            if node_diff.children:
                self._order_hierarchy_by_after(node_diff.children)

    def _is_row_excluded(
        self, row: _OccurrenceRow, excluded_types_set: set[str], paths_excluded: set[str]
    ) -> tuple[bool, str]:
        """Check if an occurrence row should be excluded by type or parent path.

        Args:
            row: The occurrence row to check
            excluded_types_set: Set of type IDs to exclude
            paths_excluded: Set of paths that are excluded

        Returns:
            Tuple of (is_excluded, path_to_exclude)
        """
        # Check if node type is excluded
        if row.type_id in excluded_types_set:
            return True, row.path

        # Check if parent path is excluded
        parent_path = self._get_parent_path(row.path)
        if parent_path and parent_path in paths_excluded:
            return True, row.path

        return False, ""

    def _compare_node_pair(
        self,
        old_row: _OccurrenceRow,
        new_row: _OccurrenceRow,
        excluded_properties: list[str],
        excluded_properties_by_type: dict[str, list[str]] | None = None,
        precision: int | None = None,
    ) -> NodeDiff:
        """Compare one old/new occurrence node pair directly."""
        if excluded_properties_by_type is None:
            excluded_properties_by_type = {}
        effective = _effective_exclusions(
            excluded_properties,
            excluded_properties_by_type,
            old_row.type_id,
            new_row.type_id,
        )
        property_diffs = self._property_comparator.compare_properties(
            old_row.properties,
            new_row.properties,
            list(effective),
            precision=precision,
        )
        return NodeDiff(
            path=new_row.path,
            type_id=new_row.type_id,
            label=new_row.label,
            property_diffs=property_diffs,
            children=[],
            old_path=old_row.path,
            new_path=new_row.path,
            old_after=old_row.after,
            new_after=new_row.after,
            precision=self._precision,
        )

    def _label_for_object(self, obj: SnapshotObject) -> str:
        """Return object label from properties when present, else fallback name."""
        label_prop = obj.properties.get("Label")
        if label_prop is None:
            return obj.name
        paths = getattr(label_prop.value, "paths", None)
        if not isinstance(paths, dict):
            return obj.name
        root = paths.get(".")
        if root is None:
            return obj.name
        value = getattr(root, "value", None)
        return str(value) if value is not None else obj.name

    def _materialize_occurrence_rows(self, snapshot: Snapshot) -> list[_OccurrenceRow]:
        """Join normalized snapshot objects/occurrences into comparison rows."""
        object_by_name = {obj.name: obj for obj in snapshot.objects}
        rows: list[_OccurrenceRow] = []
        for occ in snapshot.occurrences:
            obj = object_by_name.get(occ.object_name)
            if obj is not None:
                rows.append(
                    _OccurrenceRow(
                        id=obj.id,
                        name=obj.name,
                        type_id=obj.type_id,
                        label=self._label_for_object(obj),
                        path=occ.path,
                        after=occ.after,
                        properties=obj.properties,
                    )
                )
        return rows

    def _collect_old_pass_diffs(
        self,
        sorted_old_rows: list[_OccurrenceRow],
        new_by_path: dict[str, _OccurrenceRow],
        excluded_types_set: set[str],
        excluded_properties: list[str],
        excluded_properties_by_type: dict[str, list[str]],
        precision: int,
    ) -> tuple[list[NodeDiff], int, int]:
        """Create deleted/modified diffs scanning old snapshot rows."""
        diffs: list[NodeDiff] = []
        deleted_count = 0
        modified_count = 0
        paths_excluded: set[str] = set()

        for old_row in sorted_old_rows:
            is_excluded, path_to_exclude = self._is_row_excluded(old_row, excluded_types_set, paths_excluded)
            if is_excluded:
                paths_excluded.add(path_to_exclude)
                continue

            new_row = new_by_path.get(old_row.path)
            if new_row is None:
                diffs.append(
                    self._create_deleted_node_diff(
                        old_row,
                        excluded_properties,
                        excluded_properties_by_type,
                        precision,
                    )
                )
                deleted_count += 1
                continue

            node_diff = self._compare_node_pair(
                old_row,
                new_row,
                excluded_properties,
                excluded_properties_by_type,
                precision,
            )
            if node_diff.state == DiffState.MODIFIED:
                modified_count += 1
            diffs.append(node_diff)

        return diffs, deleted_count, modified_count

    def _collect_added_diffs(
        self,
        sorted_new_rows: list[_OccurrenceRow],
        old_by_path: dict[str, _OccurrenceRow],
        excluded_types_set: set[str],
        excluded_properties: list[str],
        excluded_properties_by_type: dict[str, list[str]],
        precision: int,
    ) -> tuple[list[NodeDiff], int]:
        """Create added diffs scanning new snapshot rows."""
        diffs: list[NodeDiff] = []
        added_count = 0
        # Independent exclusion domain for new-snapshot pass.
        paths_excluded: set[str] = set()

        for new_row in sorted_new_rows:
            if new_row.path in old_by_path:
                continue
            is_excluded, path_to_exclude = self._is_row_excluded(new_row, excluded_types_set, paths_excluded)
            if is_excluded:
                paths_excluded.add(path_to_exclude)
                continue

            diffs.append(
                self._create_added_node_diff(
                    new_row,
                    excluded_properties,
                    excluded_properties_by_type,
                    precision,
                )
            )
            added_count += 1

        return diffs, added_count

    def _create_added_node_diff(
        self,
        row: _OccurrenceRow,
        excluded_properties: list[str],
        excluded_properties_by_type: dict[str, list[str]] | None = None,
        precision: int | None = None,
    ) -> NodeDiff:
        """Create a NodeDiff for an added occurrence row.

        This is called for nodes that exist only in the new snapshot (not in old).
        The entire node is considered ADDED, regardless of its properties.

        For added nodes, old_path and old_after are None since the node didn't exist
        in the old snapshot.

        Args:
            row: The occurrence row from the new snapshot
            excluded_properties: List of property names to exclude from comparison
            excluded_properties_by_type: Dict mapping type IDs to excluded properties

        Returns:
            NodeDiff with ADDED state
        """
        # For added nodes, use global + new type exclusions
        if excluded_properties_by_type is None:
            excluded_properties_by_type = {}
        effective = _effective_exclusions(excluded_properties, excluded_properties_by_type, None, row.type_id)

        # For added nodes, all properties are "added" (old_value=None)
        property_diffs = self._property_comparator.compare_properties(
            {},
            row.properties,
            list(effective),
            precision=precision,
        )

        # For added rows: old_path=None, new_path=row.path, old_after=None, new_after=row.after
        return NodeDiff(
            path=row.path,
            type_id=row.type_id,
            label=row.label,
            property_diffs=property_diffs,
            children=[],  # Will be populated hierarchically later
            old_path=None,
            new_path=row.path,
            old_after=None,
            new_after=row.after,
            precision=self._precision,
            _force_state=DiffState.ADDED,
        )

    def _create_deleted_node_diff(
        self,
        row: _OccurrenceRow,
        excluded_properties: list[str],
        excluded_properties_by_type: dict[str, list[str]] | None = None,
        precision: int | None = None,
    ) -> NodeDiff:
        """Create a NodeDiff for a deleted occurrence row.

        This is called for nodes that exist only in the old snapshot (not in new).
        The entire node is considered DELETED, regardless of its properties.

        For deleted nodes, new_path and new_after are None since the node doesn't
        exist in the new snapshot.

        Args:
            row: The occurrence row from the old snapshot
            excluded_properties: List of property names to exclude from comparison
            excluded_properties_by_type: Dict mapping type IDs to excluded properties

        Returns:
            NodeDiff with DELETED state
        """
        # For deleted nodes, use global + old type exclusions
        if excluded_properties_by_type is None:
            excluded_properties_by_type = {}
        effective = _effective_exclusions(excluded_properties, excluded_properties_by_type, row.type_id, None)

        # For deleted nodes, all properties are "deleted" (new_value=None)
        property_diffs = self._property_comparator.compare_properties(
            row.properties,
            {},
            list(effective),
            precision=precision,
        )

        # For deleted rows: old_path=row.path, new_path=None, old_after=row.after, new_after=None
        return NodeDiff(
            path=row.path,
            type_id=row.type_id,
            label=row.label,
            property_diffs=property_diffs,
            children=[],  # Will be populated hierarchically later
            old_path=row.path,
            new_path=None,
            old_after=row.after,
            new_after=None,
            precision=self._precision,
            _force_state=DiffState.DELETED,
        )

    def compare_snapshots(
        self,
        old_snapshot: Snapshot,
        new_snapshot: Snapshot,
        excluded_properties: list[str],
        excluded_types: list[str],
        excluded_properties_by_type: dict[str, list[str]] | None = None,
        precision: int = 2,
    ) -> DiffResult:
        """Compare two snapshots using occurrence-path comparison and produce DiffResult.

        This is the main entry point for tree comparison using the optimized algorithm:
        1. Sort both snapshots by path length (parents first)
        2. Build path indexes for old/new occurrence rows
        3. Process old rows to create deleted/modified diffs
        4. Process new rows to create added diffs
        5. Build DiffHierarchy using add_node()
        6. Reorder roots and siblings using node ``after`` links
        7. Return DiffResult with DiffHierarchy and counts

        This algorithm achieves O((n+m) log (n+m)) complexity by using inline
        set lookups for exclusion filtering instead of O(n*m) prefix checks.

        Args:
            old_snapshot: The old snapshot to compare
            new_snapshot: The new snapshot to compare
            excluded_properties: List of property names to exclude from comparison
            excluded_types: List of type IDs to exclude from comparison
            excluded_properties_by_type: Dict mapping type IDs to property names
                to exclude for that type only. If None, no type-specific exclusions
                are applied.

        Returns:
            DiffResult containing hierarchy and counts
        """
        if excluded_properties_by_type is None:
            excluded_properties_by_type = {}

        self._precision = precision

        old_rows = self._materialize_occurrence_rows(old_snapshot)
        new_rows = self._materialize_occurrence_rows(new_snapshot)

        excluded_types_set = set(excluded_types)
        sorted_old_rows = self._sort_rows_by_path_depth(old_rows)
        sorted_new_rows = self._sort_rows_by_path_depth(new_rows)
        new_by_path: dict[str, _OccurrenceRow] = {row.path: row for row in new_rows}
        old_by_path: dict[str, _OccurrenceRow] = {row.path: row for row in old_rows}

        old_diffs, deleted_count, modified_count = self._collect_old_pass_diffs(
            sorted_old_rows,
            new_by_path,
            excluded_types_set,
            excluded_properties,
            excluded_properties_by_type,
            precision,
        )
        added_diffs, added_count = self._collect_added_diffs(
            sorted_new_rows,
            old_by_path,
            excluded_types_set,
            excluded_properties,
            excluded_properties_by_type,
            precision,
        )
        all_node_diffs = old_diffs + added_diffs

        # Build DiffHierarchy
        hierarchy = DiffHierarchy()
        for node_diff in all_node_diffs:
            hierarchy.add_node(node_diff)

        # Order roots/children by node after-links (new snapshot preferred).
        self._order_hierarchy_by_after(hierarchy.roots)

        # Return DiffResult with hierarchy and counts
        return DiffResult(
            old_snapshot=old_snapshot,
            new_snapshot=new_snapshot,
            added_count=added_count,
            deleted_count=deleted_count,
            modified_count=modified_count,
            hierarchy=hierarchy,
        )


class PropertyComparator:
    """Compares property values between two nodes.

    Delegates state calculation to ``PropertyDiff``, which uses path-based
    diffs internally. This class only handles property name iteration,
    exclusion filtering, and deterministic alphabetical ordering.
    """

    def __init__(self, precision: int = 2) -> None:
        """Initialize PropertyComparator with precision setting.

        Args:
            precision: Number of decimal places for float comparison (default: 2)
        """
        self._precision = precision

    def compare_properties(
        self,
        old_props: dict[str, Property],
        new_props: dict[str, Property],
        excluded_properties: list[str],
        precision: int | None = None,
    ) -> list[PropertyDiff]:
        """Compare properties between two nodes and produce a list of PropertyDiff objects.

        Properties are iterated in deterministic alphabetical order. Excluded
        properties are skipped. ``PropertyDiff`` objects are created for every
        non-excluded property (including unchanged ones).

        Args:
            old_props: Dictionary of property names to values from the old node
            new_props: Dictionary of property names to values from the new node
            excluded_properties: List of property names to exclude from comparison

        Returns:
            List of PropertyDiff objects for all non-excluded properties (including unchanged)
        """
        effective_precision = self._precision if precision is None else precision
        property_diffs: list[PropertyDiff] = []
        all_prop_names = sorted(set(old_props.keys()) | set(new_props.keys()))

        for prop_name in all_prop_names:
            if prop_name in excluded_properties:
                continue

            property_diffs.append(
                PropertyDiff(
                    property_name=prop_name,
                    old_value=old_props.get(prop_name),
                    new_value=new_props.get(prop_name),
                    precision=effective_precision,
                )
            )

        return property_diffs


__all__ = ["TreeComparator", "PropertyComparator"]
