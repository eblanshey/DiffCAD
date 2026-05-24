# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: Diff subdomain containing diff engine, comparators,
# and diff result models for comparing document snapshots.
"""Diff domain module."""

from .comparator import PropertyComparator, TreeComparator
from .engine import DiffEngine
from .models import (
    DiffHierarchy,
    DiffResult,
    DiffState,
    NodeDiff,
    PropertyDiff,
    PropertyPathDiff,
)
from .visual_diff import FreeCADVisualDiffPort


__all__ = [
    "DiffResult",
    "DiffHierarchy",
    "NodeDiff",
    "PropertyDiff",
    "PropertyPathDiff",
    "DiffState",
    "DiffEngine",
    "TreeComparator",
    "PropertyComparator",
    "FreeCADVisualDiffPort",
]
