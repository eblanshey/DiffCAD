# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: This module provides the core snapshot domain models including
# Snapshot, SnapshotRepository protocol, and InMemorySnapshotRepository implementation.
# It also provides utility functions like get_snapshot_directory_for_document for
# determining snapshot storage locations. These are used for capturing and storing
# document state as tree structures.
"""Snapshot domain module."""

from pathlib import Path

from .models import Snapshot, SnapshotMetadata
from .repository import InMemorySnapshotRepository, SnapshotRepository


def get_snapshot_directory_for_document(document_path: str) -> Path:
    """Get the .snapshots directory for a given document file path.

    The snapshot directory is alongside the file in a hidden .snapshots directory.
    Example: /path/to/mydoc.FCStd -> /path/to/.snapshots

    Args:
        document_path: String path to the document file (FCStd or similar).

    Returns:
        Path to the .snapshots directory.
    """
    return Path(document_path).parent / ".snapshots"


__all__ = [
    "Snapshot",
    "SnapshotMetadata",
    "SnapshotRepository",
    "InMemorySnapshotRepository",
    "get_snapshot_directory_for_document",
]
