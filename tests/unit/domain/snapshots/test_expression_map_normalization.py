# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for expression path normalization and expression map
# building functions used by the gui_extractor to parse FreeCAD ExpressionEngine entries.
"""Tests for expression path normalization and expression map building."""

from freecad.history_wb.domain.snapshots.gui_extractor import (
    _build_expression_map_for_property,
    _normalize_expression_path_for_property,
)


class TestNormalizeExpressionPathForProperty:
    """Tests for _normalize_expression_path_for_property function."""

    def test_dot_length_normalizes_to_root(self) -> None:
        """'.Length' with prop_name='Length' normalizes to '.'."""
        result = _normalize_expression_path_for_property("Length", ".Length")
        assert result == "."

    def test_undot_length_normalizes_to_root(self) -> None:
        """'Length' with prop_name='Length' normalizes to '.'."""
        result = _normalize_expression_path_for_property("Length", "Length")
        assert result == "."

    def test_dot_placement_base_x_normalizes_to_base_x(self) -> None:
        """.Placement.Base.x with prop_name='Placement' normalizes to 'Base.x'."""
        result = _normalize_expression_path_for_property("Placement", ".Placement.Base.x")
        assert result == "Base.x"

    def test_undot_placement_base_x_normalizes_to_base_x(self) -> None:
        """'Placement.Base.x' with prop_name='Placement' normalizes to 'Base.x'."""
        result = _normalize_expression_path_for_property("Placement", "Placement.Base.x")
        assert result == "Base.x"

    def test_dot_constraints_bracket_normalizes_to_bracket_key(self) -> None:
        """.Constraints[0] with prop_name='Constraints' normalizes to '[0]'."""
        result = _normalize_expression_path_for_property("Constraints", ".Constraints[0]")
        assert result == "[0]"

    def test_undot_constraints_bracket_normalizes_to_bracket_key(self) -> None:
        """'Constraints[0]' with prop_name='Constraints' normalizes to '[0]'."""
        result = _normalize_expression_path_for_property("Constraints", "Constraints[0]")
        assert result == "[0]"

    def test_dot_constraints_named_normalizes_to_name(self) -> None:
        """.Constraints.MyConstr with prop_name='Constraints' normalizes to 'MyConstr'."""
        result = _normalize_expression_path_for_property("Constraints", ".Constraints.MyConstr")
        assert result == "MyConstr"

    def test_undot_constraints_named_normalizes_to_name(self) -> None:
        """'Constraints.MyConstr' with prop_name='Constraints' normalizes to 'MyConstr'."""
        result = _normalize_expression_path_for_property("Constraints", "Constraints.MyConstr")
        assert result == "MyConstr"

    def test_unrelated_property_returns_none(self) -> None:
        """.Height with prop_name='Length' returns None."""
        result = _normalize_expression_path_for_property("Length", ".Height")
        assert result is None

    def test_unrelated_undot_property_returns_none(self) -> None:
        """'Height' with prop_name='Length' returns None."""
        result = _normalize_expression_path_for_property("Length", "Height")
        assert result is None

    def test_partial_prefix_match_returns_none(self) -> None:
        """'.Lengths' with prop_name='Length' returns None (partial prefix)."""
        result = _normalize_expression_path_for_property("Length", ".Lengths")
        assert result is None

    def test_placement_with_rotation_angle(self) -> None:
        """.Placement.Rotation.Angle with prop_name='Placement' normalizes to 'Rotation.Angle'."""
        result = _normalize_expression_path_for_property("Placement", ".Placement.Rotation.Angle")
        assert result == "Rotation.Angle"


