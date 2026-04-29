# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Path-based domain value classes for deterministic
# property extraction, expression preservation, and YAML round-trip behavior.
"""Path-based domain value classes for deterministic property extraction,
expression preservation, and YAML round-trip behavior.

This module defines a set of data path value classes that wrap FreeCAD and
Python values into structured path entries. Each value shape (primitive,
vector, rotation, placement, constraint, list, unknown) is
represented by a dedicated class with a deterministic set of path keys.

The module provides:

* ``PropertyPathValue`` - A single path entry with type, value, expression,
  and optional FreeCAD type info. Float values use tolerance-based equality.
  QUANTITY types store an associated unit string and serialize as canonical
  text like ``"10.0 mm"``.
* ``DataPath`` - A Protocol that all path-based data classes implement,
  providing factory methods for creation from FreeCAD values or serialized
  dicts, and a ``serialize`` method for YAML output.
* Concrete ``DataPath`` subclasses: ``PrimitiveData``, ``VectorData``,
  ``RotationData``, ``PlacementData``, ``ConstraintData``, ``UnknownData``,
  and ``ListData``.
* O(1) dispatch maps and constructor functions for converting FreeCAD/
  Python values to the correct ``DataPath`` subclass, and vice versa.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar, Protocol, runtime_checkable

from ...utils import float_values_equal

# Import fallback precision only for ad-hoc value construction (mainly tests);
# runtime comparison/display precision is supplied via settings-driven flows.
from ..config import FLOAT_PRECISION as DEFAULT_FLOAT_PRECISION


class SnapshotFormatError(ValueError):
    """Raised when serialized snapshot data does not match the current format."""


class DataPathKind(StrEnum):
    """Top-level data path shape identifiers for serialized values.

    Used as keys in DATA_PATH_KIND_MAP for serialization round-trips.
    """

    Primitive = "Primitive"
    Vector = "Vector"
    Rotation = "Rotation"
    Placement = "Placement"
    Constraint = "Constraint"
    List = "List"
    Unknown = "Unknown"


class PropertyPathType(StrEnum):
    """Property path value types matching YAML serialization format.

    These types are stored as strings in serialized output and used to
    reconstruct ``PropertyPathValue`` instances during deserialization.
    """

    FLOAT = "FLOAT"
    INT = "INT"
    STRING = "STRING"
    BOOL = "BOOL"
    NULL = "NULL"
    QUANTITY = "QUANTITY"


@dataclass(frozen=True)
class PropertyPathValue:
    """A single path entry with type, value, optional expression, and FreeCAD type info.

    Float and Quantity values use tolerance-based equality based on the configured
    precision (rounding to N decimal places). Expressions are compared for equality,
    so two values with different expressions are never equal even if their values match.
    QUANTITY types store a numeric value with an associated unit string.
    """

    type_: PropertyPathType
    value: Any
    expression: str | None = None
    freecad_type: str | None = None
    precision: int = DEFAULT_FLOAT_PRECISION  # Decimal places for float comparison
    unit: str | None = None  # Unit string for QUANTITY types (e.g. "mm", "N")

    @staticmethod
    def from_python(value: Any, expression: str | None = None) -> PropertyPathValue:
        """Create a PropertyPathValue from a plain Python value.

        Args:
            value: The Python value to wrap. Booleans are detected before
                integers since ``bool`` is a subclass of ``int``.
            expression: Optional expression string that drives this value.

        Returns:
            A new PropertyPathValue with the appropriate type.
        """
        if value is None:
            return PropertyPathValue(PropertyPathType.NULL, None, expression)
        if isinstance(value, bool):
            return PropertyPathValue(PropertyPathType.BOOL, value, expression)
        if isinstance(value, int):
            return PropertyPathValue(PropertyPathType.INT, value, expression)
        if isinstance(value, float):
            return PropertyPathValue(PropertyPathType.FLOAT, float(value), expression)
        return PropertyPathValue(PropertyPathType.STRING, str(value), expression)

    def __eq__(self, other: object) -> bool:
        """Equality with float precision for FLOAT and QUANTITY types.

        Two values are equal if they have the same type, the same expression
        (both None or both the same string), and values that round to the
        same value at the configured precision for floats. QUANTITY types
        also require matching unit strings.
        """
        if not isinstance(other, PropertyPathValue):
            return NotImplemented
        if self.type_ != other.type_:
            return False
        if self.expression != other.expression:
            return False
        if self.type_ == PropertyPathType.FLOAT:
            # Use the minimum precision of both values for comparison
            precision = min(self.precision, other.precision)
            return float_values_equal(float(self.value), float(other.value), precision)
        if self.type_ == PropertyPathType.QUANTITY:
            precision = min(self.precision, other.precision)
            value_eq = float_values_equal(float(self.value), float(other.value), precision)
            unit_eq = self.unit == other.unit
            return value_eq and unit_eq
        return self.value == other.value


@runtime_checkable
class DataPath(Protocol):
    """Protocol for path-based data containers with serialization support.

    All concrete DataPath classes implement this protocol, providing factory
    methods for creation from FreeCAD values or serialized dicts, and a
    serialize method for YAML output.
    """

    DATA_PATH_KIND: ClassVar[DataPathKind]

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> DataPath: ...

    @staticmethod
    def from_serialized_value(data: Any) -> DataPath: ...

    def serialize(self) -> dict[str, Any]: ...


def _serialize_path_entries(paths: dict[str, PropertyPathValue]) -> dict[str, Any]:
    """Serialize a dict of path entries to a plain dict suitable for YAML.

    Args:
        paths: Mapping of path strings to PropertyPathValue instances.

    Returns:
        A dict where each value is a dict with keys "type", "value",
        "expression", and "freecad_type" (only if non-None).
    """
    result: dict[str, Any] = {}
    for path, pv in paths.items():
        result[path] = _serialize_path_entry(pv)
    return result


def _serialize_path_entry(pv: PropertyPathValue) -> dict[str, Any]:
    """Serialize one path value to a YAML-compatible dict."""
    entry: dict[str, Any] = {"type": pv.type_.value}
    _add_serialized_path_value(entry, pv)
    _add_optional_path_metadata(entry, pv)
    return entry


def _add_serialized_path_value(entry: dict[str, Any], pv: PropertyPathValue) -> None:
    """Add serialized value field when the path value has persisted data."""
    if pv.type_ == PropertyPathType.QUANTITY:
        entry["value"] = _serialize_quantity_value(pv)
    elif pv.value is not None:
        entry["value"] = pv.value


def _add_optional_path_metadata(entry: dict[str, Any], pv: PropertyPathValue) -> None:
    """Add optional path metadata fields to serialized output."""
    if pv.expression is not None:
        entry["expression"] = pv.expression
    if pv.freecad_type is not None:
        entry["freecad_type"] = pv.freecad_type


def _deserialize_path_entries(raw: dict[str, Any]) -> dict[str, PropertyPathValue]:
    """Deserialize a plain dict back into path entries.

    Args:
        raw: A dict produced by _serialize_path_entries.

    Returns:
        Mapping of path strings to PropertyPathValue instances.
    """
    paths: dict[str, PropertyPathValue] = {}
    for path, entry in raw.items():
        type_name = entry.get("type")
        if type_name is None:
            raise SnapshotFormatError(f"Path entry '{path}' missing required 'type' field")
        try:
            pt = PropertyPathType(type_name)
        except ValueError:
            raise SnapshotFormatError(f"Unknown property path type for '{path}': {type_name}") from None
        value = entry.get("value")
        unit = entry.get("unit")
        if pt == PropertyPathType.QUANTITY:
            value, unit = _deserialize_quantity_value(value, unit)
        paths[path] = PropertyPathValue(
            type_=pt,
            value=value,
            expression=entry.get("expression"),
            freecad_type=entry.get("freecad_type"),
            unit=unit,
        )
    return paths


def _serialize_quantity_value(pv: PropertyPathValue) -> str:
    """Serialize a quantity path value as a canonical text scalar."""
    value_text = repr(float(pv.value))
    if pv.unit:
        return f"{value_text} {pv.unit}"
    return value_text


def _deserialize_quantity_value(value: Any, legacy_unit: Any = None) -> tuple[float, str | None]:
    """Parse a serialized quantity scalar into numeric value and unit."""
    if isinstance(value, str):
        number_text, sep, unit_text = value.partition(" ")
        return float(number_text), unit_text if sep else None
    return float(value), str(legacy_unit) if legacy_unit is not None else None


def _quantity_path_value(value: Any, expression: str | None = None, unit: str | None = None) -> PropertyPathValue:
    """Create a QUANTITY path value from a FreeCAD quantity or value/unit pair."""
    quantity_value = float(getattr(value, "Value", value))
    quantity_unit = unit
    if quantity_unit is None:
        quantity_text = str(value)
        _, sep, parsed_unit = quantity_text.partition(" ")
        quantity_unit = parsed_unit if sep else None
    return PropertyPathValue(PropertyPathType.QUANTITY, quantity_value, expression=expression, unit=quantity_unit)


def _root_expression(expr_map: dict[str, str]) -> str | None:
    """Get the root expression from an expression map using the '.' key.

    Args:
        expr_map: Expression mapping from path keys to expression strings.

    Returns:
        The expression string for the root path, or None if not present.
    """
    return expr_map.get(".")


def _runtime_type_key(value: Any) -> str:
    """Get a module-qualified type key like 'Base.Vector'.

    Args:
        value: Any Python object.

    Returns:
        A string in the format "module.ClassName".
    """
    t = type(value)
    return f"{t.__module__}.{t.__name__}"


def _safe_display_value(value: Any) -> str:
    """Safely convert a value to string, handling exceptions.

    Args:
        value: Any Python object.

    Returns:
        The string representation of the value, or a fallback showing
        the type key if str() raises an exception.
    """
    try:
        return str(value)
    except Exception:  # noqa: BLE001
        return f"<{_runtime_type_key(value)}>"


def _list_item_expression(expr_map: dict[str, str], index: int, item: Any) -> str | None:
    """Get expression for a list item by index or name.

    Checks the expression map for an index key like '[0]' first, then
    falls back to the item's 'Name' attribute if present.

    Args:
        expr_map: Expression mapping.
        index: The list index.
        item: The list item to look up.

    Returns:
        The expression string, or None if not found.
    """
    k_index = f"[{index}]"
    if k_index in expr_map:
        return expr_map[k_index]

    name = getattr(item, "Name", None)
    if isinstance(name, str) and name and name in expr_map:
        return expr_map[name]

    return None


# ---------------------------------------------------------------------------
# DataPath concrete implementations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PrimitiveData:
    """Wraps primitive Python values with a single '.' path entry."""

    DATA_PATH_KIND: ClassVar[DataPathKind] = DataPathKind.Primitive
    paths: dict[str, PropertyPathValue]

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> PrimitiveData:
        """Create PrimitiveData from a FreeCAD/Python primitive value.

        Args:
            value: A primitive value (int, float, str, bool, None).
            expr_map: Expression mapping that may contain a '.' key.

        Returns:
            A new PrimitiveData with the value at the '.' path.
        """
        root_expr = _root_expression(expr_map)
        if _runtime_type_key(value) == "Base.Quantity":
            return PrimitiveData(paths={".": _quantity_path_value(value, root_expr)})
        return PrimitiveData(paths={".": PropertyPathValue.from_python(value, root_expr)})

    @staticmethod
    def from_serialized_value(data: Any) -> PrimitiveData:
        """Create PrimitiveData from a serialized dict.

        Args:
            data: A dict with a 'paths' key containing serialized path entries.

        Returns:
            A new PrimitiveData instance.
        """
        raw_paths = data.get("paths", {})
        return PrimitiveData(paths=_deserialize_path_entries(raw_paths))

    def serialize(self) -> dict[str, Any]:
        """Serialize this PrimitiveData to a dict for YAML output.

        Returns:
            A dict with 'kind' and 'paths' keys.
        """
        return {"kind": self.DATA_PATH_KIND.value, "paths": _serialize_path_entries(self.paths)}


@dataclass(frozen=True)
class VectorData:
    """Wraps a Base.Vector with x/y/z path entries."""

    DATA_PATH_KIND: ClassVar[DataPathKind] = DataPathKind.Vector
    paths: dict[str, PropertyPathValue]

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> VectorData:
        """Create VectorData from a FreeCAD Base.Vector value.

        Extracts x, y, z coordinates and stores them as separate path entries.
        Each coordinate uses its corresponding expression from expr_map if present.
        If the root expression map contains a '.' key, it is stored as a root path entry.

        Args:
            value: A FreeCAD Base.Vector or compatible object.
            expr_map: Expression mapping that may contain 'x', 'y', 'z', and '.' keys.

        Returns:
            A new VectorData instance.
        """
        paths: dict[str, PropertyPathValue] = {
            "x": PropertyPathValue(PropertyPathType.FLOAT, float(value.x), expr_map.get("x")),
            "y": PropertyPathValue(PropertyPathType.FLOAT, float(value.y), expr_map.get("y")),
            "z": PropertyPathValue(PropertyPathType.FLOAT, float(value.z), expr_map.get("z")),
        }
        root_expr = _root_expression(expr_map)
        if root_expr is not None:
            paths["."] = PropertyPathValue(PropertyPathType.NULL, None, root_expr)
        return VectorData(paths=paths)

    @staticmethod
    def from_serialized_value(data: Any) -> VectorData:
        """Create VectorData from a serialized dict.

        Args:
            data: A dict with a 'paths' key containing serialized path entries.

        Returns:
            A new VectorData instance.
        """
        return VectorData(paths=_deserialize_path_entries(data.get("paths", {})))

    def serialize(self) -> dict[str, Any]:
        """Serialize this VectorData to a dict for YAML output.

        Returns:
            A dict with 'kind' and 'paths' keys.
        """
        return {"kind": self.DATA_PATH_KIND.value, "paths": _serialize_path_entries(self.paths)}


@dataclass(frozen=True)
class RotationData:
    """Wraps a Base.Rotation with Angle/Axis.x/Axis.y/Axis.z path entries."""

    DATA_PATH_KIND: ClassVar[DataPathKind] = DataPathKind.Rotation
    paths: dict[str, PropertyPathValue]

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> RotationData:
        """Create RotationData from a FreeCAD Base.Rotation value.

        Extracts Angle and Axis (x, y, z) and stores them as separate path entries.
        If the expression map contains 'Axis', it is stored as a nested path entry.
        If the root expression map contains a '.' key, it is stored as a root path entry.

        Args:
            value: A FreeCAD Base.Rotation or compatible object.
            expr_map: Expression mapping that may contain 'Angle', 'Axis', and '.' keys.

        Returns:
            A new RotationData instance.
        """
        axis = value.Axis
        paths: dict[str, PropertyPathValue] = {
            "Angle": _quantity_path_value(math.degrees(value.Angle), expr_map.get("Angle"), "deg"),
            "Axis.x": PropertyPathValue(PropertyPathType.FLOAT, float(axis.x), expr_map.get("Axis.x")),
            "Axis.y": PropertyPathValue(PropertyPathType.FLOAT, float(axis.y), expr_map.get("Axis.y")),
            "Axis.z": PropertyPathValue(PropertyPathType.FLOAT, float(axis.z), expr_map.get("Axis.z")),
        }
        if "Axis" in expr_map:
            paths["Axis"] = PropertyPathValue(PropertyPathType.NULL, None, expr_map["Axis"])
        root_expr = _root_expression(expr_map)
        if root_expr is not None:
            paths["."] = PropertyPathValue(PropertyPathType.NULL, None, root_expr)
        return RotationData(paths=paths)

    @staticmethod
    def from_serialized_value(data: Any) -> RotationData:
        """Create RotationData from a serialized dict.

        Args:
            data: A dict with a 'paths' key containing serialized path entries.

        Returns:
            A new RotationData instance.
        """
        return RotationData(paths=_deserialize_path_entries(data.get("paths", {})))

    def serialize(self) -> dict[str, Any]:
        """Serialize this RotationData to a dict for YAML output.

        Returns:
            A dict with 'kind' and 'paths' keys.
        """
        return {"kind": self.DATA_PATH_KIND.value, "paths": _serialize_path_entries(self.paths)}


@dataclass(frozen=True)
class PlacementData:
    """Wraps a Base.Placement with Base.x/y/z and Rotation.* path entries."""

    DATA_PATH_KIND: ClassVar[DataPathKind] = DataPathKind.Placement
    paths: dict[str, PropertyPathValue]

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> PlacementData:
        """Create PlacementData from a FreeCAD Base.Placement value.

        Extracts Base coordinates (x, y, z) and Rotation properties (Angle,
        Axis.x, Axis.y, Axis.z) and stores them as separate path entries.
        If the expression map contains 'Rotation' or 'Rotation.Axis' keys,
        they are stored as nested path entries. If the root expression map
        contains a '.' key, it is stored as a root path entry.

        Args:
            value: A FreeCAD Base.Placement or compatible object.
            expr_map: Expression mapping with nested keys for placement components.

        Returns:
            A new PlacementData instance.
        """
        base = value.Base
        rot = value.Rotation
        axis = rot.Axis
        paths: dict[str, PropertyPathValue] = {
            "Base.x": _quantity_path_value(base.x, expr_map.get("Base.x"), "mm"),
            "Base.y": _quantity_path_value(base.y, expr_map.get("Base.y"), "mm"),
            "Base.z": _quantity_path_value(base.z, expr_map.get("Base.z"), "mm"),
            "Rotation.Angle": _quantity_path_value(math.degrees(rot.Angle), expr_map.get("Rotation.Angle"), "deg"),
            "Rotation.Axis.x": PropertyPathValue(
                PropertyPathType.FLOAT, float(axis.x), expr_map.get("Rotation.Axis.x")
            ),
            "Rotation.Axis.y": PropertyPathValue(
                PropertyPathType.FLOAT, float(axis.y), expr_map.get("Rotation.Axis.y")
            ),
            "Rotation.Axis.z": PropertyPathValue(
                PropertyPathType.FLOAT, float(axis.z), expr_map.get("Rotation.Axis.z")
            ),
        }
        if "Rotation" in expr_map:
            paths["Rotation"] = PropertyPathValue(PropertyPathType.NULL, None, expr_map["Rotation"])
        if "Rotation.Axis" in expr_map:
            paths["Rotation.Axis"] = PropertyPathValue(PropertyPathType.NULL, None, expr_map["Rotation.Axis"])
        root_expr = _root_expression(expr_map)
        if root_expr is not None:
            paths["."] = PropertyPathValue(PropertyPathType.NULL, None, root_expr)
        return PlacementData(paths=paths)

    @staticmethod
    def from_serialized_value(data: Any) -> PlacementData:
        """Create PlacementData from a serialized dict.

        Args:
            data: A dict with a 'paths' key containing serialized path entries.

        Returns:
            A new PlacementData instance.
        """
        return PlacementData(paths=_deserialize_path_entries(data.get("paths", {})))

    def serialize(self) -> dict[str, Any]:
        """Serialize this PlacementData to a dict for YAML output.

        Returns:
            A dict with 'kind' and 'paths' keys.
        """
        return {"kind": self.DATA_PATH_KIND.value, "paths": _serialize_path_entries(self.paths)}


@dataclass(frozen=True)
class ConstraintData:
    """Wraps a Sketcher.Constraint with VISIBLE_FIELDS path entries."""

    DATA_PATH_KIND: ClassVar[DataPathKind] = DataPathKind.Constraint
    paths: dict[str, PropertyPathValue]

    VISIBLE_FIELDS = (
        "Type",
        "Name",
        "Value",
        "First",
        "FirstPos",
        "Second",
        "SecondPos",
        "Third",
        "ThirdPos",
        "Driving",
        "IsActive",
    )

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> ConstraintData:
        """Create ConstraintData from a FreeCAD Sketcher.Constraint value.

        Extracts the VISIBLE_FIELDS (Type, Name, Value, First, FirstPos,
        Second, SecondPos, Third, ThirdPos, Driving, IsActive) from the
        constraint object and stores them as separate path entries. None
        values are skipped. Name is also skipped when it is an empty string.
        If the root expression map contains a '.' key, it is stored as a
        root path entry.

        Args:
            value: A FreeCAD Sketcher.Constraint or compatible object.
            expr_map: Expression mapping that may contain a '.' key.

        Returns:
            A new ConstraintData instance.
        """
        paths: dict[str, PropertyPathValue] = {}
        for name in ConstraintData.VISIBLE_FIELDS:
            if not hasattr(value, name):
                continue
            v = getattr(value, name)
            if v is None:
                continue
            if name == "Name" and v == "":
                continue
            paths[name] = PropertyPathValue.from_python(v, None)

        root_expr = _root_expression(expr_map)
        if root_expr is not None:
            paths["."] = PropertyPathValue(PropertyPathType.NULL, None, root_expr)

        return ConstraintData(paths=paths)

    @staticmethod
    def from_serialized_value(data: Any) -> ConstraintData:
        """Create ConstraintData from a serialized dict.

        Args:
            data: A dict with a 'paths' key containing serialized path entries.

        Returns:
            A new ConstraintData instance.
        """
        return ConstraintData(paths=_deserialize_path_entries(data.get("paths", {})))

    def serialize(self) -> dict[str, Any]:
        """Serialize this ConstraintData to a dict for YAML output.

        Returns:
            A dict with 'kind' and 'paths' keys.
        """
        return {"kind": self.DATA_PATH_KIND.value, "paths": _serialize_path_entries(self.paths)}


@dataclass(frozen=True)
class UnknownData:
    """Wraps unknown FreeCAD types with display value and type info."""

    DATA_PATH_KIND: ClassVar[DataPathKind] = DataPathKind.Unknown
    paths: dict[str, PropertyPathValue]

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> UnknownData:
        """Create UnknownData from an unrecognized FreeCAD type.

        Stores the string representation of the value and its runtime type
        key in the root path entry. If the expression map contains a '.'
        key, it is preserved as the root expression.

        Args:
            value: A FreeCAD object not matching any known type.
            expr_map: Expression mapping that may contain a '.' key.

        Returns:
            A new UnknownData instance.
        """
        type_key = _runtime_type_key(value)
        display = _safe_display_value(value)
        return UnknownData(
            paths={
                ".": PropertyPathValue(
                    PropertyPathType.STRING,
                    display,
                    _root_expression(expr_map),
                    freecad_type=type_key,
                )
            },
        )

    @staticmethod
    def from_serialized_value(data: Any) -> UnknownData:
        """Create UnknownData from a serialized dict.

        Args:
            data: A dict with a 'paths' key containing serialized path entries.

        Returns:
            A new UnknownData instance.
        """
        return UnknownData(paths=_deserialize_path_entries(data.get("paths", {})))

    def serialize(self) -> dict[str, Any]:
        """Serialize this UnknownData to a dict for YAML output.

        Returns:
            A dict with 'kind' and 'paths' keys.
        """
        return {"kind": self.DATA_PATH_KIND.value, "paths": _serialize_path_entries(self.paths)}


@dataclass(frozen=True)
class ListData:
    """Wraps a list of items, each as a DataPath, with optional root path entry."""

    DATA_PATH_KIND: ClassVar[DataPathKind] = DataPathKind.List
    paths: dict[str, PropertyPathValue]
    items: list[DataPath]

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> ListData:
        """Create ListData from a FreeCAD/Python list value.

        Recursively converts each list item to the appropriate DataPath subclass
        using data_path_from_freecad_value. Items are keyed by their index in
        the expression map (e.g., '[0]', '[1]') or by their 'Name' attribute.
        If the root expression map contains a '.' key, it is stored as a root
        path entry.

        Args:
            value: A list or tuple of values.
            expr_map: Expression mapping with index or name keys for items.

        Returns:
            A new ListData instance with converted items.
        """
        items: list[DataPath] = []
        for i, item in enumerate(value):
            item_expr = _list_item_expression(expr_map, i, item)
            item_expr_map = {".": item_expr} if item_expr is not None else {}
            items.append(data_path_from_freecad_value(item, item_expr_map))
        list_paths: dict[str, PropertyPathValue] = {}
        root_expr = _root_expression(expr_map)
        if root_expr is not None:
            list_paths["."] = PropertyPathValue(PropertyPathType.NULL, None, root_expr)
        return ListData(paths=list_paths, items=items)

    @staticmethod
    def from_serialized_value(data: Any) -> ListData:
        """Create ListData from a serialized dict.

        Args:
            data: A dict with 'paths' and 'items' keys.

        Returns:
            A new ListData instance with deserialized items.
        """
        raw_items = data.get("items", [])
        return ListData(
            paths=_deserialize_path_entries(data.get("paths", {})),
            items=[data_path_from_serialized(it) for it in raw_items],
        )

    def serialize(self) -> dict[str, Any]:
        """Serialize this ListData to a dict for YAML output.

        Returns:
            A dict with 'kind', 'paths', and 'items' keys.
        """
        return {
            "kind": self.DATA_PATH_KIND.value,
            "paths": _serialize_path_entries(self.paths),
            "items": [item.serialize() for item in self.items],
        }


# ---------------------------------------------------------------------------
# Dispatch maps and constructor functions
# ---------------------------------------------------------------------------

FREECAD_TYPE_MAP: dict[str, type[DataPath]] = {
    "Base.Quantity": PrimitiveData,
    "Base.Vector": VectorData,
    "Base.Rotation": RotationData,
    "Base.Placement": PlacementData,
    "Sketcher.Constraint": ConstraintData,
}

PYTHON_TYPE_MAP: dict[type[Any], type[DataPath]] = {
    bool: PrimitiveData,
    int: PrimitiveData,
    float: PrimitiveData,
    str: PrimitiveData,
    type(None): PrimitiveData,
    list: ListData,
    tuple: ListData,
}

DATA_PATH_KIND_MAP: dict[str, type[DataPath]] = {
    DataPathKind.Primitive.value: PrimitiveData,
    DataPathKind.Vector.value: VectorData,
    DataPathKind.Rotation.value: RotationData,
    DataPathKind.Placement.value: PlacementData,
    DataPathKind.Constraint.value: ConstraintData,
    DataPathKind.List.value: ListData,
    DataPathKind.Unknown.value: UnknownData,
}


def data_path_from_freecad_value(value: Any, expr_map: dict[str, str]) -> DataPath:
    """Dispatch a FreeCAD/Python value to the correct DataPath subclass.

    Checks the PYTHON_TYPE_MAP first for built-in types (bool, int, float,
    str, None, list, tuple), then the FREECAD_TYPE_MAP for known FreeCAD
    types (Base.Quantity, Base.Vector, Base.Rotation, Base.Placement,
    Sketcher.Constraint). Falls back to UnknownData for unrecognized types.

    Args:
        value: The value to convert.
        expr_map: Expression mapping for this value.

    Returns:
        The appropriate DataPath subclass instance.
    """
    py_cls = PYTHON_TYPE_MAP.get(type(value))
    if py_cls is not None:
        return py_cls.from_freecad_value(value, expr_map)

    fc_cls = FREECAD_TYPE_MAP.get(_runtime_type_key(value))
    if fc_cls is not None:
        return fc_cls.from_freecad_value(value, expr_map)

    return UnknownData.from_freecad_value(value, expr_map)


def data_path_from_serialized(data: dict[str, Any]) -> DataPath:
    """Deserialize a dict back into the correct DataPath subclass.

    Uses the 'kind' key in the data dict to look up the appropriate
    DataPath class in DATA_PATH_KIND_MAP.

    Args:
        data: A serialized dict with 'kind' and 'paths' keys.

    Returns:
        The appropriate DataPath subclass instance.
    """
    kind = data.get("kind")
    if kind is None:
        raise SnapshotFormatError("Property payload missing required 'kind' field")
    cls = DATA_PATH_KIND_MAP.get(kind)
    if cls is None:
        raise SnapshotFormatError(f"Unknown data path kind: {kind}")
    return cls.from_serialized_value(data)


__all__ = [
    "DataPathKind",
    "SnapshotFormatError",
    "PropertyPathType",
    "PropertyPathValue",
    "DataPath",
    "PrimitiveData",
    "VectorData",
    "RotationData",
    "PlacementData",
    "ConstraintData",
    "UnknownData",
    "ListData",
    "data_path_from_freecad_value",
    "data_path_from_serialized",
    "FREECAD_TYPE_MAP",
    "PYTHON_TYPE_MAP",
    "DATA_PATH_KIND_MAP",
]
