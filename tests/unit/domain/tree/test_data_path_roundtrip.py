# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for round-trip serialization/deserialization of
# all DataPath types through their serialize() and from_serialized_value() methods.
"""Unit tests for DataPath round-trip serialization."""

from freecad.history_wb.domain.tree.data_path import (
    DATA_PATH_KIND_MAP,
    ConstraintData,
    DataPathKind,
    ListData,
    PlacementData,
    PrimitiveData,
    PropertyPathType,
    PropertyPathValue,
    RotationData,
    SnapshotFormatError,
    UnknownData,
    VectorData,
    data_path_from_freecad_value,
    data_path_from_serialized,
)


class TestPrimitiveDataRoundTrip:
    """Round-trip tests for PrimitiveData."""

    def test_roundtrip_int(self) -> None:
        """Test PrimitiveData round-trip with integer value."""
        original = data_path_from_freecad_value(42, {})
        assert isinstance(original, PrimitiveData)
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, PrimitiveData)
        assert restored.paths["."].value == 42
        assert restored.paths["."].type_ == PropertyPathType.INT

    def test_roundtrip_float(self) -> None:
        """Test PrimitiveData round-trip with float value."""
        original = data_path_from_freecad_value(3.14, {})
        assert isinstance(original, PrimitiveData)
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, PrimitiveData)
        assert restored.paths["."].value == 3.14
        assert restored.paths["."].type_ == PropertyPathType.FLOAT

    def test_roundtrip_string(self) -> None:
        """Test PrimitiveData round-trip with string value."""
        original = data_path_from_freecad_value("hello", {})
        assert isinstance(original, PrimitiveData)
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, PrimitiveData)
        assert restored.paths["."].value == "hello"

    def test_roundtrip_with_expression(self) -> None:
        """Test PrimitiveData round-trip preserves expression."""
        original = data_path_from_freecad_value(42, {".": "Sketch001.X"})
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, PrimitiveData)
        assert restored.paths["."].expression == "Sketch001.X"

    def test_roundtrip_none(self) -> None:
        """Test PrimitiveData round-trip with None value."""
        original = data_path_from_freecad_value(None, {})
        assert isinstance(original, PrimitiveData)
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, PrimitiveData)
        assert restored.paths["."].type_ == PropertyPathType.NULL


class TestUnknownDataRoundTrip:
    """Round-trip tests for UnknownData."""

    def test_roundtrip(self) -> None:
        """Test UnknownData round-trip."""

        class CustomType:
            def __str__(self) -> str:
                return "<CustomType>"

        original = data_path_from_freecad_value(CustomType(), {})
        assert isinstance(original, UnknownData)
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, UnknownData)
        assert restored.paths["."].freecad_type is not None
        assert "CustomType" in restored.paths["."].freecad_type


class TestQuantityPrimitiveRoundTrip:
    """Round-trip tests for PrimitiveData with single QUANTITY path."""

    def test_roundtrip_value_and_unit(self) -> None:
        """Test quantity primitive round-trip stores canonical quantity path string."""
        original = PrimitiveData(
            paths={
                ".": PropertyPathValue(
                    PropertyPathType.QUANTITY,
                    10.0,
                    unit="mm",
                ),
            }
        )
        serialized = original.serialize()
        assert serialized["kind"] == "Primitive"
        assert serialized["paths"]["."]["value"] == "10.0 mm"
        assert "unit" not in serialized["paths"]["."]
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, PrimitiveData)
        assert set(restored.paths.keys()) == {"."}
        assert restored.paths["."].type_ == PropertyPathType.QUANTITY
        assert restored.paths["."].value == 10.0
        assert restored.paths["."].unit == "mm"

    def test_roundtrip_expression_preserved(self) -> None:
        """Test quantity primitive round-trip preserves expression on root path."""
        original = PrimitiveData(
            paths={
                ".": PropertyPathValue(
                    PropertyPathType.QUANTITY,
                    5.0,
                    expression="Body.Length",
                    unit="mm",
                ),
            }
        )
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, PrimitiveData)
        assert set(restored.paths.keys()) == {"."}
        assert restored.paths["."].value == 5.0
        assert restored.paths["."].unit == "mm"
        assert restored.paths["."].expression == "Body.Length"


