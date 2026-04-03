"""File responsibility: Unit tests for ListSnapshotsAction."""

import datetime

import pytest

from freecad.diff_wb.application.actions.queries import ListSnapshotsAction
from freecad.diff_wb.domain.snapshots.models import Snapshot
from freecad.diff_wb.domain.snapshots.repository import InMemorySnapshotRepository
from freecad.diff_wb.domain.tree.node import TreeNode


class TestListSnapshotsAction:
    """Test suite for ListSnapshotsAction."""

    def test_execute_returns_all_snapshots(self) -> None:
        """Returns list of all snapshots."""
        # Arrange
        repo = InMemorySnapshotRepository()

        mock_snapshot1 = Snapshot(
            snapshot_id="",  # Will be assigned by repository
            document_name="Document1",
            timestamp=datetime.datetime(2024, 1, 1, 10, 0),
            nodes=[
                TreeNode(
                    id=1,
                    name="Object1",
                    type_id="Part::Feature",
                    label="Object1",
                    path="Object1",
                    after=None,
                    properties={},
                )
            ],
        )
        mock_snapshot2 = Snapshot(
            snapshot_id="",  # Will be assigned by repository
            document_name="Document2",
            timestamp=datetime.datetime(2024, 1, 2, 11, 0),
            nodes=[],
        )
        repo.add_snapshot(mock_snapshot1)
        repo.add_snapshot(mock_snapshot2)

        action = ListSnapshotsAction(snapshot_repo=repo)

        # Act
        result = action.execute()

        # Assert
        assert len(result) == 2

    def test_execute_empty_repository(self) -> None:
        """Returns empty list when no snapshots."""
        # Arrange
        repo = InMemorySnapshotRepository()
        action = ListSnapshotsAction(snapshot_repo=repo)

        # Act
        result = action.execute()

        # Assert
        assert result == []
        assert len(result) == 0

    def test_execute_formats_summaries(self) -> None:
        """Each item is SnapshotSummary."""
        # Arrange
        repo = InMemorySnapshotRepository()

        mock_snapshot = Snapshot(
            snapshot_id="",  # Will be assigned by repository
            document_name="TestDocument",
            timestamp=datetime.datetime(2024, 1, 1, 10, 0),
            nodes=[
                TreeNode(
                    id=1,
                    name="Object1",
                    type_id="Part::Feature",
                    label="Object1",
                    path="Object1",
                    after=None,
                    properties={},
                ),
                TreeNode(
                    id=2,
                    name="Child1",
                    type_id="Part::Feature",
                    label="Child1",
                    path="Object1/Child1",
                    after="Object1",
                    properties={},
                ),
            ],
        )
        snapshot_id = repo.add_snapshot(mock_snapshot)

        action = ListSnapshotsAction(snapshot_repo=repo)

        # Act
        result = action.execute()

        # Assert
        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        assert len(result) == 1
        assert isinstance(result[0], SnapshotSummary)
        assert result[0].id == snapshot_id  # Verify ID is the UUID from repository
        assert result[0].name == "TestDocument"
        assert result[0].created_at == "2024-01-01T10:00:00"
        assert result[0].node_count == 2  # Object1 + Child1

    def test_execute_returns_unique_ids(self) -> None:
        """Each snapshot should have a unique ID."""
        # Arrange
        repo = InMemorySnapshotRepository()
        repo.add_snapshot(
            Snapshot(
                snapshot_id="",  # Will be assigned by repository
                document_name="Doc1",
                timestamp=datetime.datetime.now(),
                nodes=[],
            )
        )
        repo.add_snapshot(
            Snapshot(
                snapshot_id="",  # Will be assigned by repository
                document_name="Doc2",
                timestamp=datetime.datetime.now(),
                nodes=[],
            )
        )

        action = ListSnapshotsAction(snapshot_repo=repo)

        # Act
        result = action.execute()

        # Assert
        assert len(result) == 2
        assert result[0].id != result[1].id  # IDs should be different


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
