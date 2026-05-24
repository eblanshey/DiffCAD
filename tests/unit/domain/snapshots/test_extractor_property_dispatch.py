# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for _extract_property_value function verifying it uses
# the new Property.from_freecad API with expression maps instead of the legacy API.
"""Tests for extractor property dispatch using new Property.from_freecad API."""

from freecad.history_wb.domain.snapshots.gui_extractor import (
    _build_expression_map_for_property,
    _extract_property_value,
)
from freecad.history_wb.domain.tree import Property


class MockFreeCADObject:
    """Mock FreeCAD object for testing property extraction."""

    def __init__(self, properties_values=None, expression_engine=None, property_groups=None):
        """Initialize mock FreeCAD object.

        Args:
            properties_values: Dict mapping property names to their values
            expression_engine: List of [prop_name, expression] pairs
            property_groups: Dict mapping property names to group names
        """
        self._properties_values = properties_values or {}
        self._expression_engine = expression_engine or []
        self._property_groups = property_groups or {}

    def __getattr__(self, name):
        if name in self._properties_values:
            return self._properties_values[name]
        if name == "ExpressionEngine":
            return self._expression_engine
        if name == "PropertiesList":
            return list(self._properties_values.keys())
        raise AttributeError(name)

    def getGroupOfProperty(self, prop_name):
        return self._property_groups.get(prop_name, "")


