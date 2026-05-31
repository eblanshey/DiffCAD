"""File responsibility: Action and document-diff result models for application orchestration."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from ...domain.diff import DiffResult
from ...domain.diff.models import DiffState
from ...domain.freecad_ports import DocumentLike
from ...domain.git.models import GitRepository
from ...domain.snapshots.models import Snapshot


__all__ = [
    "Result",
    "SnapshotResult",
    "CompareResult",
    "SnapshotSummary",
    "SnapshotLoadStatus",
    "SnapshotLoadResult",
    "SnapshotIssue",
    "GeneralDiffIssue",
    "DiffIssues",
    "DocumentDiffResult",
    "DocumentDiffMode",
    "CreateDocumentDiffsRequest",
]


class SnapshotLoadStatus(Enum):
    """Outcome when loading snapshot from git/index."""

    FOUND = auto()
    DOCUMENT_MISSING = auto()
    SNAPSHOT_MISSING = auto()
    INVALID_SNAPSHOT = auto()


@dataclass(frozen=True)
class SnapshotLoadResult:
    """Snapshot loading outcome with typed status."""

    snapshot: Snapshot | None
    status: SnapshotLoadStatus


class SnapshotIssue(Enum):
    """Side-specific snapshot loading issue."""

    MISSING = auto()
    INVALID = auto()


class GeneralDiffIssue(Enum):
    """General non-side-specific document diff issue."""

    DIFF_COMPUTATION_FAILED = auto()
    GIT_CHANGED_NO_PARAMETRIC_DIFF = auto()


@dataclass
class DiffIssues:
    """Categorized issues from snapshot loading and diff computation."""

    old_snapshot: SnapshotIssue | None = None
    new_snapshot: SnapshotIssue | None = None
    general: list[GeneralDiffIssue] = field(default_factory=list)

    def has_any(self) -> bool:
        """Return True when any issue exists on either side or general bucket."""
        return self.old_snapshot is not None or self.new_snapshot is not None or bool(self.general)

@dataclass(frozen=True)
class DocumentDiffResult:
    """Application-level diff result for one FCStd document."""

    git_path: str
    document_state: DiffState
    issues: DiffIssues = field(default_factory=DiffIssues)
    snapshot_diff: DiffResult | None = None


class DocumentDiffMode(Enum):
    """Selection mode for document diff orchestration."""

    WORKING_TREE = auto()
    STAGING = auto()
    COMMIT = auto()


@dataclass(frozen=True)
class CreateDocumentDiffsRequest:
    """Inputs for computing document-level diff results.

    Field semantics:
    - mode: Diff source selection.
    - repo: Repository context.
    - commit_hash: Required only for COMMIT mode. Ignored in STAGING/WORKING_TREE.
    - eligible_docs: Required only for WORKING_TREE mode.
      - None/[] means no open eligible documents.
      - COMMIT/STAGING ignore this field.
    """

    mode: DocumentDiffMode
    repo: GitRepository
    commit_hash: str | None = None
    eligible_docs: list[DocumentLike] | None = None


@dataclass
class Result:
    """Generic result type for all actions.

    Attributes:
        is_success: True if action succeeded
        data: Value on success (type varies by action, use Any for flexibility)
        message: Error message on failure
    """

    is_success: bool
    data: Any = None  # Value on success (type varies by action)
    message: str | None = None  # Error message on failure

    @staticmethod
    def success(data: Any) -> "Result":
        """Factory method for successful results."""
        return Result(is_success=True, data=data, message=None)

    @staticmethod
    def failure(message: str) -> "Result":
        """Factory method for failed results."""
        return Result(is_success=False, data=None, message=message)


@dataclass
class SnapshotResult:
    """Result of snapshot creation operation."""

    success: bool
    snapshot_id: str | None
    snapshot_name: str | None
    error_message: str | None


@dataclass
class CompareResult:
    """Result of comparison operation."""

    success: bool
    diff_result: DiffResult | None
    error_message: str | None


@dataclass
class SnapshotSummary:
    """Summary information for a snapshot (for listing)."""

    id: str
    name: str
    created_at: str
    node_count: int
