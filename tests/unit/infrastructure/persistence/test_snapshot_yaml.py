# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for YAML serialization and deserialization of snapshots.
"""Unit tests for snapshot YAML persistence."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import yaml
from freecad.history_wb.domain import Property, Snapshot, SnapshotObject, SnapshotOccurrence
from freecad.history_wb.infrastructure.persistence import SnapshotYamlSerializer


class TestSnapshotYamlSerializer:
    """Tests for the SnapshotYamlSerializer class."""

    def _create_sample_snapshot(self) -> Snapshot:
        """Create a sample snapshot for testing."""
        objects = [
            SnapshotObject(name="Body", id=1, type_id="PartDesign::Body", properties={}),
            SnapshotObject(name="Sketch", id=2, type_id="Sketcher::SketchObject", properties={}),
            SnapshotObject(
                name="Pad",
                id=3,
                type_id="PartDesign::Pad",
                properties={"Length": Property.from_freecad(10.0, {}, "Base")},
            ),
        ]
        occurrences = [
            SnapshotOccurrence(path="Body", after=None),
            SnapshotOccurrence(path="Body/Sketch", after="Body"),
            SnapshotOccurrence(path="Body/Pad", after="Body/Sketch"),
        ]
        return Snapshot(
            snapshot_id="test-uuid-1234",
            document_name="TestDocument",
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            objects=objects,
            occurrences=occurrences,
            git_path="",
        )

    @staticmethod
    def _occ(snapshot: Snapshot, path: str) -> SnapshotOccurrence | None:
        return snapshot.find_occurrence(path)

    @staticmethod
    def _obj(snapshot: Snapshot, occ: SnapshotOccurrence | None) -> SnapshotObject | None:
        if occ is None:
            return None
        return snapshot.find_object(occ.object_name)

    def test_serialize_snapshot_to_yaml_format(self) -> None:
        """Test: Serialize Snapshot to YAML format matching ProjectState.md spec."""
        snapshot = self._create_sample_snapshot()

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)

            # Read the generated YAML
            content = yaml_path.read_text()
            data = yaml.safe_load(content)

            # Verify top-level keys
            assert "v" in data, "YAML should have version field 'v'"
            assert "timestamp" in data, "YAML should have timestamp field"
            assert "uid" in data, "YAML should have uid field (document UUID)"
            assert "objects" in data, "YAML should have objects field"

            # Verify version
            assert data["v"] == 2, "Version should be 2"

            # Verify timestamp format (UTC ISO format)
            assert data["timestamp"] == "2024-01-15T10:30:00+00:00"

            # Verify uid (snapshot_id)
            assert data["uid"] == "test-uuid-1234"

            # Verify objects list
            objects = data["objects"]
            assert len(objects) == 3, "Should have 3 objects"

            # First object should be Body (id=1)
            assert objects[0]["id"] == 1
            assert objects[0]["name"] == "Body"
            assert objects[0]["type_id"] == "PartDesign::Body"
            assert objects[0]["type_id"] == "PartDesign::Body"

            # Second object should be Sketch (id=2)
            assert objects[1]["id"] == 2
            assert objects[1]["name"] == "Sketch"
            assert objects[1]["type_id"] == "Sketcher::SketchObject"

            # Third object should be Pad (id=3)
            assert objects[2]["id"] == 3
            assert objects[2]["name"] == "Pad"
            assert objects[2]["type_id"] == "PartDesign::Pad"

            occurrences = data["occurrences"]
            assert [occ["path"] for occ in occurrences] == ["Body", "Body/Pad", "Body/Sketch"]
            assert occurrences[2]["after"] == "Body"

    def test_deserialize_yaml_to_snapshot(self) -> None:
        """Test: Deserialize YAML to Snapshot with flat node structure."""
        yaml_content = """v: 2
timestamp: 2024-01-15T10:30:00+00:00
uid: test-uuid-1234
objects:
- id: 1
  name: Body
  type_id: PartDesign::Body
  properties: {}
