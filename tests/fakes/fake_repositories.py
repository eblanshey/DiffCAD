# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Fake repository implementations for testing that provide in-memory
# and hardcoded value implementations of SnapshotRepository and SettingsRepository.
"""Fake repository implementations for testing."""

from freecad.diff_wb.domain.diff.engine import DiffEngine
from freecad.diff_wb.domain.diff.models import DiffResult
from freecad.diff_wb.domain.settings.models import Settings
from freecad.diff_wb.domain.settings.repository import SettingsRepository
from freecad.diff_wb.domain.snapshots import Snapshot
from freecad.diff_wb.domain.snapshots.repository import (
    InMemorySnapshotRepository,
    SnapshotRepository,
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

    def __init__(self, excluded_types: list[str] | None = None, excluded_properties: list[str] | None = None):
        """Initialize with optional custom excluded lists.

        Args:
            excluded_types: List of type IDs to exclude (default: ["App::Origin"])
            excluded_properties: List of property names to exclude (default: ["TimeStamp", "Label2"])
        """
        self._excluded_types = excluded_types or ["App::Origin"]
        self._excluded_properties = excluded_properties or ["TimeStamp", "Label2"]

    def get_excluded_types(self) -> list[str]:
        """Get the configured excluded type IDs."""
        return self._excluded_types.copy()

    def get_excluded_properties(self) -> list[str]:
        """Get the configured excluded property names."""
        return self._excluded_properties.copy()

    def get_settings(self) -> Settings:
        """Get all settings as a Settings object."""
        return Settings(
            excluded_types=self._excluded_types.copy(),
            excluded_properties=self._excluded_properties.copy(),
        )


class FakeDiffEngine(DiffEngine):
    """Fake DiffEngine for testing that captures calls and returns controlled results.

    This fake allows tests to verify that diff computation was called correctly
    and to control the returned result without executing actual comparison logic.
    """

    def __init__(self, return_value: DiffResult | None = None, side_effect: Exception | None = None):
        """Initialize the fake diff engine.

        Args:
            return_value: The DiffResult to return on compare() call. If None, returns empty result.
            side_effect: Optional exception to raise instead of returning a result.
        """
        self._return_value = return_value or DiffResult(
            old_snapshot_name="Comparison",
            new_snapshot_name="Comparison",
            node_diffs=[],
        )
        self._side_effect = side_effect
        self._compare_calls: list[tuple[Snapshot, Snapshot, list[str], list[str]]] = []

    def compare(
        self,
        old_snapshot: Snapshot,
        new_snapshot: Snapshot,
        excluded_types: list[str],
        excluded_properties: list[str],
    ) -> DiffResult:
        """Record the call and return the configured result.

        Args:
            old_snapshot: Snapshot from the older version
            new_snapshot: Snapshot from the newer version
            excluded_types: List of type IDs to exclude from comparison
            excluded_properties: List of property names to exclude from comparison

        Returns:
            Configured DiffResult

        Raises:
            Exception: If side_effect is set
        """
        # Record the call for verification
        self._compare_calls.append((old_snapshot, new_snapshot, excluded_types, excluded_properties))

        if self._side_effect is not None:
            raise self._side_effect

        return self._return_value

    @property
    def compare_calls(self) -> list[tuple[Snapshot, Snapshot, list[str], list[str]]]:
        """Get all recorded compare() calls."""
        return self._compare_calls.copy()

    def reset(self) -> None:
        """Reset the fake to initial state."""
        self._compare_calls.clear()


__all__ = ["FakeSnapshotRepository", "FakeSettingsRepository", "InMemorySnapshotRepository", "FakeDiffEngine"]
