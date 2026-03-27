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
    """Result of comparing two tree snapshots.

    Attributes:
        added_paths: Set of paths that exist only in the new snapshot
        deleted_paths: Set of paths that exist only in the old snapshot
        common_paths: Set of paths that exist in both snapshots
        node_diffs: Hierarchical list of NodeDiff objects
    """

    added_paths: set[str]
    deleted_paths: set[str]
    common_paths: set[str]
    node_diffs: list[NodeDiff]


class TreeComparator:
    """Compares two tree structures using path-based indexing.

    This class provides instance methods for comparing tree snapshots efficiently
    using path-based indexing to achieve O(n+m) performance.

    The algorithm:
    1. Build path index for old snapshot (O(n))
    2. Build path index for new snapshot (O(m))
    3. Find added paths (in new but not old)
    4. Find deleted paths (in old but not new)
    5. Find common paths and compare nodes
    6. Reconstruct hierarchical structure from flat list
    """

    def __init__(self) -> None:
        """Initialize TreeComparator with a PropertyComparator instance."""
        self._property_comparator = PropertyComparator()

    def _build_path_index(self, root_nodes: list[TreeNode]) -> dict[str, TreeNode]:
        """Build a path-based index for O(1) node lookups.

        Traverses the tree recursively and creates a dictionary mapping each
        node's path to the node itself. This enables efficient comparison
        without nested iteration.

        Args:
            root_nodes: List of root tree nodes to index

        Returns:
            Dictionary mapping path strings to TreeNode objects
        """
        index: dict[str, TreeNode] = {}

        def _index_nodes(node: TreeNode) -> None:
            index[node.path] = node
            for child in node.children:
                _index_nodes(child)

        for root in root_nodes:
            _index_nodes(root)

        return index

    def _find_added_paths(self, old_index: dict[str, TreeNode], new_index: dict[str, TreeNode]) -> set[str]:
        """Find paths that exist only in the new snapshot.

        Args:
            old_index: Path index for the old snapshot
            new_index: Path index for the new snapshot

        Returns:
            Set of paths that are in new but not in old
        """
        return set(new_index.keys()) - set(old_index.keys())

    def _find_deleted_paths(self, old_index: dict[str, TreeNode], new_index: dict[str, TreeNode]) -> set[str]:
        """Find paths that exist only in the old snapshot.

        Args:
            old_index: Path index for the old snapshot
            new_index: Path index for the new snapshot

        Returns:
            Set of paths that are in old but not in new
        """
        return set(old_index.keys()) - set(new_index.keys())

    def _find_common_paths(self, old_index: dict[str, TreeNode], new_index: dict[str, TreeNode]) -> set[str]:
        """Find paths that exist in both snapshots.

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
    ) -> NodeDiff | None:
        """Compare two nodes at the same path and produce a NodeDiff.

        This function compares the properties of two nodes using the property_diff
        module and determines if they have been modified. If no properties differ
        (after filtering excluded properties), returns None.

        Args:
            path: The path to compare
            old_index: Path index for the old snapshot
            new_index: Path index for the new snapshot
            excluded_properties: List of property names to exclude from comparison

        Returns:
            NodeDiff if properties differ, None otherwise
        """
        old_node = old_index.get(path)
        new_node = new_index.get(path)

        if old_node is None or new_node is None:
            return None

        # Use property comparator to compare properties with exclusion filtering
        property_diffs = self._property_comparator.compare_properties(
            old_node.properties, new_node.properties, excluded_properties
        )

        # If no property differences (all excluded or identical), return None
        if not property_diffs:
            return None

        # Return NodeDiff with populated property diffs
        # State will be automatically calculated in __post_init__ based on property_diffs
        return NodeDiff(
            path=path,
            type_id=new_node.type_id,
            property_diffs=property_diffs,
            children=[],  # Will be populated recursively by reconstruct_hierarchy
        )

    def _create_added_node_diff(self, path: str, node: TreeNode, excluded_properties: list[str]) -> NodeDiff:
        """Create a NodeDiff for an added node.

        This is called for nodes that exist only in the new snapshot (not in old).
        The entire node is considered ADDED, regardless of its properties.

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

    def _create_deleted_node_diff(self, path: str, node: TreeNode, excluded_properties: list[str]) -> NodeDiff:
        """Create a NodeDiff for a deleted node.

        This is called for nodes that exist only in the old snapshot (not in new).
        The entire node is considered DELETED, regardless of its properties.

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

    def _reconstruct_hierarchy(
        self,
        node_diffs: list[NodeDiff],
        old_index: dict[str, TreeNode] | None = None,
        new_index: dict[str, TreeNode] | None = None,
    ) -> list[NodeDiff]:
        """Reconstruct hierarchical structure from a flat list of NodeDiff objects.

        Takes a list of NodeDiff objects (which may be at various depths) and
        organizes them into a proper tree structure based on path hierarchy.
        The result is sorted so that parents appear before their children,
        and siblings are sorted alphabetically.

        If a parent node is missing from the diff list but is needed to maintain
        hierarchy (e.g., a child has changes but the parent doesn't), placeholder
        parent nodes with UNCHANGED state are inserted using type information from
        the provided indices.

        Args:
            node_diffs: Flat list of NodeDiff objects
            old_index: Optional path index for the old snapshot (for placeholder types)
            new_index: Optional path index for the new snapshot (for placeholder types)

        Returns:
            Hierarchical list of NodeDiff objects with children properly nested
            and sorted in tree order (parents before children, siblings alphabetically)
        """
        if not node_diffs:
            return []

        # Sort node_diffs by path to ensure consistent ordering:
        # - Parents before children (shorter paths first when they are prefixes)
        # - Siblings sorted alphabetically
        sorted_node_diffs = sorted(node_diffs, key=lambda d: d.path.split("/"))

        # Build a lookup dictionary for quick access
        diff_by_path: dict[str, NodeDiff] = {diff.path: diff for diff in sorted_node_diffs}

        # Track which nodes have been added as children
        has_parent: set[str] = set()

        # First pass: establish parent-child relationships
        # Iterate over sorted_node_diffs to ensure children are added in sorted order
        for diff in sorted_node_diffs:
            path_parts = diff.path.split("/")
            if len(path_parts) > 1:
                # This node has a potential parent
                parent_path = "/".join(path_parts[:-1])
                if parent_path in diff_by_path:
                    parent_diff = diff_by_path[parent_path]
                    # Add this node as a child of its parent
                    # Since NodeDiff is frozen, we need to use object.__setattr__
                    object.__setattr__(parent_diff, "children", parent_diff.children + [diff])
                    has_parent.add(diff.path)

        # Second pass: collect root nodes (nodes without parents in the diff list)
        # Use sorted_node_diffs to maintain consistent ordering
        root_diffs: list[NodeDiff] = []
        for diff in sorted_node_diffs:
            if diff.path not in has_parent:
                root_diffs.append(diff)

        # Third pass: Insert placeholder parent nodes for missing ancestors
        # This ensures children are properly nested under their parents even when
        # the parents themselves have no changes
        root_diffs = self._insert_missing_ancestors(root_diffs, diff_by_path, old_index or {}, new_index or {})

        return root_diffs

    def _insert_missing_ancestors(
        self,
        root_diffs: list[NodeDiff],
        existing_diffs: dict[str, NodeDiff],
        old_index: dict[str, TreeNode],
        new_index: dict[str, TreeNode],
    ) -> list[NodeDiff]:
        """Insert placeholder parent nodes for missing ancestors.

        When a node has changes but its parent doesn't (and thus isn't in the diff
        list), this method creates placeholder parent nodes with UNCHANGED state
        to preserve the hierarchy. The type_id for placeholders is retrieved from
        the old/new indices.

        Args:
            root_diffs: Current list of root NodeDiff objects
            existing_diffs: Dictionary of all existing NodeDiff by path
            old_index: Path index for the old snapshot
            new_index: Path index for the new snapshot

        Returns:
            Updated list of root NodeDiff objects with placeholder ancestors inserted
        """
        # Collect all paths that need to be represented (from current root_diffs)
        all_paths: set[str] = set()

        def collect_paths(nodes: list[NodeDiff]) -> None:
            for node in nodes:
                all_paths.add(node.path)
                collect_paths(node.children)

        collect_paths(root_diffs)

        # For each path, check if all ancestors exist; if not, create placeholders
        def ensure_ancestor_path(path: str) -> None:
            """Ensure all ancestors of a path exist by creating placeholders."""
            path_parts = [p for p in path.split("/") if p]  # Filter out empty segments
            if len(path_parts) <= 1:
                return

            # Check each ancestor from root down to direct parent
            for i in range(1, len(path_parts)):
                ancestor_path = "/".join(path_parts[:i])
                if ancestor_path not in all_paths and ancestor_path not in existing_diffs:
                    # Need to create a placeholder for this ancestor
                    # Get type_id from old or new index
                    old_node = old_index.get(ancestor_path)
                    new_node = new_index.get(ancestor_path)
                    type_id = old_node.type_id if old_node else (new_node.type_id if new_node else "Unknown")

                    placeholder = NodeDiff(
                        path=ancestor_path,
                        type_id=type_id,
                        property_diffs=[],
                        children=[],
                        _force_state=DiffState.UNCHANGED,
                    )
                    existing_diffs[ancestor_path] = placeholder
                    all_paths.add(ancestor_path)

        # Process all paths to ensure ancestors exist
        paths_to_process = list(all_paths)
        for path in paths_to_process:
            ensure_ancestor_path(path)

        # Rebuild the hierarchy with placeholders included
        # Re-sort to include new placeholders
        all_diffs = list(existing_diffs.values())
        sorted_diffs = sorted(all_diffs, key=lambda d: d.path.split("/"))

        # Clear children and rebuild relationships
        for diff in sorted_diffs:
            object.__setattr__(diff, "children", [])

        has_parent: set[str] = set()
        for diff in sorted_diffs:
            path_parts = diff.path.split("/")
            if len(path_parts) > 1:
                parent_path = "/".join(path_parts[:-1])
                if parent_path in existing_diffs:
                    parent_diff = existing_diffs[parent_path]
                    object.__setattr__(parent_diff, "children", parent_diff.children + [diff])
                    has_parent.add(diff.path)

        # Collect final root nodes
        final_roots: list[NodeDiff] = []
        for diff in sorted_diffs:
            if diff.path not in has_parent:
                final_roots.append(diff)

        return final_roots

    def compare_snapshots(
        self,
        old_root_nodes: list[TreeNode],
        new_root_nodes: list[TreeNode],
        excluded_properties: list[str],
    ) -> TreeDiffResult:
        """Compare two snapshots and produce a hierarchical diff result.

        This is the main entry point for tree comparison. It uses path-based
        indexing to achieve O(n+m) performance where n and m are the number
        of nodes in each snapshot.

        Args:
            old_root_nodes: Root nodes of the old snapshot
            new_root_nodes: Root nodes of the new snapshot
            excluded_properties: List of property names to exclude from comparison

        Returns:
            TreeDiffResult containing all comparison results
        """
        # Build path indices for both snapshots
        old_index = self._build_path_index(old_root_nodes)
        new_index = self._build_path_index(new_root_nodes)

        # Find added, deleted, and common paths
        added_paths = self._find_added_paths(old_index, new_index)
        deleted_paths = self._find_deleted_paths(old_index, new_index)
        common_paths = self._find_common_paths(old_index, new_index)

        # Collect all NodeDiff objects
        all_node_diffs: list[NodeDiff] = []

        # Create NodeDiff for added paths
        for path in added_paths:
            node = new_index[path]
            all_node_diffs.append(self._create_added_node_diff(path, node, excluded_properties))

        # Create NodeDiff for deleted paths
        for path in deleted_paths:
            node = old_index[path]
            all_node_diffs.append(self._create_deleted_node_diff(path, node, excluded_properties))

        # Compare common paths
        for path in common_paths:
            node_diff = self._compare_nodes_by_path(path, old_index, new_index, excluded_properties)
            if node_diff is not None:
                all_node_diffs.append(node_diff)

        # Reconstruct hierarchy (pass indices for placeholder type resolution)
        hierarchical_diffs = self._reconstruct_hierarchy(all_node_diffs, old_index, new_index)

        return TreeDiffResult(
            added_paths=added_paths,
            deleted_paths=deleted_paths,
            common_paths=common_paths,
            node_diffs=hierarchical_diffs,
        )


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
            List of PropertyDiff objects for non-excluded properties that have differences
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

            # Only include if there's an actual difference
            if prop_diff.state != DiffState.UNCHANGED:
                property_diffs.append(prop_diff)

        return property_diffs


__all__ = ["TreeComparator", "PropertyComparator", "TreeDiffResult"]
