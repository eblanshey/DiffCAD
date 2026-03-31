"""File responsibility: Unit tests for property tree building and CamelCase conversion.

These tests verify:
- _camelcase_to_spaces() converts CamelCase names to space-separated names
- get_property_children() correctly expands different property types
- is_expandable() correctly identifies expandable values
- _expand_placement() expands Placement objects correctly
- _expand_rotation() expands Rotation objects correctly
- _expand_material() expands Material objects correctly
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from freecad.diff_wb.ui.views.property_tree import (
    _camelcase_to_spaces,
    _expand_material,
    _expand_placement,
    _expand_rotation,
    get_property_children,
    is_expandable,
)


# Mock classes for testing property expansion
@dataclass
class MockVector:
    """Mock Vector class with x, y, z attributes."""

    x: float
    y: float
    z: float


@dataclass
class MockRotation:
    """Mock Rotation class with Angle and Axis."""

    Angle: float
    Axis: Any = None


@dataclass
class MockPlacement:
    """Mock Placement class with Position, Rotation, Axis."""

    Position: Any = None
    Rotation: Any = None
    Axis: Any = None


class TestCamelCaseToSpaces:
    """Tests for _camelcase_to_spaces() helper function."""

    def test_saved_geometry_becomes_saved_geometry(self) -> None:
        """Test: 'SavedGeometry' → 'Saved Geometry'"""
        result = _camelcase_to_spaces("SavedGeometry")
        assert result == "Saved Geometry"

    def test_single_word_remains_unchanged(self) -> None:
        """Test: 'Placement' → 'Placement' (single word, no change)"""
        result = _camelcase_to_spaces("Placement")
        assert result == "Placement"

    def test_trailing_number_gets_space(self) -> None:
        """Test: 'Label2' → 'Label 2'"""
        result = _camelcase_to_spaces("Label2")
        assert result == "Label 2"

    def test_x_direction_becomes_x_direction(self) -> None:
        """Test: 'XDirection' → 'X Direction'"""
        result = _camelcase_to_spaces("XDirection")
        assert result == "X Direction"

    def test_placement_with_sub_parts(self) -> None:
        """Test: 'Placement' remains 'Placement' (single word)."""
        result = _camelcase_to_spaces("Placement")
        assert result == "Placement"

    def test_mixed_case_word(self) -> None:
        """Test: 'XMin' → 'X Min'"""
        result = _camelcase_to_spaces("XMin")
        assert result == "X Min"

    def test_all_caps_abbr_stays_together(self) -> None:
        """Test: 'XMLDoc' → 'XML Doc' - consecutive capitals split at transition."""
        result = _camelcase_to_spaces("XMLDoc")
        assert result == "XML Doc"

    def test_empty_string(self) -> None:
        """Test: Empty string remains empty."""
        result = _camelcase_to_spaces("")
        assert result == ""

    def test_single_character(self) -> None:
        """Test: Single character remains unchanged."""
        result = _camelcase_to_spaces("X")
        assert result == "X"

    def test_starting_uppercase(self) -> None:
        """Test: First character uppercase doesn't add leading space."""
        result = _camelcase_to_spaces("Angle")
        assert result == "Angle"

    def test_consecutive_uppercase_no_space(self) -> None:
        """Test: Consecutive uppercase letters (like 'ABC') stay together."""
        result = _camelcase_to_spaces("ABCDef")
        assert result == "ABC Def"

    def test_rotation_becomes_rotation(self) -> None:
        """Test: 'Rotation' → 'Rotation' (single word)."""
        result = _camelcase_to_spaces("Rotation")
        assert result == "Rotation"

    def test_material_becomes_material(self) -> None:
        """Test: 'Material' → 'Material' (single word)."""
        result = _camelcase_to_spaces("Material")
        assert result == "Material"


class TestIsExpandable:
    """Tests for is_expandable() function."""

    def test_none_is_not_expandable(self) -> None:
        """Test: None values are not expandable."""
        assert is_expandable(None) is False

    def test_non_empty_list_is_expandable(self) -> None:
        """Test: Non-empty lists are expandable."""
        assert is_expandable([1, 2, 3]) is True

    def test_non_empty_tuple_is_expandable(self) -> None:
        """Test: Non-empty tuples are expandable."""
        assert is_expandable((1, 2, 3)) is True

    def test_empty_list_is_not_expandable(self) -> None:
        """Test: Empty lists are not expandable."""
        assert is_expandable([]) is False

    def test_empty_tuple_is_not_expandable(self) -> None:
        """Test: Empty tuples are not expandable."""
        assert is_expandable(()) is False

    def test_non_empty_dict_is_expandable(self) -> None:
        """Test: Non-empty dicts are expandable."""
        assert is_expandable({"key": "value"}) is True

    def test_empty_dict_is_not_expandable(self) -> None:
        """Test: Empty dicts are not expandable."""
        assert is_expandable({}) is False

    def test_vector_is_expandable(self) -> None:
        """Test: Vector-like objects (x, y, z) are expandable."""
        vector = MockVector(1.0, 2.0, 3.0)
        assert is_expandable(vector) is True

    def test_object_with_dict_is_expandable(self) -> None:
        """Test: Objects with __dict__ are expandable."""
        obj = MockPlacement(Position=MockVector(0, 0, 0))
        assert is_expandable(obj) is True

    def test_object_without_dict_is_not_expandable(self) -> None:
        """Test: Objects without __dict__ are not expandable."""
        # Use a simple type without __dict__ or with empty __dict__
        assert is_expandable(42) is False
        assert is_expandable("string") is False


