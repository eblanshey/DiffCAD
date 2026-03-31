# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: Domain layer containing core business logic
# including tree models, snapshot management, diff computation engines,
# and port interfaces for external system interactions.
"""Domain models for the Diff Workbench.

This package contains the core domain models that represent FreeCAD documents
and snapshots. These models are pure Python with no FreeCAD dependencies,
enabling easy testing and validation. It also defines port interfaces
(Protocols) for external system interactions.
"""

from .diff import DiffEngine, DiffResult, DiffState, NodeDiff, PropertyComparator, TreeComparator
from .ports import AppPort, FreeCadContext, FreeCadPort
from .snapshots import InMemorySnapshotRepository, Snapshot, SnapshotMetadata, SnapshotRepository
from .snapshots.gui_extractor import SnapshotExtractor
from .tree import Placement, Property, PropertyType, Rotation, TreeNode, Vector


__all__ = [
    # Ports
    "FreeCadPort",
    "AppPort",
    "FreeCadContext",
    # Tree models
    "TreeNode",
    "Property",
    "PropertyType",
    "Vector",
    "Rotation",
    "Placement",
    # Snapshots
    "Snapshot",
    "SnapshotMetadata",
    "SnapshotRepository",
    "InMemorySnapshotRepository",
    "SnapshotExtractor",
    # Diff
    "DiffResult",
    "NodeDiff",
    "PropertyDiff",
    "DiffState",
    "DiffEngine",
    "TreeComparator",
    "PropertyComparator",
]
