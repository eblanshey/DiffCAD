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
        snapshot = Snapshot(document_name="TestDocument", timestamp=timestamp)
        assert snapshot.document_name == "TestDocument"
        assert snapshot.timestamp == timestamp

    def test_with_root_nodes(self):
        """Test snapshot with root nodes."""
        node = TreeNode(name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(document_name="TestDocument", timestamp=timestamp, root_nodes=[node])
        assert len(snapshot.root_nodes) == 1

    def test_get_all_nodes(self):
        """Test getting all nodes recursively."""
        child = TreeNode(name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", is_root=False)
        parent = TreeNode(name="Body", type_id="PartDesign::Body", label="Body", path="Body", children=[child])
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(document_name="TestDocument", timestamp=timestamp, root_nodes=[parent])
        all_nodes = snapshot.get_all_nodes()
        assert len(all_nodes) == 2

    def test_find_node_by_path(self):
        """Test finding a node by path."""
        child = TreeNode(name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", is_root=False)
        parent = TreeNode(name="Body", type_id="PartDesign::Body", label="Body", path="Body", children=[child])
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(document_name="TestDocument", timestamp=timestamp, root_nodes=[parent])
        found = snapshot.find_node_by_path("Body/Pad")
        assert found is not None
        assert found.name == "Pad"

    def test_find_nonexistent_node(self):
        """Test finding a nonexistent node."""
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(document_name="TestDocument", timestamp=timestamp)
        found = snapshot.find_node_by_path("NonExistent")
        assert found is None

    def test_snapshot_sorting(self):
        """Test that snapshots can be sorted by timestamp."""
        ts1 = datetime(2024, 1, 1, 0, 0, 0)
        ts2 = datetime(2024, 1, 2, 0, 0, 0)
        ts3 = datetime(2024, 1, 1, 12, 0, 0)

        snapshot1 = Snapshot(document_name="TestDocument", timestamp=ts1)
        snapshot2 = Snapshot(document_name="TestDocument", timestamp=ts2)
        snapshot3 = Snapshot(document_name="TestDocument", timestamp=ts3)

        # Sort snapshots by timestamp
        sorted_snapshots = sorted([snapshot2, snapshot1, snapshot3], key=lambda s: s.timestamp)

        assert sorted_snapshots[0] == snapshot1  # Earliest
        assert sorted_snapshots[1] == snapshot3  # Middle
        assert sorted_snapshots[2] == snapshot2  # Latest
