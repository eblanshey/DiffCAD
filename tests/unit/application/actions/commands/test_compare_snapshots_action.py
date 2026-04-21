"""File responsibility: Unit tests for CompareSnapshotsAction."""

import datetime

from freecad.diff_wb.application.actions.commands import CompareSnapshotsAction
from freecad.diff_wb.domain.snapshots.models import Snapshot
from freecad.diff_wb.domain.tree import Property
from freecad.diff_wb.domain.tree.node import TreeNode
from tests.fakes import FakeDiffEngine, FakeSettingsRepository, FakeSnapshotRepository


class TestCompareSnapshotsAction:
    """Test suite for CompareSnapshotsAction."""

    def test_execute_success_computes_diff(self) -> None:
        """Happy path: compares two snapshots successfully."""
        # Arrange
        snapshot_repo = FakeSnapshotRepository()
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            nodes=[
                TreeNode(
                    id=1,
                    name="Node1",
                    type_id="Part::Feature",
                    label="Node1",
                    path="Node1",
                    after=None,
                    properties={},
                )
            ],
            git_path="",
        )
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            nodes=[
                TreeNode(
                    id=1,
                    name="Node1",
                    type_id="Part::Feature",
                    label="Node1 Modified",
                    path="Node1",
                    after=None,
                    properties={},
                )
            ],
            git_path="",
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        diff_engine = FakeDiffEngine()
        settings_repo = FakeSettingsRepository()

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id, new_id)

        # Assert
        assert result.success is True
        assert result.diff_result is not None
        assert result.error_message is None
        assert len(diff_engine.compute_diff_calls) == 1

    def test_execute_old_not_found(self) -> None:
        """Error: old snapshot ID doesn't exist."""
        # Arrange
        snapshot_repo = FakeSnapshotRepository()
        diff_engine = FakeDiffEngine()
        settings_repo = FakeSettingsRepository()

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute("nonexistent-old-id", "some-new-id")

        # Assert
        assert result.success is False
        assert result.diff_result is None
        assert result.error_message == "Old snapshot 'nonexistent-old-id' not found"

    def test_execute_new_not_found(self) -> None:
        """Error: new snapshot ID doesn't exist."""
        # Arrange
        snapshot_repo = FakeSnapshotRepository()
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            nodes=[],
            git_path="",
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)

        diff_engine = FakeDiffEngine()
        settings_repo = FakeSettingsRepository()

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id, "nonexistent-new-id")

        # Assert
        assert result.success is False
        assert result.diff_result is None
        assert result.error_message == "New snapshot 'nonexistent-new-id' not found"

    def test_execute_computes_diff(self) -> None:
        """Verifies DiffEngine is called with correct parameters."""
        # Arrange
        snapshot_repo = FakeSnapshotRepository()
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            nodes=[
                TreeNode(
                    id=1,
                    name="Node1",
                    type_id="Part::Feature",
                    label="Node1",
                    path="Node1",
                    after=None,
                    properties={"Property1": Property.from_freecad("Value1", {}, "Base")},
                )
            ],
            git_path="",
        )
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            nodes=[
                TreeNode(
                    id=1,
                    name="Node1",
                    type_id="Part::Feature",
                    label="Node1",
                    path="Node1",
                    after=None,
                    properties={"Property1": Property.from_freecad("Value1", {}, "Base")},
                )
            ],
            git_path="",
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        diff_engine = FakeDiffEngine()
        settings_repo = FakeSettingsRepository()

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id, new_id)

        # Assert
        assert result.success is True
        assert result.diff_result is not None
        assert result.error_message is None
        assert len(diff_engine.compute_diff_calls) == 1
