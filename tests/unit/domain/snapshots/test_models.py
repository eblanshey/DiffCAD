# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the Snapshot class including creation, node retrieval,
# path-based node finding, and sorting functionality.
"""Unit tests for the Snapshot class."""

from datetime import datetime

from freecad.diff_wb.domain import Snapshot, TreeNode


class TestSnapshot:
    """Tests for the Snapshot class."""

    def test_creation(self):
        """Test snapshot creation."""
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(snapshot_id="test-id", document_name="TestDocument", timestamp=timestamp)
        assert snapshot.document_name == "TestDocument"
        assert snapshot.timestamp == timestamp

    def test_with_flat_nodes_list(self):
        """Test snapshot creation with flat nodes list."""
        node = TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(snapshot_id="test-id", document_name="TestDocument", timestamp=timestamp, nodes=[node])
        assert len(snapshot.nodes) == 1

    def test_root_node_identification(self):
        """Test root node identification - path without '/' separator."""
        root_node = TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(snapshot_id="test-id", document_name="TestDocument", timestamp=timestamp, nodes=[root_node])

        # Root node has path equal to its name (no "/" separator)
        assert "/" not in snapshot.nodes[0].path
        assert snapshot.nodes[0].path == "Body"

    def test_non_root_node_path(self):
        """Test non-root node has path with '/' separator."""
        root_node = TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        child_node = TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad")
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(
            snapshot_id="test-id", document_name="TestDocument", timestamp=timestamp, nodes=[root_node, child_node]
        )

        # Non-root node has path with "/" separator
        assert "/" in snapshot.nodes[1].path
        assert snapshot.nodes[1].path == "Body/Pad"

    def test_get_all_nodes_returns_flat_list(self):
        """Test get_all_nodes() returns flat list directly without recursion."""
        root_node = TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        child_node = TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad")
        grandchild_node = TreeNode(
            id=3, name="Sketch", type_id="Sketcher::SketchObject", label="Sketch", path="Body/Pad/Sketch"
        )
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(
            snapshot_id="test-id",
            document_name="TestDocument",
            timestamp=timestamp,
            nodes=[root_node, child_node, grandchild_node],
        )

        all_nodes = snapshot.get_all_nodes()

        # Should return flat list directly without recursion
        assert len(all_nodes) == 3
        assert all_nodes == [root_node, child_node, grandchild_node]

    def test_find_node_by_path_searches_flat_list(self):
        """Test find_node_by_path() searches flat list efficiently."""
        root_node = TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        child_node = TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad")
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(
            snapshot_id="test-id", document_name="TestDocument", timestamp=timestamp, nodes=[root_node, child_node]
        )

        found = snapshot.find_node_by_path("Body/Pad")
        assert found is not None
        assert found.name == "Pad"
        assert found.id == 2

    def test_find_node_by_path_root(self):
        """Test find_node_by_path() for root node."""
        root_node = TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        child_node = TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad")
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(
            snapshot_id="test-id", document_name="TestDocument", timestamp=timestamp, nodes=[root_node, child_node]
        )

        found = snapshot.find_node_by_path("Body")
        assert found is not None
        assert found.name == "Body"
        assert found.id == 1

    def test_find_nonexistent_node(self):
        """Test finding a nonexistent node."""
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(snapshot_id="test-id", document_name="TestDocument", timestamp=timestamp)
        found = snapshot.find_node_by_path("NonExistent")
        assert found is None

    def test_node_count_returns_flat_list_length(self):
        """Test node_count returns correct flat list length."""
        root_node = TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        child_node = TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad")
        grandchild_node = TreeNode(
            id=3, name="Sketch", type_id="Sketcher::SketchObject", label="Sketch", path="Body/Pad/Sketch"
        )
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(
            snapshot_id="test-id",
            document_name="TestDocument",
            timestamp=timestamp,
            nodes=[root_node, child_node, grandchild_node],
        )

        # Should return flat list length directly
        assert snapshot.node_count == 3

    def test_snapshot_can_be_created_from_flat_nodes(self):
        """Test Snapshot can be created from list of flat nodes."""
        nodes = [
            TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None),
            TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", after="Body"),
            TreeNode(id=3, name="Box", type_id="Part::Box", label="Box", path="Box", after=None),
        ]
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(snapshot_id="test-id", document_name="TestDocument", timestamp=timestamp, nodes=nodes)

        # Verify all nodes are accessible
        assert snapshot.node_count == 3
        all_nodes = snapshot.get_all_nodes()
        assert len(all_nodes) == 3

        # Verify root nodes are identified correctly (path without "/")
        root_paths = [n.path for n in all_nodes if "/" not in n.path]
        assert "Body" in root_paths
        assert "Box" in root_paths

    def test_snapshot_sorting(self):
        """Test that snapshots can be sorted by timestamp."""
        ts1 = datetime(2024, 1, 1, 0, 0, 0)
        ts2 = datetime(2024, 1, 2, 0, 0, 0)
        ts3 = datetime(2024, 1, 1, 12, 0, 0)

        snapshot1 = Snapshot(snapshot_id="test-id-1", document_name="TestDocument", timestamp=ts1)
        snapshot2 = Snapshot(snapshot_id="test-id-2", document_name="TestDocument", timestamp=ts2)
        snapshot3 = Snapshot(snapshot_id="test-id-3", document_name="TestDocument", timestamp=ts3)

        # Sort snapshots by timestamp
        sorted_snapshots = sorted([snapshot2, snapshot1, snapshot3], key=lambda s: s.timestamp)

        assert sorted_snapshots[0] == snapshot1  # Earliest
        assert sorted_snapshots[1] == snapshot3  # Middle
        assert sorted_snapshots[2] == snapshot2  # Latest