class TestBuildExpressionMapForProperty:
    """Tests for _build_expression_map_for_property function."""

    def test_length_expression_builds_root_map(self) -> None:
        """ExpressionEngine [['Length', '10 mm']] builds expr_map with '.' key."""
        expr_engine = [["Length", "10 mm"]]
        result = _build_expression_map_for_property("Length", expr_engine)
        assert result == {".": "10 mm"}

    def test_dot_length_expression_builds_root_map(self) -> None:
        """.Length expression in ExpressionEngine builds expr_map with '.' key."""
        expr_engine = [[".Length", "Sketch.Length * 2"]]
        result = _build_expression_map_for_property("Length", expr_engine)
        assert result == {".": "Sketch.Length * 2"}

    def test_placement_nested_expressions(self) -> None:
        """Multiple Placement sub-path expressions build correct normalized map."""
        expr_engine = [
            [".Placement.Base.x", "10 mm"],
            [".Placement.Base.y", "20 mm"],
            [".Placement.Rotation.Angle", "45.0"],
        ]
        result = _build_expression_map_for_property("Placement", expr_engine)
        assert result == {
            "Base.x": "10 mm",
            "Base.y": "20 mm",
            "Rotation.Angle": "45.0",
        }

    def test_constraints_bracket_expressions(self) -> None:
        """Constraint bracket expressions build correct normalized map."""
        expr_engine = [
            [".Constraints[0]", "5 mm"],
            [".Constraints[1]", "10 mm"],
        ]
        result = _build_expression_map_for_property("Constraints", expr_engine)
        assert result == {"[0]": "5 mm", "[1]": "10 mm"}

    def test_constraints_named_expressions(self) -> None:
        """Constraint named expressions build correct normalized map."""
        expr_engine = [
            [".Constraints.MyConstr", "DistanceX"],
        ]
        result = _build_expression_map_for_property("Constraints", expr_engine)
        assert result == {"MyConstr": "DistanceX"}

    def test_duplicate_resolution_dotted_wins(self) -> None:
        """When both dotted and undotted forms exist, dotted form wins."""
        expr_engine = [
            ["Length", "undotted_expr"],
            [".Length", "dotted_expr"],
        ]
        result = _build_expression_map_for_property("Length", expr_engine)
        assert result == {".": "dotted_expr"}

    def test_duplicate_resolution_undotted_first_dotted_later_wins(self) -> None:
        """When undotted comes first and dotted comes later, dotted wins."""
        expr_engine = [
            [".Length", "dotted_expr"],
            ["Length", "undotted_expr"],
        ]
        result = _build_expression_map_for_property("Length", expr_engine)
        # dotted form should win because it starts with '.'
        assert result == {".": "dotted_expr"}

    def test_empty_expression_engine_returns_empty_dict(self) -> None:
        """Empty ExpressionEngine list returns empty dict."""
        result = _build_expression_map_for_property("Length", [])
        assert result == {}

    def test_non_list_expression_engine_returns_empty_dict(self) -> None:
        """Non-list ExpressionEngine (e.g., None) returns empty dict."""
        result = _build_expression_map_for_property("Length", None)
        assert result == {}

    def test_invalid_entries_are_skipped(self) -> None:
        """Invalid entries (too short, wrong type) are skipped."""
        expr_engine = [
            ["Length", "valid"],
            ["only_one_entry"],  # Too short
            "not_a_list",  # Not a list/tuple
            [],  # Empty list
            [""],  # Single element
        ]
        result = _build_expression_map_for_property("Length", expr_engine)
        assert result == {".": "valid"}

    def test_unrelated_expressions_filtered_out(self) -> None:
        """Expressions for unrelated properties are excluded from the map."""
        expr_engine = [
            ["Length", "10 mm"],
            ["Width", "20 mm"],
            [".Placement.Base.x", "1.0"],
        ]
        result = _build_expression_map_for_property("Length", expr_engine)
        assert result == {".": "10 mm"}
        assert "Width" not in result
        assert "Base.x" not in result

    def test_mixed_dotted_undot_same_property(self) -> None:
        """Mixed dotted and undotted forms for same property resolve deterministically."""
        expr_engine = [
            ["Length", "first"],
            [".Length", "second"],
        ]
        result = _build_expression_map_for_property("Length", expr_engine)
        assert result == {".": "second"}

    def test_multiple_properties_in_engine(self) -> None:
        """ExpressionEngine with entries for multiple properties filters correctly."""
        expr_engine = [
            ["Length", "10 mm"],
            [".Width", "20 mm"],
            ["Height", "30 mm"],
        ]
        length_result = _build_expression_map_for_property("Length", expr_engine)
        width_result = _build_expression_map_for_property("Width", expr_engine)
        height_result = _build_expression_map_for_property("Height", expr_engine)

        assert length_result == {".": "10 mm"}
        assert width_result == {".": "20 mm"}
        assert height_result == {".": "30 mm"}
