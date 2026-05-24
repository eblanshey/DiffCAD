# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: This module provides the core snapshot domain models including
# Snapshot, SnapshotRepository protocol, and InMemorySnapshotRepository implementation.
# It also provides utility functions like get_snapshot_yaml_path_for_document for
# determining snapshot YAML file locations. These are used for capturing and storing
# document state as tree structures.
"""Snapshot domain module."""

import os
from pathlib import Path

from ..git.paths import to_git_path
from .models import Snapshot, SnapshotMetadata, SnapshotObject, SnapshotOccurrence
from .repository import InMemorySnapshotRepository, SnapshotRepository
from .serializer import SnapshotDeserializer


def get_snapshot_yaml_path_for_document(document_path: str) -> Path:
    """Get the YAML snapshot path for a given document file path.

    The snapshot is alongside the file in a hidden .snapshots directory.
    Example: /path/to/mydoc.FCStd -> /path/to/.snapshots/mydoc.yaml

    Args:
        document_path: String path to the document file (FCStd or similar).

    Returns:
        Path to the YAML snapshot file.
    """
    normalized_document_path = to_git_path(document_path)
    doc_path = Path(normalized_document_path)
    parent_dir = doc_path.parent
    doc_name = os.path.splitext(doc_path.name)[0]
    return parent_dir / ".snapshots" / f"{doc_name}.yaml"


__all__ = [
    "Snapshot",
    "SnapshotMetadata",
    "SnapshotObject",
    "SnapshotOccurrence",
    "SnapshotRepository",
    "SnapshotDeserializer",
    "InMemorySnapshotRepository",
    "get_snapshot_yaml_path_for_document",
]
