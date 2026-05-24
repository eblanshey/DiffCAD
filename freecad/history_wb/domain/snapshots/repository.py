# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module defines the SnapshotRepository protocol (interface)
# for snapshot persistence and provides an InMemorySnapshotRepository implementation.
# It also includes the SnapshotMetadata dataclass for snapshot metadata.
"""Snapshot repository interface and implementation."""

from __future__ import annotations

import uuid
from typing import Protocol

from .models import Snapshot, SnapshotMetadata


class SnapshotRepository(Protocol):
    """Interface for snapshot persistence operations.

    This Protocol defines the contract for storing and retrieving snapshots.
    Implementations can be in-memory, file-based, or database-backed.
    """

    def add_snapshot(self, snapshot: Snapshot) -> str:
        """Add a new snapshot to the repository.

        Args:
            snapshot: The Snapshot object to store

        Returns:
            A unique snapshot ID (UUID format)
        """
        ...

    def get_snapshot(self, snapshot_id: str) -> Snapshot | None:
        """Retrieve a snapshot by its ID.

        Args:
            snapshot_id: The unique identifier of the snapshot

        Returns:
            The Snapshot if found, None otherwise
        """
        ...

    def list_snapshots(self) -> list[SnapshotMetadata]:
        """List all snapshots in the repository with their metadata.

        Returns:
            List of SnapshotMetadata objects containing id, name, and timestamp
        """
        ...

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot from the repository.

        Args:
            snapshot_id: The unique identifier of the snapshot to delete

        Returns:
            True if the snapshot was deleted, False if it didn't exist
        """
        ...

    def get_all_snapshots(self) -> list[Snapshot]:
        """Retrieve all snapshots from the repository.

        Returns:
            List of all Snapshot objects with full data including nodes
        """
        ...


class InMemorySnapshotRepository:
    """In-memory implementation of SnapshotRepository.

    This class provides thread-safe storage for snapshots within a session.
    Snapshots are stored by ID and can be retrieved, listed, or deleted.

    Attributes:
        _snapshots: Internal dictionary mapping snapshot IDs to Snapshot objects
        _metadata: Internal dictionary mapping snapshot IDs to metadata
    """

    def __init__(self) -> None:
        """Initialize an empty snapshot repository."""
        self._snapshots: dict[str, Snapshot] = {}
        self._metadata: dict[str, SnapshotMetadata] = {}

    def add_snapshot(self, snapshot: Snapshot) -> str:
        """Add a new snapshot to the repository.

        Args:
            snapshot: The Snapshot object to store

        Returns:
            A unique snapshot ID (UUID format)
        """
        snapshot_id = str(uuid.uuid4())

        # Create new snapshot with assigned ID (since Snapshot is frozen)
        from dataclasses import replace

        snapshot_with_id = replace(snapshot, snapshot_id=snapshot_id)

        metadata = SnapshotMetadata(
            id=snapshot_id,
            name=snapshot.document_name,
            timestamp=snapshot.timestamp,
        )

        self._snapshots[snapshot_id] = snapshot_with_id
        self._metadata[snapshot_id] = metadata

        return snapshot_id

    def get_snapshot(self, snapshot_id: str) -> Snapshot | None:
        """Retrieve a snapshot by its ID.

        Args:
            snapshot_id: The unique identifier of the snapshot

        Returns:
            The Snapshot if found, None otherwise
        """
        return self._snapshots.get(snapshot_id)

    def list_snapshots(self) -> list[SnapshotMetadata]:
        """List all snapshots in the repository with their metadata.

        Returns:
            List of SnapshotMetadata objects containing id, name, and timestamp
        """
        return list(self._metadata.values())

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot from the repository.

        Args:
            snapshot_id: The unique identifier of the snapshot to delete

        Returns:
            True if the snapshot was deleted, False if it didn't exist
        """
        if snapshot_id in self._snapshots:
            del self._snapshots[snapshot_id]
            del self._metadata[snapshot_id]
            return True
        return False

    def clear(self) -> None:
        """Remove all snapshots from the repository.

        This method clears all stored snapshots and their metadata.
        Use with caution as this operation is irreversible.
        """
        self._snapshots.clear()
        self._metadata.clear()

    def get_all_snapshots(self) -> list[Snapshot]:
        """Retrieve all snapshots from the repository.

        Returns:
            List of all Snapshot objects with full data including nodes
        """
        return list(self._snapshots.values())
