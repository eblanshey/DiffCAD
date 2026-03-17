# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains domain models for representing FreeCAD
# property values, including Vector, Rotation, Placement, and the unified Property
# type. It also includes type detection logic for converting FreeCAD property values
# to domain models.
"""Property value models for FreeCAD document snapshots."""

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, ClassVar


logger = logging.getLogger(__name__)


class PropertyType(Enum):
    """Types of FreeCAD properties."""

    # TODO: switch to explicit values; determine which values to use (hard coded, or taken from freecad?)
    # Basic types
    BOOL = auto()
    INT = auto()
    FLOAT = auto()
    STRING = auto()

    # Vector-based types
    VECTOR = auto()  # x, y, z
    PLACEMENT = auto()  # position + rotation

    # Compound types
    EXPRESSION = auto()  # Expression string

    # Special types (deferred for later phases)
    SHAPE = auto()  # Geometry data
    MATERIAL = auto()  # Material assignment
    UNKNOWN = auto()


# Registry of property type handlers. Consulted by Property.from_freecad_property() to delegate
# complex type conversion (e.g., "Position" -> Vector, "Placement" -> Placement).
# To add a new type: inherit from PropertyHandler, define PROPERTY_NAMES, implement
# from_freecad_value(), and decorate with @register_handler.
_PROPERTY_HANDLERS: list[type["PropertyHandler"]] = []


def register_handler(cls: type) -> type:
    """Decorator to register a property handler class."""
    _PROPERTY_HANDLERS.append(cls)
    return cls


class PropertyHandler:
    """Base class for property type handlers."""

    PROPERTY_NAMES: ClassVar[frozenset[str]] = frozenset()

    @classmethod
    def handles(cls, prop_name: str) -> bool:
        return prop_name in cls.PROPERTY_NAMES

    @classmethod
    def from_freecad_value(cls, value: Any, expression: str | None = None) -> "Property":
        raise NotImplementedError("Subclasses must implement from_freecad_value")


@register_handler
@dataclass(frozen=True)
class Vector(PropertyHandler):
    """A 3D vector representing position or direction.

    Attributes:
        x: X coordinate
        y: Y coordinate
        z: Z coordinate
    """

    PROPERTY_NAMES: ClassVar[frozenset[str]] = frozenset(
        {"Position", "Axis", "Direction", "Normal", "Translation", "StartPoint", "EndPoint"}
    )

    x: float
    y: float
    z: float

    def __str__(self) -> str:
        return f"({self.x}, {self.y}, {self.z})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector):
            return NotImplemented
        # Use approximate equality for floats
        tolerance = 1e-9
        return (
            abs(self.x - other.x) < tolerance
            and abs(self.y - other.y) < tolerance
            and abs(self.z - other.z) < tolerance
        )

    @classmethod
    def from_freecad_value(cls, value: Any, expression: str | None = None) -> "Property":
        try:
            return Property(
                type_=PropertyType.VECTOR,
                value=cls(x=float(value.x), y=float(value.y), z=float(value.z)),
                expression=expression,
            )
        except Exception as e:
            logger.warning("Failed to extract Vector property: %s", e)
            raise


@dataclass(frozen=True)
class Rotation:
    """A rotation represented by axis-angle notation.

    FreeCAD uses axis-angle representation internally. A rotation consists of
    an axis (unit vector) and an angle (in degrees).

    Attributes:
        axis_x: X component of rotation axis
        axis_y: Y component of rotation axis
        axis_z: Z component of rotation axis
        angle_degrees: Rotation angle in degrees
    """

    axis_x: float
    axis_y: float
    axis_z: float
    angle_degrees: float

    def __str__(self) -> str:
        return f"Axis=({self.axis_x}, {self.axis_y}, {self.axis_z}), Angle={self.angle_degrees}\u00b0"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rotation):
            return NotImplemented
        # Use approximate equality for floats
        tolerance = 1e-9
        return (
            abs(self.axis_x - other.axis_x) < tolerance
            and abs(self.axis_y - other.axis_y) < tolerance
            and abs(self.axis_z - other.axis_z) < tolerance
            and abs(self.angle_degrees - other.angle_degrees) < tolerance
        )

    @classmethod
    def identity(cls) -> "Rotation":
        """Create an identity rotation (no rotation)."""
        return cls(axis_x=0.0, axis_y=0.0, axis_z=1.0, angle_degrees=0.0)


@register_handler
@dataclass(frozen=True)
class Placement(PropertyHandler):
    """A placement combining position and orientation.

    Represents a transformation in 3D space, combining a position vector
    and a rotation. This is the fundamental way FreeCAD positions objects.

    Attributes:
        position: The position vector
        rotation: The rotation (axis-angle)
    """

    PROPERTY_NAMES: ClassVar[frozenset[str]] = frozenset({"Placement"})

    position: Vector
    rotation: Rotation

    def __str__(self) -> str:
        return f"Pos={self.position}, Rot={self.rotation}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Placement):
            return NotImplemented
        return self.position == other.position and self.rotation == other.rotation

    @classmethod
    def identity(cls) -> "Placement":
        """Create an identity placement (origin, no rotation)."""
        return cls(position=Vector(0.0, 0.0, 0.0), rotation=Rotation.identity())

    @classmethod
    def from_freecad_value(cls, value: Any, expression: str | None = None) -> "Property":
        try:
            pos = getattr(value, "Position", None)
            rot = getattr(value, "Rotation", None)
            if not pos or not rot:
                raise ValueError("Placement missing Position or Rotation")
            return Property(
                type_=PropertyType.PLACEMENT,
                value=cls(
                    position=Vector(x=float(pos.x), y=float(pos.y), z=float(pos.z)),
                    rotation=Rotation(
                        axis_x=float(rot.AxisX),
                        axis_y=float(rot.AxisY),
                        axis_z=float(rot.AxisZ),
                        angle_degrees=float(rot.Angle),
                    ),
                ),
                expression=expression,
            )
        except Exception as e:
            logger.warning("Failed to extract Placement property: %s", e)
            raise


