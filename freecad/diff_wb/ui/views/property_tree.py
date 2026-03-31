"""File responsibility: Helper functions for building property trees and displaying properties.

This module provides utility functions for:
- Converting CamelCase property names to space-separated names (matching FreeCAD display)
- Property tree building logic (for future phases)
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from typing import Any


def _camelcase_to_spaces(name: str) -> str:
    """Insert spaces before uppercase letters and digits, matching FreeCAD display.

    This function converts CamelCase property names to space-separated names
    to match how FreeCAD displays property names in its UI (e.g., "Saved Geometry"
    instead of "SavedGeometry").

    Args:
        name: The CamelCase property name to convert.

    Returns:
        The property name with spaces inserted before uppercase letters or digits
        (except at the start or when following another uppercase or digit).
    """
    if not name:
        return name

    result = [name[0]]  # Start with first character
    upper_sequence_start = 0 if name[0].isupper() else -1

    for i in range(1, len(name)):
        char = name[i]
        prev_char = name[i - 1]

        if char.isupper():
            # If we hit an uppercase after lowercase, add space (e.g., "SavedGeometry" -> before G)
            if prev_char.islower():
                result.append(" ")
            # If we were in an uppercase sequence and now at end of sequence (next is lowercase),
            # add space. This handles "XMLDoc" -> "XML Doc"
            elif upper_sequence_start >= 0 and i + 1 < len(name) and name[i + 1].islower():
                result.append(" ")
                upper_sequence_start = -1  # Reset
            upper_sequence_start = i
        elif char.islower():
            upper_sequence_start = -1
        elif char.isdigit():
            # Add space before digit if preceded by letter
            if prev_char.isalpha():
                result.append(" ")
            upper_sequence_start = -1
        else:
            upper_sequence_start = -1

        result.append(char)

    return "".join(result)


def get_property_children(name: str, value: Any) -> list[tuple[str, Any]]:
    """Get children for any property value.

    Recursively expands:
    - Explicit types (Placement, Rotation) with named children
    - Vector-like objects (x, y, z attributes)
    - Lists/tuples (by index)
    - Dicts (by key)
    - Objects with __dict__ (by attribute)

    Note: This function is part of Phase 4 implementation but is included
    here for forward compatibility and to keep related functionality together.

    Args:
        name: The property name (used to determine explicit expansion type).
        value: The property value to expand.

    Returns:
        List of (child_name, child_value) tuples for expandable properties.
    """
    if value is None:
        return []

    # 1. Explicit types with known structure
    if name == "Placement":
        return _expand_placement(value)
    if name == "Rotation":
        return _expand_rotation(value)
    if name == "Material":
        return _expand_material(value)

    # 2. Vector-like objects (has x, y, z)
    if hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z"):
        return [("x", value.x), ("y", value.y), ("z", value.z)]

    # 3. Lists/tuples - expand by index
    if isinstance(value, (list, tuple)) and len(value) > 0:
        return [(f"[{i}]", v) for i, v in enumerate(value)]

    # 4. Dicts - expand by key
    if isinstance(value, dict) and len(value) > 0:
        return [(str(k), v) for k, v in value.items()]

    # 5. Objects with __dict__ - expand public attributes
    attrs = getattr(value, "__dict__", None)
    if attrs:
        return [(k, v) for k, v in attrs.items() if not k.startswith("_")]

    return []


def is_expandable(value: Any) -> bool:
    """Check if value should display as expandable (has children).

    Args:
        value: The property value to check.

    Returns:
        True if the value should be displayed as expandable, False otherwise.
    """
    if value is None:
        return False

    # Check each expansion type
    if isinstance(value, (list, tuple)) and len(value) > 0:
        return True
    if isinstance(value, dict) and len(value) > 0:
        return True
    if hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z"):
        return True
    return bool(getattr(value, "__dict__", None))


def _expand_placement(value: Any) -> list[tuple[str, Any]]:
    """Expand a Placement property into its components.

    Args:
        value: A Placement object with Position, Rotation, and Axis properties.

    Returns:
        List of (component_name, component_value) tuples.
    """
    result = []

    # Try to get Position (Vector)
    if hasattr(value, "Position") and value.Position is not None:
        result.append(("Position", value.Position))

    # Try to get Rotation (Rotation/Angle)
    if hasattr(value, "Rotation") and value.Rotation is not None:
        result.append(("Rotation", value.Rotation))

    # Try to get Axis (Vector)
    if hasattr(value, "Axis") and value.Axis is not None:
        result.append(("Axis", value.Axis))

    return result


def _expand_rotation(value: Any) -> list[tuple[str, Any]]:
    """Expand a Rotation property into its components.

    Args:
        value: A Rotation object with Angle and Axis properties.

    Returns:
        List of (component_name, component_value) tuples.
    """
    result = []

    # Try to get Angle
    if hasattr(value, "Angle") and value.Angle is not None:
        result.append(("Angle", value.Angle))

    # Try to get Axis (Vector)
    if hasattr(value, "Axis") and value.Axis is not None:
        result.append(("Axis", value.Axis))

    return result


def _expand_material(value: Any) -> list[tuple[str, Any]]:
    """Expand a Material property into its components.

    Args:
        value: A Material object (dict-like or object with __dict__).

    Returns:
        List of (component_name, component_value) tuples.
    """
    # Material is typically a dict
    if isinstance(value, dict):
        return [(str(k), v) for k, v in value.items()]

    # Or an object with __dict__
    attrs = getattr(value, "__dict__", None)
    if attrs:
        return [(k, v) for k, v in attrs.items() if not k.startswith("_")]

    return []
