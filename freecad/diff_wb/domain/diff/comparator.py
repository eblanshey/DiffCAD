# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Efficient tree comparison algorithms using path-based indexing
# for O(n+m) performance. Compares two document snapshots and produces a hierarchical
# structure of NodeDiff objects representing added, deleted, and modified nodes.
#
# The module contains two main classes:
# - TreeComparator: Compares tree structures using path-based indexing
# - PropertyComparator: Compares property values and delegates state calculation
#   to PropertyDiff (which uses path-based diffs internally).
"""Tree and property comparison algorithms."""

from collections import deque

from ..snapshots import Snapshot
from ..tree.node import TreeNode
from ..tree.property import Property
from .models import DiffHierarchy, DiffResult, DiffState, NodeDiff, PropertyDiff


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
    """Compares two tree structures using ID-based indexing.

    This class provides instance methods for comparing tree snapshots efficiently
    using ID-based indexing to achieve O(n+m) performance. The flat node structure
    contains id, path, and after fields for move/reorder detection.

    The algorithm:
    1. Sort both snapshots by path length (parents first)
    2. Build ID index for new snapshot (O(m))
    3. Process old nodes to create deleted/modified diffs
    4. Process new nodes to create added diffs
    5. Build DiffHierarchy using add_node()
    6. Reorder roots and siblings using node ``after`` links
    7. Return DiffResult with DiffHierarchy and counts
    """

    def __init__(self) -> None:
        """Initialize TreeComparator with a PropertyComparator instance."""
        self._property_comparator = PropertyComparator()

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

    def _sort_nodes_by_path_length(self, nodes: list[TreeNode]) -> list[TreeNode]:
        """Sort nodes by path length (shortest first - parents before children).

        This ensures parents are processed before children for proper exclusion logic.

        Args:
            nodes: List of TreeNode objects to sort

        Returns:
            List of nodes sorted by path depth (shallowest first)
        """
        return sorted(nodes, key=lambda n: (n.path.count("/") if n.path else 0, n.path))

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
        if node_diff.new_path is not None:
            return node_diff.new_after
        return node_diff.old_after

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

    def _is_node_excluded(
        self, node: TreeNode, excluded_types_set: set[str], paths_excluded: set[str]
    ) -> tuple[bool, str]:
        """Check if a node should be excluded based on type or parent path.

        Args:
            node: The tree node to check
            excluded_types_set: Set of type IDs to exclude
            paths_excluded: Set of paths that are excluded

        Returns:
            Tuple of (is_excluded, path_to_exclude)
        """
        # Check if node type is excluded
        if node.type_id in excluded_types_set:
            return True, node.path

        # Check if parent path is excluded
        parent_path = self._get_parent_path(node.path)
        if parent_path and parent_path in paths_excluded:
            return True, node.path

        return False, ""

    def _compare_nodes_by_id(
        self,
        node_id: int,
        old_index: dict[int, TreeNode],
        new_index: dict[int, TreeNode],
        excluded_properties: list[str],
        excluded_properties_by_type: dict[str, list[str]] | None = None,
    ) -> NodeDiff:
        """Compare two nodes at the same ID and produce a NodeDiff.

        This function compares the properties of two nodes using the property_diff
        module and determines if they have been modified. If no properties differ
        (after filtering excluded properties), returns an UNCHANGED NodeDiff.

        The NodeDiff includes old_path, new_path, old_after, new_after fields
        for future move/reorder detection.

        Args:
            node_id: The node ID to compare
            old_index: ID index for the old snapshot
            new_index: ID index for the new snapshot
            excluded_properties: List of property names to exclude from comparison
            excluded_properties_by_type: Dict mapping type IDs to excluded properties

        Returns:
            NodeDiff with MODIFIED state if properties differ, UNCHANGED otherwise
        """
        old_node = old_index.get(node_id)
        new_node = new_index.get(node_id)

        # Both nodes should exist for common IDs (called from compare_snapshots)
        if old_node is None or new_node is None:
            raise ValueError(f"Cannot compare nodes by ID: one or both not found for ID {node_id}")

        # Compute effective exclusions using union of old and new type rules
        if excluded_properties_by_type is None:
            excluded_properties_by_type = {}
        effective = _effective_exclusions(
            excluded_properties,
            excluded_properties_by_type,
            old_node.type_id,
            new_node.type_id,
        )

        # Use property comparator to compare properties with exclusion filtering
        property_diffs = self._property_comparator.compare_properties(
            old_node.properties, new_node.properties, list(effective)
        )

        # Return NodeDiff - state will be auto-calculated in __post_init__
        # Include old_path, new_path, old_after, new_after for move/reorder detection
        return NodeDiff(
            path=new_node.path,
            type_id=new_node.type_id,
            property_diffs=property_diffs,
            children=[],  # Will be populated hierarchically later
            old_path=old_node.path,
            new_path=new_node.path,
            old_after=old_node.after,
            new_after=new_node.after,
        )

    def _create_added_node_diff(
        self,
        node_id: int,
        node: TreeNode,
        excluded_properties: list[str],
        excluded_properties_by_type: dict[str, list[str]] | None = None,
    ) -> NodeDiff:
        """Create a NodeDiff for an added node (ID-based).

        This is called for nodes that exist only in the new snapshot (not in old).
        The entire node is considered ADDED, regardless of its properties.

        For added nodes, old_path and old_after are None since the node didn't exist
        in the old snapshot.

        Args:
            node_id: The node ID (for ID-based indexing)
            node: The TreeNode from the new snapshot
            excluded_properties: List of property names to exclude from comparison
            excluded_properties_by_type: Dict mapping type IDs to excluded properties

        Returns:
            NodeDiff with ADDED state
        """
        # For added nodes, use global + new type exclusions
        if excluded_properties_by_type is None:
            excluded_properties_by_type = {}
        effective = _effective_exclusions(excluded_properties, excluded_properties_by_type, None, node.type_id)

        # For added nodes, all properties are "added" (old_value=None)
        property_diffs = self._property_comparator.compare_properties({}, node.properties, list(effective))

        # For added nodes: old_path=None, new_path=node.path, old_after=None, new_after=node.after
        return NodeDiff(
            path=node.path,
            type_id=node.type_id,
            property_diffs=property_diffs,
            children=[],  # Will be populated hierarchically later
            old_path=None,
            new_path=node.path,
            old_after=None,
            new_after=node.after,
            _force_state=DiffState.ADDED,
        )

    def _create_deleted_node_diff(
        self,
        node_id: int,
        node: TreeNode,
        excluded_properties: list[str],
        excluded_properties_by_type: dict[str, list[str]] | None = None,
    ) -> NodeDiff:
        """Create a NodeDiff for a deleted node (ID-based).

        This is called for nodes that exist only in the old snapshot (not in new).
        The entire node is considered DELETED, regardless of its properties.

        For deleted nodes, new_path and new_after are None since the node doesn't
        exist in the new snapshot.

        Args:
            node_id: The node ID (for ID-based indexing)
            node: The TreeNode from the old snapshot
            excluded_properties: List of property names to exclude from comparison
            excluded_properties_by_type: Dict mapping type IDs to excluded properties

        Returns:
            NodeDiff with DELETED state
        """
        # For deleted nodes, use global + old type exclusions
        if excluded_properties_by_type is None:
            excluded_properties_by_type = {}
        effective = _effective_exclusions(excluded_properties, excluded_properties_by_type, node.type_id, None)

        # For deleted nodes, all properties are "deleted" (new_value=None)
        property_diffs = self._property_comparator.compare_properties(node.properties, {}, list(effective))

        # For deleted nodes: old_path=node.path, new_path=None, old_after=node.after, new_after=None
        return NodeDiff(
            path=node.path,
            type_id=node.type_id,
            property_diffs=property_diffs,
            children=[],  # Will be populated hierarchically later
            old_path=node.path,
            new_path=None,
            old_after=node.after,
            new_after=None,
            _force_state=DiffState.DELETED,
        )

    def _process_old_nodes(
        self,
        sorted_old_nodes: list[TreeNode],
        id_index_new: dict[int, TreeNode],
        excluded_types_set: set[str],
        excluded_properties: list[str],
        excluded_properties_by_type: dict[str, list[str]],
    ) -> tuple[list[NodeDiff], set[int], set[str], int, int]:
        """Process old nodes to create diffs for deleted and modified nodes.

        Args:
            sorted_old_nodes: Old nodes sorted by path length
            id_index_new: ID index for new snapshot
            excluded_types_set: Set of type IDs to exclude
            excluded_properties: List of property names to exclude
            excluded_properties_by_type: Dict mapping type IDs to excluded properties

        Returns:
            Tuple of (node_diffs, old_node_ids, paths_excluded, deleted_count, modified_count)
        """
        node_diffs: list[NodeDiff] = []
        old_node_ids: set[int] = set()
        paths_excluded: set[str] = set()
        deleted_count = 0
        modified_count = 0

        for old_node in sorted_old_nodes:
            old_node_ids.add(old_node.id)

            # Check exclusions
            is_excluded, path_to_exclude = self._is_node_excluded(old_node, excluded_types_set, paths_excluded)
            if is_excluded:
                paths_excluded.add(path_to_exclude)
                continue

            # Get matching new node by ID
            new_node = id_index_new.get(old_node.id)

            # Create node diff
            node_diff: NodeDiff
            if new_node is None:
                node_diff = self._create_deleted_node_diff(
                    old_node.id, old_node, excluded_properties, excluded_properties_by_type
                )
                deleted_count += 1
            else:
                node_diff = self._compare_nodes_by_id(
                    old_node.id,
                    {old_node.id: old_node},
                    id_index_new,
                    excluded_properties,
                    excluded_properties_by_type,
                )
                if node_diff.state == DiffState.MODIFIED:
                    modified_count += 1

            node_diffs.append(node_diff)

        return node_diffs, old_node_ids, paths_excluded, deleted_count, modified_count

    def _process_new_nodes(
        self,
        sorted_new_nodes: list[TreeNode],
        old_node_ids: set[int],
        excluded_types_set: set[str],
        excluded_properties: list[str],
        excluded_properties_by_type: dict[str, list[str]],
    ) -> tuple[list[NodeDiff], int]:
        """Process new nodes to create diffs for added nodes.

        Args:
            sorted_new_nodes: New nodes sorted by path length
            old_node_ids: Set of IDs from old snapshot
            excluded_types_set: Set of type IDs to exclude
            excluded_properties: List of property names to exclude
            excluded_properties_by_type: Dict mapping type IDs to excluded properties

        Returns:
            Tuple of (added_node_diffs, added_count)
        """
        added_node_ids = {node.id for node in sorted_new_nodes} - old_node_ids
        added_node_diffs: list[NodeDiff] = []
        added_count = 0
        paths_excluded: set[str] = set()

        for new_node in sorted_new_nodes:
            if new_node.id not in added_node_ids:
                continue

            # Check exclusions
            is_excluded, path_to_exclude = self._is_node_excluded(new_node, excluded_types_set, paths_excluded)
            if is_excluded:
                paths_excluded.add(path_to_exclude)
                continue

            node_diff = self._create_added_node_diff(
                new_node.id, new_node, excluded_properties, excluded_properties_by_type
            )
            added_count += 1
            added_node_diffs.append(node_diff)

        return added_node_diffs, added_count

    def compare_snapshots(
        self,
        old_snapshot: Snapshot,
        new_snapshot: Snapshot,
        excluded_properties: list[str],
        excluded_types: list[str],
        excluded_properties_by_type: dict[str, list[str]] | None = None,
    ) -> DiffResult:
        """Compare two snapshots using ID-based comparison and produce a DiffResult.

        This is the main entry point for tree comparison using the optimized algorithm:
        1. Sort both snapshots by path length (parents first)
        2. Build ID index for new snapshot (by ID)
        3. Process old nodes to create deleted/modified diffs
        4. Process new nodes to create added diffs
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

        # Extract nodes from snapshots
        old_nodes = old_snapshot.nodes
        new_nodes = new_snapshot.nodes

        # Prepare data structures
        excluded_types_set = set(excluded_types)
        sorted_old_nodes = self._sort_nodes_by_path_length(old_nodes)
        sorted_new_nodes = self._sort_nodes_by_path_length(new_nodes)
        id_index_new: dict[int, TreeNode] = {node.id: node for node in new_nodes}

        # Process old nodes for deleted and modified diffs
        old_node_diffs, old_node_ids, _, deleted_count, modified_count = self._process_old_nodes(
            sorted_old_nodes,
            id_index_new,
            excluded_types_set,
            excluded_properties,
            excluded_properties_by_type,
        )

        # Process new nodes for added diffs
        added_node_diffs, added_count = self._process_new_nodes(
            sorted_new_nodes,
            old_node_ids,
            excluded_types_set,
            excluded_properties,
            excluded_properties_by_type,
        )

        # Combine all node diffs
        all_node_diffs = old_node_diffs + added_node_diffs

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

    def compare_properties(
        self,
        old_props: dict[str, Property],
        new_props: dict[str, Property],
        excluded_properties: list[str],
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
                )
            )

        return property_diffs


__all__ = ["TreeComparator", "PropertyComparator"]
