# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains the Snapshot class which represents
# a point-in-time capture of a FreeCAD document as a tree structure, and the
# SnapshotMetadata dataclass for snapshot metadata. It uses TreeNode and Property
# from the tree domain models.
"""Snapshot domain models."""

from dataclasses import dataclass, field
from datetime import datetime

from ..tree.node import TreeNode


@dataclass
class SnapshotMetadata:
    """Metadata for a stored snapshot.

    Attributes:
        id: Unique identifier for the snapshot
        name: Human-readable name for the snapshot
        timestamp: Timestamp when the snapshot was created
    """

    id: str
    name: str
    timestamp: datetime


@dataclass(frozen=True)
class Snapshot:
    """A snapshot of a FreeCAD document at a point in time.

    A snapshot captures the complete state of a document as a tree structure.
    It includes metadata about when the snapshot was taken and provides
    methods for comparing against other snapshots.

    Attributes:
        document_name: Name of the document
        timestamp: Timestamp when the snapshot was taken
        root_nodes: List of root-level tree nodes (top-level objects)
    """

    document_name: str
    timestamp: datetime
    root_nodes: list[TreeNode] = field(default_factory=list)

    def __str__(self) -> str:
        node_count = sum(self._count_nodes(node) for node in self.root_nodes)
        return f"Snapshot({self.document_name}, {len(self.root_nodes)} objects, {node_count} total nodes)"

    def _count_nodes(self, node: TreeNode) -> int:
        """Helper to count all nodes recursively."""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count

    def get_all_nodes(self) -> list[TreeNode]:
        """Get all nodes in the tree (flattened)."""
        all_nodes = []
        for root in self.root_nodes:
            all_nodes.extend(self._collect_nodes(root))
        return all_nodes

    def _collect_nodes(self, node: TreeNode) -> list[TreeNode]:
        """Recursively collect all nodes."""
        nodes = [node]
        for child in node.children:
            nodes.extend(self._collect_nodes(child))
        return nodes

    def find_node_by_path(self, path: str) -> TreeNode | None:
        """Find a node by its path.

        Args:
            path: The path to the node (e.g., "Body/Pad")

        Returns:
            The node if found, None otherwise
        """
        for root in self.root_nodes:
            node = self._find_node_recursive(root, path)
            if node:
                return node
        return None

    def _find_node_recursive(self, node: TreeNode, target_path: str) -> TreeNode | None:
        """Recursively search for a node by path."""
        if node.path == target_path:
            return node
        for child in node.children:
            found = self._find_node_recursive(child, target_path)
            if found:
                return found
        return None