@dataclass(frozen=True)
class Property:
    """A value of a FreeCAD property.

    This is a union type that can represent any FreeCAD property value.
    It includes type information to enable proper comparison and display.

    Attributes:
        type_: The type of this property value
        value: The actual value (type depends on type_)
        expression: Optional expression if this value is driven by an expression
    """

    type_: PropertyType
    value: Any
    expression: str | None = None

    def __str__(self) -> str:
        """String representation suitable for display."""
        if self.expression:
            return f"{self.value} (expr: {self.expression})"
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        """Compare two property values for equality.

        Two property values are equal if they have the same type, value, and expression.
        Expression differences are considered significant even if values are the same.
        """
        if not isinstance(other, Property):
            return NotImplemented

        # Different types are never equal
        if self.type_ != other.type_:
            return False

        # Expressions must match (if one has an expression and the other doesn't, they're different)
        if self.expression != other.expression:
            return False

        # For floats, use approximate equality
        if self.type_ == PropertyType.FLOAT:
            tolerance = 1e-9
            return bool(abs(self.value - other.value) < tolerance)

        return bool(self.value == other.value)

    @classmethod
    def create(cls, type_: PropertyType, value: Any, expression: str | None = None) -> "Property":
        """Create a Property with proper type handling.

        This factory method accepts structured data (tuples/dicts) as the value
        parameter and internally creates the appropriate domain objects.

        Args:
            type_: The property type
            value: The value in structured form:
                - BOOL, INT, FLOAT, STRING: direct value
                - VECTOR: tuple (x, y, z)
                - PLACEMENT: dict {"position": (x, y, z), "rotation": (ax, ay, az, angle)}
            expression: Optional expression that drives this value

        Returns:
            A Property instance with properly structured value

        Examples:
            >>> Property.create(PropertyType.BOOL, True)
            >>> Property.create(PropertyType.INT, 42)
            >>> Property.create(PropertyType.FLOAT, 3.14)
            >>> Property.create(PropertyType.STRING, "hello")
            >>> Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
            >>> Property.create(
            ...     PropertyType.PLACEMENT, {"position": (0, 0, 0), "rotation": (0, 0, 1, 90)}
            ... )
        """
        if type_ == PropertyType.BOOL:
            return cls(type_=type_, value=bool(value), expression=expression)
        elif type_ == PropertyType.INT:
            return cls(type_=type_, value=int(value), expression=expression)
        elif type_ == PropertyType.FLOAT:
            return cls(type_=type_, value=float(value), expression=expression)
        elif type_ == PropertyType.STRING:
            return cls(type_=type_, value=str(value), expression=expression)
        elif type_ == PropertyType.VECTOR:
            # value is expected to be a tuple (x, y, z)
            x, y, z = value
            return cls(type_=type_, value=Vector(x=x, y=y, z=z), expression=expression)
        elif type_ == PropertyType.PLACEMENT:
            # value is expected to be a dict {"position": (x,y,z), "rotation": (ax,ay,az,angle)}
            pos = value["position"]
            rot = value["rotation"]
            return cls(
                type_=type_,
                value=Placement(
                    position=Vector(x=pos[0], y=pos[1], z=pos[2]),
                    rotation=Rotation(axis_x=rot[0], axis_y=rot[1], axis_z=rot[2], angle_degrees=rot[3]),
                ),
                expression=expression,
            )
        else:
            # For unknown/expression/shape/material types, store value as-is
            return cls(type_=type_, value=value, expression=expression)

    @staticmethod
    def from_freecad_property(prop_name: str, value: Any, expression: str | None = None) -> "Property":
        """Create a Property from a FreeCAD property value.

        This factory method delegates to registered handlers for complex types
        (VECTOR, PLACEMENT) and falls back to type inference for basic types.

        Args:
            prop_name: The FreeCAD property name (e.g., "Placement", "Position", "Length")
            value: The raw value from the FreeCAD object
            expression: Optional expression that drives this value

        Returns:
            A Property with properly detected type and converted value
        """
        # Try registered handlers first
        for handler in _PROPERTY_HANDLERS:
            if handler.handles(prop_name):
                return handler.from_freecad_value(value, expression)

        # Fall back to type inference from value
        prop_type = Property._infer_type_from_value(value)
        return Property.create(prop_type, value, expression=expression)

    @staticmethod
    def _infer_type_from_value(val: Any) -> PropertyType:
        """Infer PropertyType from a Python value."""
        if isinstance(val, bool):
            return PropertyType.BOOL
        elif isinstance(val, int):
            return PropertyType.INT
        elif isinstance(val, float):
            return PropertyType.FLOAT
        elif val is None or isinstance(val, str):
            return PropertyType.STRING
        else:
            # For complex types, default to STRING
            return PropertyType.STRING


__all__ = ["Property", "PropertyType", "Vector", "Rotation", "Placement"]
