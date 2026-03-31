"""File responsibility: Application-level tests for TakeSnapshotAction.

These tests verify the complete take snapshot workflow using real domain services
(SnapshotExtractor, DiffEngine) with fake ports (FakeFreeCadPort, InMemorySnapshotRepository).

See AGENTS.md in this directory for more information about application action testing.
"""

from freecad.diff_wb.application.actions.commands.take_snapshot import TakeSnapshotAction
from freecad.diff_wb.domain.snapshots.gui_extractor import SnapshotExtractor
from freecad.diff_wb.domain.snapshots.repository import InMemorySnapshotRepository
from tests.fakes.fake_freecad_port import FakeFreeCadPort


class TestTakeSnapshotAction:
    """Application-level tests for TakeSnapshotAction using real domain services."""

    def test_take_snapshot_with_valid_document(self):
        """Test successful snapshot creation with a valid document."""
        # Arrange
        fake_doc = type("FakeDocument", (), {"Name": "TestDocument", "Objects": []})()
        fake_freecad_port = FakeFreeCadPort(active_document=fake_doc)
        snapshot_repo = InMemorySnapshotRepository()
        extractor = SnapshotExtractor()

        action = TakeSnapshotAction(
            freecad_port=fake_freecad_port,
            extractor=extractor,
            snapshot_repo=snapshot_repo,
        )

        # Act
        result = action.execute(name="test_snapshot")

        # Assert
        assert result.success is True
        assert result.snapshot_name == "test_snapshot"
        assert result.snapshot_id is not None
        assert result.error_message is None

    def test_take_snapshot_with_no_document(self):
        """Test snapshot creation when no document is active."""
        # Arrange
        fake_freecad_port = FakeFreeCadPort(active_document=None)
        snapshot_repo = InMemorySnapshotRepository()
        extractor = SnapshotExtractor()

        action = TakeSnapshotAction(
            freecad_port=fake_freecad_port,
            extractor=extractor,
            snapshot_repo=snapshot_repo,
        )

        # Act
        result = action.execute(name="test_snapshot")

        # Assert
        assert result.success is False
        assert result.snapshot_name is None
        assert result.snapshot_id is None
        assert result.error_message == "No active document available"

    def test_take_snapshot_auto_generates_name(self):
        """Test that snapshot name is auto-generated with timestamp when not provided."""
        # Arrange
        fake_doc = type("FakeDocument", (), {"Name": "MyDoc", "Objects": []})()
        fake_freecad_port = FakeFreeCadPort(active_document=fake_doc)
        snapshot_repo = InMemorySnapshotRepository()
        extractor = SnapshotExtractor()

        action = TakeSnapshotAction(
            freecad_port=fake_freecad_port,
            extractor=extractor,
            snapshot_repo=snapshot_repo,
        )

        # Act
        result = action.execute(name=None)

        # Assert - name should include timestamp for uniqueness
        assert result.success is True
        assert result.snapshot_name is not None
        assert result.snapshot_name.startswith("MyDoc_")
        # Verify format: MyDoc_YYYYMMDD_HHMMSS (3 parts separated by _)
        parts = result.snapshot_name.split("_")
        assert len(parts) == 3  # doc_name + date + time
        assert result.snapshot_id is not None

    def test_take_snapshot_with_tree_nodes(self):
        """Test snapshot creation with actual tree nodes."""
        # Arrange

        # Create a mock document with objects
        mock_obj = type(
            "MockObject",
            (),
            {
                "Name": "Part",
                "TypeId": "Part::Feature",
                "Label": "Part",
                "PropertiesList": [],
                "OutList": [],
            },
        )()
        fake_doc = type("FakeDocument", (), {"Name": "TestDoc", "Objects": [mock_obj]})()
        fake_freecad_port = FakeFreeCadPort(active_document=fake_doc)
        snapshot_repo = InMemorySnapshotRepository()
        extractor = SnapshotExtractor()

        action = TakeSnapshotAction(
            freecad_port=fake_freecad_port,
            extractor=extractor,
            snapshot_repo=snapshot_repo,
        )

        # Act
        result = action.execute(name="snapshot_with_nodes")

        # Assert
        assert result.success is True
        assert result.snapshot_name == "snapshot_with_nodes"
        assert result.snapshot_id is not None

    def test_take_snapshot_saves_to_repository(self):
        """Test that created snapshot is saved to repository."""
        # Arrange
        fake_doc = type("FakeDocument", (), {"Name": "TestDoc", "Objects": []})()
        fake_freecad_port = FakeFreeCadPort(active_document=fake_doc)
        snapshot_repo = InMemorySnapshotRepository()
        extractor = SnapshotExtractor()

        action = TakeSnapshotAction(
            freecad_port=fake_freecad_port,
            extractor=extractor,
            snapshot_repo=snapshot_repo,
        )

        # Act
        result = action.execute(name="test_snapshot")

        # Assert
        assert result.success is True
        # Verify snapshot was saved in repository
        assert result.snapshot_id is not None
        saved_snapshot = snapshot_repo.get_snapshot(result.snapshot_id)
        assert saved_snapshot is not None
        assert saved_snapshot.document_name == "TestDoc"

    def test_take_snapshot_custom_name(self):
        """Test using a custom snapshot name."""
        # Arrange
        fake_doc = type("FakeDocument", (), {"Name": "TestDoc", "Objects": []})()
        fake_freecad_port = FakeFreeCadPort(active_document=fake_doc)
        snapshot_repo = InMemorySnapshotRepository()
        extractor = SnapshotExtractor()

        action = TakeSnapshotAction(
            freecad_port=fake_freecad_port,
            extractor=extractor,
            snapshot_repo=snapshot_repo,
        )

        # Act
        result = action.execute(name="my_custom_snapshot_name")

        # Assert
        assert result.success is True
        assert result.snapshot_name == "my_custom_snapshot_name"
