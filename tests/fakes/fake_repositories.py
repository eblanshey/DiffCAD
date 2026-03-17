# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Fake repository implementations for testing that provide in-memory
# and hardcoded value implementations of SnapshotRepository and SettingsRepository.
"""Fake repository implementations for testing."""

from freecad.diff_wb.domain.settings.repository import SettingsRepository
from freecad.diff_wb.domain.snapshots.repository import (
    InMemorySnapshotRepository,
    SnapshotRepository,
)


class FakeSnapshotRepository(SnapshotRepository):
    """In-memory snapshot repository for testing.

    This is an alias for InMemorySnapshotRepository which provides
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


__all__ = ["FakeSnapshotRepository", "FakeSettingsRepository", "InMemorySnapshotRepository"]
