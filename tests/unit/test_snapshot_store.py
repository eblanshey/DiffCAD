# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for SnapshotStore."""

from datetime import datetime

import pytest

from freecad.diff_wb.domain.snapshot import Snapshot, TreeNode
from freecad.diff_wb.domain.property_value import PropertyValue, PropertyType
from freecad.diff_wb.snapshot.snapshot_store import SnapshotStore


class TestSnapshotStore:
    """Tests for SnapshotStore class."""

    def test_store_creation_and_initialization(self):
        """Test that store can be created and starts empty."""
        store = SnapshotStore()
        assert store.list_snapshots() == []

    def test_add_snapshot_returns_snapshot_id(self):
        """Test that add_snapshot returns a unique snapshot_id."""
        store = SnapshotStore()
        root_nodes = [
            TreeNode(
                name="TestObject",
                type_id="PartDesign::Body",
                label="Test Body",
                path="TestObject",
                is_root=True,
                properties={},
                children=[],
            )
        ]
        snapshot_id = store.add_snapshot("test_snapshot", root_nodes)

        assert snapshot_id is not None
        assert isinstance(snapshot_id, str)

    def test_get_snapshot_returns_snapshot(self):
        """Test that get_snapshot returns the stored snapshot."""
        store = SnapshotStore()
        root_nodes = [
            TreeNode(
                name="TestObject",
                type_id="PartDesign::Body",
                label="Test Body",
                path="TestObject",
                is_root=True,
                properties={"Label": PropertyValue(type_=PropertyType.STRING, value="Test Body")},
                children=[],
            )
        ]
        snapshot_id = store.add_snapshot("test_snapshot", root_nodes)

        snapshot = store.get_snapshot(snapshot_id)

        assert snapshot is not None
        assert snapshot.document_name == "test_snapshot"
        assert len(snapshot.root_nodes) == 1
        assert snapshot.root_nodes[0].name == "TestObject"

    def test_get_snapshot_returns_none_for_invalid_id(self):
        """Test that get_snapshot returns None for non-existent ID."""
        store = SnapshotStore()
        result = store.get_snapshot("non_existent_id")
        assert result is None

    def test_list_snapshots_returns_metadata(self):
        """Test that list_snapshots returns snapshot metadata."""
        store = SnapshotStore()
        root_nodes = [
            TreeNode(
                name="TestObject",
                type_id="PartDesign::Body",
                label="Test Body",
                path="TestObject",
                is_root=True,
                properties={},
                children=[],
            )
        ]
        snapshot_id = store.add_snapshot("test_snapshot", root_nodes)

        snapshots = store.list_snapshots()

        assert len(snapshots) == 1
        assert snapshots[0]["id"] == snapshot_id
        assert snapshots[0]["name"] == "test_snapshot"
        assert "timestamp" in snapshots[0]

    def test_delete_snapshot_removes_snapshot(self):
        """Test that delete_snapshot removes the snapshot."""
        store = SnapshotStore()
        root_nodes = [
            TreeNode(
                name="TestObject",
                type_id="PartDesign::Body",
                label="Test Body",
                path="TestObject",
                is_root=True,
                properties={},
                children=[],
            )
        ]
        snapshot_id = store.add_snapshot("test_snapshot", root_nodes)

        store.delete_snapshot(snapshot_id)

        assert store.get_snapshot(snapshot_id) is None
        assert len(store.list_snapshots()) == 0

    def test_delete_snapshot_returns_true_on_success(self):
        """Test that delete_snapshot returns True on successful deletion."""
        store = SnapshotStore()
        root_nodes = [
            TreeNode(
                name="TestObject",
                type_id="PartDesign::Body",
                label="Test Body",
                path="TestObject",
                is_root=True,
                properties={},
                children=[],
            )
        ]
        snapshot_id = store.add_snapshot("test_snapshot", root_nodes)

        result = store.delete_snapshot(snapshot_id)

        assert result is True

    def test_delete_snapshot_returns_false_for_invalid_id(self):
        """Test that delete_snapshot returns False for non-existent ID."""
        store = SnapshotStore()
        result = store.delete_snapshot("non_existent_id")
        assert result is False

    def test_duplicate_name_handling(self):
        """Test that duplicate snapshot names are allowed (different IDs)."""
        store = SnapshotStore()
        root_nodes1 = [
            TreeNode(
                name="Object1",
                type_id="PartDesign::Body",
                label="Object 1",
                path="Object1",
                is_root=True,
                properties={},
                children=[],
            )
        ]
        root_nodes2 = [
            TreeNode(
                name="Object2",
                type_id="PartDesign::Body",
                label="Object 2",
                path="Object2",
                is_root=True,
                properties={},
                children=[],
            )
        ]

        id1 = store.add_snapshot("same_name", root_nodes1)
        id2 = store.add_snapshot("same_name", root_nodes2)

        # Both should have different IDs
        assert id1 != id2

        # Both should be retrievable
        snap1 = store.get_snapshot(id1)
        snap2 = store.get_snapshot(id2)

        assert snap1 is not None
        assert snap2 is not None
        assert snap1.document_name == "same_name"
        assert snap2.document_name == "same_name"
        assert snap1.root_nodes[0].name == "Object1"
        assert snap2.root_nodes[0].name == "Object2"

    def test_empty_store_behavior(self):
        """Test behavior of empty store operations."""
        store = SnapshotStore()

        # List should return empty list
        assert store.list_snapshots() == []

        # Get should return None
        assert store.get_snapshot("any_id") is None

        # Delete should return False
        assert store.delete_snapshot("any_id") is False

    def test_clear_removes_all_snapshots(self):
        """Test that clear() removes all snapshots."""
        store = SnapshotStore()

        # Add multiple snapshots
        for i in range(3):
            root_nodes = [
                TreeNode(
                    name=f"Object{i}",
                    type_id="PartDesign::Body",
                    label=f"Object {i}",
                    path=f"Object{i}",
                    is_root=True,
                    properties={},
                    children=[],
                )
            ]
            store.add_snapshot(f"snapshot_{i}", root_nodes)

        assert len(store.list_snapshots()) == 3

        store.clear()

        assert store.list_snapshots() == []
        assert len(store._snapshots) == 0

    def test_snapshot_timestamp_is_set(self):
        """Test that snapshot timestamp is set correctly."""
        store = SnapshotStore()
        root_nodes = [
            TreeNode(
                name="TestObject",
                type_id="PartDesign::Body",
                label="Test Body",
                path="TestObject",
                is_root=True,
                properties={},
                children=[],
            )
        ]

        before = datetime.now()
        snapshot_id = store.add_snapshot("test_snapshot", root_nodes)
        after = datetime.now()

        snapshot = store.get_snapshot(snapshot_id)
        assert snapshot is not None
        assert before <= snapshot.timestamp <= after

    def test_nested_children_preserved(self):
        """Test that nested child nodes are preserved in storage."""
        store = SnapshotStore()
        child_node = TreeNode(
            name="Child",
            type_id="PartDesign::Feature",
            label="Child Feature",
            path="Parent/Child",
            is_root=False,
            properties={"Length": PropertyValue(type_=PropertyType.FLOAT, value=10.0)},
            children=[],
        )
        parent_node = TreeNode(
            name="Parent",
            type_id="PartDesign::Body",
            label="Parent Body",
            path="Parent",
            is_root=True,
            properties={},
            children=[child_node],
        )
        root_nodes = [parent_node]

        snapshot_id = store.add_snapshot("nested_test", root_nodes)
        snapshot = store.get_snapshot(snapshot_id)

        assert snapshot is not None
        assert len(snapshot.root_nodes) == 1
        assert len(snapshot.root_nodes[0].children) == 1
        assert snapshot.root_nodes[0].children[0].name == "Child"