- id: 2
  name: Sketch
  type_id: Sketcher::SketchObject
  properties: {}
- id: 3
  name: Pad
  type_id: PartDesign::Pad
  properties:
    Length:
      kind: Primitive
      paths:
        .:
          type: FLOAT
          value: 10.0
      group: Base
occurrences:
- path: Body
  object: Body
  after: null
- path: Body/Sketch
  object: Sketch
  after: null
- path: Body/Pad
  object: Pad
  after: Body/Sketch
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            yaml_path.write_text(yaml_content)

            snapshot = SnapshotYamlSerializer.from_yaml_file(yaml_path)

            # Verify snapshot metadata
            assert snapshot.snapshot_id == "test-uuid-1234"
            assert snapshot.document_name == ""  # Not in YAML, defaults to empty
            assert snapshot.timestamp == datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

            # Verify flat node structure
            assert len(snapshot.occurrences) == 3, "Should have 3 occurrences"

            # Check first node (id=1)
            occ1 = self._occ(snapshot, "Body")
            obj1 = self._obj(snapshot, occ1)
            assert occ1 is not None
            assert obj1 is not None
            assert obj1.id == 1
            assert obj1.name == "Body"
            assert obj1.type_id == "PartDesign::Body"
            assert occ1.path == "Body"
            assert occ1.after is None

            # Check second node (id=2)
            occ2 = self._occ(snapshot, "Body/Sketch")
            obj2 = self._obj(snapshot, occ2)
            assert occ2 is not None
            assert obj2 is not None
            assert obj2.id == 2
            assert obj2.name == "Sketch"
            assert obj2.type_id == "Sketcher::SketchObject"
            assert occ2.after is None

            # Check third node (id=3)
            occ3 = self._occ(snapshot, "Body/Pad")
            obj3 = self._obj(snapshot, occ3)
            assert occ3 is not None
            assert obj3 is not None
            assert obj3.id == 3
            assert obj3.name == "Pad"
            assert obj3.type_id == "PartDesign::Pad"
            assert occ3.after == "Body/Sketch"

    def test_roundtrip_produces_identical_output(self) -> None:
        """Test: Round-trip (serialize → deserialize → serialize) produces identical output."""
        original_snapshot = self._create_sample_snapshot()

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"

            # First serialize
            SnapshotYamlSerializer.to_yaml(original_snapshot, yaml_path)
            first_output = yaml_path.read_text()

            # Deserialize
            restored_snapshot = SnapshotYamlSerializer.from_yaml_file(yaml_path)

            # Re-serialize
            SnapshotYamlSerializer.to_yaml(restored_snapshot, yaml_path)
            second_output = yaml_path.read_text()

            # Compare outputs - they should be identical
            first_data = yaml.safe_load(first_output)
            second_data = yaml.safe_load(second_output)
            assert first_data == second_data

    def test_loading_yaml_creates_correct_flat_node_structure(self) -> None:
        """Test: Loading YAML creates correct flat node structure."""
        yaml_content = """v: 2
timestamp: 2024-02-20T12:00:00+00:00
uid: doc-uuid-5678
objects:
- id: 10
  name: Origin
  type_id: Part::Origin
  properties: {}
- id: 20
  name: X_Axis
  type_id: Part::Line
  properties: {}
- id: 21
  name: Y_Axis
  type_id: Part::Line
  properties: {}
- id: 30
  name: Body
  type_id: PartDesign::Body
  properties: {}
occurrences:
- path: Origin
  object: Origin
  after: null
- path: Origin/X_Axis
  object: X_Axis
  after: null
- path: Origin/Y_Axis
  object: Y_Axis
  after: Origin/X_Axis
- path: Body
  object: Body
  after: null
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            yaml_path.write_text(yaml_content)

            snapshot = SnapshotYamlSerializer.from_yaml_file(yaml_path)

            # Verify it's a flat list (no hierarchical children)
            assert snapshot.node_count == 4

            # Verify all nodes are accessible by path
            assert snapshot.find_occurrence("Origin") is not None
            assert snapshot.find_occurrence("Origin/X_Axis") is not None
            assert snapshot.find_occurrence("Origin/Y_Axis") is not None
            assert snapshot.find_occurrence("Body") is not None

            # Verify "after" field is correctly populated
            origin_occ = snapshot.find_occurrence("Origin")
            assert origin_occ is not None
            assert origin_occ.after is None  # Root node

            x_axis = snapshot.find_occurrence("Origin/X_Axis")
            assert x_axis is not None
            assert x_axis.after is None  # First child of Origin

            y_axis = snapshot.find_occurrence("Origin/Y_Axis")
            assert y_axis is not None
            assert y_axis.after == "Origin/X_Axis"  # Second child

            body = snapshot.find_occurrence("Body")
            assert body is not None
            assert body.after is None  # Different parent, first in its group

    def test_serialize_empty_snapshot(self) -> None:
        """Test: Serialize snapshot with no nodes."""
        snapshot = Snapshot(
            snapshot_id="empty-uuid",
            document_name="EmptyDoc",
            timestamp=datetime(2024, 3, 1, tzinfo=UTC),
            objects=[],
            occurrences=[],
            git_path="",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)

            data = yaml.safe_load(yaml_path.read_text())
            assert data["objects"] == []
            assert data["uid"] == "empty-uuid"

    def test_deserialize_empty_snapshot(self) -> None:
        """Test: Deserialize snapshot with no objects."""
        yaml_content = """v: 2
