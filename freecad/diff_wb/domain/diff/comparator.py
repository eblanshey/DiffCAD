# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides efficient tree comparison algorithms
# that use path-based indexing for O(n+m) performance. It compares two document
# snapshots and produces a hierarchical structure of NodeDiff objects representing
# added, deleted, and modified nodes.
#
# The module contains two main classes:
# - TreeComparator: Compares tree structures using path-based indexing
# - PropertyComparator: Compares property values with type-aware equality
#
# Comparison rules for properties:
# - BOOL, INT, STRING: Exact equality
# - FLOAT: Approximate equality (tolerance=1e-9)
# - VECTOR: Component-wise approximate equality
# - PLACEMENT: Position + rotation comparison
# - EXPRESSION: String equality (expression changes are significant)
"""Tree and property comparison algorithms."""

from dataclasses import dataclass

from ..tree.node import TreeNode
from ..tree.property import Property
from .models import DiffState, NodeDiff, PropertyDiff


@dataclass(frozen=True)
class TreeDiffResult:
    """Result of comparing two tree snapshots using ID-based comparison.

    Attributes:
        added_ids: Set of node IDs that exist only in the new snapshot
        deleted_ids: Set of node IDs that exist only in the old snapshot
        common_ids: Set of node IDs that exist in both snapshots
        node_diffs: Hierarchical list of NodeDiff objects
    """

    added_ids: set[int]
    deleted_ids: set[int]
    common_ids: set[int]
    node_diffs: list[NodeDiff]


