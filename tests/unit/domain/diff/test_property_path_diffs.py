# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for path-level diff primitives (PropertyPathDiff,
# _flatten_data_path, _join_path, and value/expression state helpers).
"""Tests for path-level diff primitives in the domain diff models."""

import dataclasses

from freecad.diff_wb.domain.diff.models import (
    DiffState,
    PropertyPathDiff,
    _calc_expression_state,
    _calc_value_state,
    _flatten_data_path,
    _join_path,
    _path_expression,
    _path_values_equal,
)
from freecad.diff_wb.domain.tree.data_path import (
    ConstraintData,
    ListData,
    PlacementData,
    PrimitiveData,
    PropertyPathType,
    PropertyPathValue,
    QuantityData,
    RotationData,
    UnknownData,
    VectorData,
)


# ---------------------------------------------------------------------------
# _path_expression
# ---------------------------------------------------------------------------


class TestPathExpression:
    """Tests for _path_expression helper."""

    def test_returns_expression_from_value(self) -> None:
        pv = PropertyPathValue(PropertyPathType.FLOAT, 1.0, expression="Sketch.Constraints[0]")
        assert _path_expression(pv) == "Sketch.Constraints[0]"

    def test_returns_none_for_none_input(self) -> None:
        assert _path_expression(None) is None

    def test_returns_none_when_no_expression(self) -> None:
        pv = PropertyPathValue(PropertyPathType.INT, 42)
        assert _path_expression(pv) is None


# ---------------------------------------------------------------------------
# _calc_value_state
# ---------------------------------------------------------------------------


class TestCalcValueState:
    """Tests for _calc_value_state helper."""

    def test_both_none_unchanged(self) -> None:
        assert _calc_value_state(None, None) == DiffState.UNCHANGED

    def test_old_none_new_some_added(self) -> None:
        pv = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        assert _calc_value_state(None, pv) == DiffState.ADDED

    def test_old_some_new_none_deleted(self) -> None:
        pv = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        assert _calc_value_state(pv, None) == DiffState.DELETED

    def test_equal_values_unchanged(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.INT, 42)
        pv2 = PropertyPathValue(PropertyPathType.INT, 42)
        assert _calc_value_state(pv1, pv2) == DiffState.UNCHANGED

    def test_different_values_modified(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.INT, 42)
        pv2 = PropertyPathValue(PropertyPathType.INT, 43)
        assert _calc_value_state(pv1, pv2) == DiffState.MODIFIED

    def test_different_types_modified(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.INT, 42)
        pv2 = PropertyPathValue(PropertyPathType.STRING, "42")
        assert _calc_value_state(pv1, pv2) == DiffState.MODIFIED


# ---------------------------------------------------------------------------
# _calc_expression_state
# ---------------------------------------------------------------------------


class TestCalcExpressionState:
    """Tests for _calc_expression_state helper."""

    def test_both_none_unchanged(self) -> None:
        assert _calc_expression_state(None, None) == DiffState.UNCHANGED

    def test_old_none_new_some_added(self) -> None:
        assert _calc_expression_state(None, "Sketch.Constraints[0]") == DiffState.ADDED

    def test_old_some_new_none_deleted(self) -> None:
        assert _calc_expression_state("Sketch.Constraints[0]", None) == DiffState.DELETED

    def test_equal_expressions_unchanged(self) -> None:
        assert _calc_expression_state("a", "a") == DiffState.UNCHANGED

    def test_different_expressions_modified(self) -> None:
        assert _calc_expression_state("a", "b") == DiffState.MODIFIED


# ---------------------------------------------------------------------------
# _path_values_equal
# ---------------------------------------------------------------------------


