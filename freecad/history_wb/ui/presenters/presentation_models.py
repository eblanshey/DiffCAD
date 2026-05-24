"""File responsibility: UI-friendly presentation models for diff display."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from ...domain.diff.models import DiffState
from ...qt import QtCore, QtGui
from ...resources import get_icon_path


__all__ = [
    "DiffTreePresentation",
    "NodePresentation",
    "PropertyPresentation",
    "SnapshotPresentation",
    "DocumentStatusIndicator",
    "NewFileIndicator",
    "OldSnapshotMissingIndicator",
    "SnapshotMissingIndicator",
    "InvalidSnapshotIndicator",
    "DiffComputationFailedIndicator",
]


@dataclass(frozen=True)
class DocumentStatusIndicator:
    """UI indicator shown beside a document root row."""

    tooltip: str
    icon: QtGui.QIcon


@dataclass(frozen=True)
class NewFileIndicator(DocumentStatusIndicator):
    """Indicator for new documents missing in old ref."""

    def __init__(self) -> None:
        super().__init__(
            tooltip=cast(str, QtCore.QT_TRANSLATE_NOOP("History", "New document")),
            icon=QtGui.QIcon(str(get_icon_path("DocumentStatusNewFile.svg"))),
        )


@dataclass(frozen=True)
class OldSnapshotMissingIndicator(DocumentStatusIndicator):
    """Indicator for old-ref snapshot missing while document exists."""

    def __init__(self) -> None:
        super().__init__(
            tooltip=cast(
                str,
                QtCore.QT_TRANSLATE_NOOP(
                    "History",
                    "Cannot find old snapshot. Tree comparison cannot be generated.",
                ),
            ),
            icon=QtGui.QIcon(str(get_icon_path("DocumentStatusOldSnapshotMissing.svg"))),
        )


@dataclass(frozen=True)
class SnapshotMissingIndicator(DocumentStatusIndicator):
    """Indicator for current/target snapshot missing."""

    def __init__(self) -> None:
        super().__init__(
            tooltip=cast(
                str,
                QtCore.QT_TRANSLATE_NOOP(
                    "History", "The selected iteration does not have a snapshot for this document"
                ),
            ),
            icon=QtGui.QIcon(str(get_icon_path("DocumentStatusSnapshotMissing.svg"))),
        )


@dataclass(frozen=True)
class InvalidSnapshotIndicator(DocumentStatusIndicator):
    """Indicator for invalid/corrupt snapshot payload."""

    def __init__(self) -> None:
        super().__init__(
            tooltip=cast(
                str,
                QtCore.QT_TRANSLATE_NOOP(
                    "History", "The older snapshot is invalid, so a tree comparison cannot be generated."
                ),
            ),
            icon=QtGui.QIcon(str(get_icon_path("DocumentStatusInvalidSnapshot.svg"))),
        )


@dataclass(frozen=True)
class DiffComputationFailedIndicator(DocumentStatusIndicator):
    """Indicator for diff engine failure during comparison."""

    def __init__(self) -> None:
        super().__init__(
            tooltip=cast(str, QtCore.QT_TRANSLATE_NOOP("History", "Diff computation failed")),
            icon=QtGui.QIcon(str(get_icon_path("DocumentStatusDiffFailed.svg"))),
        )


@dataclass(frozen=True)
class NodePresentation:
    """UI-friendly format for a tree node."""

    path: str
    type_id: str
    label: str
    state: DiffState
    has_changes: bool
    visual_diff_enabled: bool = False
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
        indicators: List of status indicators shown near document label
        stage_button_enabled: True if the stage button should be enabled
    """

    nodes: list[NodePresentation]
    git_path: str
    indicators: list[DocumentStatusIndicator]
    stage_button_enabled: bool = False
