"""File responsibility: Application action for computing diff between snapshots."""

from typing import TYPE_CHECKING, Protocol

from ...domain.snapshots.models import Snapshot
from ...utils import Log
from .result_models import Result


if TYPE_CHECKING:
    from ...domain.diff.models import DiffResult


__all__ = ["CreateDiffAction", "DiffEngineProtocol"]


class DiffEngineProtocol(Protocol):
    """Protocol for DiffEngine to enable duck-typing and dependency injection."""

    def compute_diff(self, old: Snapshot | None, new: Snapshot) -> "DiffResult": ...  # noqa: E704


class CreateDiffAction:
    """Compute diff between two snapshots using DiffEngine."""

    def __init__(self, diff_engine: DiffEngineProtocol) -> None:
        self._diff_engine = diff_engine

    def execute(self, old_snapshot: Snapshot | None, new_snapshot: Snapshot) -> Result:
        """Compute diff between two snapshots.

        Args:
            old_snapshot: The older snapshot to compare from (can be None for working tree).
            new_snapshot: The newer snapshot to compare to.

        Returns:
            Result containing DiffResult on success, or failure message on error.
        """
        try:
            diff_result = self._diff_engine.compute_diff(old_snapshot, new_snapshot)
            return Result.success(diff_result)
        except (RuntimeError, ValueError, TypeError, AttributeError, LookupError) as e:
            Log.exception(f"Failed to compute diff for '{new_snapshot.document_name}': {e}")
            return Result.failure(f"Failed to compute diff for '{new_snapshot.document_name}': {e}")
