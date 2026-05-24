# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the DiffEngine class that orchestrates
# diff computation between two snapshots. It coordinates between TreeComparator
# and PropertyComparator, applies filtering based on excluded types and properties,
# and produces a complete DiffResult.
#
# The engine uses dependency injection for SettingsRepository to determine
# configuration at runtime.
"""Diff computation engine."""

from typing import Protocol

from ...utils import Log
from ..config import EXCLUDED_PROPERTIES, EXCLUDED_PROPERTIES_BY_TYPE, EXCLUDED_TYPES, FLOAT_PRECISION
from ..settings import SettingsRepository
from ..snapshots import Snapshot
from .comparator import TreeComparator
from .models import DiffResult


class TreeComparatorProtocol(Protocol):
    """Protocol for TreeComparator to enable dependency injection."""

    def compare_snapshots(
        self,
        old_snapshot: Snapshot,
        new_snapshot: Snapshot,
        excluded_properties: list[str],
        excluded_types: list[str],
        excluded_properties_by_type: dict[str, list[str]] | None = None,
        precision: int = 2,
    ) -> DiffResult: ...


class DiffEngine:
    """Orchestrates diff computation between two snapshots.

    This class coordinates the tree comparison and property comparison
    processes, applying user-configured filters for excluded types and
    properties.

    The engine uses dependency injection for SettingsRepository and
    TreeComparator, allowing different implementations and easy mocking.

    Attributes:
        _settings_repo: Settings repository for accessing configuration
        _tree_comparator: Tree comparator instance for tree comparison
    """

    def __init__(
        self,
        settings_repo: SettingsRepository | None = None,
        tree_comparator: TreeComparatorProtocol | None = None,
    ) -> None:
        """Initialize the diff engine.

        Args:
            settings_repo: Settings repository for accessing configuration.
                If None, uses default values from config.py.
            tree_comparator: Tree comparator instance. If None, creates
                a default TreeComparator instance.
        """
        self._settings_repo = settings_repo
        self._tree_comparator = tree_comparator or TreeComparator()

    def _get_excluded_node_types(self) -> list[str]:
        """Get list of excluded type IDs.

        Returns:
            List of type IDs to exclude, using settings repo if available
        """
        if self._settings_repo is not None:
            return self._settings_repo.get_excluded_types()
        return EXCLUDED_TYPES

    def _get_excluded_properties(self) -> list[str]:
        """Get list of excluded property names.

        Returns:
            List of property names to exclude, using settings repo if available
        """
        if self._settings_repo is not None:
            return self._settings_repo.get_excluded_properties()
        return EXCLUDED_PROPERTIES

    def _get_excluded_properties_by_type(self) -> dict[str, list[str]]:
        """Get type-specific property exclusions.

        Returns:
            Dict mapping type IDs to lists of excluded property names,
            using settings repo if available
        """
        if self._settings_repo is not None:
            return self._settings_repo.get_excluded_properties_by_type()
        return dict(EXCLUDED_PROPERTIES_BY_TYPE)

    def _get_float_precision(self) -> int:
        """Get float precision for comparison.

        Returns:
            Number of decimal places for float comparison, using settings repo if available
        """
        if self._settings_repo is not None:
            return self._settings_repo.get_float_precision()
        return FLOAT_PRECISION

    # Excluded types filtering is handled in TreeComparator during diff building

    def compute_diff(self, old: Snapshot | None, new: Snapshot) -> DiffResult:
        """Compute diff between two snapshots.

        Steps:
        1. Handle None case (compare snapshot against itself)
        2. Get settings (excluded types/properties/type-specific)
        3. Compare trees using TreeComparator (includes type filtering)
        4. Apply property-level exclusions (including type-specific)
        5. Return DiffResult

        Args:
            old: The old snapshot to compare (can be None)
            new: The new snapshot to compare

        Returns:
            DiffResult containing all differences between the snapshots
        """
        # Handle None case: use same snapshot for both
        # This triggers the "same snapshot" warning in DiffResult.__post_init__
        if old is None:
            Log.info(
                f"No previous snapshot provided for '{new.document_name}'. "
                "Comparing snapshot against itself - this will show no changes."
            )
            old = new

        # Step 1: Get settings
        excluded_node_types = self._get_excluded_node_types()
        excluded_properties = self._get_excluded_properties()
        excluded_properties_by_type = self._get_excluded_properties_by_type()
        precision = self._get_float_precision()

        # Step 2: Compare trees using TreeComparator (filters excluded types internally)
        result = self._tree_comparator.compare_snapshots(
            old, new, excluded_properties, excluded_node_types, excluded_properties_by_type, precision
        )

        return result


__all__ = ["DiffEngine"]
