"""File responsibility: Action result models for commands and queries."""

from dataclasses import dataclass
from typing import Any

from ...domain.diff import DiffResult


__all__ = ["Result", "SnapshotResult", "CompareResult", "SnapshotSummary"]


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
