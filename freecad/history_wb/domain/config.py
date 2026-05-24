# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides hard-coded configuration defaults for the
# diff workbench, including excluded types, excluded properties, and float precision.
# These values serve as fallback defaults when no user preferences are configured.
"""Hard-coded configuration defaults."""

# Type IDs to exclude from diff computation by default
# Objects of these types and their children are removed from the diff view
# Decision: Start permissive - only exclude truly auto-generated types
EXCLUDED_TYPES = [
    "App::Origin",  # Origin elements (planes, axes) are auto-generated
]

# Property names to exclude from diff comparison
# These properties often change without meaningful semantic differences
# Auto-excluded properties (always excluded, even if user manually sets them)
EXCLUDED_PROPERTIES = [
    # Timestamp/change tracking
    "TimeStamp",
    "LastModified",
    # Auto-generated labels
    "Label2",  # Auto-generated secondary label
    # Version tracking
    "_ElementMapVersion",  # Internal version tracking
    # Internal state tracking
    "EditorMode",  # UI-only property
    "EditorObject",  # UI-only property
    "Proxy",  # Contains custom logic not useful for diffing, e.g. assembly joint logic
    "SvgIncluded",  # Techdraw cache
    "PatIncluded",  # Techdraw cache
]

# Configurable float precision for comparison and display (matching FreeCAD's lowPrec)
FLOAT_PRECISION = 2

# Type-specific property exclusions
# Maps FreeCAD type IDs to lists of property names to exclude for that type only.
# This allows excluding a property for one type while keeping it visible for others.
EXCLUDED_PROPERTIES_BY_TYPE: dict[str, list[str]] = {
    "TechDraw::DrawSVGTemplate": ["PageResult"],
}
