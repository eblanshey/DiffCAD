# SPDX-License-Identifier: LGPL-3.0-or-later
"""Domain model for FreeCAD property values.

This module provides a unified representation of FreeCAD property values,
supporting all common property types found in PartDesign and Part workbenches.
It also includes domain models for 3D vectors and placements.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class PropertyType(Enum):
    """Types of FreeCAD properties."""

    # Basic types
    BOOL = auto()
    INT = auto()
    FLOAT = auto()
    STRING = auto()

    # Vector-based types
    VECTOR = auto()  # x, y, z
    PLACEMENT = auto()  # position + rotation

    # Compound types
    LINK = auto()  # Reference to another object
    EXPRESSION = auto()  # Expression string

    # Special types (deferred for later phases)
    SHAPE = auto()  # Geometry data
    MATERIAL = auto()  # Material assignment
    UNKNOWN = auto()


@dataclass(frozen=True)
class Vector:
    """A 3D vector representing position or direction.

    Attributes:
        x: X coordinate
        y: Y coordinate
        z: Z coordinate
    """

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


@dataclass(frozen=True)
class Placement:
    """A placement combining position and orientation.

    Represents a transformation in 3D space, combining a position vector
    and a rotation. This is the fundamental way FreeCAD positions objects.

    Attributes:
        position: The position vector
        rotation: The rotation (axis-angle)
    """

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


@dataclass(frozen=True)
class PropertyValue:
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
            return f"{self.value} (via {self.expression})"
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        """Compare two property values for equality.

        Two property values are equal if they have the same type, value, and expression.
        Expression differences are considered significant even if values are the same.
        """
        if not isinstance(other, PropertyValue):
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
    def create(cls, type_: PropertyType, value: Any, expression: str | None = None) -> "PropertyValue":
        """Create a PropertyValue with proper type handling.

        This factory method accepts structured data (tuples/dicts) as the value
        parameter and internally creates the appropriate domain objects.

        Args:
            type_: The property type
            value: The value in structured form:
                - BOOL, INT, FLOAT, STRING, LINK: direct value
                - VECTOR: tuple (x, y, z)
                - PLACEMENT: dict {"position": (x, y, z), "rotation": (ax, ay, az, angle)}
            expression: Optional expression that drives this value

        Returns:
            A PropertyValue instance with properly structured value

        Examples:
            >>> PropertyValue.create(PropertyType.BOOL, True)
            >>> PropertyValue.create(PropertyType.INT, 42)
            >>> PropertyValue.create(PropertyType.FLOAT, 3.14)
            >>> PropertyValue.create(PropertyType.STRING, "hello")
            >>> PropertyValue.create(PropertyType.LINK, "Body")
            >>> PropertyValue.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
            >>> PropertyValue.create(
            ...     PropertyType.PLACEMENT, {"position": (0, 0, 0), "rotation": (0, 0, 1, 90)}
            ... )
        """
        if type_ == PropertyType.BOOL:
            return cls(type_=type_, value=bool(value), expression=expression)
        elif type_ == PropertyType.INT:
            return cls(type_=type_, value=int(value), expression=expression)
        elif type_ == PropertyType.FLOAT:
            return cls(type_=type_, value=float(value), expression=expression)
        elif type_ in (PropertyType.STRING, PropertyType.LINK):
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
    def from_freecad_property(prop_name: str, value: Any, expression: str | None = None) -> "PropertyValue":
        """Create a PropertyValue from a FreeCAD property value.

        This factory method handles type detection based on property names
        and value types, encapsulating all FreeCAD-specific logic in the domain layer.

        Args:
            prop_name: The FreeCAD property name (e.g., "Placement", "Position", "Length")
            value: The raw value from the FreeCAD object
            expression: Optional expression that drives this value

        Returns:
            A PropertyValue with properly detected type and converted value

        Examples:
            >>> # Placement property
            >>> class MockPlacement:
            ...     class Position:
            ...         x, y, z = 1.0, 2.0, 3.0
            ...
            ...     class Rotation:
            ...         AxisX, AxisY, AxisZ, Angle = 0, 0, 1, 90
            ...
            ...     Position = Position()
            ...     Rotation = Rotation()
            >>> PropertyValue.from_freecad_property("Placement", MockPlacement())
            PropertyValue(type_=PropertyType.PLACEMENT, value=Placement(...))

            >>> # Position property (vector)
            >>> class MockVector:
            ...     x, y, z = 1.0, 2.0, 3.0
            >>> PropertyValue.from_freecad_property("Position", MockVector())
            PropertyValue(type_=PropertyType.VECTOR, value=Vector(x=1.0, y=2.0, z=3.0))

            >>> # Simple float property
            >>> PropertyValue.from_freecad_property("Length", 10.5)
            PropertyValue(type_=PropertyType.FLOAT, value=10.5)
        """
        # FreeCAD property names that indicate VECTOR type
        VECTOR_PROPERTY_NAMES: frozenset[str] = frozenset(
            {"Position", "Axis", "Direction", "Normal", "Translation", "StartPoint", "EndPoint"}
        )

        # FreeCAD property names that indicate PLACEMENT type
        PLACEMENT_PROPERTY_NAMES: frozenset[str] = frozenset({"Placement"})

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

        # Property name-based type detection (most reliable for FreeCAD)
        if prop_name in PLACEMENT_PROPERTY_NAMES:
            # Extract Placement from FreeCAD object
            pos = getattr(value, "Position", None)
            rot = getattr(value, "Rotation", None)
            if pos and rot:
                pos_x = float(getattr(pos, "x", 0))
                pos_y = float(getattr(pos, "y", 0))
                pos_z = float(getattr(pos, "z", 0))
                rot_ax = float(getattr(rot, "AxisX", 0))
                rot_ay = float(getattr(rot, "AxisY", 0))
                rot_az = float(getattr(rot, "AxisZ", 0))
                rot_angle = float(getattr(rot, "Angle", 0))
                return PropertyValue.create(
                    PropertyType.PLACEMENT,
                    {"position": (pos_x, pos_y, pos_z), "rotation": (rot_ax, rot_ay, rot_az, rot_angle)},
                    expression=expression,
                )
            # If we can't extract placement data, fall through to value-based detection

        # Vector-like property names
        if prop_name in VECTOR_PROPERTY_NAMES and hasattr(value, "x"):
            vec_x = float(getattr(value, "x", 0))
            vec_y = float(getattr(value, "y", 0))
            vec_z = float(getattr(value, "z", 0))
            return PropertyValue.create(PropertyType.VECTOR, (vec_x, vec_y, vec_z), expression=expression)

        # Fall back to type inference from value
        prop_type = _infer_type_from_value(value)
        return PropertyValue.create(prop_type, value, expression=expression)


def make_property_value(type_: PropertyType, value: Any, **kwargs: Any) -> PropertyValue:
    """Factory function to create a PropertyValue with proper type handling.

    This is an alias for PropertyValue.create() for backward compatibility.

    Args:
        type_: The property type
        value: The value
        **kwargs: Additional arguments (e.g., expression)

    Returns:
        A PropertyValue instance
    """
    return PropertyValue.create(type_=type_, value=value, **kwargs)