class TestVectorDataRoundTrip:
    """Round-trip tests for VectorData."""

    def test_roundtrip(self) -> None:
        """Test VectorData round-trip via direct construction."""
        original = VectorData(
            paths={
                "x": PropertyPathValue(PropertyPathType.FLOAT, 1.0, None),
                "y": PropertyPathValue(PropertyPathType.FLOAT, 2.0, None),
                "z": PropertyPathValue(PropertyPathType.FLOAT, 3.0, None),
            }
        )
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, VectorData)
        assert restored.paths["x"].value == 1.0
        assert restored.paths["y"].value == 2.0
        assert restored.paths["z"].value == 3.0

    def test_roundtrip_with_expression(self) -> None:
        """Test VectorData round-trip preserves expressions."""
        original = VectorData(
            paths={
                "x": PropertyPathValue(PropertyPathType.FLOAT, 1.0, "Body.X"),
                "y": PropertyPathValue(PropertyPathType.FLOAT, 2.0, "Body.Y"),
                "z": PropertyPathValue(PropertyPathType.FLOAT, 3.0, None),
            }
        )
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, VectorData)
        assert restored.paths["x"].expression == "Body.X"
        assert restored.paths["y"].expression == "Body.Y"


class TestRotationDataRoundTrip:
    """Round-trip tests for RotationData."""

    def test_roundtrip(self) -> None:
        """Test RotationData round-trip via direct construction."""
        original = RotationData(
            paths={
                "Angle": PropertyPathValue(PropertyPathType.FLOAT, 90.0, None),
                "Axis.x": PropertyPathValue(PropertyPathType.FLOAT, 0.0, None),
                "Axis.y": PropertyPathValue(PropertyPathType.FLOAT, 0.0, None),
                "Axis.z": PropertyPathValue(PropertyPathType.FLOAT, 1.0, None),
            }
        )
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, RotationData)
        assert abs(restored.paths["Angle"].value - 90.0) < 1e-9
        assert abs(restored.paths["Axis.x"].value - 0.0) < 1e-9
        assert abs(restored.paths["Axis.y"].value - 0.0) < 1e-9
        assert abs(restored.paths["Axis.z"].value - 1.0) < 1e-9

    def test_roundtrip_with_expression(self) -> None:
        """Test RotationData round-trip preserves root expression."""
        original = RotationData(
            paths={
                "Angle": PropertyPathValue(PropertyPathType.FLOAT, 45.0, None),
                "Axis.x": PropertyPathValue(PropertyPathType.FLOAT, 0.0, None),
                "Axis.y": PropertyPathValue(PropertyPathType.FLOAT, 0.0, None),
                "Axis.z": PropertyPathValue(PropertyPathType.FLOAT, 1.0, None),
                ".": PropertyPathValue(PropertyPathType.NULL, None, "Body.Rotation"),
            }
        )
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, RotationData)
        assert restored.paths["."].expression == "Body.Rotation"


class TestPlacementDataRoundTrip:
    """Round-trip tests for PlacementData."""

    def test_roundtrip(self) -> None:
        """Test PlacementData round-trip via direct construction."""
        original = PlacementData(
            paths={
                "Base.x": PropertyPathValue(PropertyPathType.FLOAT, 1.0, None),
                "Base.y": PropertyPathValue(PropertyPathType.FLOAT, 2.0, None),
                "Base.z": PropertyPathValue(PropertyPathType.FLOAT, 3.0, None),
                "Rotation.Angle": PropertyPathValue(PropertyPathType.FLOAT, 90.0, None),
                "Rotation.Axis.x": PropertyPathValue(PropertyPathType.FLOAT, 0.0, None),
                "Rotation.Axis.y": PropertyPathValue(PropertyPathType.FLOAT, 0.0, None),
                "Rotation.Axis.z": PropertyPathValue(PropertyPathType.FLOAT, 1.0, None),
            }
        )
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, PlacementData)
        assert restored.paths["Base.x"].value == 1.0
        assert restored.paths["Base.y"].value == 2.0
        assert restored.paths["Base.z"].value == 3.0
        assert abs(restored.paths["Rotation.Angle"].value - 90.0) < 1e-9
        assert abs(restored.paths["Rotation.Axis.x"].value - 0.0) < 1e-9
        assert abs(restored.paths["Rotation.Axis.y"].value - 0.0) < 1e-9
        assert abs(restored.paths["Rotation.Axis.z"].value - 1.0) < 1e-9

    def test_roundtrip_with_expression(self) -> None:
        """Test PlacementData round-trip preserves expressions."""
        original = PlacementData(
            paths={
                "Base.x": PropertyPathValue(PropertyPathType.FLOAT, 0.0, "Body.X"),
                "Base.y": PropertyPathValue(PropertyPathType.FLOAT, 0.0, None),
                "Base.z": PropertyPathValue(PropertyPathType.FLOAT, 0.0, None),
                "Rotation.Angle": PropertyPathValue(PropertyPathType.FLOAT, 0.0, "Body.Rot"),
                "Rotation.Axis.x": PropertyPathValue(PropertyPathType.FLOAT, 0.0, None),
                "Rotation.Axis.y": PropertyPathValue(PropertyPathType.FLOAT, 0.0, None),
                "Rotation.Axis.z": PropertyPathValue(PropertyPathType.FLOAT, 1.0, None),
            }
        )
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, PlacementData)
        assert restored.paths["Base.x"].expression == "Body.X"
        assert restored.paths["Rotation.Angle"].expression == "Body.Rot"


