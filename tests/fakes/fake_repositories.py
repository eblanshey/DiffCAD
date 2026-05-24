# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Fake repository implementations for testing that provide in-memory
# and hardcoded value implementations of SnapshotRepository and SettingsRepository.
"""Fake repository implementations for testing."""

import datetime

from freecad.history_wb.domain.diff.engine import DiffEngine
from freecad.history_wb.domain.diff.models import DiffHierarchy, DiffResult
from freecad.history_wb.domain.settings.models import Settings
from freecad.history_wb.domain.settings.repository import SettingsRepository
from freecad.history_wb.domain.snapshots import Snapshot
from freecad.history_wb.domain.snapshots.models import SnapshotObject, SnapshotOccurrence
from freecad.history_wb.domain.snapshots.repository import (
    InMemorySnapshotRepository,
    SnapshotRepository,
)


def snapshot_from_rows(
    *,
    snapshot_id: str,
    document_name: str,
    timestamp: datetime.datetime,
    tree: list | None = None,
    objects: list[SnapshotObject] | None = None,
    occurrences: list[SnapshotOccurrence] | None = None,
    git_path: str = "",
) -> Snapshot:
    """Build normalized Snapshot for fake fixtures."""
    if tree is not None:
        objects = [SnapshotObject(name=n.name, id=n.id, type_id=n.type_id, properties=n.properties) for n in tree]
        occurrences = [SnapshotOccurrence(path=n.path, after=n.after) for n in tree]
    return Snapshot(
        snapshot_id=snapshot_id,
        document_name=document_name,
        timestamp=timestamp,
        objects=objects or [],
        occurrences=occurrences or [],
        git_path=git_path,
    )


class FakeSnapshotRepository(InMemorySnapshotRepository, SnapshotRepository):
    """In-memory snapshot repository for testing.

    This extends InMemorySnapshotRepository which provides
    a simple in-memory implementation suitable for unit tests.
    """

    pass


class FakeSettingsRepository(SettingsRepository):
    """Settings repository with hardcoded values for testing.

    Provides fixed excluded types and properties for predictable test behavior.
    """

    def __init__(
        self,
        excluded_types: list[str] | None = None,
        excluded_properties: list[str] | None = None,
        excluded_properties_by_type: dict[str, list[str]] | None = None,
    ):
        """Initialize with optional custom excluded lists.

        Args:
            excluded_types: List of type IDs to exclude (default: ["App::Origin"])
            excluded_properties: List of property names to exclude (default: ["TimeStamp", "Label2"])
            excluded_properties_by_type: Dict mapping type IDs to property names to exclude
                for that type only (default: empty dict)
        """
        self._excluded_types = excluded_types or ["App::Origin"]
        self._excluded_properties = excluded_properties or ["TimeStamp", "Label2"]
        self._excluded_properties_by_type = excluded_properties_by_type or {}

    def get_excluded_types(self) -> list[str]:
        """Get the configured excluded type IDs."""
        return self._excluded_types.copy()

    def get_excluded_properties(self) -> list[str]:
        """Get the configured excluded property names."""
        return self._excluded_properties.copy()

    def get_excluded_properties_by_type(self) -> dict[str, list[str]]:
        """Get the configured type-specific property exclusions."""
        return dict(self._excluded_properties_by_type)

    def get_float_precision(self) -> int:
        """Get the configured float precision."""
        return 2

    def get_settings(self) -> Settings:
        """Get all settings as a Settings object."""
        return Settings(
            excluded_types=self._excluded_types.copy(),
            excluded_properties=self._excluded_properties.copy(),
            excluded_properties_by_type=self.get_excluded_properties_by_type(),
        )


class FakeDiffEngine(DiffEngine):
    """Fake DiffEngine for testing that captures calls and returns controlled results.

    This fake allows tests to verify that diff computation was called correctly
    and to control the returned result without executing actual comparison logic.
    """

    def __init__(self, return_value: DiffResult | None = None, side_effect: Exception | None = None):
        """Initialize the fake diff engine.

        Args:
            return_value: The DiffResult to return on compute_diff() call. If None, returns empty result.
            side_effect: Optional exception to raise instead of returning a result.
        """
        # Create default snapshots for the fake result
        default_old_snapshot = snapshot_from_rows(
            snapshot_id="fake-old-id",
            document_name="Comparison",
            timestamp=datetime.datetime.now(),
            tree=[],
        )
        default_new_snapshot = snapshot_from_rows(
            snapshot_id="fake-new-id",
            document_name="Comparison",
            timestamp=datetime.datetime.now(),
            tree=[],
        )
        self._return_value = return_value or DiffResult(
            old_snapshot=default_old_snapshot,
            new_snapshot=default_new_snapshot,
            hierarchy=DiffHierarchy(),
        )
        self._side_effect = side_effect
        self._compute_diff_calls: list[tuple[Snapshot | None, Snapshot]] = []

    def compute_diff(self, old: Snapshot | None, new: Snapshot) -> DiffResult:
        """Record the call and return the configured result.

        Args:
            old: Snapshot from the older version (can be None)
            new: Snapshot from the newer version

        Returns:
            Configured DiffResult

        Raises:
            Exception: If side_effect is set
        """
        # Record the call for verification
        self._compute_diff_calls.append((old, new))

        if self._side_effect is not None:
            raise self._side_effect

        return self._return_value

    @property
    def compute_diff_calls(self) -> list[tuple[Snapshot | None, Snapshot]]:
        """Get all recorded compute_diff() calls."""
        return self._compute_diff_calls.copy()

    def reset(self) -> None:
        """Reset the fake to initial state."""
        self._compute_diff_calls.clear()


__all__ = ["FakeSnapshotRepository", "FakeSettingsRepository", "InMemorySnapshotRepository", "FakeDiffEngine"]