class TestExtractPropertyValue:
    """Tests for _extract_property_value function with new Property.from_freecad API."""

    def test_primitive_value_wrapped_in_primitive_data(self) -> None:
        """Integer property value is wrapped in PrimitiveData via Property.from_freecad."""
        obj = MockFreeCADObject(properties_values={"Length": 10})
        prop = _extract_property_value(obj, "Length")

        assert prop is not None
        assert isinstance(prop, Property)
        assert prop.value.DATA_PATH_KIND.value == "Primitive"

    def test_float_value_wrapped_in_primitive_data(self) -> None:
        """Float property value is wrapped in PrimitiveData."""
        obj = MockFreeCADObject(properties_values={"Angle": 45.5})
        prop = _extract_property_value(obj, "Angle")

        assert prop is not None
        assert isinstance(prop, Property)
        assert prop.value.DATA_PATH_KIND.value == "Primitive"

    def test_string_value_wrapped_in_primitive_data(self) -> None:
        """String property value is wrapped in PrimitiveData."""
        obj = MockFreeCADObject(properties_values={"Label": "Test Label"})
        prop = _extract_property_value(obj, "Label")

        assert prop is not None
        assert isinstance(prop, Property)
        assert prop.value.DATA_PATH_KIND.value == "Primitive"

    def test_boolean_value_wrapped_in_primitive_data(self) -> None:
        """Boolean property value is wrapped in PrimitiveData."""
        obj = MockFreeCADObject(properties_values={"Visibility": True})
        prop = _extract_property_value(obj, "Visibility")

        assert prop is not None
        assert isinstance(prop, Property)
        assert prop.value.DATA_PATH_KIND.value == "Primitive"

    def test_none_value_wrapped_in_primitive_data(self) -> None:
        """None property value is wrapped in PrimitiveData."""
        obj = MockFreeCADObject(properties_values={"OptionalProp": None})
        prop = _extract_property_value(obj, "OptionalProp")

        assert prop is not None
        assert isinstance(prop, Property)
        assert prop.value.DATA_PATH_KIND.value == "Primitive"

    def test_expression_map_passed_through(self) -> None:
        """Expression map from ExpressionEngine is properly passed through to Property."""
        expr_engine = [["Length", "Sketch.Length * 2"]]
        obj = MockFreeCADObject(
            properties_values={"Length": 10.0},
            expression_engine=expr_engine,
            property_groups={"Length": "Side1"},
        )
        prop = _extract_property_value(obj, "Length")

        assert prop is not None
        assert isinstance(prop, Property)
        # The PrimitiveData should have the expression at the '.' key
        assert "." in prop.value.paths
        assert prop.value.paths["."].expression == "Sketch.Length * 2"

    def test_property_group_is_set(self) -> None:
        """Property group is correctly set from getGroupOfProperty()."""
        obj = MockFreeCADObject(
            properties_values={"Length": 10},
            property_groups={"Length": "Side1"},
        )
        prop = _extract_property_value(obj, "Length")

        assert prop is not None
        assert prop.group == "Side1"

    def test_property_group_defaults_to_base(self) -> None:
        """Property group defaults to 'Base' when getGroupOfProperty returns empty string."""
        obj = MockFreeCADObject(
            properties_values={"Length": 10},
            property_groups={"Length": ""},
        )
        prop = _extract_property_value(obj, "Length")

        assert prop is not None
        assert prop.group == "Base"

    def test_expression_map_with_nested_paths(self) -> None:
        """Nested expression paths are correctly normalized and passed through."""
        expr_engine = [
            [".Placement.Base.x", "10 mm"],
            [".Placement.Base.y", "20 mm"],
        ]
        # Mock a Placement-like object (unknown type, so goes to UnknownData)
        mock_placement = MockFreeCADObject(
            properties_values={"Base": type("MockBase", (), {"x": 10.0, "y": 20.0, "z": 0.0})()}
        )
        obj = MockFreeCADObject(
            properties_values={"Placement": mock_placement},
            expression_engine=expr_engine,
            property_groups={"Placement": "Base"},
        )
        prop = _extract_property_value(obj, "Placement")

        assert prop is not None
        assert isinstance(prop, Property)
        # The expr_map is built correctly (Base.x, Base.y keys exist)
        # and is passed to Property.from_freecad. The dispatch depends on
        # the runtime type key of the value, which for a mock is UnknownData.
        # We verify the expr_map was built correctly by checking the function directly.
        expr_map = _build_expression_map_for_property("Placement", expr_engine)
        assert expr_map == {"Base.x": "10 mm", "Base.y": "20 mm"}

    def test_no_expression_engine_returns_empty_map(self) -> None:
        """When no expression engine exists, Property is created with empty expr_map."""
        obj = MockFreeCADObject(properties_values={"Length": 10})
        prop = _extract_property_value(obj, "Length")

        assert prop is not None
        assert isinstance(prop, Property)
        # No expression should be set
        assert prop.value.paths["."].expression is None

    def test_list_value_wrapped_in_list_data(self) -> None:
        """List property value is wrapped in ListData via Property.from_freecad."""
        obj = MockFreeCADObject(properties_values={"Constraints": [1, 2, 3]})
        prop = _extract_property_value(obj, "Constraints")

        assert prop is not None
        assert isinstance(prop, Property)
        assert prop.value.DATA_PATH_KIND.value == "List"
        assert len(prop.value.items) == 3

    def test_list_with_expression_map(self) -> None:
        """List items with expression map entries get proper item expressions."""
        expr_engine = [
            [".Constraints[0]", "5 mm"],
            [".Constraints[1]", "10 mm"],
        ]
        obj = MockFreeCADObject(
            properties_values={"Constraints": [1, 2]},
            expression_engine=expr_engine,
            property_groups={"Constraints": "Sketch"},
        )
        prop = _extract_property_value(obj, "Constraints")

        assert prop is not None
        assert isinstance(prop, Property)
        assert prop.value.DATA_PATH_KIND.value == "List"
        assert len(prop.value.items) == 2
        # Each item is a DataPath with paths dict; first item should have the expression
        assert prop.value.items[0].paths["."].expression == "5 mm"
        # Second item should have the expression
        assert prop.value.items[1].paths["."].expression == "10 mm"

    def test_build_expression_map_for_property_returns_correct_map(self) -> None:
        """_build_expression_map_for_property builds correct expr_map from ExpressionEngine."""
        expr_engine = [
            ["Length", "10 mm"],
            [".Width", "20 mm"],
        ]
        result = _build_expression_map_for_property("Length", expr_engine)
        assert result == {".": "10 mm"}

        width_result = _build_expression_map_for_property("Width", expr_engine)
        assert width_result == {".": "20 mm"}

    def test_property_from_freecad_api_signature(self) -> None:
        """Property.from_freecad accepts (fc_value, expr_map, group) signature."""
        fc_value = 10.0
        expr_map = {".": "10 mm"}
        group = "Side1"

        prop = Property.from_freecad(fc_value, expr_map, group)

        assert isinstance(prop, Property)
        assert prop.group == group
        assert prop.value.paths["."].expression == "10 mm"