class TestConstraintDataRoundTrip:
    """Round-trip tests for ConstraintData."""

    def test_roundtrip(self) -> None:
        """Test ConstraintData round-trip via direct construction."""
        original = ConstraintData(
            paths={
                "Type": PropertyPathValue(PropertyPathType.INT, 0, None),
                "Name": PropertyPathValue(PropertyPathType.STRING, "Distance1", None),
                "Value": PropertyPathValue(PropertyPathType.FLOAT, 10.0, None),
                "First": PropertyPathValue(PropertyPathType.INT, 1, None),
                "FirstPos": PropertyPathValue(PropertyPathType.INT, 0, None),
                "Second": PropertyPathValue(PropertyPathType.INT, 2, None),
                "SecondPos": PropertyPathValue(PropertyPathType.INT, 1, None),
                "Third": PropertyPathValue(PropertyPathType.INT, -2000, None),
                "ThirdPos": PropertyPathValue(PropertyPathType.INT, 0, None),
                "Driving": PropertyPathValue(PropertyPathType.BOOL, True, None),
                "IsActive": PropertyPathValue(PropertyPathType.BOOL, True, None),
            }
        )
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, ConstraintData)
        actual_values = {path: pv.value for path, pv in restored.paths.items() if path != "."}
        assert actual_values == {
            "Type": 0,
            "Name": "Distance1",
            "Value": 10.0,
            "First": 1,
            "FirstPos": 0,
            "Second": 2,
            "SecondPos": 1,
            "Third": -2000,
            "ThirdPos": 0,
            "Driving": True,
            "IsActive": True,
        }

    def test_from_freecad_value_extracts_extended_fields(self) -> None:
        """ConstraintData.from_freecad_value should include name, positions, and flags."""

        class MockConstraint:
            Type = "Distance"
            Name = "LengthConstraint"
            Value = 15.0
            First = 3
            FirstPos = 1
            Second = 4
            SecondPos = 2
            Third = -2000
            ThirdPos = 0
            Driving = True
            IsActive = True
            InVirtualSpace = False

        result = ConstraintData.from_freecad_value(MockConstraint(), expr_map={".": "5 mm"})

        actual_values = {path: pv.value for path, pv in result.paths.items() if path != "."}
        assert actual_values == {
            "Type": "Distance",
            "Name": "LengthConstraint",
            "Value": 15.0,
            "First": 3,
            "FirstPos": 1,
            "Second": 4,
            "SecondPos": 2,
            "Third": -2000,
            "ThirdPos": 0,
            "Driving": True,
            "IsActive": True,
        }
        assert result.paths["."].expression == "5 mm"
        assert "InVirtualSpace" not in actual_values

    def test_from_freecad_value_omits_empty_name(self) -> None:
        """ConstraintData.from_freecad_value should omit Name when unset."""

        class MockConstraint:
            Type = "Distance"
            Name = ""
            Value = 10.0
            First = 1
            FirstPos = 0
            Second = -2000
            SecondPos = 0
            Third = -2000
            ThirdPos = 0
            Driving = True
            IsActive = True

        result = ConstraintData.from_freecad_value(MockConstraint(), expr_map={})

        assert "Name" not in result.paths

    def test_roundtrip_with_expression(self) -> None:
        """Test ConstraintData round-trip preserves root expression."""
        original = ConstraintData(
            paths={
                "Type": PropertyPathValue(PropertyPathType.INT, 0, None),
                ".": PropertyPathValue(PropertyPathType.NULL, None, "Sketch.Constraints"),
            }
        )
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, ConstraintData)
        assert restored.paths["."].expression == "Sketch.Constraints"


