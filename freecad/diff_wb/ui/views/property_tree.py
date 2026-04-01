"""File responsibility: Helper functions for building property trees and displaying properties.

This module provides utility functions for:
- Converting CamelCase property names to space-separated names (matching FreeCAD display)
- Property tree building logic (for future phases)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...utils import Log


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

    Only expands explicitly approved types:
    - Explicit types (Placement, Rotation) with named children
    - Vector-like objects (x, y, z attributes)
    - Lists/tuples (by index)
    - Dicts (by key)

    All other types (including FreeCAD C++ wrapped objects like Constraint) are
    treated as leaf nodes and converted to strings.

    Note: This function is part of Phase 4 implementation but is included
    here for forward compatibility and to keep related functionality together.

    Args:
        name: The property name (used to determine explicit expansion type).
        value: The property value to expand.

    Returns:
        List of (child_name, child_value) tuples for expandable properties.
    """
    Log.debug(f"[DEBUG] get_property_children called: name={name!r}, value={value!r}, type={type(value).__name__}")

    if value is None:
        Log.debug("[DEBUG]   value is None, returning []")
        return []

    # Exclude Python primitive types (they should be leaf nodes, not expanded)
    if isinstance(value, (int, float, bool, str, bytes)):
        Log.debug(f"[DEBUG]   value is primitive type ({type(value).__name__}), returning []")
        return []

    # 1. Explicit types with known structure
    if name == "Placement":
        Log.debug("[DEBUG]   Expanding as Placement")
        result = _expand_placement(value)
        Log.debug(f"[DEBUG]   Placement expansion result: {result}")
        return result
    if name == "Rotation":
        Log.debug("[DEBUG]   Expanding as Rotation")
        result = _expand_rotation(value)
        Log.debug(f"[DEBUG]   Rotation expansion result: {result}")
        return result

    # 2. Vector-like objects (has x, y, z)
    if hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z"):
        Log.debug("[DEBUG]   Expanding as vector-like object")
        result = [("x", value.x), ("y", value.y), ("z", value.z)]
        Log.debug(f"[DEBUG]   Vector expansion result: {result}")
        return result

    # 3. Lists/tuples - expand by index
    if isinstance(value, (list, tuple)) and len(value) > 0:
        Log.debug(f"[DEBUG]   Expanding as list/tuple with {len(value)} items")
        result = [(str(i), v) for i, v in enumerate(value)]
        Log.debug(f"[DEBUG]   List expansion result: {len(result)} children")
        return result

    # 4. Dicts - expand by key
    if isinstance(value, dict) and len(value) > 0:
        Log.debug(f"[DEBUG]   Expanding as dict with {len(value)} keys")
        result = [(str(k), v) for k, v in value.items()]
        Log.debug(f"[DEBUG]   Dict expansion result: {len(result)} children")
        return result

    # All other types are not expanded (including FreeCAD C++ wrapped objects)
    Log.debug(f"[DEBUG]   value is not an approved expandable type ({type(value).__name__}), returning []")
    return []


def is_expandable(value: Any, feature_name: str = "", property_name: str = "") -> bool:
    """Check if value should display as expandable (has children).

    Only explicitly approved types are expandable:
    - Lists/tuples
    - Dicts
    - Vector-like objects (x, y, z)

    All other types (including Placement, Rotation, and FreeCAD C++ wrapped objects)
    are handled by get_property_children() based on the property name.

    Args:
        value: The property value to check.
        feature_name: Name of the FreeCAD feature (for debug logging).
        property_name: Name of the property (for debug logging).

    Returns:
        True if the value should be displayed as expandable, False otherwise.
    """
    # Debug logging
    Log.debug(
        f"[DEBUG] is_expandable: feature={feature_name!r}, property={property_name!r}, "
        f"value_type={type(value).__name__}"
    )

    if value is None:
        Log.debug("  -> False (None)")
        return False

    # Exclude Python primitive types
    if isinstance(value, (int, float, bool, str, bytes)):
        Log.debug("  -> False (primitive type)")
        return False

    # Approved expandable types
    if isinstance(value, (list, tuple)) and len(value) > 0:
        Log.debug(f"  -> True (list/tuple with {len(value)} items)")
        return True
    if isinstance(value, dict) and len(value) > 0:
        Log.debug(f"  -> True (dict with {len(value)} keys)")
        return True
    if hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z"):
        Log.debug("  -> True (vector-like)")
        return True

    # All other types are not directly expandable here
    # (Placement/Rotation expansion is handled by property name in get_property_children)
    Log.debug("  -> False (not an approved expandable type)")
    return False


def _expand_placement(value: Any) -> list[tuple[str, Any]]:
    """Expand a Placement property into its components.

    FreeCAD Placement has:
    - position: Vector (position)
    - rotation: Rotation object

    Args:
        value: A Placement object.

    Returns:
        List of (component_name, component_value) tuples.
    """
    result = []

    # Try both 'position' and 'Base' attributes (different FreeCAD versions/APIs)
    if hasattr(value, "position") and value.position is not None:
        result.append(("Position", value.position))
    elif hasattr(value, "Base") and value.Base is not None:
        result.append(("Base", value.Base))

    # Try both 'rotation' and 'Rotation' attributes
    if hasattr(value, "rotation") and value.rotation is not None:
        result.append(("Rotation", value.rotation))
    elif hasattr(value, "Rotation") and value.Rotation is not None:
        result.append(("Rotation", value.Rotation))

    return result


def _expand_rotation(value: Any) -> list[tuple[str, Any]]:
    """Expand a Rotation property into its components.

    Args:
        value: A Rotation object with angle/axis properties.

    Returns:
        List of (component_name, component_value) tuples.
    """
    result = []

    # Try both 'angle' and 'Angle' attributes
    if hasattr(value, "angle") and value.angle is not None:
        result.append(("Angle", value.angle))
    elif hasattr(value, "Angle") and value.Angle is not None:
        result.append(("Angle", value.Angle))

    # Try both 'axis' and 'Axis' attributes
    if hasattr(value, "axis") and value.axis is not None:
        result.append(("Axis", value.axis))
    elif hasattr(value, "Axis") and value.Axis is not None:
        result.append(("Axis", value.Axis))

    return result
