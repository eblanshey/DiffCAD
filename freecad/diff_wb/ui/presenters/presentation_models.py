"""File responsibility: UI-friendly presentation models for diff display."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...domain.diff.models import DiffState


__all__ = [
    "DiffTreePresentation",
    "NodePresentation",
    "PropertyPresentation",
    "SnapshotPresentation",
]


@dataclass(frozen=True)
class NodePresentation:
    """UI-friendly format for a tree node."""

    path: str
    type_id: str
    state: DiffState
    has_changes: bool
    children: list[NodePresentation] = field(default_factory=list)


@dataclass(frozen=True)
class PropertyPresentation:
    """UI-friendly format for property differences.

    This model stores raw values for computing sub-property diffs when expanded.
    Display formatting is performed on-demand in the view layer using str().
    """

    # Core identification
    name: str
    state: DiffState

    # Value fields - raw values for computing sub-property diffs when expanded
    old_value: Any = None  # Actual old value for expandable properties
    new_value: Any = None  # Actual new value for expandable properties

    # Children computed by domain (not re-diffed in UI)
    children: list[PropertyPresentation] = field(default_factory=list)

    # Grouping
    group: str | None = None  # Group name for grouping (e.g., "Base", "Format")


@dataclass(frozen=True)
class SnapshotPresentation:
    """UI-friendly format for snapshot summary."""

    id: str
    name: str
    created_at: str
    node_count: int


@dataclass(frozen=True)
class DiffTreePresentation:
    """Wrapper for presenting a single diff tree with metadata.

    Attributes:
        nodes: Transformed list of root NodePresentation objects
        git_path: Git path of the document
        warnings: List of warning strings from DiffResult.warnings
        stage_button_enabled: True if the stage button should be enabled
    """

    nodes: list[NodePresentation]
    git_path: str
    warnings: list[str]
    stage_button_enabled: bool = False
