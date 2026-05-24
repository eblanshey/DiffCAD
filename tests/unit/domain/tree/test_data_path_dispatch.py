# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for data_path dispatch functions including
# Python type dispatch and unknown type fallback behavior.
"""Unit tests for data_path dispatch functions."""

import pytest
from freecad.history_wb.domain.tree.data_path import (
    DataPath,
    ListData,
    PlacementData,
    PrimitiveData,
    PropertyPathType,
    RotationData,
    UnknownData,
    data_path_from_freecad_value,
)


class MockUnknownType:
    """A mock class simulating an unknown FreeCAD type."""

    def __str__(self) -> str:
        return "<MockUnknownType display>"


def _init_vector(self: object, x: float, y: float, z: float) -> None:
    """Initialize a Base.Vector-shaped test double."""
    self.x = x
    self.y = y
    self.z = z


def _init_rotation(self: object, angle: float, axis: object) -> None:
    """Initialize a Base.Rotation-shaped test double."""
    self.Angle = angle
    self.Axis = axis


def _init_placement(self: object, base: object, rotation: object) -> None:
    """Initialize a Base.Placement-shaped test double."""
    self.Base = base
    self.Rotation = rotation


BaseVector = type("Vector", (), {"__module__": "Base", "__init__": _init_vector})
BaseRotation = type("Rotation", (), {"__module__": "Base", "__init__": _init_rotation})
BasePlacement = type("Placement", (), {"__module__": "Base", "__init__": _init_placement})


def _base_vector(x: float, y: float, z: float) -> object:
    """Create a Base.Vector-shaped test object."""
    return BaseVector(x=x, y=y, z=z)


def _base_rotation(angle: float) -> object:
    """Create a Base.Rotation-shaped test object."""
    axis = _base_vector(0.0, 0.0, 1.0)
    assert isinstance(axis, BaseVector)
    return BaseRotation(angle=angle, axis=axis)


def _base_placement() -> object:
    """Create a Base.Placement-shaped test object."""
    base = _base_vector(1.0, 2.0, 3.0)
    rotation = _base_rotation(1.0)
    assert isinstance(base, BaseVector)
    assert isinstance(rotation, BaseRotation)
    return BasePlacement(base=base, rotation=rotation)


class TestPythonTypeDispatch:
    """Tests for dispatch based on Python built-in types."""

    @pytest.mark.parametrize(
        ("value", "expected_class"),
        [
            (True, PrimitiveData),
            (False, PrimitiveData),
            (42, PrimitiveData),
            (-7, PrimitiveData),
            (3.14, PrimitiveData),
            (0.0, PrimitiveData),
            ("hello", PrimitiveData),
            ("", PrimitiveData),
            (None, PrimitiveData),
            ([1, 2, 3], ListData),
            ((1, 2, 3), ListData),
        ],
    )
    def test_python_type_dispatch(self, value: object, expected_class: type[DataPath]) -> None:
        """Test that Python built-in types dispatch to the correct DataPath class."""
        result = data_path_from_freecad_value(value, {})
        assert isinstance(result, expected_class)

    def test_int_dispatch(self) -> None:
        """Test that int values dispatch to PrimitiveData with correct path."""
        result = data_path_from_freecad_value(42, {})
        assert isinstance(result, PrimitiveData)
        assert "." in result.paths
        assert result.paths["."].value == 42

    def test_list_dispatch(self) -> None:
        """Test that list values dispatch to ListData."""
        result = data_path_from_freecad_value([1, 2, 3], {})
        assert isinstance(result, ListData)
        assert len(result.items) == 3


class TestFreeCadQuantityPathDispatch:
    """Tests for quantity-valued paths in FreeCAD-shaped values."""

    def test_placement_length_and_angle_paths_are_quantities(self) -> None:
        """Placement Base coordinates and Rotation.Angle dispatch to QUANTITY paths."""
        result = data_path_from_freecad_value(_base_placement(), {})

        assert isinstance(result, PlacementData)
        assert result.paths["Base.x"].type_ == PropertyPathType.QUANTITY
        assert result.paths["Base.x"].unit == "mm"
        assert result.paths["Rotation.Angle"].type_ == PropertyPathType.QUANTITY
        assert result.paths["Rotation.Angle"].unit == "deg"
        assert result.paths["Rotation.Axis.x"].type_ == PropertyPathType.FLOAT

    def test_rotation_angle_path_is_quantity(self) -> None:
        """Rotation Angle dispatches to a QUANTITY path while Axis remains floats."""
        result = data_path_from_freecad_value(_base_rotation(1.0), {})

        assert isinstance(result, RotationData)
        assert result.paths["Angle"].type_ == PropertyPathType.QUANTITY
        assert result.paths["Angle"].unit == "deg"
        assert result.paths["Axis.x"].type_ == PropertyPathType.FLOAT

    def test_tuple_dispatch(self) -> None:
        """Test that tuple values dispatch to ListData with correct item count."""
        result = data_path_from_freecad_value((1, 2, 3), {})
        assert isinstance(result, ListData)
        assert len(result.items) == 3


class TestUnknownFallback:
    """Tests for unknown type fallback to UnknownData."""

    def test_unknown_type_fallback(self) -> None:
        """Test that unrecognized types fall back to UnknownData."""
        mock = MockUnknownType()
        result = data_path_from_freecad_value(mock, {})
        assert isinstance(result, UnknownData)

    def test_unknown_contains_freecad_type(self) -> None:
        """Test that UnknownData contains freecad_type info."""
        mock = MockUnknownType()
        result = data_path_from_freecad_value(mock, {})
        assert isinstance(result, UnknownData)
        assert "." in result.paths
        assert result.paths["."].freecad_type is not None
        assert "MockUnknownType" in result.paths["."].freecad_type

    def test_unknown_contains_root_display_string(self) -> None:
        """Test that UnknownData root path contains display string."""
        mock = MockUnknownType()
        result = data_path_from_freecad_value(mock, {})
        assert isinstance(result, UnknownData)
        assert result.paths["."].value == "<MockUnknownType display>"

    def test_unknown_with_expression(self) -> None:
        """Test that UnknownData preserves expression."""
        mock = MockUnknownType()
        result = data_path_from_freecad_value(mock, {".": "Some.Expression"})
        assert isinstance(result, UnknownData)
        assert result.paths["."].expression == "Some.Expression"

    def test_unknown_type_key_format(self) -> None:
        """Test that the freecad_type key has module.name format."""
        mock = MockUnknownType()
        result = data_path_from_freecad_value(mock, {})
        type_key = result.paths["."].freecad_type
        assert type_key is not None
        assert "." in type_key  # Should have module.name format
