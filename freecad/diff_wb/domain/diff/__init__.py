# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: Diff subdomain containing diff engine, comparators,
# and diff result models for comparing document snapshots.
"""Diff domain module."""

from .comparator import PropertyComparator, TreeComparator
from .engine import DiffEngine
from .models import DiffResult, DiffState, NodeDiff, PropertyDiff


__all__ = ["DiffResult", "NodeDiff", "PropertyDiff", "DiffState", "DiffEngine", "TreeComparator", "PropertyComparator"]
