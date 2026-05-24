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
from .freecad_ports import (
    AppPort,
    DocumentObjectLike,
    FreeCadContext,
    FreeCadFileManagerPort,
    FreeCadPort,
    GuiDocumentLike,
    GuiLike,
)
from .snapshots import (
    InMemorySnapshotRepository,
    Snapshot,
    SnapshotMetadata,
    SnapshotObject,
    SnapshotOccurrence,
    SnapshotRepository,
)
from .snapshots.gui_extractor import SnapshotExtractor
from .tree import Property, TreeNode


__all__ = [
    # Ports
    "FreeCadPort",
    "AppPort",
    "FreeCadContext",
    "FreeCadFileManagerPort",
    "DocumentObjectLike",
    "GuiLike",
    "GuiDocumentLike",
    # Tree models
    "TreeNode",
    "Property",
    # Snapshots
    "Snapshot",
    "SnapshotMetadata",
    "SnapshotObject",
    "SnapshotOccurrence",
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