timestamp: 2024-03-01T00:00:00+00:00
uid: empty-uuid
objects: []
occurrences: []
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            yaml_path.write_text(yaml_content)

            snapshot = SnapshotYamlSerializer.from_yaml_file(yaml_path)

            assert snapshot.snapshot_id == "empty-uuid"
            assert snapshot.node_count == 0

    def test_objects_sorted_by_id(self) -> None:
        """Test: Objects are stored sorted by integer id."""
        objects = [
            SnapshotObject(id=5, name="NodeE", type_id="TypeE", properties={}),
            SnapshotObject(id=1, name="NodeA", type_id="TypeA", properties={}),
            SnapshotObject(id=3, name="NodeC", type_id="TypeC", properties={}),
            SnapshotObject(id=2, name="NodeB", type_id="TypeB", properties={}),
        ]
        occurrences = [
            SnapshotOccurrence(path="E", after=None),
            SnapshotOccurrence(path="A", after=None),
            SnapshotOccurrence(path="C", after=None),
            SnapshotOccurrence(path="B", after=None),
        ]
        snapshot = Snapshot(
            snapshot_id="sort-test",
            document_name="SortTest",
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            objects=objects,
            occurrences=occurrences,
            git_path="",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)

            data = yaml.safe_load(yaml_path.read_text())
            ids = [obj["id"] for obj in data["objects"]]
            assert ids == [1, 2, 3, 5], "Objects should be sorted by id"

    def test_yaml_path_field_for_text_diff_readability(self) -> None:
        """Test: Include path field (not parent) for human-readable text diffs."""
        yaml_content = """v: 2
timestamp: 2024-01-01T00:00:00+00:00
uid: test-path-field
objects:
- id: 1
  name: Pad
  type_id: PartDesign::Pad
  properties: {}
occurrences:
- path: Body/Pad
  object: Pad
  after: null
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            yaml_path.write_text(yaml_content)

            snapshot = SnapshotYamlSerializer.from_yaml_file(yaml_path)
            node = snapshot.find_occurrence("Body/Pad")
            assert node is not None

            # Verify path is stored (not parent)
            assert node.path == "Body/Pad"
            # Should NOT have a parent field
            assert not hasattr(node, "parent")


class TestSnapshotYamlSerializerOverwrite:
    """Tests for YAML overwrite behavior when persisting snapshots."""

    def test_to_yaml_overwrites_existing_file(self) -> None:
        """Test: to_yaml overwrites existing file rather than appending or creating new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"

            # Create initial YAML content with old data
            old_data = {
                "v": 2,
                "timestamp": "2024-01-01T00:00:00+00:00",
                "uid": "old-uuid-123",
                "objects": [],
                "occurrences": [],
            }
            yaml_path.write_text(yaml.dump(old_data))

            # Verify old content exists
            old_content = yaml.safe_load(yaml_path.read_text())
            assert old_content["uid"] == "old-uuid-123"

            # Serialize new snapshot to the same path
            new_snapshot = Snapshot(
                snapshot_id="new-uuid-456",
                document_name="TestDoc",
                timestamp=datetime(2024, 6, 15, tzinfo=UTC),
                objects=[],
                occurrences=[],
                git_path="",
            )
            SnapshotYamlSerializer.to_yaml(new_snapshot, yaml_path)

            # Read the file and verify it was overwritten (not appended)
            new_content = yaml.safe_load(yaml_path.read_text())
            assert new_content["uid"] == "new-uuid-456"
            # Old data should be completely gone
            assert new_content["timestamp"] == "2024-06-15T00:00:00+00:00"

    def test_multiple_serializations_update_file_size(self) -> None:
        """Test: Multiple serializations update file size appropriately (overwrite, not append)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"

            # First serialization - small snapshot
            snapshot1 = Snapshot(
                snapshot_id="small-uuid",
                document_name="SmallDoc",
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                objects=[],
                occurrences=[],
                git_path="",
            )
            SnapshotYamlSerializer.to_yaml(snapshot1, yaml_path)
            first_size = yaml_path.stat().st_size

            # Second serialization - larger snapshot with more nodes
            objects = [SnapshotObject(id=i, name=f"Node{i}", type_id="Type", properties={}) for i in range(10)]
            occurrences = [SnapshotOccurrence(path=f"P{i}", after=None) for i in range(10)]
            snapshot2 = Snapshot(
                snapshot_id="large-uuid",
                document_name="LargeDoc",
                timestamp=datetime(2024, 12, 31, tzinfo=UTC),
                objects=objects,
                occurrences=occurrences,
                git_path="",
            )
            SnapshotYamlSerializer.to_yaml(snapshot2, yaml_path)
            second_size = yaml_path.stat().st_size

            # Third serialization - back to small snapshot
            SnapshotYamlSerializer.to_yaml(snapshot1, yaml_path)
            third_size = yaml_path.stat().st_size

            # File sizes should change based on content, not grow monotonically
            # (which would indicate appending behavior)
            assert second_size > first_size, "Larger snapshot should produce larger file"
            assert third_size == first_size, "Same snapshot should produce same file size (overwrite)"

    def test_to_yaml_replaces_all_content_on_overwrite(self) -> None:
        """Test: All content is replaced when overwriting, including nested structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"

            # Create YAML with complex nested properties
            complex_yaml = """v: 2
timestamp: 2024-01-01T00:00:00+00:00
uid: complex-old
objects:
- id: 999
  name: OldObject
  type_id: OldType
  properties:
    OldProp:
      type: STRING
      value: old_value
      expression: old_expr
      group: OldGroup
occurrences:
- path: Old/Path
  object: OldObject
  after: null
"""
            yaml_path.write_text(complex_yaml)

            # Create simple snapshot with no properties
            simple_snapshot = Snapshot(
                snapshot_id="simple-uuid",
                document_name="SimpleDoc",
                timestamp=datetime(2024, 6, 1, tzinfo=UTC),
                objects=[SnapshotObject(id=1, name="SimpleNode", type_id="SimpleType", properties={})],
                occurrences=[SnapshotOccurrence(path="Simple", after=None)],
                git_path="",
            )
            SnapshotYamlSerializer.to_yaml(simple_snapshot, yaml_path)

            # Read and verify all old content is gone
            new_data = yaml.safe_load(yaml_path.read_text())

            # Old data should be completely replaced
            assert new_data["uid"] == "simple-uuid"
            assert len(new_data["objects"]) == 1
            assert new_data["objects"][0]["name"] == "SimpleNode"
            # Old object should be completely gone
            assert new_data["objects"][0]["id"] != 999
            assert "OldProp" not in new_data["objects"][0].get("properties", {})


