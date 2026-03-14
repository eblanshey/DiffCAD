# SPDX-License-Identifier: LGPL-3.0-or-later
"""Snapshot management module for FreeCAD Diff Workbench.

This module provides functionality for extracting document state from FreeCAD,
storing snapshots in-memory, and providing mutation operations for creating
and retrieving snapshots.

Modules:
    snapshot_query: Document state extraction from FreeCAD documents
    snapshot_store: In-memory storage for snapshots
    snapshot_mutations: Snapshot creation and management operations
"""

from .snapshot_mutations import create_snapshot, delete_snapshot, get_default_store, get_snapshot, list_snapshots
from .snapshot_query import extract_tree
from .snapshot_store import SnapshotStore


__all__ = [
    "extract_tree",
    "SnapshotStore",
    "create_snapshot",
    "get_default_store",
    "list_snapshots",
    "get_snapshot",
    "delete_snapshot",
]
