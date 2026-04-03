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

    A snapshot captures the complete state of a document as a flat list
    of nodes. Each node contains its path (for move detection) and 'after'
    field (for sibling ordering). Root nodes have paths equal to their name
    (e.g., "Body"), while child nodes have paths with "/" separator
    (e.g., "Body/Pad").

    Attributes:
        snapshot_id: Unique identifier for this snapshot (UUID)
        document_name: Name of the document
        timestamp: Timestamp when the snapshot was taken
        nodes: Flat list of all tree nodes in the document
    """

    snapshot_id: str
    document_name: str
    timestamp: datetime
    nodes: list[TreeNode] = field(default_factory=list)

    @property
    def node_count(self) -> int:
        """Return total count of all nodes in the snapshot.

        Returns:
            Total number of nodes in the flat list
        """
        return len(self.nodes)

    def __str__(self) -> str:
        return f"Snapshot({self.document_name}, {len(self.nodes)} objects, {self.node_count} total nodes)"

    def get_all_nodes(self) -> list[TreeNode]:
        """Get all nodes in the snapshot as a flat list.

        Returns:
            Flat list of all TreeNode objects
        """
        return list(self.nodes)

    def find_node_by_path(self, path: str) -> TreeNode | None:
        """Find a node by its path.

        Args:
            path: The path to the node (e.g., "Body/Pad"). Root nodes
                have path equal to their name (e.g., "Body").

        Returns:
            The node if found, None otherwise
        """
        for node in self.nodes:
            if node.path == path:
                return node
        return None
