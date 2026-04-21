# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for YAML persistence wiring with the DataPath-based
# Property model. Verifies serialization envelopes, list payloads, unknown payloads,
# and complete snapshot round-trips.
"""Tests for YAML persistence with DataPath-based Property model.

Phase 4: YAML Persistence Wiring.

Verifies that:
- Property serialization uses Property.to_serialized() envelope (type_, paths, group)
- List payload uses items with per-item paths envelopes
- Unknown payload preserves path-level freecad_type + display root
- Complete snapshot round-trip equality for mixed property types
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from freecad.diff_wb.domain import Property, Snapshot, TreeNode
from freecad.diff_wb.domain.tree.data_path import (
    ListData,
    PrimitiveData,
    PropertyPathType,
    PropertyPathValue,
    UnknownData,
)
from freecad.diff_wb.infrastructure.persistence import SnapshotYamlSerializer


class TestSerializePropertiesEnvelope:
    """Tests for _serialize_properties using Property.to_serialized() envelope."""

    def test_primitive_property_envelope(self):
        """A primitive property should serialize with type_, paths, and group keys."""
        prop = Property.from_freecad(10.0, {}, group="Base")
        result = SnapshotYamlSerializer._serialize_properties({"Length": prop})

        assert "Length" in result
        length_data = result["Length"]
        assert "type_" in length_data
        assert length_data["type_"] == "Primitive"
        assert "paths" in length_data
        assert "." in length_data["paths"]
        assert "group" in length_data
        assert length_data["group"] == "Base"

    @pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
    def test_placement_property_envelope(self):
        """A placement property should serialize with type_, paths, and group keys."""
        from FreeCAD import Base

        placement = Base.Placement()
        prop = Property.from_freecad(placement, {}, group="Base")
        result = SnapshotYamlSerializer._serialize_properties({"Placement": prop})

        placement_data = result["Placement"]
        assert placement_data["type_"] == "Placement"
        assert "paths" in placement_data
        assert "group" in placement_data
        assert placement_data["group"] == "Base"
        # Verify sub-paths are present
        assert "Base.x" in placement_data["paths"]
        assert "Base.y" in placement_data["paths"]
        assert "Base.z" in placement_data["paths"]

    @pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
    def test_vector_property_envelope(self):
        """A vector property should serialize with type_, paths, and group keys."""
        from FreeCAD import Base

        vec = Base.Vector(1.0, 2.0, 3.0)
        prop = Property.from_freecad(vec, {}, group="Data")
        result = SnapshotYamlSerializer._serialize_properties({"Position": prop})

        vec_data = result["Position"]
        assert vec_data["type_"] == "Vector"
        assert "paths" in vec_data
        assert "x" in vec_data["paths"]
        assert "y" in vec_data["paths"]
        assert "z" in vec_data["paths"]
        assert vec_data["group"] == "Data"

    @pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
    def test_quantity_property_envelope_root_string_only(self):
        """A quantity property should serialize with type_, paths, and group keys."""
        from FreeCAD import Base

        qty = Base.Quantity("10 mm")
        prop = Property.from_freecad(qty, {}, group="Base")
        result = SnapshotYamlSerializer._serialize_properties({"Length": prop})

        qty_data = result["Length"]
        assert qty_data["type_"] == "Quantity"
        assert "paths" in qty_data
        assert set(qty_data["paths"].keys()) == {"."}
        assert qty_data["paths"]["."]["type_"] == "STRING"
        assert qty_data["paths"]["."]["value"] == "10.0 mm"
        assert "Value" not in qty_data["paths"]
        assert "Unit" not in qty_data["paths"]

    def test_string_property_envelope(self):
        """A string property should serialize with type_, paths, and group keys."""
        prop = Property.from_freecad("TestString", {}, group="View")
        result = SnapshotYamlSerializer._serialize_properties({"Label": prop})

        str_data = result["Label"]
        assert str_data["type_"] == "Primitive"
        assert str_data["paths"]["."]["type_"] == "STRING"
        assert str_data["paths"]["."]["value"] == "TestString"
        assert str_data["group"] == "View"


class TestListPayloadWithItems:
    """Tests for list property serialization using items with per-item paths envelopes."""

    def test_list_property_serializes_items(self):
        """A list property should serialize with type_, paths, and items keys."""
        # Build a ListData manually with primitive items
        items = [
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.INT, 1)}),
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.INT, 2)}),
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.INT, 3)}),
        ]
        list_data = ListData(paths={}, items=items)
        prop = Property(value=list_data, group="Sketch")

        result = SnapshotYamlSerializer._serialize_properties({"Constraints": prop})
        list_payload = result["Constraints"]

        assert list_payload["type_"] == "List"
        assert "items" in list_payload
        assert len(list_payload["items"]) == 3
        assert list_payload["group"] == "Sketch"

    def test_list_items_have_paths_envelopes(self):
        """Each list item should have its own type_ and paths envelope."""
        items = [
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.STRING, "A")}),
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.STRING, "B")}),
        ]
        list_data = ListData(paths={}, items=items)
        prop = Property(value=list_data, group="Base")

        result = SnapshotYamlSerializer._serialize_properties({"Items": prop})
        items_data = result["Items"]["items"]

        assert items_data[0]["type_"] == "Primitive"
        assert "paths" in items_data[0]
        assert items_data[0]["paths"]["."]["value"] == "A"

        assert items_data[1]["type_"] == "Primitive"
        assert items_data[1]["paths"]["."]["value"] == "B"

    def test_list_with_constraint_items(self):
        """A list of constraint-like items should serialize each item with paths."""
        items = [
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.STRING, "DistanceX")}),
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.STRING, "Coincident")}),
        ]
        list_data = ListData(paths={}, items=items)
        prop = Property(value=list_data, group="Sketch")

        result = SnapshotYamlSerializer._serialize_properties({"Constraints": prop})
        list_payload = result["Constraints"]

        assert list_payload["type_"] == "List"
        assert len(list_payload["items"]) == 2
        assert list_payload["items"][0]["paths"]["."]["value"] == "DistanceX"
        assert list_payload["items"][1]["paths"]["."]["value"] == "Coincident"

    def test_list_with_expression_root_path(self):
        """A list with a root expression should include it in the paths envelope."""
        list_paths = {
            ".": PropertyPathValue(PropertyPathType.NULL, None, "SomeExpr"),
        }
        items = [
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.INT, 1)}),
        ]
        list_data = ListData(paths=list_paths, items=items)
        prop = Property(value=list_data, group="Base")

        result = SnapshotYamlSerializer._serialize_properties({"Constraints": prop})
        assert result["Constraints"]["paths"]["."]["type_"] == "NULL"
        assert result["Constraints"]["paths"]["."]["expression"] == "SomeExpr"


class TestUnknownPayloadPreservation:
    """Tests for unknown payload preserving path-level freecad_type and display root."""

    def test_unknown_payload_has_freecad_type(self):
        """An unknown property should preserve freecad_type in the root path entry."""
        prop = Property.from_freecad(object(), {}, group="Data")
        result = SnapshotYamlSerializer._serialize_properties({"UnknownProp": prop})

        unknown_data = result["UnknownProp"]
        assert unknown_data["type_"] == "Unknown"
        assert "paths" in unknown_data
        assert "." in unknown_data["paths"]
        assert "freecad_type" in unknown_data["paths"]["."]

    def test_unknown_payload_has_display_value(self):
        """An unknown property should store display value in the root path."""
        prop = Property.from_freecad(object(), {}, group="Data")
        result = SnapshotYamlSerializer._serialize_properties({"UnknownProp": prop})

        unknown_data = result["UnknownProp"]
        assert unknown_data["paths"]["."]["type_"] == "STRING"
        assert "value" in unknown_data["paths"]["."]

    def test_unknown_roundtrip_preserves_freecad_type(self):
        """Serializing and deserializing an unknown should preserve freecad_type."""
        original = Property.from_freecad(object(), {}, group="Data")
        serialized = original.to_serialized()
        restored = Property.from_serialized(serialized)

        assert isinstance(restored.value, UnknownData)
        assert restored.value.paths["."].freecad_type is not None
        assert restored.value.paths["."].freecad_type == original.value.paths["."].freecad_type

    def test_unknown_roundtrip_preserves_display_value(self):
        """Serializing and deserializing an unknown should preserve display value."""
        original = Property.from_freecad(object(), {}, group="Data")
        serialized = original.to_serialized()
        restored = Property.from_serialized(serialized)

        assert restored.value.paths["."].value == original.value.paths["."].value


class TestSnapshotRoundTrip:
    """Tests for complete snapshot round-trip equality with mixed property types."""

    def test_roundtrip_serialization_deserialization(self):
        """A snapshot with mixed properties should round-trip through YAML."""
        props = {
            "Length": Property.from_freecad(10.0, {}, group="Base"),
            "Name": Property.from_freecad("TestPad", {}, group="Data"),
            "Enabled": Property.from_freecad(True, {}, group="View"),
            "Count": Property.from_freecad(42, {}, group="Data"),
            "Ratio": Property.from_freecad(0.75, {}, group="Base"),
        }
        node = TreeNode(
            id=1,
            name="TestPad",
            type_id="PartDesign::Pad",
            label="TestPad",
            path="TestPad",
            after=None,
            properties=props,
        )
        snapshot = Snapshot(
            snapshot_id="roundtrip-test",
            document_name="RoundTripDoc",
            timestamp=datetime(2024, 6, 15, tzinfo=UTC),
            nodes=[node],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)

            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        # Verify structure
        assert len(restored.nodes) == 1
        restored_node = restored.nodes[0]
        assert restored_node.id == 1
        assert len(restored_node.properties) == len(props)

    def test_roundtrip_preserves_primitive_values(self):
        """Primitive property values should survive round-trip unchanged."""
        props = {
            "FloatVal": Property.from_freecad(3.14, {}, group="Base"),
            "IntVal": Property.from_freecad(42, {}, group="Data"),
            "StrVal": Property.from_freecad("hello", {}, group="View"),
            "BoolVal": Property.from_freecad(False, {}, group="View"),
        }
        node = TreeNode(id=1, name="Test", type_id="Test", label="Test", path="Test", after=None, properties=props)
        snapshot = Snapshot(
            snapshot_id="prim", document_name="", timestamp=datetime(2024, 1, 1, tzinfo=UTC), nodes=[node]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_props = restored.nodes[0].properties
        assert isinstance(restored_props["FloatVal"].value, PrimitiveData)
        assert restored_props["FloatVal"].value.paths["."].value == pytest.approx(3.14)
        assert restored_props["IntVal"].value.paths["."].value == 42
        assert restored_props["StrVal"].value.paths["."].value == "hello"
        assert restored_props["BoolVal"].value.paths["."].value is False

    def test_roundtrip_preserves_group(self):
        """Property groups should survive round-trip unchanged."""
        props = {
            "A": Property.from_freecad(1.0, {}, group="Base"),
            "B": Property.from_freecad(2.0, {}, group="Data"),
            "C": Property.from_freecad(3.0, {}, group="View"),
        }
        node = TreeNode(id=1, name="Test", type_id="Test", label="Test", path="Test", after=None, properties=props)
        snapshot = Snapshot(
            snapshot_id="grp", document_name="", timestamp=datetime(2024, 1, 1, tzinfo=UTC), nodes=[node]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        assert restored.nodes[0].properties["A"].group == "Base"
        assert restored.nodes[0].properties["B"].group == "Data"
        assert restored.nodes[0].properties["C"].group == "View"

    def test_roundtrip_preserves_expression(self):
        """Expressions stored in path entries should survive round-trip."""
        props = {
            "Length": Property.from_freecad(10.0, {".": "5 mm"}, group="Base"),
        }
        node = TreeNode(id=1, name="Test", type_id="Test", label="Test", path="Test", after=None, properties=props)
        snapshot = Snapshot(
            snapshot_id="expr", document_name="", timestamp=datetime(2024, 1, 1, tzinfo=UTC), nodes=[node]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_prop = restored.nodes[0].properties["Length"]
        assert isinstance(restored_prop.value, PrimitiveData)
        assert restored_prop.value.paths["."].expression == "5 mm"

    @pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
    def test_roundtrip_preserves_vector(self):
        """Vector property values should survive round-trip with correct coordinates."""
        from FreeCAD import Base

        from freecad.diff_wb.domain.tree.data_path import VectorData

        vec = Base.Vector(1.5, 2.5, 3.5)
        props = {"Position": Property.from_freecad(vec, {}, group="Base")}
        node = TreeNode(id=1, name="Test", type_id="Test", label="Test", path="Test", after=None, properties=props)
        snapshot = Snapshot(
            snapshot_id="vec", document_name="", timestamp=datetime(2024, 1, 1, tzinfo=UTC), nodes=[node]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_prop = restored.nodes[0].properties["Position"]
        assert isinstance(restored_prop.value, VectorData)
        assert restored_prop.value.paths["x"].value == pytest.approx(1.5)
        assert restored_prop.value.paths["y"].value == pytest.approx(2.5)
        assert restored_prop.value.paths["z"].value == pytest.approx(3.5)

    @pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
    def test_roundtrip_preserves_placement(self):
        """Placement property values should survive round-trip with correct components."""
        from FreeCAD import Base

        from freecad.diff_wb.domain.tree.data_path import PlacementData

        placement = Base.Placement(Base.Vector(1.0, 2.0, 3.0), Base.Rotation(0, 0, 1, 45))
        props = {"Placement": Property.from_freecad(placement, {}, group="Base")}
        node = TreeNode(id=1, name="Test", type_id="Test", label="Test", path="Test", after=None, properties=props)
        snapshot = Snapshot(
            snapshot_id="plc", document_name="", timestamp=datetime(2024, 1, 1, tzinfo=UTC), nodes=[node]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_prop = restored.nodes[0].properties["Placement"]
        assert isinstance(restored_prop.value, PlacementData)
        assert restored_prop.value.paths["Base.x"].value == pytest.approx(1.0)
        assert restored_prop.value.paths["Base.y"].value == pytest.approx(2.0)
        assert restored_prop.value.paths["Base.z"].value == pytest.approx(3.0)

    @pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
    def test_roundtrip_preserves_quantity_root_string(self):
        """Quantity property values should survive round-trip with root string value."""
        from FreeCAD import Base

        from freecad.diff_wb.domain.tree.data_path import QuantityData

        qty = Base.Quantity("10 mm")
        props = {"Amount": Property.from_freecad(qty, {}, group="Base")}
        node = TreeNode(id=1, name="Test", type_id="Test", label="Test", path="Test", after=None, properties=props)
        snapshot = Snapshot(
            snapshot_id="qty", document_name="", timestamp=datetime(2024, 1, 1, tzinfo=UTC), nodes=[node]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_prop = restored.nodes[0].properties["Amount"]
        assert isinstance(restored_prop.value, QuantityData)
        assert set(restored_prop.value.paths.keys()) == {"."}
        assert restored_prop.value.paths["."].value == "10.0 mm"
        assert "Value" not in restored_prop.value.paths
        assert "Unit" not in restored_prop.value.paths

    def test_roundtrip_preserves_list(self):
        """List property values should survive round-trip with correct items."""
        props = {"Items": Property.from_freecad([1, 2, 3], {}, group="Base")}
        node = TreeNode(id=1, name="Test", type_id="Test", label="Test", path="Test", after=None, properties=props)
        snapshot = Snapshot(
            snapshot_id="lst", document_name="", timestamp=datetime(2024, 1, 1, tzinfo=UTC), nodes=[node]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_prop = restored.nodes[0].properties["Items"]
        assert isinstance(restored_prop.value, ListData)
        assert len(restored_prop.value.items) == 3
        assert restored_prop.value.items[0].paths["."].value == 1
        assert restored_prop.value.items[1].paths["."].value == 2
        assert restored_prop.value.items[2].paths["."].value == 3

    def test_roundtrip_with_empty_properties(self):
        """A snapshot with empty properties should round-trip correctly."""
        node = TreeNode(id=1, name="Empty", type_id="Test", label="Empty", path="Empty", after=None, properties={})
        snapshot = Snapshot(
            snapshot_id="empty", document_name="", timestamp=datetime(2024, 1, 1, tzinfo=UTC), nodes=[node]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        assert len(restored.nodes[0].properties) == 0

    def test_roundtrip_with_unknown_property(self):
        """An unknown property should survive round-trip with freecad_type preserved."""
        props = {"Unknown": Property.from_freecad(object(), {}, group="Data")}
        node = TreeNode(id=1, name="Test", type_id="Test", label="Test", path="Test", after=None, properties=props)
        snapshot = Snapshot(
            snapshot_id="unknown", document_name="", timestamp=datetime(2024, 1, 1, tzinfo=UTC), nodes=[node]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_prop = restored.nodes[0].properties["Unknown"]
        assert isinstance(restored_prop.value, UnknownData)
        assert restored_prop.value.paths["."].freecad_type is not None
        assert restored_prop.value.paths["."].freecad_type == props["Unknown"].value.paths["."].freecad_type

    def test_yaml_output_format_matches_spec(self):
        """The YAML output should match the DataPath-based envelope spec."""
        props = {"Length": Property.from_freecad(10.0, {}, group="Base")}
        node = TreeNode(id=1, name="Test", type_id="Test", label="Test", path="Test", after=None, properties=props)
        snapshot = Snapshot(
            snapshot_id="fmt", document_name="", timestamp=datetime(2024, 1, 1, tzinfo=UTC), nodes=[node]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            content = yaml_path.read_text()
            data = yaml.safe_load(content)

        # Check the property envelope structure
        prop_data = data["objects"][0]["properties"]["Length"]
        assert "type_" in prop_data
        assert prop_data["type_"] == "Primitive"
        assert "paths" in prop_data
        assert "group" in prop_data
        assert prop_data["group"] == "Base"
        # Should NOT have old-style "value" or "expression" at property level
        assert "value" not in prop_data
        assert "expression" not in prop_data

    def test_yaml_output_has_paths_not_value(self):
        """Serialized properties should use 'paths' key, not 'value' key."""
        props = {"Length": Property.from_freecad(10.0, {}, group="Base")}
        node = TreeNode(id=1, name="Test", type_id="Test", label="Test", path="Test", after=None, properties=props)
        snapshot = Snapshot(
            snapshot_id="paths", document_name="", timestamp=datetime(2024, 1, 1, tzinfo=UTC), nodes=[node]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            data = yaml.safe_load(yaml_path.read_text())

        prop_data = data["objects"][0]["properties"]["Length"]
        assert "paths" in prop_data
        assert "value" not in prop_data

    def test_multiple_nodes_with_different_property_types(self):
        """A snapshot with multiple nodes having different property types should round-trip."""
        nodes = [
            TreeNode(
                id=1,
                name="Pad",
                type_id="PartDesign::Pad",
                label="Pad",
                path="Pad",
                after=None,
                properties={
                    "Length": Property.from_freecad(10.0, {}, group="Base"),
                    "Enabled": Property.from_freecad(True, {}, group="View"),
                },
            ),
            TreeNode(
                id=2,
                name="Sketch",
                type_id="Sketcher::SketchObject",
                label="Sketch",
                path="Sketch",
                after="Pad",
                properties={
                    "Name": Property.from_freecad("MySketch", {}, group="Data"),
                    "Count": Property.from_freecad(5, {}, group="Data"),
                },
            ),
        ]
        snapshot = Snapshot(
            snapshot_id="multi",
            document_name="MultiDoc",
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            nodes=nodes,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        assert len(restored.nodes) == 2
        # Verify Pad node
        pad_node = restored.nodes[0]
        assert pad_node.name == "Pad"
        assert "Length" in pad_node.properties
        assert "Enabled" in pad_node.properties
        # Verify Sketch node
        sketch_node = restored.nodes[1]
        assert sketch_node.name == "Sketch"
        assert "Name" in sketch_node.properties
        assert "Count" in sketch_node.properties
