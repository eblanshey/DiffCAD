# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for Property class including creation, equality,
# expression support, serialization roundtrip, and list comparison behavior.
"""Unit tests for the Property class."""

import pytest
from freecad.history_wb.domain.tree.data_path import (
    DataPathKind,
    ListData,
    PrimitiveData,
    PropertyPathType,
)
from freecad.history_wb.domain.tree.property import Property


class MockConstraint:
    """Mock constraint simulating FreeCAD C++ wrapped object without __eq__."""

    def __init__(self, name: str, constraint_type: str):
        self.Name = name
        self.Type = constraint_type

    def __str__(self):
        return f"<Constraint '{self.Name}' type={self.Type}>"


class TestPropertyCreation:
    """Tests for Property.from_freecad creation behavior."""

    @pytest.mark.parametrize(
        ("value", "expected_kind", "check_value"),
        [
            (True, PrimitiveData, lambda p: p.value.paths["."].value is True),
            (False, PrimitiveData, lambda p: p.value.paths["."].value is False),
            (42, PrimitiveData, lambda p: p.value.paths["."].value == 42),
            (3.14, PrimitiveData, lambda p: p.value.paths["."].value == 3.14),
            ("hello", PrimitiveData, lambda p: p.value.paths["."].value == "hello"),
            (None, PrimitiveData, lambda p: p.value.paths["."].type_ == PropertyPathType.NULL),
        ],
    )
    def test_primitive_creation(self, value: object, expected_kind: type, check_value) -> None:
        """Test primitive property value creation."""
        pv = Property.from_freecad(value, {}, "Base")
        assert isinstance(pv.value, expected_kind)
        check_value(pv)

    def test_list_creation(self) -> None:
        """Test list property value creation."""
        pv = Property.from_freecad(["a", "b", "c"], {}, "Base")
        assert isinstance(pv.value, ListData)
        assert len(pv.value.items) == 3

    def test_unknown_type_preserves_display_value(self) -> None:
        """Test that unknown types preserve display value and type info."""

        class CustomObj:
            def __str__(self):
                return "CustomObj(1, 2, 3)"

        pv = Property.from_freecad(CustomObj(), {}, "Base")
        from freecad.history_wb.domain.tree.data_path import UnknownData

        assert isinstance(pv.value, UnknownData)
        assert pv.value.paths["."].value == "CustomObj(1, 2, 3)"
        assert pv.value.paths["."].freecad_type is not None
        assert "CustomObj" in pv.value.paths["."].freecad_type

    def test_group_default_is_base(self) -> None:
        """Test default group is 'Base'."""
        pv = Property.from_freecad(42, {})
        assert pv.group == "Base"

    def test_group_custom_assignment(self) -> None:
        """Test custom group assignment."""
        pv = Property.from_freecad(42, {}, "Data")
        assert pv.group == "Data"


class TestPropertyEquality:
    """Tests for Property equality behavior."""

    def test_same_value_equal(self) -> None:
        """Test equality for same type and value."""
        pv1 = Property.from_freecad(42, {}, "Base")
        pv2 = Property.from_freecad(42, {}, "Base")
        assert pv1 == pv2

    def test_different_type_not_equal(self) -> None:
        """Test inequality for different types."""
        pv1 = Property.from_freecad(42, {}, "Base")
        pv2 = Property.from_freecad(42.0, {}, "Base")
        assert pv1 != pv2

    def test_float_approximate_equality(self) -> None:
        """Test approximate equality for floats within precision."""
        pv1 = Property.from_freecad(1.0, {}, "Base")
        pv2 = Property.from_freecad(1.0 + 1e-10, {}, "Base")
        assert pv1 == pv2

    def test_different_value_not_equal(self) -> None:
        """Test inequality for different values."""
        pv1 = Property.from_freecad(42, {}, "Base")
        pv2 = Property.from_freecad(43, {}, "Base")
        assert pv1 != pv2

    def test_different_group_not_equal(self) -> None:
        """Test inequality for different groups."""
        pv1 = Property.from_freecad(42, {}, "Base")
        pv2 = Property.from_freecad(42, {}, "Data")
        assert pv1 != pv2