class TestPathValuesEqual:
    """Tests for _path_values_equal helper."""

    def test_float_close_equal(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.0 + 1e-10)
        assert _path_values_equal(pv1, pv2) is True

    def test_float_far_different_not_equal(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 2.0)
        assert _path_values_equal(pv1, pv2) is False

    def test_float_at_tolerance_boundary(self) -> None:
        # Values exactly at 1e-9 apart should be equal
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 0.0)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1e-9)
        assert _path_values_equal(pv1, pv2) is True

    def test_int_equal(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.INT, 42)
        pv2 = PropertyPathValue(PropertyPathType.INT, 42)
        assert _path_values_equal(pv1, pv2) is True

    def test_int_not_equal(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.INT, 42)
        pv2 = PropertyPathValue(PropertyPathType.INT, 43)
        assert _path_values_equal(pv1, pv2) is False

    def test_string_equal(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.STRING, "hello")
        pv2 = PropertyPathValue(PropertyPathType.STRING, "hello")
        assert _path_values_equal(pv1, pv2) is True

    def test_string_not_equal(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.STRING, "hello")
        pv2 = PropertyPathValue(PropertyPathType.STRING, "world")
        assert _path_values_equal(pv1, pv2) is False

    def test_bool_equal(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.BOOL, True)
        pv2 = PropertyPathValue(PropertyPathType.BOOL, True)
        assert _path_values_equal(pv1, pv2) is True

    def test_null_equal(self) -> None:
        pv1 = PropertyPathValue(PropertyPathType.NULL, None)
        pv2 = PropertyPathValue(PropertyPathType.NULL, None)
        assert _path_values_equal(pv1, pv2) is True


# ---------------------------------------------------------------------------
# _join_path
# ---------------------------------------------------------------------------


class TestJoinPath:
    """Tests for _join_path helper."""

    def test_empty_prefix_dot(self) -> None:
        assert _join_path("", ".") == "."

    def test_prefix_dot(self) -> None:
        assert _join_path("[0]", ".") == "[0]"

    def test_no_prefix_rel(self) -> None:
        assert _join_path("", "x") == "x"

    def test_prefix_with_dotted_rel(self) -> None:
        assert _join_path("", "Base.x") == "Base.x"

    def test_prefix_dot_rel(self) -> None:
        assert _join_path("[0]", "Value") == "[0].Value"

    def test_prefix_bracket_rel(self) -> None:
        assert _join_path("Constraints", "[2]") == "Constraints[2]"

    def test_nested_bracket(self) -> None:
        assert _join_path("[0]", "[1]") == "[0][1]"


# ---------------------------------------------------------------------------
# _flatten_data_path
# ---------------------------------------------------------------------------


