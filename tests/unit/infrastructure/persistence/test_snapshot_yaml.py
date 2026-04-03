# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for YAML serialization and deserialization of snapshots.
"""Unit tests for snapshot YAML persistence."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import yaml

from freecad.diff_wb.domain import Property, PropertyType, Snapshot, TreeNode
from freecad.diff_wb.infrastructure.persistence import SnapshotYamlSerializer


class TestSnapshotYamlSerializer:
    """Tests for the SnapshotYamlSerializer class."""

    def _create_sample_snapshot(self) -> Snapshot:
        """Create a sample snapshot for testing."""
        nodes = [
            TreeNode(
                id=1,
                name="Body",
                type_id="PartDesign::Body",
                label="Body",
                path="Body",
                after=None,
            ),
            TreeNode(
                id=2,
                name="Sketch",
                type_id="Sketcher::SketchObject",
                label="Sketch",
                path="Body/Sketch",
                after="Body",
            ),
            TreeNode(
                id=3,
                name="Pad",
                type_id="PartDesign::Pad",
                label="Pad",
                path="Body/Pad",
                after="Sketch",
                properties={"Length": Property.create(PropertyType.FLOAT, 10.0)},
            ),
        ]
        return Snapshot(
            snapshot_id="test-uuid-1234",
            document_name="TestDocument",
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            nodes=nodes,
        )

    def test_serialize_snapshot_to_yaml_format(self):
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
            assert data["v"] == 1, "Version should be 1"

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
            assert objects[0]["path"] == "Body"
            assert objects[0]["after"] is None

            # Second object should be Sketch (id=2)
            assert objects[1]["id"] == 2
            assert objects[1]["name"] == "Sketch"
            assert objects[1]["path"] == "Body/Sketch"
            assert objects[1]["after"] == "Body"

            # Third object should be Pad (id=3)
            assert objects[2]["id"] == 3
            assert objects[2]["name"] == "Pad"
            assert objects[2]["path"] == "Body/Pad"
            assert objects[2]["after"] == "Sketch"

    def test_deserialize_yaml_to_snapshot(self):
        """Test: Deserialize YAML to Snapshot with flat node structure."""
        yaml_content = """v: 1
timestamp: 2024-01-15T10:30:00+00:00
uid: test-uuid-1234
objects:
- id: 1
  name: Body
  type_id: PartDesign::Body
  label: Body
  path: Body
  after: null
  properties: {}
- id: 2
  name: Sketch
  type_id: Sketcher::SketchObject
  label: Sketch
  path: Body/Sketch
  after: Body
  properties: {}
