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

from ...utils import Log
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

        # Check if there are any actual changes (excluding unchanged)
        has_changes = any(diff.state != DiffState.UNCHANGED for diff in property_diffs)

        # If no property differences (all excluded or identical), return None
        if not has_changes:
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

        Log.info(f"[COMPARATOR] Building hierarchical diffs for {len(sorted_paths)} paths")
        Log.info(f"[COMPARATOR] Added paths: {added_paths}")
        Log.info(f"[COMPARATOR] Deleted paths: {deleted_paths}")

        for path in sorted_paths:
            Log.info(f"[COMPARATOR] Processing path: {path}")
            # a. CREATE NodeDiff for this path
            node_diff: NodeDiff
            if path in added_paths:
                node = new_index[path]
                node_diff = self._create_added_node_diff(path, node, excluded_properties)
                Log.info(f"[COMPARATOR]   Created ADDED node: {path}, type={node_diff.type_id}")
            elif path in deleted_paths:
                node = old_index[path]
                node_diff = self._create_deleted_node_diff(path, node, excluded_properties)
                Log.info(f"[COMPARATOR]   Created DELETED node: {path}, type={node_diff.type_id}")
            else:  # common path with changes
                result = self._compare_nodes_by_path(path, old_index, new_index, excluded_properties)
                # If no changes, skip (shouldn't happen for common_paths in sorted_paths, but safety check)
                if result is None:
                    Log.info(f"[COMPARATOR]   Skipping unchanged path: {path}")
                    continue
                node_diff = result
                prop_count = len(node_diff.property_diffs)
                Log.info(f"[COMPARATOR]   Created MODIFIED node: {path}, type={node_diff.type_id}, props={prop_count}")

            # b. ENSURE PARENT EXISTS
            parent_path = self._get_parent_path(path)
            Log.info(f"[COMPARATOR]   Parent path for {path}: '{parent_path}'")
            if parent_path:
                if parent_path not in diff_by_path:
                    Log.info(f"[COMPARATOR]   Parent '{parent_path}' not found, creating placeholder")
                    self._ensure_placeholder(parent_path, old_index, new_index, diff_by_path, has_parent)
                else:
                    Log.info(f"[COMPARATOR]   Parent '{parent_path}' already exists in diff_by_path")

                # c. LINK CHILD TO PARENT
                if parent_path in diff_by_path:
                    parent = diff_by_path[parent_path]
                    object.__setattr__(parent, "children", parent.children + [node_diff])
                    has_parent.add(path)
                    Log.info(
                        f"[COMPARATOR]   Linked {path} to parent {parent_path} "
                        f"(parent now has {len(parent.children)} children)"
                    )
                else:
                    Log.warning(
                        f"[COMPARATOR]   WARNING: Parent '{parent_path}' still not in diff_by_path "
                        "after ensure_placeholder!"
                    )

            # d. REGISTER IN INDEX
            diff_by_path[path] = node_diff
            Log.info(f"[COMPARATOR]   Registered {path} in diff_by_path (total: {len(diff_by_path)})")

        Log.info(f"[COMPARATOR] Final: {len(diff_by_path)} nodes in diff_by_path, {len(has_parent)} have parents")
        roots = [d for d in diff_by_path.values() if d.path not in has_parent]
        Log.info(f"[COMPARATOR] Root nodes: {[r.path for r in roots]}")

        return diff_by_path, has_parent

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

        The algorithm:
        1. Build path indices for both snapshots
        2. Find added, deleted, and common paths
        3. For common paths, compare nodes and collect those with changes
        4. Sort all changed paths (ensures parents before children)
        5. Single-pass iteration: create diffs, ensure parents exist, link children
        6. Return root nodes (those without parents)

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

        Log.info(f"[COMPARATOR] Old index has {len(old_index)} paths: {sorted(old_index.keys())}")
        Log.info(f"[COMPARATOR] New index has {len(new_index)} paths: {sorted(new_index.keys())}")

        # Find added, deleted, and common paths
        added_paths = self._find_added_paths(old_index, new_index)
        deleted_paths = self._find_deleted_paths(old_index, new_index)
        common_paths = self._find_common_paths(old_index, new_index)

        Log.info(f"[COMPARATOR] Added: {added_paths}")
        Log.info(f"[COMPARATOR] Deleted: {deleted_paths}")
        Log.info(f"[COMPARATOR] Common: {len(common_paths)} paths")

        # COLLECT ALL CHANGED PATHS
        all_paths: set[str] = added_paths | deleted_paths
        for path in common_paths:
            node_diff = self._compare_nodes_by_path(path, old_index, new_index, excluded_properties)
            if node_diff is not None:
                all_paths.add(path)

        Log.info(f"[COMPARATOR] All changed paths ({len(all_paths)}): {sorted(all_paths)}")

        # SORT PATHS (ensures parents before children)
        sorted_paths = sorted(all_paths, key=lambda p: p.split("/"))
        Log.info(f"[COMPARATOR] Sorted paths: {sorted_paths}")

        # SINGLE-PASS ITERATION to build hierarchical diffs
        diff_by_path, has_parent = self._build_hierarchical_diffs(
            sorted_paths, added_paths, deleted_paths, old_index, new_index, excluded_properties
        )

        # RETURN ROOT NODES (nodes without parents)
        roots = [diff for diff in diff_by_path.values() if diff.path not in has_parent]
        roots = sorted(roots, key=lambda d: d.path.split("/"))

        Log.info(f"[COMPARATOR] Returning {len(roots)} root nodes: {[r.path for r in roots]}")

        return TreeDiffResult(
            added_paths=added_paths,
            deleted_paths=deleted_paths,
            common_paths=common_paths,
            node_diffs=roots,
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