class TestFlattenDataPath:
    """Tests for _flatten_data_path across all DataPath types."""

    def test_primitive_data(self) -> None:
        pd = PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.FLOAT, 1.0)})
        result = _flatten_data_path(pd)
        assert result == {".": PropertyPathValue(PropertyPathType.FLOAT, 1.0)}

    def test_primitive_data_preserves_root_dot(self) -> None:
        """Flattening preserves root path "." (no empty-root fallback)."""
        pd = PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.STRING, "hello")})
        result = _flatten_data_path(pd)
        assert "." in result
        assert "" not in result

    def test_quantity_data_root_only(self) -> None:
        """QuantityData flattens to a single root '.' path with STRING value."""
        qd = QuantityData(
            paths={
                ".": PropertyPathValue(PropertyPathType.STRING, "10.0 mm"),
            }
        )
        result = _flatten_data_path(qd)
        assert list(result.keys()) == ["."]
        assert result["."].value == "10.0 mm"
        assert result["."].type_ == PropertyPathType.STRING

    def test_quantity_data_with_root_expression(self) -> None:
        """QuantityData with root expression stores expression on the same entry."""
        qd = QuantityData(
            paths={
                ".": PropertyPathValue(PropertyPathType.STRING, "10.0 mm", "Sketch.Length"),
            }
        )
        result = _flatten_data_path(qd)
        assert "." in result
        assert result["."].value == "10.0 mm"
        assert result["."].expression == "Sketch.Length"
        assert "Value" not in result
        assert "Unit" not in result

    def test_vector_data(self) -> None:
        vd = VectorData(
            paths={
                "x": PropertyPathValue(PropertyPathType.FLOAT, 1.0),
                "y": PropertyPathValue(PropertyPathType.FLOAT, 2.0),
                "z": PropertyPathValue(PropertyPathType.FLOAT, 3.0),
            }
        )
        result = _flatten_data_path(vd)
        assert "x" in result
        assert "y" in result
        assert "z" in result

    def test_vector_data_with_root(self) -> None:
        vd = VectorData(
            paths={
                ".": PropertyPathValue(PropertyPathType.NULL, None, "Sketch.Position"),
                "x": PropertyPathValue(PropertyPathType.FLOAT, 1.0),
                "y": PropertyPathValue(PropertyPathType.FLOAT, 2.0),
                "z": PropertyPathValue(PropertyPathType.FLOAT, 3.0),
            }
        )
        result = _flatten_data_path(vd)
        assert "." in result
        assert "x" in result

    def test_rotation_data(self) -> None:
        rd = RotationData(
            paths={
                "Angle": PropertyPathValue(PropertyPathType.FLOAT, 0.5),
                "Axis.x": PropertyPathValue(PropertyPathType.FLOAT, 0.0),
                "Axis.y": PropertyPathValue(PropertyPathType.FLOAT, 1.0),
                "Axis.z": PropertyPathValue(PropertyPathType.FLOAT, 0.0),
            }
        )
        result = _flatten_data_path(rd)
        assert "Angle" in result
        assert "Axis.x" in result
        assert "Axis.y" in result
        assert "Axis.z" in result

    def test_placement_data(self) -> None:
        pd = PlacementData(
            paths={
                "Base.x": PropertyPathValue(PropertyPathType.FLOAT, 0.0),
                "Base.y": PropertyPathValue(PropertyPathType.FLOAT, 0.0),
                "Base.z": PropertyPathValue(PropertyPathType.FLOAT, 0.0),
                "Rotation.Angle": PropertyPathValue(PropertyPathType.FLOAT, 0.0),
                "Rotation.Axis.x": PropertyPathValue(PropertyPathType.FLOAT, 0.0),
                "Rotation.Axis.y": PropertyPathValue(PropertyPathType.FLOAT, 1.0),
                "Rotation.Axis.z": PropertyPathValue(PropertyPathType.FLOAT, 0.0),
            }
        )
        result = _flatten_data_path(pd)
        assert "Base.x" in result
        assert "Base.y" in result
        assert "Base.z" in result
        assert "Rotation.Angle" in result

    def test_constraint_data(self) -> None:
        cd = ConstraintData(
            paths={
                "Type": PropertyPathValue(PropertyPathType.STRING, "Distance"),
                "Name": PropertyPathValue(PropertyPathType.STRING, "LengthConstraint"),
                "Value": PropertyPathValue(PropertyPathType.FLOAT, 1.0),
                "First": PropertyPathValue(PropertyPathType.INT, 1),
                "FirstPos": PropertyPathValue(PropertyPathType.INT, 1),
                "Second": PropertyPathValue(PropertyPathType.INT, 2),
                "SecondPos": PropertyPathValue(PropertyPathType.INT, 0),
                "Third": PropertyPathValue(PropertyPathType.INT, -2000),
                "ThirdPos": PropertyPathValue(PropertyPathType.INT, 0),
                "Driving": PropertyPathValue(PropertyPathType.BOOL, True),
                "IsActive": PropertyPathValue(PropertyPathType.BOOL, True),
            }
        )
        result = _flatten_data_path(cd)
        assert "Type" in result
        assert "Name" in result
        assert "Value" in result
        assert "First" in result
        assert "FirstPos" in result
        assert "Second" in result
        assert "SecondPos" in result
        assert "Third" in result
        assert "ThirdPos" in result
        assert "Driving" in result
        assert "IsActive" in result

    def test_unknown_data(self) -> None:
        ud = UnknownData(
            paths={
                ".": PropertyPathValue(
                    PropertyPathType.STRING,
                    "<Base.Vector>",
                    freecad_type="Base.Vector",
                ),
            }
        )
        result = _flatten_data_path(ud)
        assert "." in result
        assert result["."].value == "<Base.Vector>"
        assert result["."].freecad_type == "Base.Vector"

    def test_list_data_flat_paths(self) -> None:
        """ListData with root path entry flattens correctly."""
        ld = ListData(
            paths={
                ".": PropertyPathValue(PropertyPathType.NULL, None, "Sketch.Constraints"),
            },
            items=[],
        )
        result = _flatten_data_path(ld)
        assert "." in result
        assert result["."].expression == "Sketch.Constraints"

    def test_list_data_with_items(self) -> None:
        """ListData with items emits keys like '[0]', '[0].Value', '[1].Type'."""
        item0 = PrimitiveData(
            paths={
                ".": PropertyPathValue(PropertyPathType.INT, 42),
            }
        )
        item1 = PrimitiveData(
            paths={
                ".": PropertyPathValue(PropertyPathType.INT, 99),
            }
        )
        ld = ListData(paths={}, items=[item0, item1])
        result = _flatten_data_path(ld)
        assert "[0]" in result
        assert "[1]" in result
        assert result["[0]"].value == 42
        assert result["[1]"].value == 99

    def test_list_data_nested_item_values(self) -> None:
        """ListData items with sub-paths emit nested keys."""
        # Item 0 is a PrimitiveData
        item0 = PrimitiveData(
            paths={
                ".": PropertyPathValue(PropertyPathType.INT, 42),
            }
        )
        # Item 1 is a ConstraintData with Type, Value, etc.
        item1 = ConstraintData(
            paths={
                "Type": PropertyPathValue(PropertyPathType.INT, 0),
                "Value": PropertyPathValue(PropertyPathType.FLOAT, 1.0),
            }
        )
        ld = ListData(paths={}, items=[item0, item1])
        result = _flatten_data_path(ld)
        assert "[0]" in result
        assert "[1].Type" in result
        assert "[1].Value" in result
        assert result["[1].Type"].value == 0
        assert result["[1].Value"].value == 1.0

    def test_list_data_with_root_and_items(self) -> None:
        """ListData with both root path and items produces all keys."""
        item0 = PrimitiveData(
            paths={
                ".": PropertyPathValue(PropertyPathType.INT, 42),
            }
        )
        ld = ListData(
            paths={
                ".": PropertyPathValue(PropertyPathType.NULL, None, "ListRoot"),
            },
            items=[item0],
        )
        result = _flatten_data_path(ld)
        assert "." in result
        assert "[0]" in result
        assert result["."].expression == "ListRoot"
        assert result["[0]"].value == 42


# ---------------------------------------------------------------------------
# PropertyPathDiff
# ---------------------------------------------------------------------------


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

    def test_float_tolerance_in_value_state(self) -> None:
        """Float values within tolerance produce UNCHANGED value_state."""
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
        # This tests that unchanged paths are present (not filtered out).
        pv = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        diff = PropertyPathDiff(path="Base.x", old_value=pv, new_value=pv)
        assert diff.path == "Base.x"
        assert diff.value_state == DiffState.UNCHANGED
        # The path exists in the diff even though it's unchanged.

    def test_frozen_dataclass(self) -> None:
        """PropertyPathDiff is a frozen dataclass."""
        pv = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        diff = PropertyPathDiff(path=".", old_value=pv, new_value=pv)
        try:
            diff.path = "x"  # type: ignore[assignment]
            raise AssertionError("Should not be able to modify frozen dataclass")
        except dataclasses.FrozenInstanceError:
            pass  # Expected
