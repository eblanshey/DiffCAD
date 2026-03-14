# SPDX-License-Identifier: LGPL-3.0-or-later
"""Snapshot creation and management operations.

This module provides mutation operations for creating and managing snapshots
of FreeCAD documents.
"""

from __future__ import annotations

from typing import Any

from freecad.diff_wb.domain.snapshot import Snapshot
from freecad.diff_wb.ports.freecad_context import FreeCadContext
from freecad.diff_wb.snapshot.snapshot_query import extract_tree
from freecad.diff_wb.snapshot.snapshot_store import SnapshotStore


# Global default store for session-based snapshot management
_default_store: SnapshotStore = SnapshotStore()


def get_default_store() -> SnapshotStore:
    """Get the default snapshot store for the current session.

    Returns:
        The global SnapshotStore instance used by default for snapshot operations.

    Example:
        >>> store = get_default_store()
        >>> store.list_snapshots()
    """
    return _default_store


def create_snapshot(name: str, ctx: FreeCadContext | None = None) -> str:
    """Create a new snapshot of the active FreeCAD document.

    This function extracts the current document state and stores it in the
    default snapshot store with the given name.

    Args:
        name: A human-readable name for the snapshot
        ctx: Optional FreeCadContext. If None, uses runtime context.

    Returns:
        A unique snapshot ID that can be used to retrieve the snapshot later.

    Raises:
        ValueError: If the name is empty or None

    Example:
        >>> snapshot_id = create_snapshot("Before Changes")
        >>> print(f"Snapshot created: {snapshot_id}")
        >>> # Later...
        >>> snapshot = get_default_store().get_snapshot(snapshot_id)
    """
    if not name:
        raise ValueError("Snapshot name cannot be empty")

    # Extract the document tree
    snapshot: Snapshot = extract_tree(ctx)

    # Store the snapshot
    snapshot_id = _default_store.add_snapshot(name, snapshot.root_nodes)

    return snapshot_id


def delete_snapshot(snapshot_id: str) -> bool:
    """Delete a snapshot from the default store.

    Args:
        snapshot_id: The unique identifier of the snapshot to delete

    Returns:
        True if the snapshot was deleted, False if it didn't exist

    Example:
        >>> success = delete_snapshot("abc-123-def")
        >>> if success:
        ...     print("Snapshot deleted")
    """
    return _default_store.delete_snapshot(snapshot_id)


def list_snapshots() -> list[dict[str, Any]]:
    """List all snapshots in the default store.

    Returns:
        List of dictionaries containing snapshot metadata (id, name, timestamp)

    Example:
        >>> snapshots = list_snapshots()
        >>> for snap in snapshots:
        ...     print(f"{snap['name']} - {snap['timestamp']}")
    """
    return _default_store.list_snapshots()


def get_snapshot(snapshot_id: str) -> Snapshot | None:
    """Retrieve a snapshot by its ID from the default store.

    Args:
        snapshot_id: The unique identifier of the snapshot

    Returns:
        The Snapshot if found, None otherwise

    Example:
        >>> snapshot = get_snapshot("abc-123-def")
        >>> if snapshot:
        ...     print(f"Found {len(snapshot.root_nodes)} root objects")
    """
    return _default_store.get_snapshot(snapshot_id)