class TestExpandPlacement:
    """Tests for _expand_placement() function."""

    def test_expand_placement_with_all_components(self) -> None:
        """Test: Placement with Position, Rotation, and Axis expands correctly."""
        rotation = MockRotation(Angle=45.0, Axis=MockVector(0, 0, 1))
        position = MockVector(10.0, 20.0, 30.0)
        axis = MockVector(0, 0, 1)
        placement = MockPlacement(Position=position, Rotation=rotation, Axis=axis)

        result = _expand_placement(placement)

        assert len(result) == 3
        names = [item[0] for item in result]
        assert "Position" in names
        assert "Rotation" in names
        assert "Axis" in names
        # Check values
        assert result[0][1] == position
        assert result[1][1] == rotation
        assert result[2][1] == axis

    def test_expand_placement_with_only_position(self) -> None:
        """Test: Placement with only Position expands correctly."""
        position = MockVector(1.0, 2.0, 3.0)
        placement = MockPlacement(Position=position)

        result = _expand_placement(placement)

        assert len(result) == 1
        assert result[0][0] == "Position"
        assert result[0][1] == position

    def test_expand_placement_with_only_rotation(self) -> None:
        """Test: Placement with only Rotation expands correctly."""
        rotation = MockRotation(Angle=30.0)
        placement = MockPlacement(Rotation=rotation)

        result = _expand_placement(placement)

        assert len(result) == 1
        assert result[0][0] == "Rotation"
        assert result[0][1] == rotation

    def test_expand_placement_with_none_components(self) -> None:
        """Test: Placement with all None components returns empty list."""
        placement = MockPlacement(Position=None, Rotation=None, Axis=None)

        result = _expand_placement(placement)

        assert result == []


class TestExpandRotation:
    """Tests for _expand_rotation() function."""

    def test_expand_rotation_with_all_components(self) -> None:
        """Test: Rotation with Angle and Axis expands correctly."""
        rotation = MockRotation(Angle=45.0, Axis=MockVector(0, 0, 1))

        result = _expand_rotation(rotation)

        assert len(result) == 2
        names = [item[0] for item in result]
        assert "Angle" in names
        assert "Axis" in names

    def test_expand_rotation_with_only_angle(self) -> None:
        """Test: Rotation with only Angle expands correctly."""
        rotation = MockRotation(Angle=30.0)

        result = _expand_rotation(rotation)

        assert len(result) == 1
        assert result[0][0] == "Angle"
        assert result[0][1] == 30.0

    def test_expand_rotation_with_only_axis(self) -> None:
        """Test: Rotation with only Axis expands correctly."""
        axis = MockVector(1, 0, 0)
        rotation = MockRotation(Angle=None, Axis=axis)

        result = _expand_rotation(rotation)

        assert len(result) == 1
        assert result[0][0] == "Axis"
        assert result[0][1] == axis

    def test_expand_rotation_with_none_components(self) -> None:
        """Test: Rotation with all None components returns empty list."""
        rotation = MockRotation(Angle=None, Axis=None)

        result = _expand_rotation(rotation)

        assert result == []


class TestExpandMaterial:
    """Tests for _expand_material() function."""

    def test_expand_material_dict(self) -> None:
        """Test: Material as dict expands correctly."""
        material = {"diffuse": (1, 0, 0), "ambient": (0.5, 0.5, 0.5)}

        result = _expand_material(material)

        assert len(result) == 2
        names = [item[0] for item in result]
        assert "diffuse" in names
        assert "ambient" in names

    def test_expand_material_dict_with_string_keys(self) -> None:
        """Test: Material dict with string keys expands correctly."""
        material = {"name": "test", "color": "red"}

        result = _expand_material(material)

        assert len(result) == 2
        assert ("name", "test") in result
        assert ("color", "red") in result

    def test_expand_material_object_with_dict(self) -> None:
        """Test: Material as object with __dict__ expands correctly."""

        class MaterialObject:
            def __init__(self):
                self.diffuse = (1, 0, 0)
                self.ambient = (0.5, 0.5, 0.5)

        material = MaterialObject()

        result = _expand_material(material)

        assert len(result) == 2
        names = [item[0] for item in result]
        assert "diffuse" in names
        assert "ambient" in names

    def test_expand_material_object_excludes_private_attrs(self) -> None:
        """Test: Material expansion excludes private attributes."""

        class MaterialObject:
            def __init__(self):
                self.diffuse = (1, 0, 0)
                self._private = "hidden"

        material = MaterialObject()

        result = _expand_material(material)

        assert len(result) == 1
        assert result[0][0] == "diffuse"

    def test_expand_material_empty_dict(self) -> None:
        """Test: Empty dict material returns empty list."""
        material = {}

        result = _expand_material(material)

        assert result == []

    def test_expand_material_object_without_dict(self) -> None:
        """Test: Material without dict returns empty list."""
        # An object that doesn't have __dict__ (unlikely but possible)
        result = _expand_material(42)
        assert result == []


