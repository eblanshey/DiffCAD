# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the Property class including creation, equality,
# expression support, and serialization functionality via the DataPath model.
"""Unit tests for the Property class."""

from freecad.diff_wb.domain.tree.data_path import (
    InternalType,
    ListData,
    PrimitiveData,
    PropertyPathType,
)
from freecad.diff_wb.domain.tree.property import Property


class MockConstraint:
    """Mock constraint simulating FreeCAD C++ wrapped object without __eq__."""

    def __init__(self, name: str, constraint_type: str):
        self.Name = name
        self.Type = constraint_type

    def __str__(self):
        return f"<Constraint '{self.Name}' type={self.Type}>"


class TestProperty:
    """Tests for the Property class."""

    # =====================================================================
    # Property.from_freecad() Tests
    # =====================================================================

    def test_bool_creation(self) -> None:
        """Test boolean property value creation."""
        pv = Property.from_freecad(True, {}, "Base")
        assert isinstance(pv.value, PrimitiveData)
        assert pv.value.paths["."].type_ == PropertyPathType.BOOL
        assert pv.value.paths["."].value is True

    def test_int_creation(self) -> None:
        """Test integer property value creation."""
        pv = Property.from_freecad(42, {}, "Base")
        assert isinstance(pv.value, PrimitiveData)
        assert pv.value.paths["."].type_ == PropertyPathType.INT
        assert pv.value.paths["."].value == 42

    def test_float_creation(self) -> None:
        """Test float property value creation."""
        pv = Property.from_freecad(3.14, {}, "Base")
        assert isinstance(pv.value, PrimitiveData)
        assert pv.value.paths["."].type_ == PropertyPathType.FLOAT
        assert pv.value.paths["."].value == 3.14

    def test_string_creation(self) -> None:
        """Test string property value creation."""
        pv = Property.from_freecad("hello", {}, "Base")
        assert isinstance(pv.value, PrimitiveData)
        assert pv.value.paths["."].type_ == PropertyPathType.STRING
        assert pv.value.paths["."].value == "hello"

    def test_unknown_type_preserves_display_value(self) -> None:
        """Test that unknown types preserve display value and type info."""

        class CustomObj:
            def __str__(self):
                return "CustomObj(1, 2, 3)"

        pv = Property.from_freecad(CustomObj(), {}, "Base")
        # Unknown types go to UnknownData, not PrimitiveData
        from freecad.diff_wb.domain.tree.data_path import UnknownData

        assert isinstance(pv.value, UnknownData)
        assert pv.value.paths["."].value == "CustomObj(1, 2, 3)"
        assert pv.value.paths["."].freecad_type is not None
        assert "CustomObj" in pv.value.paths["."].freecad_type

    def test_list_creation(self) -> None:
        """Test list property value creation."""
        pv = Property.from_freecad(["a", "b", "c"], {}, "Base")
        assert isinstance(pv.value, ListData)
        assert len(pv.value.items) == 3

    def test_none_creation(self) -> None:
        """Test None property value creation."""
        pv = Property.from_freecad(None, {}, "Base")
        assert isinstance(pv.value, PrimitiveData)
        assert pv.value.paths["."].type_ == PropertyPathType.NULL
        assert pv.value.paths["."].value is None

    def test_group_default(self) -> None:
        """Test default group is 'Base'."""
        pv = Property.from_freecad(42, {})
        assert pv.group == "Base"

    def test_group_custom(self) -> None:
        """Test custom group assignment."""
        pv = Property.from_freecad(42, {}, "Data")
        assert pv.group == "Data"

    # =====================================================================
    # Equality Tests
    # =====================================================================

    def test_equality_same_type(self) -> None:
        """Test equality for same type values."""
        pv1 = Property.from_freecad(42, {}, "Base")
        pv2 = Property.from_freecad(42, {}, "Base")
        assert pv1 == pv2

    def test_inequality_different_type(self) -> None:
        """Test inequality for different types."""
        pv1 = Property.from_freecad(42, {}, "Base")
        pv2 = Property.from_freecad(42.0, {}, "Base")
        assert pv1 != pv2

    def test_float_approximate_equality(self) -> None:
        """Test approximate equality for floats."""
        pv1 = Property.from_freecad(1.0, {}, "Base")
        pv2 = Property.from_freecad(1.0 + 1e-10, {}, "Base")
        assert pv1 == pv2

    def test_inequality_different_values(self) -> None:
        """Test inequality for different values."""
        pv1 = Property.from_freecad(42, {}, "Base")
        pv2 = Property.from_freecad(43, {}, "Base")
        assert pv1 != pv2

    def test_inequality_different_groups(self) -> None:
        """Test inequality for different groups."""
        pv1 = Property.from_freecad(42, {}, "Base")
        pv2 = Property.from_freecad(42, {}, "Data")
        assert pv1 != pv2

    # =====================================================================
    # Expression Support Tests
    # =====================================================================

    def test_bool_with_expression(self) -> None:
        """Test boolean property with expression."""
        pv = Property.from_freecad(True, {".": "Sketch001.Constrain"}, "Base")
        assert isinstance(pv.value, PrimitiveData)
        assert pv.value.paths["."].type_ == PropertyPathType.BOOL
        assert pv.value.paths["."].value is True
        assert pv.value.paths["."].expression == "Sketch001.Constrain"

    def test_int_with_expression(self) -> None:
        """Test integer property with expression."""
        pv = Property.from_freecad(10, {".": "Sketch001.Count"}, "Base")
        assert isinstance(pv.value, PrimitiveData)
        assert pv.value.paths["."].type_ == PropertyPathType.INT
        assert pv.value.paths["."].value == 10
        assert pv.value.paths["."].expression == "Sketch001.Count"

    def test_float_with_expression(self) -> None:
        """Test float property with expression."""
        pv = Property.from_freecad(5.5, {".": "Body.Length"}, "Base")
        assert isinstance(pv.value, PrimitiveData)
        assert pv.value.paths["."].type_ == PropertyPathType.FLOAT
        assert pv.value.paths["."].value == 5.5
        assert pv.value.paths["."].expression == "Body.Length"

    def test_string_with_expression(self) -> None:
        """Test string property with expression."""
        pv = Property.from_freecad("test", {".": "Document.Name"}, "Base")
        assert isinstance(pv.value, PrimitiveData)
        assert pv.value.paths["."].type_ == PropertyPathType.STRING
        assert pv.value.paths["."].value == "test"
        assert pv.value.paths["."].expression == "Document.Name"

    def test_equality_same_value_different_expression(self) -> None:
        """Test that same values with different expressions are NOT equal."""
        pv1 = Property.from_freecad(10.0, {}, "Base")
        pv2 = Property.from_freecad(10.0, {".": "Sketch001.X"}, "Base")
        assert pv1 != pv2

    def test_equality_expression_vs_no_expression(self) -> None:
        """Test that value with expression differs from value without."""
        pv1 = Property.from_freecad(42, {".": "Some.Expression"}, "Base")
        pv2 = Property.from_freecad(42, {}, "Base")
        assert pv1 != pv2

    def test_equality_same_expression(self) -> None:
        """Test that same value and expression are equal."""
        pv1 = Property.from_freecad("hello", {".": "Doc.Name"}, "Base")
        pv2 = Property.from_freecad("hello", {".": "Doc.Name"}, "Base")
        assert pv1 == pv2

    def test_equality_different_expressions(self) -> None:
        """Test that same value with different expressions are NOT equal."""
        pv1 = Property.from_freecad((1.0, 2.0, 3.0), {".": "Sketch001.X"}, "Base")
        pv2 = Property.from_freecad((1.0, 2.0, 3.0), {".": "Sketch002.X"}, "Base")
        assert pv1 != pv2

    def test_equality_both_none_expressions(self) -> None:
        """Test equality when both have no expressions."""
        pv1 = Property.from_freecad(False, {}, "Base")
        pv2 = Property.from_freecad(False, {}, "Base")
        assert pv1 == pv2


