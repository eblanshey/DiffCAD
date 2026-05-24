# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for float precision propagation from settings through
# diff computation. Verifies that runtime precision settings affect float equality
# comparisons consistently across the comparison stack.
"""Tests for float precision propagation from settings."""

from unittest.mock import MagicMock

from freecad.history_wb.domain.config import FLOAT_PRECISION as DEFAULT_FLOAT_PRECISION
from freecad.history_wb.domain.diff.engine import DiffEngine
from freecad.history_wb.domain.diff.models import (
    DiffState,
    PropertyDiff,
    _path_values_equal,
)
from freecad.history_wb.domain.snapshots import Snapshot
from freecad.history_wb.domain.snapshots.models import SnapshotObject, SnapshotOccurrence
from freecad.history_wb.domain.tree.data_path import (
    PrimitiveData,
    PropertyPathType,
    PropertyPathValue,
)
from freecad.history_wb.domain.tree.property import Property


class TestPrecisionBoundary:
    """Tests for default precision boundary behavior."""

    def test_default_precision_boundary(self) -> None:
        """Values rounding to same at default precision are equal."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.567)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.569)
        assert _path_values_equal(pv1, pv2, precision=DEFAULT_FLOAT_PRECISION) is True

    def test_custom_precision_changes_result(self) -> None:
        """Higher precision makes previously equal values differ."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.567)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.569)
        # Precision 2: both round to 1.57
        assert _path_values_equal(pv1, pv2, precision=2) is True
        # Precision 3: 1.567 vs 1.569 differ
        assert _path_values_equal(pv1, pv2, precision=3) is False

    def test_precision_propagates_through_property_diff(self) -> None:
        """PropertyDiff state reflects precision parameter."""
        old_prop = Property(
            value=PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.FLOAT, 1.567)}), group="Test"
        )
        new_prop = Property(
            value=PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.FLOAT, 1.569)}), group="Test"
        )
        diff_at_2 = PropertyDiff(property_name="TestProp", old_value=old_prop, new_value=new_prop, precision=2)
        assert diff_at_2.state == DiffState.UNCHANGED

        diff_at_3 = PropertyDiff(property_name="TestProp", old_value=old_prop, new_value=new_prop, precision=3)
        assert diff_at_3.state == DiffState.MODIFIED


class TestPrecisionInDiffEngine:
    """Tests for precision propagation through DiffEngine."""

    def _make_snapshot(self, snapshot_id: str, float_val: float) -> Snapshot:
        return Snapshot(
            snapshot_id=snapshot_id,
            document_name="Test",
            timestamp=__import__("datetime").datetime.now(),
            objects=[
                SnapshotObject(
                    name="TestNode",
                    id=1,
                    type_id="Part::Feature",
                    properties={
                        "Value": Property(
                            value=PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.FLOAT, float_val)}),
                            group="Test",
                        )
                    },
                )
            ],
            occurrences=[SnapshotOccurrence(path="TestNode", after=None)],
        )

    def test_diff_engine_uses_settings_repo_precision(self) -> None:
        """DiffEngine.compute_diff() respects precision from settings repo."""
        settings_low = MagicMock()
        settings_low.get_excluded_types.return_value = []
        settings_low.get_excluded_properties.return_value = []
        settings_low.get_excluded_properties_by_type.return_value = {}
        settings_low.get_float_precision.return_value = 2

        settings_high = MagicMock()
        settings_high.get_excluded_types.return_value = []
        settings_high.get_excluded_properties.return_value = []
        settings_high.get_excluded_properties_by_type.return_value = {}
        settings_high.get_float_precision.return_value = 3

        old_snap = self._make_snapshot("old", 1.567)
        new_snap = self._make_snapshot("new", 1.569)

        engine_low = DiffEngine(settings_repo=settings_low)
        result_low = engine_low.compute_diff(old_snap, new_snap)
        assert result_low.hierarchy.roots[0].state == DiffState.UNCHANGED

        engine_high = DiffEngine(settings_repo=settings_high)
        result_high = engine_high.compute_diff(old_snap, new_snap)
        assert result_high.hierarchy.roots[0].state == DiffState.MODIFIED