class TestGetPropertyChildren:
    """Tests for get_property_children() function."""

    def test_get_children_for_none(self) -> None:
        """Test: None value returns empty list."""
        result = get_property_children("test", None)
        assert result == []

    def test_get_children_for_placement(self) -> None:
        """Test: Placement property expands correctly."""
        rotation = MockRotation(Angle=45.0, Axis=MockVector(0, 0, 1))
        position = MockVector(10.0, 20.0, 30.0)
        axis = MockVector(0, 0, 1)
        placement = MockPlacement(Position=position, Rotation=rotation, Axis=axis)

        result = get_property_children("Placement", placement)

        assert len(result) == 3
        names = [item[0] for item in result]
        assert "Position" in names
        assert "Rotation" in names
        assert "Axis" in names

    def test_get_children_for_rotation(self) -> None:
        """Test: Rotation property expands correctly."""
        rotation = MockRotation(Angle=45.0, Axis=MockVector(0, 0, 1))

        result = get_property_children("Rotation", rotation)

        assert len(result) == 2
        names = [item[0] for item in result]
        assert "Angle" in names
        assert "Axis" in names

    def test_get_children_for_material_dict(self) -> None:
        """Test: Material property as dict expands correctly."""
        material = {"diffuse": (1, 0, 0), "ambient": (0.5, 0.5, 0.5)}

        result = get_property_children("Material", material)

        assert len(result) == 2

    def test_get_children_for_vector(self) -> None:
        """Test: Vector-like objects expand to x, y, z."""
        vector = MockVector(1.0, 2.0, 3.0)

        result = get_property_children("Position", vector)

        assert len(result) == 3
        assert ("x", 1.0) in result
        assert ("y", 2.0) in result
        assert ("z", 3.0) in result

    def test_get_children_for_list(self) -> None:
        """Test: Lists expand by index."""
        items = ["a", "b", "c"]

        result = get_property_children("Items", items)

        assert len(result) == 3
        assert ("[0]", "a") in result
        assert ("[1]", "b") in result
        assert ("[2]", "c") in result

    def test_get_children_for_tuple(self) -> None:
        """Test: Tuples expand by index."""
        items = (1, 2, 3)

        result = get_property_children("Items", items)

        assert len(result) == 3
        assert ("[0]", 1) in result
        assert ("[1]", 2) in result
        assert ("[2]", 3) in result

    def test_get_children_for_empty_list(self) -> None:
        """Test: Empty list returns empty list."""
        result = get_property_children("Items", [])
        assert result == []

    def test_get_children_for_dict(self) -> None:
        """Test: Dict expands by key."""
        data = {"key1": "value1", "key2": "value2"}

        result = get_property_children("Data", data)

        assert len(result) == 2
        assert ("key1", "value1") in result
        assert ("key2", "value2") in result

    def test_get_children_for_empty_dict(self) -> None:
        """Test: Empty dict returns empty list."""
        result = get_property_children("Data", {})
        assert result == []

    def test_get_children_for_object_with_dict(self) -> None:
        """Test: Objects with __dict__ expand by attribute."""

        class CustomObject:
            def __init__(self):
                self.prop1 = "value1"
                self.prop2 = 42

        obj = CustomObject()

        result = get_property_children("Custom", obj)

        assert len(result) == 2
        names = [item[0] for item in result]
        assert "prop1" in names
        assert "prop2" in names

    def test_get_children_for_object_excludes_private(self) -> None:
        """Test: Object expansion excludes private attributes."""

        class CustomObject:
            def __init__(self):
                self.public = "value"
                self._private = "hidden"

        obj = CustomObject()

        result = get_property_children("Custom", obj)

        assert len(result) == 1
        assert result[0][0] == "public"

    def test_get_children_for_nested_list(self) -> None:
        """Test: Nested lists expand correctly."""
        items = [[1, 2], [3, 4]]

        result = get_property_children("Items", items)

        assert len(result) == 2
        assert ("[0]", [1, 2]) in result
        assert ("[1]", [3, 4]) in result

    def test_get_children_for_nested_vector_in_list(self) -> None:
        """Test: Lists containing Vectors also expand."""
        items = [MockVector(1, 2, 3), MockVector(4, 5, 6)]

        result = get_property_children("Items", items)

        assert len(result) == 2
        # Each item in the list should be a Vector
        assert result[0][0] == "[0]"
        assert isinstance(result[0][1], MockVector)
        assert result[1][0] == "[1]"
        assert isinstance(result[1][1], MockVector)

    def test_get_children_for_non_expandable_value(self) -> None:
        """Test: Non-expandable values return empty list."""
        result = get_property_children("Name", "some string")
        assert result == []

    def test_get_children_for_integer(self) -> None:
        """Test: Integer values return empty list."""
        result = get_property_children("Count", 42)
        assert result == []
