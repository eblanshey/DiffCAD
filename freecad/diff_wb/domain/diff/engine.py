# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the DiffEngine class that orchestrates
# diff computation between two snapshots. It coordinates between TreeComparator
# and PropertyComparator, applies filtering based on excluded types and properties,
# and produces a complete DiffResult.
#
# The engine uses dependency injection for SettingsRepository to determine
# configuration at runtime.
"""Diff computation engine."""

from typing import Protocol

from ...config import EXCLUDED_PROPERTIES, EXCLUDED_TYPES
from ..settings import SettingsRepository
from ..snapshots import Snapshot
from ..tree import TreeNode
from .comparator import TreeComparator, TreeDiffResult
from .models import DiffResult


class TreeComparatorProtocol(Protocol):
    """Protocol for TreeComparator to enable dependency injection."""

    def compare_snapshots(
        self,
        old_root_nodes: list[TreeNode],
        new_root_nodes: list[TreeNode],
        excluded_properties: list[str],
    ) -> TreeDiffResult: ...


class DiffEngine:
    """Orchestrates diff computation between two snapshots.

    This class coordinates the tree comparison and property comparison
    processes, applying user-configured filters for excluded types and
    properties.

    The engine uses dependency injection for SettingsRepository and
    TreeComparator, allowing different implementations and easy mocking.

    Attributes:
        _settings_repo: Settings repository for accessing configuration
        _tree_comparator: Tree comparator instance for tree comparison
    """

    def __init__(
        self,
        settings_repo: SettingsRepository | None = None,
        tree_comparator: TreeComparatorProtocol | None = None,
    ) -> None:
        """Initialize the diff engine.

        Args:
            settings_repo: Settings repository for accessing configuration.
                If None, uses default values from config.py.
            tree_comparator: Tree comparator instance. If None, creates
                a default TreeComparator instance.
        """
        self._settings_repo = settings_repo
        self._tree_comparator = tree_comparator or TreeComparator()

    def _get_excluded_node_types(self) -> list[str]:
        """Get list of excluded type IDs.

        Returns:
            List of type IDs to exclude, using settings repo if available
        """
        if self._settings_repo is not None:
            return self._settings_repo.get_excluded_types()
        return EXCLUDED_TYPES

    def _get_excluded_properties(self) -> list[str]:
        """Get list of excluded property names.

        Returns:
            List of property names to exclude, using settings repo if available
        """
        if self._settings_repo is not None:
            return self._settings_repo.get_excluded_properties()
        return EXCLUDED_PROPERTIES

    def _filter_snapshot(self, snapshot: Snapshot, excluded_types: list[str]) -> Snapshot:
        """Filter out nodes of excluded types from a snapshot.

        This recursively removes nodes whose type_id matches any in the
        excluded_types list, along with their children.

        Args:
            snapshot: The snapshot to filter
            excluded_types: List of type IDs to exclude

        Returns:
            A new snapshot with excluded nodes removed
        """
        if not excluded_types:
            return snapshot

        def filter_node(node: TreeNode) -> TreeNode | None:
            """Recursively filter a node and its children."""
            # Check if this node's type should be excluded
            if node.type_id in excluded_types:
                return None

            # Recursively filter children
            filtered_children: list[TreeNode] = []
            for child in node.children:
                filtered_child = filter_node(child)
                if filtered_child is not None:
                    filtered_children.append(filtered_child)

            # Create a new node with filtered children
            # Note: We need to reconstruct the path since children may have changed
            return TreeNode(
                name=node.name,
                type_id=node.type_id,
                label=node.label,
                path=node.path,
                properties=node.properties,
                children=filtered_children,
            )

        # Filter all root nodes
        filtered_roots: list[TreeNode] = []
        for root in snapshot.root_nodes:
            filtered_root = filter_node(root)
            if filtered_root is not None:
                filtered_roots.append(filtered_root)

        # Return a new snapshot with filtered roots
        return Snapshot(
            document_name=snapshot.document_name,
            timestamp=snapshot.timestamp,
            root_nodes=filtered_roots,
        )

    def compute_diff(self, old: Snapshot, new: Snapshot) -> DiffResult:
        """Compute diff between two snapshots.

        Steps:
        1. Get settings (excluded types/properties)
        2. Filter snapshots based on excluded types
        3. Compare trees using TreeComparator
        4. Apply property-level exclusions
        5. Return DiffResult

        Args:
            old: The old snapshot to compare
            new: The new snapshot to compare

        Returns:
            DiffResult containing all differences between the snapshots
        """
        # Step 1: Get settings
        excluded_node_types = self._get_excluded_node_types()
        excluded_properties = self._get_excluded_properties()

        # Step 2: Filter snapshots based on excluded types
        filtered_old = self._filter_snapshot(old, excluded_node_types)
        filtered_new = self._filter_snapshot(new, excluded_node_types)

        # Step 3: Compare trees using TreeComparator
        tree_diff_result = self._tree_comparator.compare_snapshots(
            filtered_old.root_nodes, filtered_new.root_nodes, excluded_properties
        )

        # Step 4: Build NodeDiff objects for excluded type nodes (as deleted/added)
        # This ensures we track when entire branches are removed due to filtering
        # For now, we just use the tree diff result directly

        # Step 5: Construct DiffResult
        return DiffResult(
            old_snapshot_name=old.document_name,
            new_snapshot_name=new.document_name,
            node_diffs=tree_diff_result.node_diffs,
        )


__all__ = ["DiffEngine"]
