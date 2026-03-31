"""File responsibility: UI-friendly presentation models for diff display."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    pass


__all__ = ["NodePresentation", "PropertyPresentation", "SnapshotPresentation"]


@dataclass(frozen=True)
class NodePresentation:
    """UI-friendly format for a tree node."""

    path: str
    type_id: str
    state: str  # "ADDED", "DELETED", "MODIFIED", "UNCHANGED"
    has_changes: bool
    children: list["NodePresentation"] = field(default_factory=list)


@dataclass(frozen=True)
class PropertyPresentation:
    """UI-friendly format for property differences."""

    name: str
    old_display: str  # Formatted string like "10.0 (via Sketch.X)"
    new_display: str  # Formatted string like "20.0"
    state: str  # "ADDED", "DELETED", "MODIFIED", "UNCHANGED"
    value: Any = None  # Actual value for expandable properties (optional)
    group: str | None = None  # Group name for grouping (e.g., "Base", "Format")


@dataclass(frozen=True)
class SnapshotPresentation:
    """UI-friendly format for snapshot summary."""

    id: str
    name: str
    created_at: str
    node_count: int
