# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: DataPath-based Property wrapper for path-based property values.
"""DataPath-based Property wrapper for path-based property values.

This module provides the Property class, which wraps a DataPath value and
a property group (e.g., "Base", "Data", "View"). It supports creation from
FreeCAD values via expression maps, and serialization/deserialization for
YAML persistence with deterministic output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .data_path import (
    DataPath,
    data_path_from_freecad_value,
    data_path_from_serialized,
)


@dataclass(frozen=True)
class Property:
    """A FreeCAD property represented via path-based DataPath model.

    The value is always a DataPath (PrimitiveData, VectorData, etc.),
    which provides deterministic serialization and expression preservation.

    Attributes:
        value: The DataPath representing the property's structured value
        group: The FreeCAD property group (e.g., "Base", "Data", "View")
    """

    value: DataPath
    group: str = "Base"

    @classmethod
    def from_freecad(cls, fc_value: Any, expr_map: dict[str, str], group: str = "Base") -> Property:
        """Create a Property from a FreeCAD value with expression map.

        Args:
            fc_value: The raw FreeCAD property value
            expr_map: Expression map from _build_expression_map_for_property
            group: The FreeCAD property group

        Returns:
            A Property with a DataPath-based value
        """
        return cls(value=data_path_from_freecad_value(fc_value, expr_map), group=group)

    def to_serialized(self) -> dict[str, Any]:
        """Serialize this property to a dict for YAML persistence.

        Returns:
            Dict with kind, paths/items, and group keys
        """
        payload = self.value.serialize()
        payload["group"] = self.group
        return payload

    @classmethod
    def from_serialized(cls, data: dict[str, Any]) -> Property:
        """Deserialize a property from a serialized dict.

        Args:
            data: Dict with kind, paths/items, and group keys

        Returns:
            A Property with the restored DataPath value
        """
        return cls(value=data_path_from_serialized(data), group=data.get("group", "Base"))


__all__ = ["Property"]
