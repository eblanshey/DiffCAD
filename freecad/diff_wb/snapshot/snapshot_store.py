# SPDX-License-Identifier: LGPL-3.0-or-later
"""In-memory snapshot storage for the Diff Workbench.

This module provides an in-memory store for document snapshots, allowing
session-based snapshot management without persistence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from freecad.diff_wb.domain.snapshot import Snapshot, TreeNode


@dataclass
class SnapshotMetadata:
    """Metadata for a stored snapshot."""

    id: str
    name: str
    timestamp: datetime


class SnapshotStore:
    """In-memory storage for document snapshots.

    This class provides thread-safe storage for snapshots within a session.
    Snapshots are stored by ID and can be retrieved, listed, or deleted.

    Attributes:
        _snapshots: Internal dictionary mapping snapshot IDs to Snapshot objects
        _metadata: Internal dictionary mapping snapshot IDs to metadata
    """

    def __init__(self) -> None:
        """Initialize an empty snapshot store."""
        self._snapshots: dict[str, Snapshot] = {}
        self._metadata: dict[str, SnapshotMetadata] = {}

    def add_snapshot(self, name: str, root_nodes: list[TreeNode]) -> str:
        """Add a new snapshot to the store.

        Args:
            name: A human-readable name for the snapshot
            root_nodes: List of root-level tree nodes representing the document state

        Returns:
            A unique snapshot ID (UUID format)

        Example:
            >>> store = SnapshotStore()
            >>> snapshot_id = store.add_snapshot("Before Changes", root_nodes)
            >>> snapshot = store.get_snapshot(snapshot_id)
        """
        snapshot_id = str(uuid.uuid4())
        timestamp = datetime.now()

        snapshot = Snapshot(
            document_name=name,
            timestamp=timestamp,
            root_nodes=root_nodes,
        )

        metadata = SnapshotMetadata(
            id=snapshot_id,
            name=name,
            timestamp=timestamp,
        )

        self._snapshots[snapshot_id] = snapshot
        self._metadata[snapshot_id] = metadata

        return snapshot_id

    def get_snapshot(self, snapshot_id: str) -> Snapshot | None:
        """Retrieve a snapshot by its ID.

        Args:
            snapshot_id: The unique identifier of the snapshot

        Returns:
            The Snapshot if found, None otherwise

        Example:
            >>> snapshot = store.get_snapshot("abc-123-def")
            >>> if snapshot:
            ...     print(f"Found {len(snapshot.root_nodes)} root objects")
        """
        return self._snapshots.get(snapshot_id)

    def list_snapshots(self) -> list[dict[str, Any]]:
        """List all snapshots in the store with their metadata.

        Returns:
            List of dictionaries containing snapshot metadata (id, name, timestamp)

        Example:
            >>> snapshots = store.list_snapshots()
            >>> for snap in snapshots:
            ...     print(f"{snap['name']} - {snap['timestamp']}")
        """
        return [{"id": meta.id, "name": meta.name, "timestamp": meta.timestamp} for meta in self._metadata.values()]

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot from the store.

        Args:
            snapshot_id: The unique identifier of the snapshot to delete

        Returns:
            True if the snapshot was deleted, False if it didn't exist

        Example:
            >>> success = store.delete_snapshot("abc-123-def")
            >>> if success:
            ...     print("Snapshot deleted successfully")
        """
        if snapshot_id in self._snapshots:
            del self._snapshots[snapshot_id]
            del self._metadata[snapshot_id]
            return True
        return False

    def clear(self) -> None:
        """Remove all snapshots from the store.

        This method clears all stored snapshots and their metadata.
        Use with caution as this operation is irreversible.

        Example:
            >>> store.clear()
            >>> assert len(store.list_snapshots()) == 0
        """
        self._snapshots.clear()
        self._metadata.clear()
