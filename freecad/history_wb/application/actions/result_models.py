"""File responsibility: Action and document-diff result models for application orchestration."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from ...domain.diff import DiffResult
from ...domain.freecad_ports import DocumentLike
from ...domain.git.models import GitRepository
from ...domain.snapshots import Snapshot


__all__ = [
    "Result",
    "SnapshotResult",
    "CompareResult",
    "SnapshotSummary",
    "SnapshotLoadStatus",
    "SnapshotLoadResult",
    "DocumentDiffStatus",
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


class DocumentDiffStatus(Enum):
    """Document-level diff status across file/snapshot states."""

    MODIFIED = auto()
    UNCHANGED = auto()
    NEW_FILE = auto()
    OLD_SNAPSHOT_MISSING = auto()
    SNAPSHOT_MISSING = auto()
    INVALID_SNAPSHOT = auto()
    DIFF_COMPUTATION_FAILED = auto()


@dataclass(frozen=True)
class DocumentDiffResult:
    """Application-level diff result for one FCStd document."""

    git_path: str
    status: DocumentDiffStatus
    snapshot_diff: DiffResult | None = None


class DocumentDiffMode(Enum):
    """Selection mode for document diff orchestration."""

    WORKING_TREE = auto()
    STAGING = auto()
    COMMIT = auto()


@dataclass(frozen=True)
class CreateDocumentDiffsRequest:
    """Inputs for computing document-level diff results."""

    mode: DocumentDiffMode
    repo: GitRepository
    commit_hash: str | None = None
    documents: list[DocumentLike] | None = None


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