class TestPropertySerialization:
    """Tests for Property serialization and deserialization."""

    def test_serialize_primitive(self) -> None:
        """Test serialization of a primitive property."""
        pv = Property.from_freecad(42, {".": "Sketch.X"}, "Base")
        serialized = pv.to_serialized()
        assert serialized["type_"] == InternalType.Primitive.value
        assert serialized["group"] == "Base"
        assert serialized["paths"]["."]["value"] == 42
        assert serialized["paths"]["."]["expression"] == "Sketch.X"

    def test_serialize_string(self) -> None:
        """Test serialization of a string property."""
        pv = Property.from_freecad("hello", {}, "Base")
        serialized = pv.to_serialized()
        assert serialized["type_"] == InternalType.Primitive.value
        assert serialized["paths"]["."]["value"] == "hello"

    def test_deserialize_primitive(self) -> None:
        """Test deserialization of a primitive property."""
        data = {
            "type_": InternalType.Primitive.value,
            "paths": {
                ".": {"type_": "INT", "value": 42, "expression": "Sketch.X"},
            },
            "group": "Data",
        }
        pv = Property.from_serialized(data)
        assert isinstance(pv.value, PrimitiveData)
        assert pv.value.paths["."].value == 42
        assert pv.value.paths["."].expression == "Sketch.X"
        assert pv.group == "Data"

    def test_roundtrip(self) -> None:
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
    """Tests for LIST type property comparison (e.g., sketch Constraints)."""

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

        # Different objects but same string representation -> should be equal
        assert prop1 == prop2

    def test_list_with_custom_objects_different_content(self) -> None:
        """Lists with different custom object content should not be equal."""
        constraints1 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance1", "Distance"),
        ]
        constraints2 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance2", "Distance"),  # Different name
        ]

        prop1 = Property.from_freecad(constraints1, {}, "Base")
        prop2 = Property.from_freecad(constraints2, {}, "Base")

        # Different string representations -> should not be equal
        assert prop1 != prop2

    def test_list_with_different_lengths(self) -> None:
        """Lists with different lengths should not be equal."""
        constraints1 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance1", "Distance"),
        ]
        constraints2 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance1", "Distance"),
            MockConstraint("Angle1", "Angle"),  # Extra constraint
        ]

        prop1 = Property.from_freecad(constraints1, {}, "Base")
        prop2 = Property.from_freecad(constraints2, {}, "Base")

        assert prop1 != prop2

    def test_list_with_simple_values(self) -> None:
        """Lists with simple values (strings, ints) should work correctly."""
        prop1 = Property.from_freecad(["a", "b", "c"], {}, "Base")
        prop2 = Property.from_freecad(["a", "b", "c"], {}, "Base")

        assert prop1 == prop2

    def test_list_with_mixed_types(self) -> None:
        """Lists with mixed types should compare correctly."""
        prop1 = Property.from_freecad([1, "a", 3.14], {}, "Base")
        prop2 = Property.from_freecad([1, "a", 3.14], {}, "Base")

        assert prop1 == prop2

    def test_list_creation_preserves_objects(self) -> None:
        """LIST type creation should preserve the actual objects."""

        class MockObj:
            def __init__(self, value):
                self.value = value

        obj1 = MockObj(1)
        obj2 = MockObj(2)
        props = Property.from_freecad([obj1, obj2], {}, "Base")

        assert isinstance(props.value, ListData)
        assert len(props.value.items) == 2
        # Items are wrapped as PrimitiveData with the object's string repr
        assert props.value.items[0].paths["."].value == str(obj1)
        assert props.value.items[1].paths["."].value == str(obj2)
