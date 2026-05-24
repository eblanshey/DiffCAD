# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for PropertyPathDiff public behavior including
# value/expression state calculation and precision-aware float comparison.
"""Tests for PropertyPathDiff public behavior."""

from freecad.history_wb.domain.diff.models import DiffState, PropertyPathDiff
from freecad.history_wb.domain.tree.data_path import PropertyPathType, PropertyPathValue


class TestPropertyPathDiff:
    """Tests for PropertyPathDiff dataclass."""

    def test_unchanged_path(self) -> None:
        pv = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        diff = PropertyPathDiff(path=".", old_value=pv, new_value=pv)
        assert diff.value_state == DiffState.UNCHANGED
        assert diff.expression_state == DiffState.UNCHANGED

    def test_added_path(self) -> None:
        pv = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        diff = PropertyPathDiff(path="x", old_value=None, new_value=pv)
        assert diff.value_state == DiffState.ADDED

    def test_deleted_path(self) -> None:
        pv = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        diff = PropertyPathDiff(path="x", old_value=pv, new_value=None)
        assert diff.value_state == DiffState.DELETED

    def test_modified_path(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 2.0)
        diff = PropertyPathDiff(path="x", old_value=pv1, new_value=pv2)
        assert diff.value_state == DiffState.MODIFIED

    def test_float_precision_in_value_state(self) -> None:
        """Float values that round to the same value produce UNCHANGED value_state."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.0 + 1e-10)
        diff = PropertyPathDiff(path="x", old_value=pv1, new_value=pv2)
        assert diff.value_state == DiffState.UNCHANGED

    def test_expression_state_independent_of_value_state(self) -> None:
        """Expression state is computed independently of value state.

        Two values can be numerically equal but have different expressions,
        resulting in UNCHANGED value_state but MODIFIED expression_state.
        """
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.0, expression="A")
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.0, expression="B")
        diff = PropertyPathDiff(path="x", old_value=pv1, new_value=pv2)
        assert diff.value_state == DiffState.UNCHANGED
        assert diff.expression_state == DiffState.MODIFIED

    def test_value_changed_expression_unchanged(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.0, expression="A")
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 2.0, expression="A")
        diff = PropertyPathDiff(path="x", old_value=pv1, new_value=pv2)
        assert diff.value_state == DiffState.MODIFIED
        assert diff.expression_state == DiffState.UNCHANGED

    def test_expression_added_when_value_unchanged(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.0, expression="Sketch.Constraints[0]")
        diff = PropertyPathDiff(path="x", old_value=pv1, new_value=pv2)
        assert diff.value_state == DiffState.UNCHANGED
        assert diff.expression_state == DiffState.ADDED

    def test_all_paths_included_unchanged(self) -> None:
        """All paths are included in path_diffs, even unchanged ones."""
        pv = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        diff = PropertyPathDiff(path="Base.x", old_value=pv, new_value=pv)
        assert diff.path == "Base.x"
        assert diff.value_state == DiffState.UNCHANGED

    def test_precision_param_affects_value_state(self) -> None:
        """Precision parameter controls float equality threshold."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.567)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.569)
        # Precision 2: both round to 1.57 -> UNCHANGED
        diff_2 = PropertyPathDiff(path="x", old_value=pv1, new_value=pv2, precision=2)
        assert diff_2.value_state == DiffState.UNCHANGED
        # Precision 3: 1.567 vs 1.569 -> MODIFIED
        diff_3 = PropertyPathDiff(path="x", old_value=pv1, new_value=pv2, precision=3)
        assert diff_3.value_state == DiffState.MODIFIED