class TreeComparator:
    """Compares two tree structures using ID-based indexing.

    This class provides instance methods for comparing tree snapshots efficiently
    using ID-based indexing to achieve O(n+m) performance. The flat node structure
    contains id, path, and after fields for move/reorder detection.

    The algorithm:
    1. Build ID index for old snapshot (O(n))
    2. Build ID index for new snapshot (O(m))
    3. Find added IDs (in new but not old)
    4. Find deleted IDs (in old but not new)
    5. Find common IDs and compare nodes by ID
    6. Reconstruct hierarchical structure from flat list using paths
    """

    def __init__(self) -> None:
        """Initialize TreeComparator with a PropertyComparator instance."""
        self._property_comparator = PropertyComparator()

    def _build_id_index(self, nodes: list[TreeNode]) -> dict[int, TreeNode]:
        """Build an ID-based index for O(1) node lookups.

        Creates a dictionary mapping each node's ID to the node itself.
        This enables efficient comparison without nested iteration.

        Args:
            nodes: Flat list of tree nodes to index

        Returns:
            Dictionary mapping node IDs to TreeNode objects
        """
        return {node.id: node for node in nodes}

    def _find_added_ids(self, old_index: dict[int, TreeNode], new_index: dict[int, TreeNode]) -> set[int]:
        """Find node IDs that exist only in the new snapshot.

        Args:
            old_index: ID index for the old snapshot
            new_index: ID index for the new snapshot

        Returns:
            Set of IDs that are in new but not in old
        """
        return set(new_index.keys()) - set(old_index.keys())

    def _find_deleted_ids(self, old_index: dict[int, TreeNode], new_index: dict[int, TreeNode]) -> set[int]:
        """Find node IDs that exist only in the old snapshot.

        Args:
            old_index: ID index for the old snapshot
            new_index: ID index for the new snapshot

        Returns:
            Set of IDs that are in old but not in new
        """
        return set(old_index.keys()) - set(new_index.keys())

    def _find_common_ids(self, old_index: dict[int, TreeNode], new_index: dict[int, TreeNode]) -> set[int]:
        """Find node IDs that exist in both snapshots.

        Args:
            old_index: ID index for the old snapshot
            new_index: ID index for the new snapshot

        Returns:
            Set of IDs that exist in both snapshots
        """
        return set(old_index.keys()) & set(new_index.keys())

    def _build_path_index(self, root_nodes: list[TreeNode]) -> dict[str, TreeNode]:
        """Build a path-based index for O(1) node lookups (legacy method).

        Traverses the tree recursively and creates a dictionary mapping each
        node's path to the node itself. This enables efficient comparison
        without nested iteration.

        Note: This method is kept for backward compatibility. New code should
        use _build_id_index() for flat node lists.

        Args:
            root_nodes: List of root tree nodes to index

        Returns:
            Dictionary mapping path strings to TreeNode objects
        """
        index: dict[str, TreeNode] = {}

        def _index_nodes(node: TreeNode) -> None:
            index[node.path] = node
            for child in getattr(node, "children", []):
                _index_nodes(child)

        for root in root_nodes:
            _index_nodes(root)

        return index

    def _find_added_paths(self, old_index: dict[str, TreeNode], new_index: dict[str, TreeNode]) -> set[str]:
        """Find paths that exist only in the new snapshot (legacy method).

        Args:
            old_index: Path index for the old snapshot
            new_index: Path index for the new snapshot

        Returns:
            Set of paths that are in new but not in old
        """
        return set(new_index.keys()) - set(old_index.keys())

    def _find_deleted_paths(self, old_index: dict[str, TreeNode], new_index: dict[str, TreeNode]) -> set[str]:
        """Find paths that exist only in the old snapshot (legacy method).

        Args:
            old_index: Path index for the old snapshot
            new_index: Path index for the new snapshot

        Returns:
            Set of paths that are in old but not in new
        """
        return set(old_index.keys()) - set(new_index.keys())

    def _find_common_paths(self, old_index: dict[str, TreeNode], new_index: dict[str, TreeNode]) -> set[str]:
        """Find paths that exist in both snapshots (legacy method).

        Args:
            old_index: Path index for the old snapshot
            new_index: Path index for the new snapshot

        Returns:
            Set of paths that exist in both snapshots
        """
        return set(old_index.keys()) & set(new_index.keys())

    def _compare_nodes_by_path(
        self,
        path: str,
        old_index: dict[str, TreeNode],
        new_index: dict[str, TreeNode],
        excluded_properties: list[str],
    ) -> NodeDiff:
        """Compare two nodes at the same path and produce a NodeDiff.

        This function compares the properties of two nodes using the property_diff
        module and determines if they have been modified. If no properties differ
        (after filtering excluded properties), returns an UNCHANGED NodeDiff.

        Args:
            path: The path to compare
            old_index: Path index for the old snapshot
            new_index: Path index for the new snapshot
            excluded_properties: List of property names to exclude from comparison

        Returns:
            NodeDiff with MODIFIED state if properties differ, UNCHANGED otherwise
        """
        old_node = old_index.get(path)
        new_node = new_index.get(path)

        # Handle case where node exists in only one snapshot - this is a placeholder path
        # (not an actual added/deleted node, just an ancestor needed for hierarchy)
        if old_node is None or new_node is None:
            return self._create_placeholder(path, old_index, new_index)

        # Use property comparator to compare properties with exclusion filtering
        property_diffs = self._property_comparator.compare_properties(
            old_node.properties, new_node.properties, excluded_properties
        )

        # Return NodeDiff - state will be auto-calculated in __post_init__
        # Include old_path, new_path, old_after, new_after for move/reorder detection
        return NodeDiff(
            path=path,
            type_id=new_node.type_id,
            property_diffs=property_diffs,
            children=[],  # Will be populated recursively by reconstruct_hierarchy
            old_path=old_node.path,
            new_path=new_node.path,
            old_after=old_node.after,
            new_after=new_node.after,
        )

    def _compare_nodes_by_id(
        self,
        node_id: int,
        old_index: dict[int, TreeNode],
        new_index: dict[int, TreeNode],
        excluded_properties: list[str],
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

        Returns:
            NodeDiff with MODIFIED state if properties differ, UNCHANGED otherwise
        """
        old_node = old_index.get(node_id)
        new_node = new_index.get(node_id)

        # Both nodes should exist for common IDs (called from compare_snapshots)
        if old_node is None or new_node is None:
            raise ValueError(f"Cannot compare nodes by ID: one or both not found for ID {node_id}")

        # Use property comparator to compare properties with exclusion filtering
        property_diffs = self._property_comparator.compare_properties(
            old_node.properties, new_node.properties, excluded_properties
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

    def _create_added_node_diff(self, node_id: int, node: TreeNode, excluded_properties: list[str]) -> NodeDiff:
        """Create a NodeDiff for an added node (ID-based).

        This is called for nodes that exist only in the new snapshot (not in old).
        The entire node is considered ADDED, regardless of its properties.

        For added nodes, old_path and old_after are None since the node didn't exist
        in the old snapshot.

        Args:
            node_id: The node ID (for ID-based indexing)
            node: The TreeNode from the new snapshot
            excluded_properties: List of property names to exclude from comparison

        Returns:
            NodeDiff with ADDED state
        """
        # For added nodes, all properties are "added" (old_value=None)
        property_diffs = self._property_comparator.compare_properties({}, node.properties, excluded_properties)

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

    def _create_added_node_diff_by_path(self, path: str, node: TreeNode, excluded_properties: list[str]) -> NodeDiff:
        """Create a NodeDiff for an added node (legacy path-based).

        This is the legacy version that accepts path instead of node ID.
        Kept for backward compatibility with existing tests.

        Args:
            path: The path of the added node
            node: The TreeNode from the new snapshot
            excluded_properties: List of property names to exclude from comparison

        Returns:
            NodeDiff with ADDED state
        """
        # For added nodes, all properties are "added" (old_value=None)
        property_diffs = self._property_comparator.compare_properties({}, node.properties, excluded_properties)

        return NodeDiff(
            path=path,
            type_id=node.type_id,
            property_diffs=property_diffs,
            children=[],  # Will be populated recursively
            _force_state=DiffState.ADDED,
        )

    def _create_deleted_node_diff(self, node_id: int, node: TreeNode, excluded_properties: list[str]) -> NodeDiff:
        """Create a NodeDiff for a deleted node (ID-based).

        This is called for nodes that exist only in the old snapshot (not in new).
        The entire node is considered DELETED, regardless of its properties.

        For deleted nodes, new_path and new_after are None since the node doesn't
        exist in the new snapshot.

        Args:
            node_id: The node ID (for ID-based indexing)
            node: The TreeNode from the old snapshot
            excluded_properties: List of property names to exclude from comparison

        Returns:
            NodeDiff with DELETED state
        """
        # For deleted nodes, all properties are "deleted" (new_value=None)
        property_diffs = self._property_comparator.compare_properties(node.properties, {}, excluded_properties)

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

    def _create_deleted_node_diff_by_path(self, path: str, node: TreeNode, excluded_properties: list[str]) -> NodeDiff:
        """Create a NodeDiff for a deleted node (legacy path-based).

        This is the legacy version that accepts path instead of node ID.
        Kept for backward compatibility with existing tests.

        Args:
            path: The path of the deleted node
            node: The TreeNode from the old snapshot
            excluded_properties: List of property names to exclude from comparison

        Returns:
            NodeDiff with DELETED state
        """
        # For deleted nodes, all properties are "deleted" (new_value=None)
        property_diffs = self._property_comparator.compare_properties(node.properties, {}, excluded_properties)

        return NodeDiff(
            path=path,
            type_id=node.type_id,
            property_diffs=property_diffs,
            children=[],  # Will be populated recursively
            _force_state=DiffState.DELETED,
        )

    def _create_placeholder(
        self,
        path: str,
        old_index: dict[str, TreeNode],
        new_index: dict[str, TreeNode],
    ) -> NodeDiff:
        """Create a placeholder NodeDiff for hierarchy.

        This is called for paths that exist in only one snapshot (not added/deleted nodes
        themselves, but ancestors needed to maintain the tree hierarchy).

        Args:
            path: The path of the placeholder
            old_index: Path index for the old snapshot
            new_index: Path index for the new snapshot

        Returns:
            NodeDiff with UNCHANGED state
        """
        old_node = old_index.get(path)
        new_node = new_index.get(path)
        node = new_node if new_node else old_node
        type_id = node.type_id if node else "Unknown"

        return NodeDiff(
            path=path,
            type_id=type_id,
            property_diffs=[],
            children=[],
            _force_state=DiffState.UNCHANGED,
        )

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

    def _ensure_placeholder(
        self,
        path: str,
        old_index: dict[str, TreeNode],
        new_index: dict[str, TreeNode],
        diff_by_path: dict[str, NodeDiff],
        has_parent: set[str],
    ) -> None:
        """Recursively ensure a placeholder exists for a given path.

        This method creates placeholder NodeDiff objects with UNCHANGED state for
        paths that don't exist in the diff registry but are needed to maintain
        hierarchy. It recursively ensures parent placeholders exist first.

        Args:
            path: The path to ensure exists in diff_by_path
            old_index: Path index for the old snapshot (for type_id lookup)
            new_index: Path index for the new snapshot (for type_id lookup)
            diff_by_path: Registry of existing NodeDiff objects by path
            has_parent: Set of paths that have been linked to a parent
        """
        # If path already exists, nothing to do
        if path in diff_by_path:
            return

        # Recursively ensure parent exists first
        parent_path = self._get_parent_path(path)
        if parent_path:
            self._ensure_placeholder(parent_path, old_index, new_index, diff_by_path, has_parent)

        # Look up type_id from old or new index
        old_node = old_index.get(path)
        new_node = new_index.get(path)
        type_id = old_node.type_id if old_node else (new_node.type_id if new_node else "Unknown")

        # Create placeholder with UNCHANGED state
        placeholder = NodeDiff(
            path=path,
            type_id=type_id,
            property_diffs=[],
            children=[],
            _force_state=DiffState.UNCHANGED,
        )
        diff_by_path[path] = placeholder

        # Link to parent if parent exists
        if parent_path and parent_path in diff_by_path:
            parent_diff = diff_by_path[parent_path]
            object.__setattr__(parent_diff, "children", parent_diff.children + [placeholder])
            has_parent.add(path)

    def _build_hierarchical_diffs(
        self,
        sorted_paths: list[str],
        added_paths: set[str],
        deleted_paths: set[str],
        old_index: dict[str, TreeNode],
        new_index: dict[str, TreeNode],
        excluded_properties: list[str],
    ) -> tuple[dict[str, NodeDiff], set[str]]:
        """Build hierarchical diffs in a single pass.

        This method processes paths in sorted order (parents before children) and
        builds the hierarchy incrementally as each NodeDiff is created. For each path:
        1. Create the NodeDiff (added, deleted, or modified)
        2. Ensure parent placeholder exists if needed
        3. Link child to parent
        4. Register in the diff registry

        Args:
            sorted_paths: List of paths sorted so parents come before children
            added_paths: Set of paths that are additions
            deleted_paths: Set of paths that are deletions
            old_index: Path index for the old snapshot
            new_index: Path index for the new snapshot
            excluded_properties: List of property names to exclude from comparison

        Returns:
            Tuple of (diff_by_path dict, has_parent set)
        """
        diff_by_path: dict[str, NodeDiff] = {}
        has_parent: set[str] = set()

        for path in sorted_paths:
            # a. CREATE NodeDiff for this path
            node_diff: NodeDiff
            if path in added_paths:
                node = new_index[path]
                node_diff = self._create_added_node_diff_by_path(path, node, excluded_properties)
            elif path in deleted_paths:
                node = old_index[path]
                node_diff = self._create_deleted_node_diff_by_path(path, node, excluded_properties)
            else:  # common path
                node_diff = self._compare_nodes_by_path(path, old_index, new_index, excluded_properties)

            # b. ENSURE PARENT EXISTS
            parent_path = self._get_parent_path(path)
            if parent_path:
                if parent_path not in diff_by_path:
                    self._ensure_placeholder(parent_path, old_index, new_index, diff_by_path, has_parent)

                # c. LINK CHILD TO PARENT
                if parent_path in diff_by_path:
                    parent = diff_by_path[parent_path]
                    object.__setattr__(parent, "children", parent.children + [node_diff])
                    has_parent.add(path)

            # d. REGISTER IN INDEX
            diff_by_path[path] = node_diff

        return diff_by_path, has_parent

    def compare_snapshots(
        self,
        old_nodes: list[TreeNode],
        new_nodes: list[TreeNode],
        excluded_properties: list[str],
    ) -> TreeDiffResult:
        """Compare two snapshots using ID-based comparison and produce a hierarchical diff result.

        This is the main entry point for tree comparison. It supports both:
        - Flat node lists (new ID-based approach): nodes have id, path, after fields
        - Hierarchical node lists (legacy): nodes have children attribute

        The algorithm for flat structure:
        1. Build ID indices for both snapshots (O(n+m))
        2. Find added, deleted, and common IDs
        3. For each ID category, create NodeDiff with path/after info for move detection
        4. Build hierarchical structure using parent-child path relationships
        5. Return root nodes (those without parents)

        Args:
            old_nodes: Flat list of tree nodes from old snapshot
            new_nodes: Flat list of tree nodes from new snapshot
            excluded_properties: List of property names to exclude from comparison

        Returns:
            TreeDiffResult containing all comparison results with ID sets
        """
        # Build ID indices for both snapshots
        old_id_index = self._build_id_index(old_nodes)
        new_id_index = self._build_id_index(new_nodes)

        # Find added, deleted, and common IDs
        added_ids = self._find_added_ids(old_id_index, new_id_index)
        deleted_ids = self._find_deleted_ids(old_id_index, new_id_index)
        common_ids = self._find_common_ids(old_id_index, new_id_index)

        # Build hierarchical diffs using ID-based approach
        diff_by_path, has_parent = self._build_hierarchical_diffs_from_ids(
            added_ids, deleted_ids, common_ids, old_id_index, new_id_index, excluded_properties
        )

        # RETURN ROOT NODES (nodes without parents), sorted by path
        roots = [diff for diff in diff_by_path.values() if diff.path not in has_parent]
        roots = self._sort_tree(roots)

        return TreeDiffResult(
            added_ids=added_ids,
            deleted_ids=deleted_ids,
            common_ids=common_ids,
            node_diffs=roots,
        )

    def _sort_tree(self, nodes: list[NodeDiff]) -> list[NodeDiff]:
        """Recursively sort nodes and their children by path."""
        sorted_nodes = sorted(nodes, key=lambda d: d.path.split("/"))
        for node in sorted_nodes:
            if node.children:
                object.__setattr__(node, "children", self._sort_tree(node.children))
        return sorted_nodes

    def _build_hierarchical_diffs_from_ids(
        self,
        added_ids: set[int],
        deleted_ids: set[int],
        common_ids: set[int],
        old_id_index: dict[int, TreeNode],
        new_id_index: dict[int, TreeNode],
        excluded_properties: list[str],
    ) -> tuple[dict[str, NodeDiff], set[str]]:
        """Build hierarchical diffs from ID-based comparison.

        This method processes nodes and builds the hierarchy. Sets are disjoint so
        we process each one directly without membership checks.

        Args:
            added_ids: Set of IDs that are additions
            deleted_ids: Set of IDs that are deletions
            common_ids: Set of IDs that exist in both snapshots
            old_id_index: ID index for the old snapshot
            new_id_index: ID index for the new snapshot
            excluded_properties: List of property names to exclude from comparison

        Returns:
            Tuple of (diff_by_path dict, has_parent set)
        """
        diff_by_path: dict[str, NodeDiff] = {}
        has_parent: set[str] = set()

        def process_node(node_diff: NodeDiff) -> None:
            """Process a single node: ensure parent exists, link, and register."""
            parent_path = self._get_parent_path(node_diff.path)
            if parent_path:
                if parent_path not in diff_by_path:
                    self._ensure_placeholder_for_path(parent_path, old_id_index, new_id_index, diff_by_path, has_parent)
                if parent_path in diff_by_path:
                    parent_diff = diff_by_path[parent_path]
                    object.__setattr__(parent_diff, "children", parent_diff.children + [node_diff])
                    has_parent.add(node_diff.path)
            diff_by_path[node_diff.path] = node_diff

        # Process common nodes first (parents may be needed by added/deleted)
        for node_id in common_ids:
            node_diff = self._compare_nodes_by_id(node_id, old_id_index, new_id_index, excluded_properties)
            process_node(node_diff)

        # Process deleted nodes
        for node_id in deleted_ids:
            node = old_id_index[node_id]
            node_diff = self._create_deleted_node_diff(node_id, node, excluded_properties)
            process_node(node_diff)

        # Process added nodes
        for node_id in added_ids:
            node = new_id_index[node_id]
            node_diff = self._create_added_node_diff(node_id, node, excluded_properties)
            process_node(node_diff)

        return diff_by_path, has_parent

    def _ensure_placeholder_for_path(
        self,
        path: str,
        old_id_index: dict[int, TreeNode],
        new_id_index: dict[int, TreeNode],
        diff_by_path: dict[str, NodeDiff],
        has_parent: set[str],
    ) -> None:
        """Ensure a placeholder exists for a given path.

        This method creates placeholder NodeDiff objects with UNCHANGED state for
        paths that don't exist in the diff registry but are needed to maintain
        hierarchy. It recursively ensures parent placeholders exist first.

        Args:
            path: The path to ensure exists in diff_by_path
            old_id_index: ID index for the old snapshot (for type_id lookup)
            new_id_index: ID index for the new snapshot (for type_id lookup)
            diff_by_path: Registry of existing NodeDiff objects by path
            has_parent: Set of paths that have been linked to a parent
        """
        # If path already exists, nothing to do
        if path in diff_by_path:
            return

        # Recursively ensure parent exists first
        parent_path = self._get_parent_path(path)
        if parent_path and parent_path not in diff_by_path:
            self._ensure_placeholder_for_path(parent_path, old_id_index, new_id_index, diff_by_path, has_parent)

        # Look up type_id and path info from old or new index by searching all nodes
        node = None
        old_node = None
        new_node = None
        for n in list(old_id_index.values()) + list(new_id_index.values()):
            if n.path == path:
                node = n
                old_node = old_id_index.get(n.id)
                new_node = new_id_index.get(n.id)
                break

        type_id = node.type_id if node else "Unknown"
        old_path = old_node.path if old_node else None
        new_path = new_node.path if new_node else None
        old_after = old_node.after if old_node else None
        new_after = new_node.after if new_node else None

        # Create placeholder with UNCHANGED state
        placeholder = NodeDiff(
            path=path,
            type_id=type_id,
            property_diffs=[],
            children=[],
            old_path=old_path,
            new_path=new_path,
            old_after=old_after,
            new_after=new_after,
            _force_state=DiffState.UNCHANGED,
        )
        diff_by_path[path] = placeholder

        # Link to parent if parent exists
        if parent_path and parent_path in diff_by_path:
            parent_diff = diff_by_path[parent_path]
            object.__setattr__(parent_diff, "children", parent_diff.children + [placeholder])
            has_parent.add(path)


class PropertyComparator:
    """Compares property values with type-aware equality.

    This class provides instance methods for comparing property values between
    two snapshots, handling all FreeCAD property types with appropriate
    equality rules.

    Comparison rules:
    - BOOL, INT, STRING: Exact equality
    - FLOAT: Approximate equality (tolerance=1e-9)
    - VECTOR: Component-wise approximate equality
    - PLACEMENT: Position + rotation comparison
    - EXPRESSION: String equality (expression changes are significant)
    """

    def _should_exclude_property(self, prop_name: str, excluded_properties: list[str]) -> bool:
        """Check if a property should be excluded from comparison.

        Args:
            prop_name: The name of the property to check
            excluded_properties: List of property names to exclude

        Returns:
            True if the property should be excluded, False otherwise
        """
        return prop_name in excluded_properties

    def _values_are_equal(self, old_value: Property | None, new_value: Property | None) -> bool:
        """Compare two property values with type-aware equality.

        This function handles all FreeCAD property types with appropriate
        comparison rules:
        - BOOL, INT, STRING: Exact equality
        - FLOAT: Approximate equality (tolerance=1e-9)
        - VECTOR: Component-wise approximate equality
        - PLACEMENT: Position + rotation comparison
        - EXPRESSION: String equality

        Args:
            old_value: The old property value (or None)
            new_value: The new property value (or None)

        Returns:
            True if values are equal according to type-specific rules
        """
        # Handle None cases
        if old_value is None and new_value is None:
            return True
        if old_value is None or new_value is None:
            return False

        # Use Property's built-in equality which handles all types correctly
        return old_value == new_value

    def compare_properties(
        self,
        old_props: dict[str, Property],
        new_props: dict[str, Property],
        excluded_properties: list[str],
    ) -> list[PropertyDiff]:
        """Compare properties between two nodes and produce a list of PropertyDiff objects.

        This function iterates through all properties in both old and new nodes,
        creates PropertyDiff objects for each property, and filters out excluded
        properties.

        Args:
            old_props: Dictionary of property names to values from the old node
            new_props: Dictionary of property names to values from the new node
            excluded_properties: List of property names to exclude from comparison

        Returns:
            List of PropertyDiff objects for all non-excluded properties (including unchanged)
        """
        property_diffs: list[PropertyDiff] = []

        # Get all unique property names from both nodes
        all_prop_names = set(old_props.keys()) | set(new_props.keys())

        for prop_name in all_prop_names:
            # Skip excluded properties
            if self._should_exclude_property(prop_name, excluded_properties):
                continue

            old_value = old_props.get(prop_name)
            new_value = new_props.get(prop_name)

            # Create PropertyDiff for this property
            prop_diff = PropertyDiff(
                property_name=prop_name,
                old_value=old_value,
                new_value=new_value,
            )

            # Always include the property diff
            property_diffs.append(prop_diff)

        return property_diffs


__all__ = ["TreeComparator", "PropertyComparator", "TreeDiffResult"]
