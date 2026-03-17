# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: This module provides the core snapshot domain models including
# Snapshot, SnapshotRepository protocol, and InMemorySnapshotRepository implementation.
# These are used for capturing and storing document state as tree structures.
"""Snapshot domain module."""

from .models import Snapshot, SnapshotMetadata
from .repository import InMemorySnapshotRepository, SnapshotRepository


__all__ = ["Snapshot", "SnapshotMetadata", "SnapshotRepository", "InMemorySnapshotRepository"]