class TestPropertyExpression:
    """Tests for Property expression support."""

    def test_expression_preserved_on_creation(self) -> None:
        """Test that expression is stored in DataPath path entry."""
        pv = Property.from_freecad(10.0, {".": "Body.Length"}, "Base")
        assert isinstance(pv.value, PrimitiveData)
        assert pv.value.paths["."].type_ == PropertyPathType.FLOAT
        assert pv.value.paths["."].value == 10.0
        assert pv.value.paths["."].expression == "Body.Length"

    def test_same_value_different_expression_not_equal(self) -> None:
        """Test that same values with different expressions are NOT equal."""
        pv1 = Property.from_freecad(10.0, {}, "Base")
        pv2 = Property.from_freecad(10.0, {".": "Sketch001.X"}, "Base")
        assert pv1 != pv2

    def test_same_value_same_expression_equal(self) -> None:
        """Test that same value and expression are equal."""
        pv1 = Property.from_freecad("hello", {".": "Doc.Name"}, "Base")
        pv2 = Property.from_freecad("hello", {".": "Doc.Name"}, "Base")
        assert pv1 == pv2


class TestPropertySerialization:
    """Tests for Property serialization and deserialization."""

    def test_serialize_includes_group_and_kind(self) -> None:
        """Test serialization includes group, kind, and paths keys."""
        pv = Property.from_freecad(42, {".": "Sketch.X"}, "Base")
        serialized = pv.to_serialized()
        assert serialized["kind"] == DataPathKind.Primitive.value
        assert serialized["group"] == "Base"
        assert serialized["paths"]["."]["value"] == 42
        assert serialized["paths"]["."]["expression"] == "Sketch.X"

    def test_deserialize_restores_group_and_value(self) -> None:
        """Test deserialization restores group and DataPath value."""
        data = {
            "kind": DataPathKind.Primitive.value,
            "paths": {
                ".": {"type": "INT", "value": 42, "expression": "Sketch.X"},
            },
            "group": "Data",
        }
        pv = Property.from_serialized(data)
        assert isinstance(pv.value, PrimitiveData)
        assert pv.value.paths["."].value == 42
        assert pv.value.paths["."].expression == "Sketch.X"
        assert pv.group == "Data"

    def test_roundtrip_preserves_data(self) -> None:
        """Test that serialize -> deserialize roundtrip preserves data."""
        original = Property.from_freecad(3.14, {".": "Body.Length"}, "View")
        serialized = original.to_serialized()
        restored = Property.from_serialized(serialized)
        assert original == restored

    def test_roundtrip_string(self) -> None:
        """Test that serialize -> deserialize roundtrip preserves string data."""
        original = Property.from_freecad("test_label", {".": "Doc.Label"}, "Base")
        serialized = original.to_serialized()
        restored = Property.from_serialized(serialized)
        assert original == restored


class TestPropertyListComparison:
    """Tests for LIST type property comparison."""

    def test_list_with_custom_objects_same_content(self) -> None:
        """Lists with identical custom object content should be equal."""
        constraints1 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance1", "Distance"),
        ]
        constraints2 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance1", "Distance"),
        ]

        prop1 = Property.from_freecad(constraints1, {}, "Base")
        prop2 = Property.from_freecad(constraints2, {}, "Base")
        assert prop1 == prop2

    def test_list_with_custom_objects_different_content(self) -> None:
        """Lists with different custom object content should not be equal."""
        constraints1 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance1", "Distance"),
        ]
        constraints2 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance2", "Distance"),
        ]

        prop1 = Property.from_freecad(constraints1, {}, "Base")
        prop2 = Property.from_freecad(constraints2, {}, "Base")
        assert prop1 != prop2

    def test_list_with_simple_values(self) -> None:
        """Lists with simple values should compare correctly."""
        prop1 = Property.from_freecad(["a", "b", "c"], {}, "Base")
        prop2 = Property.from_freecad(["a", "b", "c"], {}, "Base")
        assert prop1 == prop2

    def test_list_creation_preserves_objects(self) -> None:
        """LIST type creation should preserve the actual objects as string repr."""

        class MockObj:
            def __init__(self, value):
                self.value = value

        obj1 = MockObj(1)
        obj2 = MockObj(2)
        props = Property.from_freecad([obj1, obj2], {}, "Base")

        assert isinstance(props.value, ListData)
        assert len(props.value.items) == 2
        assert props.value.items[0].paths["."].value == str(obj1)
        assert props.value.items[1].paths["."].value == str(obj2)