class TestSnapshotYamlSerializerFromYaml:
    """Tests for refactored from_yaml (string-based) and from_yaml_file methods."""

    @staticmethod
    def _obj(snapshot: Snapshot, occ: SnapshotOccurrence | None) -> SnapshotObject | None:
        if occ is None:
            return None
        return snapshot.find_object(occ.object_name)

    def test_from_yaml_deserializes_from_string(self) -> None:
        """Test: from_yaml deserializes Snapshot from YAML string."""
        yaml_content = """v: 2
timestamp: 2024-01-15T10:30:00+00:00
uid: test-uuid-string
objects:
- id: 1
  name: Body
  type_id: PartDesign::Body
  properties: {}
- id: 2
  name: Sketch
  type_id: Sketcher::SketchObject
  properties: {}
occurrences:
- path: Body
  object: Body
  after: null
- path: Body/Sketch
  object: Sketch
  after: null
"""
        snapshot = SnapshotYamlSerializer.from_yaml(yaml_content)

        # Verify snapshot metadata
        assert snapshot.snapshot_id == "test-uuid-string"
        assert snapshot.document_name == ""
        assert snapshot.timestamp == datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        # Verify nodes
        assert len(snapshot.occurrences) == 2
        body_occ = snapshot.find_occurrence("Body")
        body_obj = self._obj(snapshot, body_occ)
        assert body_obj is not None
        assert body_obj.id == 1
        assert body_obj.name == "Body"

        sketch_occ = snapshot.find_occurrence("Body/Sketch")
        sketch_obj = self._obj(snapshot, sketch_occ)
        assert sketch_obj is not None
        assert sketch_obj.id == 2
        assert sketch_occ is not None
        assert sketch_occ.after is None

    def test_from_yaml_handles_missing_timestamp(self) -> None:
        """Test: from_yaml uses current time when timestamp is missing."""
        yaml_content = """v: 2
uid: no-timestamp-uuid
objects: []
occurrences: []
"""
        snapshot = SnapshotYamlSerializer.from_yaml(yaml_content)

        # Should have a timestamp (current time)
        assert snapshot.timestamp is not None
        assert snapshot.snapshot_id == "no-timestamp-uuid"

    def test_from_yaml_file_calls_from_yaml_equivalently(self) -> None:
        """Test: from_yaml_file reads file and produces same result as from_yaml with content."""
        yaml_content = """v: 2
timestamp: 2024-02-20T14:00:00+00:00
uid: file-test-uuid
objects:
- id: 5
  name: TestObject
  type_id: Part::Feature
  properties:
    Length:
      kind: Primitive
      paths:
        .:
          type: FLOAT
          value: 42.5
      group: Base
occurrences:
- path: TestObject
  object: TestObject
  after: null
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            yaml_path.write_text(yaml_content)

            # Load using from_yaml_file
            snapshot_from_file = SnapshotYamlSerializer.from_yaml_file(yaml_path)

            # Load using from_yaml with same content
            snapshot_from_string = SnapshotYamlSerializer.from_yaml(yaml_content)

            # Both should produce equivalent snapshots
            assert snapshot_from_file.snapshot_id == snapshot_from_string.snapshot_id
            assert snapshot_from_file.timestamp == snapshot_from_string.timestamp
            assert len(snapshot_from_file.occurrences) == len(snapshot_from_string.occurrences)

            file_occ = snapshot_from_file.find_occurrence("TestObject")
            string_occ = snapshot_from_string.find_occurrence("TestObject")
            file_obj = snapshot_from_file.find_object(file_occ.object_name) if file_occ else None
            string_obj = snapshot_from_string.find_object(string_occ.object_name) if string_occ else None
            assert file_obj is not None
            assert string_obj is not None
            assert file_obj.id == string_obj.id


class TestSnapshotYamlDataPathEnvelope:
    """Tests for YAML serialization using DataPath-based property envelopes."""

    def test_yaml_output_uses_paths_not_value(self) -> None:
        """Serialized properties should use 'paths' key, not 'value' key."""
        snapshot = Snapshot(
            snapshot_id="test",
            document_name="Test",
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            objects=[
                SnapshotObject(
                    name="Pad",
                    id=1,
                    type_id="PartDesign::Pad",
                    properties={"Length": Property.from_freecad(10.0, {}, "Base")},
                )
            ],
            occurrences=[SnapshotOccurrence(path="Pad", after=None)],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            data = yaml.safe_load(yaml_path.read_text())

        prop_data = data["objects"][0]["properties"]["Length"]
        assert "paths" in prop_data
        assert "kind" in prop_data
        assert "group" in prop_data
        assert "value" not in prop_data
        assert "expression" not in prop_data

    def test_list_property_roundtrip(self) -> None:
        """List property values should survive round-trip with correct items."""
        snapshot = Snapshot(
            snapshot_id="list-test",
            document_name="Test",
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            objects=[
                SnapshotObject(
                    name="Sketch",
                    id=1,
                    type_id="Sketcher::SketchObject",
                    properties={"Constraints": Property.from_freecad([1, 2, 3], {}, "Base")},
                )
            ],
            occurrences=[SnapshotOccurrence(path="Sketch", after=None)],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        from freecad.history_wb.domain.tree.data_path import ListData

        constraints_prop = restored.find_object("Sketch").properties["Constraints"]
        assert isinstance(constraints_prop.value, ListData)
        assert len(constraints_prop.value.items) == 3
        assert constraints_prop.value.items[0].paths["."].value == 1
        assert constraints_prop.value.items[1].paths["."].value == 2
        assert constraints_prop.value.items[2].paths["."].value == 3

    def test_unknown_property_roundtrip(self) -> None:
        """Unknown property should survive round-trip with freecad_type preserved."""
        snapshot = Snapshot(
            snapshot_id="unknown-test",
            document_name="Test",
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            objects=[
                SnapshotObject(
                    name="Obj",
                    id=1,
                    type_id="App::Feature",
                    properties={"Unknown": Property.from_freecad(object(), {}, "Data")},
                )
            ],
            occurrences=[SnapshotOccurrence(path="Obj", after=None)],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        from freecad.history_wb.domain.tree.data_path import UnknownData

        unknown_prop = restored.find_object("Obj").properties["Unknown"]
        assert isinstance(unknown_prop.value, UnknownData)
        assert unknown_prop.value.paths["."].freecad_type is not None

    def test_mixed_property_roundtrip(self) -> None:
        """Snapshot with mixed property types should round-trip correctly."""
        snapshot = Snapshot(
            snapshot_id="mixed-test",
            document_name="TestDoc",
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            objects=[
                SnapshotObject(
                    name="Pad",
                    id=1,
                    type_id="PartDesign::Pad",
                    properties={
                        "Length": Property.from_freecad(10.0, {}, "Base"),
                        "Enabled": Property.from_freecad(True, {}, "View"),
                        "Name": Property.from_freecad("MyPad", {}, "Data"),
                    },
                ),
                SnapshotObject(
                    name="Sketch",
                    id=2,
                    type_id="Sketcher::SketchObject",
                    properties={
                        "Labels": Property.from_freecad(["a", "b"], {}, "Base"),
                    },
                ),
            ],
            occurrences=[
                SnapshotOccurrence(path="Pad", after=None),
                SnapshotOccurrence(path="Sketch", after="Pad"),
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        assert len(restored.occurrences) == 2
        pad_obj = restored.find_object("Pad")
        sketch_obj = restored.find_object("Sketch")
        assert pad_obj is not None
        assert sketch_obj is not None
        assert "Length" in pad_obj.properties
        assert "Enabled" in pad_obj.properties
        assert "Name" in pad_obj.properties
        assert "Labels" in sketch_obj.properties
