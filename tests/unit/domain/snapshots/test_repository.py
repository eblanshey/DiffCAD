# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for InMemorySnapshotRepository including store creation,
# snapshot addition/retrieval/deletion, metadata listing, and nested children handling.
"""Unit tests for InMemorySnapshotRepository."""

from datetime import datetime

from freecad.history_wb.domain import Snapshot, SnapshotObject, SnapshotOccurrence
from freecad.history_wb.domain.snapshots.repository import InMemorySnapshotRepository


def _make_snapshot(name: str, objects: list[SnapshotObject], occurrences: list[SnapshotOccurrence]) -> Snapshot:
    """Helper to create a Snapshot with current timestamp."""
    return Snapshot(
        snapshot_id="", document_name=name, timestamp=datetime.now(), objects=objects, occurrences=occurrences
    )


class TestInMemorySnapshotRepository:
    """Tests for InMemorySnapshotRepository class."""

    def test_store_creation_and_initialization(self) -> None:
        """Test that store can be created and starts empty."""
        store = InMemorySnapshotRepository()
        assert store.list_snapshots() == []

    def test_add_snapshot_returns_snapshot_id(self) -> None:
        """Test that add_snapshot returns a unique snapshot_id."""
        store = InMemorySnapshotRepository()
        objects = [
            SnapshotObject(
                id=1,
                name="TestObject",
                type_id="PartDesign::Body",
                properties={},
            )
        ]
        occurrences = [SnapshotOccurrence(path="TestObject", after=None)]
        snapshot = _make_snapshot("test_snapshot", objects, occurrences)
        snapshot_id = store.add_snapshot(snapshot)

        assert snapshot_id is not None
        assert isinstance(snapshot_id, str)

    def test_get_snapshot_returns_snapshot(self) -> None:
        """Test that get_snapshot returns the stored snapshot."""
        store = InMemorySnapshotRepository()
        objects = [
            SnapshotObject(
                id=2,
                name="TestObject",
                type_id="PartDesign::Body",
                properties={},
            )
        ]
        occurrences = [SnapshotOccurrence(path="TestObject", after=None)]
        snapshot = _make_snapshot("test_snapshot_2", objects, occurrences)
        snapshot_id = store.add_snapshot(snapshot)

        retrieved = store.get_snapshot(snapshot_id)
        assert retrieved is not None
        assert retrieved.document_name == "test_snapshot_2"
        assert len(retrieved.occurrences) == 1
        assert retrieved.occurrences[0].path == "TestObject"

    def test_delete_snapshot_removes_snapshot(self) -> None:
        """Test that delete_snapshot removes the snapshot from the store."""
        store = InMemorySnapshotRepository()
        objects = [
            SnapshotObject(
                id=3,
                name="TestObject",
                type_id="PartDesign::Body",
                properties={},
            )
        ]
        occurrences = [SnapshotOccurrence(path="TestObject", after=None)]
        snapshot = _make_snapshot("test_snapshot_3", objects, occurrences)
        snapshot_id = store.add_snapshot(snapshot)

        store.delete_snapshot(snapshot_id)
        retrieved = store.get_snapshot(snapshot_id)
        assert retrieved is None

    def test_list_snapshots_returns_all(self) -> None:
        """Test that list_snapshots returns all stored snapshots."""
        store = InMemorySnapshotRepository()
        for i in range(3):
            objects = [
                SnapshotObject(
                    id=i + 1,
                    name=f"TestObject{i}",
                    type_id="PartDesign::Body",
                    properties={},
                )
            ]
            occurrences = [SnapshotOccurrence(path=f"TestObject{i}", after=None)]
            store.add_snapshot(_make_snapshot(f"test_snapshot_{i}", objects, occurrences))

        snapshots = store.list_snapshots()
        assert len(snapshots) == 3

    def test_get_nonexistent_snapshot_returns_none(self) -> None:
        """Test that get_snapshot returns None for non-existent snapshot."""
        store = InMemorySnapshotRepository()
        retrieved = store.get_snapshot("nonexistent-id")
        assert retrieved is None
