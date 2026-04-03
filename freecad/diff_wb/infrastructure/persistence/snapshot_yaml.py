# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides YAML serialization and deserialization
# for Snapshot objects. It follows the ProjectState.md YAML format specification.
"""YAML persistence for snapshot storage and retrieval."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from freecad.diff_wb.domain import Property, PropertyType, Snapshot, TreeNode


class SnapshotYamlSerializer:
    """Serializer for snapshot YAML format.

    Provides methods to serialize and deserialize Snapshot objects to/from
    YAML files following the ProjectState.md format specification.

    YAML format:
        v: snapshot_version
        timestamp: [UTC timestamp]
        uid: [document UUID]
        objects:
        - id: 43
          type_id: Sketcher::SketchObject
          name: Sketch
          after: [sibling name or null]
          path: [full path for text diff readability]
          properties: {...}
    """

    SNAPSHOT_VERSION = 1

    @staticmethod
    def to_yaml(snapshot: Snapshot, path: Path) -> None:
        """Serialize a Snapshot to YAML format.

        Args:
            snapshot: The snapshot to serialize
            path: The path to write the YAML file to
        """
        # Sort nodes by ID (as per spec: "objects are stored in order of the integer id")
        sorted_nodes = sorted(snapshot.nodes, key=lambda n: n.id)

        objects = []
        for node in sorted_nodes:
            obj_dict = {
                "id": node.id,
                "type_id": node.type_id,
                "name": node.name,
                "after": node.after,
                "path": node.path,
                "properties": SnapshotYamlSerializer._serialize_properties(node.properties),
            }
            objects.append(obj_dict)

        data = {
            "v": SnapshotYamlSerializer.SNAPSHOT_VERSION,
            "timestamp": snapshot.timestamp.isoformat(),
            "uid": snapshot.snapshot_id,
            "objects": objects,
        }

        # Write YAML with explicit styling for better text diff readability
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    @staticmethod
    def from_yaml(path: Path) -> Snapshot:
        """Deserialize a Snapshot from YAML format.

        Args:
            path: The path to read the YAML file from

        Returns:
            The deserialized Snapshot object
        """
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Parse timestamp (yaml.safe_load may parse ISO strings as datetime objects)
        timestamp_raw = data.get("timestamp")
        if isinstance(timestamp_raw, datetime):
            timestamp = timestamp_raw
        elif isinstance(timestamp_raw, str) and timestamp_raw:
            timestamp = datetime.fromisoformat(timestamp_raw)
        else:
            timestamp = datetime.now(UTC)

        # Parse objects
        nodes = []
        for obj in data.get("objects", []):
            properties = SnapshotYamlSerializer._deserialize_properties(obj.get("properties", {}))

            node = TreeNode(
                id=obj["id"],
                name=obj["name"],
                type_id=obj["type_id"],
                label=obj.get("label", obj["name"]),
                path=obj["path"],
                after=obj.get("after"),
                properties=properties,
            )
            nodes.append(node)

        return Snapshot(
            snapshot_id=data.get("uid", ""),
            document_name="",  # Not stored in YAML format
            timestamp=timestamp,
            nodes=nodes,
        )

    @staticmethod
    def _serialize_properties(properties: dict[str, Property]) -> dict[str, Any]:
        """Serialize property dict to YAML-compatible format.

        Args:
            properties: Dictionary of property name to Property

        Returns:
            Dictionary suitable for YAML serialization
        """
        result: dict[str, Any] = {}
        for name, prop in properties.items():
            result[name] = {
                "type_": prop.type_.name,
                "value": SnapshotYamlSerializer._serialize_property_value(prop.value, prop.type_),
                "expression": prop.expression,
                "group": prop.group,
            }
        return result

    @staticmethod
    def _serialize_property_value(value: Any, type_: PropertyType) -> Any:
        """Serialize a property value to YAML-compatible format.

        Args:
            value: The property value
            type_: The property type

        Returns:
            YAML-serializable value
        """
        if type_ == PropertyType.VECTOR:
            return {"x": value.x, "y": value.y, "z": value.z}
        elif type_ == PropertyType.PLACEMENT:
            return {
                "position": {
                    "x": value.position.x,
                    "y": value.position.y,
                    "z": value.position.z,
                },
                "rotation": {
                    "axis_x": value.rotation.axis_x,
                    "axis_y": value.rotation.axis_y,
                    "axis_z": value.rotation.axis_z,
                    "angle_degrees": value.rotation.angle_degrees,
                },
            }
        elif type_ == PropertyType.LIST:
            # Convert list items to strings for serialization
            return [str(item) for item in value] if value else []
        elif type_ == PropertyType.UNKNOWN:
            # For unknown types, try to convert to string to avoid serialization errors
            # This handles FreeCAD objects that can't be pickled
            try:
                # Try YAML serialization first to check if it's serializable
                import yaml

                yaml.dump(value)
                return value
            except (TypeError, AttributeError):
                # Fall back to string representation
                return str(value) if value is not None else None
        else:
            # Primitive types can be serialized directly
            return value

    @staticmethod
    def _deserialize_properties(data: dict[str, Any]) -> dict[str, Property]:
        """Deserialize property dict from YAML format.

        Args:
            data: Dictionary from YAML

        Returns:
            Dictionary of property name to Property
        """
        if not data:
            return {}

        result = {}
        for name, prop_data in data.items():
            type_name = prop_data.get("type_", "STRING")
            try:
                type_ = PropertyType[type_name]
            except KeyError:
                type_ = PropertyType.UNKNOWN

            value = SnapshotYamlSerializer._deserialize_property_value(prop_data.get("value"), type_)

            result[name] = Property(
                type_=type_,
                value=value,
                expression=prop_data.get("expression"),
                group=prop_data.get("group", "Base"),
            )
        return result

    @staticmethod
    def _deserialize_property_value(data: Any, type_: PropertyType) -> Any:
        """Deserialize a property value from YAML format.

        Args:
            data: The serialized value from YAML
            type_: The property type

        Returns:
            The deserialized value (as proper domain object if needed)
        """
        if type_ == PropertyType.VECTOR and isinstance(data, dict):
            return Property.create(PropertyType.VECTOR, (data.get("x", 0), data.get("y", 0), data.get("z", 0)))
        elif type_ == PropertyType.PLACEMENT and isinstance(data, dict):
            pos = data.get("position", {})
            rot = data.get("rotation", {})
            return Property.create(
                PropertyType.PLACEMENT,
                {
                    "position": (pos.get("x", 0), pos.get("y", 0), pos.get("z", 0)),
                    "rotation": (
                        rot.get("axis_x", 0),
                        rot.get("axis_y", 0),
                        rot.get("axis_z", 1),
                        rot.get("angle_degrees", 0),
                    ),
                },
            )
        else:
            return data


__all__ = ["SnapshotYamlSerializer"]