- id: 3
  name: Pad
  type_id: PartDesign::Pad
  label: Pad
  path: Body/Pad
  after: Sketch
  properties:
    Length:
      type_: FLOAT
      value: 10.0
      expression: null
      group: Base
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            yaml_path.write_text(yaml_content)

            snapshot = SnapshotYamlSerializer.from_yaml(yaml_path)

            # Verify snapshot metadata
            assert snapshot.snapshot_id == "test-uuid-1234"
            assert snapshot.document_name == ""  # Not in YAML, defaults to empty
            assert snapshot.timestamp == datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

            # Verify flat node structure
            assert len(snapshot.nodes) == 3, "Should have 3 nodes"

            # Check first node (id=1)
            node1 = snapshot.find_node_by_path("Body")
            assert node1 is not None
            assert node1.id == 1
            assert node1.name == "Body"
            assert node1.type_id == "PartDesign::Body"
            assert node1.path == "Body"
            assert node1.after is None

            # Check second node (id=2)
            node2 = snapshot.find_node_by_path("Body/Sketch")
            assert node2 is not None
            assert node2.id == 2
            assert node2.name == "Sketch"
            assert node2.type_id == "Sketcher::SketchObject"
            assert node2.after == "Body"

            # Check third node (id=3)
            node3 = snapshot.find_node_by_path("Body/Pad")
            assert node3 is not None
            assert node3.id == 3
            assert node3.name == "Pad"
            assert node3.type_id == "PartDesign::Pad"
            assert node3.after == "Sketch"

    def test_roundtrip_produces_identical_output(self):
        """Test: Round-trip (serialize → deserialize → serialize) produces identical output."""
        original_snapshot = self._create_sample_snapshot()

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"

            # First serialize
            SnapshotYamlSerializer.to_yaml(original_snapshot, yaml_path)
            first_output = yaml_path.read_text()

            # Deserialize
            restored_snapshot = SnapshotYamlSerializer.from_yaml(yaml_path)

            # Re-serialize
            SnapshotYamlSerializer.to_yaml(restored_snapshot, yaml_path)
            second_output = yaml_path.read_text()

            # Compare outputs - they should be identical
            first_data = yaml.safe_load(first_output)
            second_data = yaml.safe_load(second_output)
            assert first_data == second_data

    def test_loading_yaml_creates_correct_flat_node_structure(self):
        """Test: Loading YAML creates correct flat node structure."""
        yaml_content = """v: 1
timestamp: 2024-02-20T12:00:00+00:00
uid: doc-uuid-5678
objects:
- id: 10
  name: Origin
  type_id: Part::Origin
  label: Origin
  path: Origin
  after: null
  properties: {}
- id: 20
  name: X_Axis
  type_id: Part::Line
  label: X_Axis
  path: Origin/X_Axis
  after: Origin
  properties: {}
- id: 21
  name: Y_Axis
  type_id: Part::Line
  label: Y_Axis
  path: Origin/Y_Axis
  after: X_Axis
  properties: {}
- id: 30
  name: Body
  type_id: PartDesign::Body
  label: Body
  path: Body
  after: null
  properties: {}
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            yaml_path.write_text(yaml_content)

            snapshot = SnapshotYamlSerializer.from_yaml(yaml_path)

            # Verify it's a flat list (no hierarchical children)
            assert snapshot.node_count == 4

            # Verify all nodes are accessible by path
            assert snapshot.find_node_by_path("Origin") is not None
            assert snapshot.find_node_by_path("Origin/X_Axis") is not None
            assert snapshot.find_node_by_path("Origin/Y_Axis") is not None
            assert snapshot.find_node_by_path("Body") is not None

            # Verify "after" field is correctly populated
            origin_node = snapshot.find_node_by_path("Origin")
            assert origin_node is not None
            assert origin_node.after is None  # Root node

            x_axis = snapshot.find_node_by_path("Origin/X_Axis")
            assert x_axis is not None
            assert x_axis.after == "Origin"  # First child of Origin

            y_axis = snapshot.find_node_by_path("Origin/Y_Axis")
            assert y_axis is not None
            assert y_axis.after == "X_Axis"  # Second child

            body = snapshot.find_node_by_path("Body")
            assert body is not None
            assert body.after is None  # Different parent, first in its group

    def test_serialize_empty_snapshot(self):
        """Test: Serialize snapshot with no nodes."""
        snapshot = Snapshot(
            snapshot_id="empty-uuid",
            document_name="EmptyDoc",
            timestamp=datetime(2024, 3, 1, tzinfo=UTC),
            nodes=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)

            data = yaml.safe_load(yaml_path.read_text())
            assert data["objects"] == []
            assert data["uid"] == "empty-uuid"

    def test_deserialize_empty_snapshot(self):
        """Test: Deserialize snapshot with no objects."""
        yaml_content = """v: 1
timestamp: 2024-03-01T00:00:00+00:00
uid: empty-uuid
objects: []
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            yaml_path.write_text(yaml_content)

            snapshot = SnapshotYamlSerializer.from_yaml(yaml_path)

            assert snapshot.snapshot_id == "empty-uuid"
            assert snapshot.node_count == 0

    def test_objects_sorted_by_id(self):
        """Test: Objects are stored sorted by integer id."""
        # Create snapshot with nodes not in ID order
        nodes = [
            TreeNode(id=5, name="NodeE", type_id="TypeE", label="E", path="E", after=None),
            TreeNode(id=1, name="NodeA", type_id="TypeA", label="A", path="A", after=None),
            TreeNode(id=3, name="NodeC", type_id="TypeC", label="C", path="C", after=None),
            TreeNode(id=2, name="NodeB", type_id="TypeB", label="B", path="B", after=None),
        ]
        snapshot = Snapshot(
            snapshot_id="sort-test",
            document_name="SortTest",
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            nodes=nodes,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)

            data = yaml.safe_load(yaml_path.read_text())
            ids = [obj["id"] for obj in data["objects"]]
            assert ids == [1, 2, 3, 5], "Objects should be sorted by id"

    def test_yaml_path_field_for_text_diff_readability(self):
        """Test: Include path field (not parent) for human-readable text diffs."""
        yaml_content = """v: 1
timestamp: 2024-01-01T00:00:00+00:00
uid: test-path-field
objects:
- id: 1
  name: Pad
  type_id: PartDesign::Pad
  label: Pad
  path: Body/Pad
  after: Sketch
  properties: {}
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            yaml_path.write_text(yaml_content)

            snapshot = SnapshotYamlSerializer.from_yaml(yaml_path)
            node = snapshot.nodes[0]

            # Verify path is stored (not parent)
            assert node.path == "Body/Pad"
            # Should NOT have a parent field
            assert not hasattr(node, "parent")