class TestListDataRoundTrip:
    """Round-trip tests for ListData."""

    def test_roundtrip_simple_primitives(self) -> None:
        """Test ListData round-trip with simple primitive items."""
        original = data_path_from_freecad_value([1, 2.0, "three"], {})
        assert isinstance(original, ListData)
        assert len(original.items) == 3
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, ListData)
        assert len(restored.items) == 3
        assert restored.items[0].paths["."].value == 1
        assert restored.items[1].paths["."].value == 2.0
        assert restored.items[2].paths["."].value == "three"

    def test_roundtrip_mixed_items(self) -> None:
        """Test ListData round-trip with mixed item types."""
        items = [
            42,
            3.14,
            "hello",
            True,
            None,
            [1, 2],
        ]
        original = data_path_from_freecad_value(items, {})
        assert isinstance(original, ListData)
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, ListData)
        assert len(restored.items) == 6
        # Check first item (int -> PrimitiveData)
        assert isinstance(restored.items[0], PrimitiveData)
        assert restored.items[0].paths["."].value == 42
        # Check second item (float -> PrimitiveData)
        assert isinstance(restored.items[1], PrimitiveData)
        assert restored.items[1].paths["."].value == 3.14
        # Check third item (str -> PrimitiveData)
        assert isinstance(restored.items[2], PrimitiveData)
        assert restored.items[2].paths["."].value == "hello"
        # Check fourth item (bool -> PrimitiveData)
        assert isinstance(restored.items[3], PrimitiveData)
        assert restored.items[3].paths["."].value is True
        # Check fifth item (None -> PrimitiveData)
        assert isinstance(restored.items[4], PrimitiveData)
        assert restored.items[4].paths["."].type_ == PropertyPathType.NULL
        # Check sixth item (list -> ListData)
        assert isinstance(restored.items[5], ListData)
        assert len(restored.items[5].items) == 2

    def test_roundtrip_empty_list(self) -> None:
        """Test ListData round-trip with empty list."""
        original = data_path_from_freecad_value([], {})
        assert isinstance(original, ListData)
        assert len(original.items) == 0
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, ListData)
        assert len(restored.items) == 0

    def test_roundtrip_with_root_expression(self) -> None:
        """Test ListData round-trip preserves root expression."""
        original = data_path_from_freecad_value([1, 2, 3], {".": "Sketch.Constraints"})
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, ListData)
        assert restored.paths["."].expression == "Sketch.Constraints"

    def test_roundtrip_nested_list(self) -> None:
        """Test ListData round-trip with nested lists."""
        original = data_path_from_freecad_value([[1, 2], [3, 4]], {})
        assert isinstance(original, ListData)
        assert len(original.items) == 2
        assert isinstance(original.items[0], ListData)
        assert len(original.items[0].items) == 2
        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)
        assert isinstance(restored, ListData)
        assert isinstance(restored.items[0], ListData)
        assert restored.items[0].items[0].paths["."].value == 1
        assert restored.items[1].items[1].paths["."].value == 4


class TestDataPathKindMap:
    """Tests for DATA_PATH_KIND_MAP dispatch."""

    def test_all_data_path_kinds_mapped(self) -> None:
        """Test that all DataPathKind values are in DATA_PATH_KIND_MAP."""
        for kind in DataPathKind:
            assert kind.value in DATA_PATH_KIND_MAP

    def test_deserialize_unknown_kind_fails_clearly(self) -> None:
        """Unknown data path kinds fail with a snapshot format error."""
        data = {"kind": "NonExistent", "paths": {".": {"type": "STRING", "value": "test"}}}
        try:
            data_path_from_serialized(data)
        except SnapshotFormatError as exc:
            assert "Unknown data path kind" in str(exc)
        else:
            raise AssertionError("Expected SnapshotFormatError")
