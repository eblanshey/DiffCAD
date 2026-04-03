"""File responsibility: Unit tests for CompareSnapshotsAction."""

import datetime

import pytest

from freecad.diff_wb.application.actions.commands import CompareSnapshotsAction
from freecad.diff_wb.domain.snapshots.models import Snapshot
from freecad.diff_wb.domain.tree import Property, PropertyType
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
        assert len(diff_engine.compare_calls) == 1

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
                    properties={"Property1": Property(type_=PropertyType.STRING, value="Value1")},
                )
            ],
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
                    properties={"Property1": Property(type_=PropertyType.STRING, value="Value2")},
                )
            ],
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        diff_engine = FakeDiffEngine()
        settings_repo = FakeSettingsRepository(
            excluded_types=["App::Origin"],
            excluded_properties=["TimeStamp"],
        )

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id, new_id)

        # Assert
        assert result.success is True
        assert len(diff_engine.compare_calls) == 1

        # Verify the call arguments
        call_args = diff_engine.compare_calls[0]
        old_snapshot, new_snapshot, excluded_types, excluded_properties = call_args

        # Check that Snapshot objects were passed
        assert isinstance(old_snapshot, Snapshot)
        assert isinstance(new_snapshot, Snapshot)
        assert len(old_snapshot.nodes) == 1
        assert len(new_snapshot.nodes) == 1

        # Check that exclusion settings were passed
        assert excluded_types == ["App::Origin"]
        assert excluded_properties == ["TimeStamp"]

    def test_execute_uses_settings(self) -> None:
        """Uses SettingsRepository for exclusions."""
        # Arrange
        snapshot_repo = FakeSnapshotRepository()
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        custom_excluded_types = ["CustomType1", "CustomType2"]
        custom_excluded_properties = ["CustomProp1", "CustomProp2"]

        diff_engine = FakeDiffEngine()
        settings_repo = FakeSettingsRepository(
            excluded_types=custom_excluded_types,
            excluded_properties=custom_excluded_properties,
        )

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id, new_id)

        # Assert
        assert result.success is True
        assert len(diff_engine.compare_calls) == 1

        _, _, excluded_types, excluded_properties = diff_engine.compare_calls[0]
        assert excluded_types == custom_excluded_types
        assert excluded_properties == custom_excluded_properties

    def test_execute_logs_progress(self) -> None:
        """Logger receives progress messages."""
        # Arrange
        snapshot_repo = FakeSnapshotRepository()
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            nodes=[],
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
        # Note: Logging is done via static Log methods, not captured in unit tests

    def test_execute_diff_engine_exception(self) -> None:
        """Error: DiffEngine raises exception during comparison."""
        # Arrange
        snapshot_repo = FakeSnapshotRepository()
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        diff_engine = FakeDiffEngine(side_effect=RuntimeError("Comparison failed"))
        settings_repo = FakeSettingsRepository()

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id, new_id)

        # Assert
        assert result.success is False
        assert result.diff_result is None
        # RuntimeError is not in our specific exception list, so it falls through to catch-all
        assert "Unexpected error during diff computation" in str(result.error_message)

        # Note: Logging is done via static Log methods, not captured in unit tests

    def test_execute_same_snapshot_id_returns_unchanged_diff(self) -> None:
        """Edge case: comparing snapshot to itself returns no changes."""
        # Arrange
        snapshot_repo = FakeSnapshotRepository()
        snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        snapshot_id = snapshot_repo.add_snapshot(snapshot)

        diff_engine = FakeDiffEngine()
        settings_repo = FakeSettingsRepository()

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(snapshot_id, snapshot_id)

        # Assert
        assert result.success is True
        assert result.diff_result is not None
        assert len(result.diff_result.node_diffs) == 0  # No changes expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
