# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for the DataPath-based Property wrapper class.
"""Tests for the DataPath-based Property wrapper class.

Verifies that Property.from_freecad wraps values in the correct DataPath type,
Property.to_serialized includes the group key, and Property.from_serialized
restores the group from the serialized dict.
"""

from __future__ import annotations

from freecad.diff_wb.domain.tree.data_path import (
    InternalType,
    PrimitiveData,
    PropertyPathType,
)
from freecad.diff_wb.domain.tree.property import Property


class TestPropertyFromFreecad:
    """Tests for Property.from_freecad wrapping behavior."""

    def test_float_wraps_primitive_data(self):
        """Passing a float should produce a Property with PrimitiveData value."""
        prop = Property.from_freecad(3.14, {}, group="Base")
        assert isinstance(prop.value, PrimitiveData)
        assert prop.value.INTERNAL_TYPE is InternalType.Primitive

    def test_int_wraps_primitive_data(self):
        """Passing an int should produce a Property with PrimitiveData value."""
        prop = Property.from_freecad(42, {}, group="Data")
        assert isinstance(prop.value, PrimitiveData)

    def test_string_wraps_primitive_data(self):
        """Passing a string should produce a Property with PrimitiveData value."""
        prop = Property.from_freecad("hello", {}, group="View")
        assert isinstance(prop.value, PrimitiveData)

    def test_bool_wraps_primitive_data(self):
        """Passing a bool should produce a Property with PrimitiveData value."""
        prop = Property.from_freecad(True, {}, group="Base")
        assert isinstance(prop.value, PrimitiveData)

    def test_none_wraps_primitive_data(self):
        """Passing None should produce a Property with PrimitiveData value."""
        prop = Property.from_freecad(None, {}, group="Base")
        assert isinstance(prop.value, PrimitiveData)

    def test_list_wraps_list_data(self):
        """Passing a list should produce a Property with ListData value."""
        from freecad.diff_wb.domain.tree.data_path import ListData

        prop = Property.from_freecad([1, 2, 3], {}, group="Base")
        assert isinstance(prop.value, ListData)

    def test_expression_map_preserved_in_primitive(self):
        """Expression map '.' key should be stored in the PrimitiveData path."""
        prop = Property.from_freecad(10.0, {".": "5 mm"}, group="Base")
        assert isinstance(prop.value, PrimitiveData)
        path_entry = prop.value.paths["."]
        assert path_entry.expression == "5 mm"
        assert path_entry.type_ is PropertyPathType.FLOAT

    def test_default_group_is_base(self):
        """When no group is specified, the default should be 'Base'."""
        prop = Property.from_freecad(42, {})
        assert prop.group == "Base"

    def test_group_is_stored(self):
        """The group parameter should be stored on the Property."""
        prop = Property.from_freecad(42, {}, group="Data")
        assert prop.group == "Data"
        prop2 = Property.from_freecad(42, {}, group="View")
        assert prop2.group == "View"


class TestPropertyToSerialized:
    """Tests for Property.to_serialized output."""

    def test_serialized_includes_group_key(self):
        """Serialized output should include the 'group' key."""
        prop = Property.from_freecad(3.14, {}, group="Data")
        result = prop.to_serialized()
        assert "group" in result
        assert result["group"] == "Data"

    def test_serialized_includes_type_key(self):
        """Serialized output should include the 'type_' key from the DataPath."""
        prop = Property.from_freecad(3.14, {}, group="Base")
        result = prop.to_serialized()
        assert "type_" in result
        assert result["type_"] == "Primitive"

    def test_serialized_includes_paths_key(self):
        """Serialized output should include the 'paths' key from the DataPath."""
        prop = Property.from_freecad(3.14, {}, group="Base")
        result = prop.to_serialized()
        assert "paths" in result
        assert "." in result["paths"]

    def test_serialized_preserves_group_across_types(self):
        """Group should be preserved for different DataPath types."""
        prop = Property.from_freecad([1, 2], {}, group="View")
        result = prop.to_serialized()
        assert result["group"] == "View"


class TestPropertyFromSerialized:
    """Tests for Property.from_serialized restoration."""

    def test_from_serialized_restores_group(self):
        """Deserialized Property should restore the group from the dict."""
        data = {
            "type_": "Primitive",
            "paths": {
                ".": {
                    "type_": "FLOAT",
                    "value": 3.14,
                }
            },
            "group": "Data",
        }
        prop = Property.from_serialized(data)
        assert prop.group == "Data"

    def test_from_serialized_defaults_to_base_group(self):
        """If no group key is present, default should be 'Base'."""
        data = {
            "type_": "Primitive",
            "paths": {
                ".": {
                    "type_": "INT",
                    "value": 42,
                }
            },
        }
        prop = Property.from_serialized(data)
        assert prop.group == "Base"

    def test_from_serialized_restores_value(self):
        """Deserialized Property should have the correct DataPath value."""
        data = {
            "type_": "Primitive",
            "paths": {
                ".": {
                    "type_": "FLOAT",
                    "value": 3.14,
                }
            },
            "group": "View",
        }
        prop = Property.from_serialized(data)
        assert isinstance(prop.value, PrimitiveData)
        assert prop.value.paths["."].value == 3.14

    def test_roundtrip_preserves_group(self):
        """Serializing and deserializing should preserve the group."""
        original = Property.from_freecad(42, {}, group="Data")
        serialized = original.to_serialized()
        restored = Property.from_serialized(serialized)
        assert restored.group == original.group
