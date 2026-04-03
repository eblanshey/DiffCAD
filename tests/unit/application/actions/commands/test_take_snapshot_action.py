"""File responsibility: Unit tests for TakeSnapshotAction."""

import datetime
from typing import cast
from unittest.mock import MagicMock

import pytest

from freecad.diff_wb.application.actions.commands import TakeSnapshotAction
from freecad.diff_wb.domain.snapshots.models import Snapshot
from freecad.diff_wb.domain.snapshots.repository import InMemorySnapshotRepository
from freecad.diff_wb.domain.tree.node import TreeNode
from tests.fakes.fake_freecad_port import FakeFreeCadPort


class TestTakeSnapshotAction:
    """Test suite for TakeSnapshotAction."""

    def test_execute_success_creates_snapshot(self) -> None:
        """Happy path: creates snapshot, returns success."""
        # Arrange
        doc = MagicMock()
        doc.Name = "TestDocument"
        freecad_port = FakeFreeCadPort(active_document=doc)
        repo = InMemorySnapshotRepository()

        mock_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDocument",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )

        action = TakeSnapshotAction(
            freecad_port=freecad_port,
            extractor=MagicMock(extract_tree=MagicMock(return_value=mock_snapshot)),
            snapshot_repo=repo,
        )

        # Act
        result = action.execute()

        # Assert
        assert result.success is True
        assert result.snapshot_id is not None
        # Name should include timestamp for uniqueness
        assert result.snapshot_name is not None
        assert result.snapshot_name.startswith("TestDocument_")
        assert result.error_message is None

        # Verify snapshot was saved
        saved_snapshot = repo.get_snapshot(result.snapshot_id)
        assert saved_snapshot is not None
        assert saved_snapshot.document_name == "TestDocument"

    def test_execute_no_active_document(self) -> None:
        """Error: no active document available."""
        # Arrange
        freecad_port = FakeFreeCadPort(active_document=None)
        repo = InMemorySnapshotRepository()

        action = TakeSnapshotAction(
            freecad_port=freecad_port,
            extractor=MagicMock(),
            snapshot_repo=repo,
        )

        # Act
        result = action.execute()

        # Assert
        assert result.success is False
        assert result.snapshot_id is None
        assert result.snapshot_name is None
        assert result.error_message == "No active document available"

    def test_execute_extraction_failure(self) -> None:
        """Error: extractor raises exception."""
        # Arrange
        doc = MagicMock()
        doc.Name = "TestDocument"
        freecad_port = FakeFreeCadPort(active_document=doc)
        repo = InMemorySnapshotRepository()

        action = TakeSnapshotAction(
            freecad_port=freecad_port,
            extractor=MagicMock(extract_tree=MagicMock(side_effect=RuntimeError("Extraction failed"))),
            snapshot_repo=repo,
        )

        # Act
        result = action.execute()

        # Assert
        assert result.success is False
        assert result.snapshot_id is None
        assert result.snapshot_name is None
        # RuntimeError is not in our specific exception list, so it falls through to catch-all
        assert "Unexpected error during snapshot extraction" in str(result.error_message)

    def test_execute_saves_to_repository(self) -> None:
        """Verifies snapshot is saved to repository."""
        # Arrange
        doc = MagicMock()
        doc.Name = "TestDocument"
        freecad_port = FakeFreeCadPort(active_document=doc)
        repo = InMemorySnapshotRepository()

        mock_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDocument",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        extractor = MagicMock(extract_tree=MagicMock(return_value=mock_snapshot))

        action = TakeSnapshotAction(
            freecad_port=freecad_port,
            extractor=extractor,
            snapshot_repo=repo,
        )

        # Act
        result = action.execute()

        # Assert
        assert result.success is True
        assert len(repo.list_snapshots()) == 1
        saved_snapshot = repo.get_snapshot(cast(str, result.snapshot_id))
        assert saved_snapshot is not None

    def test_execute_generates_unique_id(self) -> None:
        """Each snapshot gets unique UUID."""
        # Arrange
        doc = MagicMock()
        doc.Name = "TestDocument"
        freecad_port = FakeFreeCadPort(active_document=doc)
        repo = InMemorySnapshotRepository()

        mock_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDocument",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        extractor = MagicMock(extract_tree=MagicMock(return_value=mock_snapshot))

        action = TakeSnapshotAction(
            freecad_port=freecad_port,
            extractor=extractor,
            snapshot_repo=repo,
        )

        # Act: Create multiple snapshots
        result1 = action.execute()
        result2 = action.execute()
        result3 = action.execute()

        # Assert
        assert result1.snapshot_id != result2.snapshot_id
        assert result2.snapshot_id != result3.snapshot_id
        assert result1.snapshot_id != result3.snapshot_id

    def test_execute_with_custom_name(self) -> None:
        """Uses provided name parameter."""
        # Arrange
        doc = MagicMock()
        doc.Name = "TestDocument"
        freecad_port = FakeFreeCadPort(active_document=doc)
        repo = InMemorySnapshotRepository()

        mock_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDocument",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        extractor = MagicMock(extract_tree=MagicMock(return_value=mock_snapshot))

        action = TakeSnapshotAction(
            freecad_port=freecad_port,
            extractor=extractor,
            snapshot_repo=repo,
        )

        # Act
        result = action.execute(name="CustomName")

        # Assert
        assert result.success is True
        assert result.snapshot_name == "CustomName"

    def test_generate_default_name_from_document(self) -> None:
        """Tests _generate_default_name uses document Name with timestamp."""

        # Arrange - Create a proper mock document with Name set
        class MockDocument:
            Name = "MyDoc"

        doc = MockDocument()
        action = TakeSnapshotAction(
            freecad_port=MagicMock(),
            extractor=MagicMock(),
            snapshot_repo=MagicMock(),
        )

        # Act - call as an instance method
        name = action._generate_default_name(doc)

        # Assert - format should be MyDoc_YYYYMMDD_HHMMSS
        assert name.startswith("MyDoc_")
        parts = name.split("_")
        assert len(parts) == 3  # doc_name + date + time
        assert len(parts[1]) == 8  # date part (YYYYMMDD)
        assert len(parts[2]) == 6  # time part (HHMMSS)

    def test_generate_default_name_fallback_to_timestamp(self) -> None:
        """Tests _generate_default_name fallback when Name is None."""

        # Arrange - Create a proper mock document with Name set to None
        class MockDocumentNone:
            Name = None

        doc = MockDocumentNone()
        action = TakeSnapshotAction(
            freecad_port=MagicMock(),
            extractor=MagicMock(),
            snapshot_repo=MagicMock(),
        )

        # Act - call as an instance method
        name = action._generate_default_name(doc)

        # Assert - should use timestamp format
        assert isinstance(name, str) and "snapshot_" in name

    def test_execute_with_none_document_name(self) -> None:
        """Generates timestamp-based name when document has no Name."""
        # Arrange
        doc = MagicMock()
        doc.Name = None
        freecad_port = FakeFreeCadPort(active_document=doc)
        repo = InMemorySnapshotRepository()

        mock_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDocument",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        extractor = MagicMock(extract_tree=MagicMock(return_value=mock_snapshot))

        action = TakeSnapshotAction(
            freecad_port=freecad_port,
            extractor=extractor,
            snapshot_repo=repo,
        )

        # Act
        result = action.execute()

        # Assert
        assert result.success is True
        assert isinstance(result.snapshot_name, str) and "snapshot_" in result.snapshot_name

    def test_execute_with_exception_document(self) -> None:
        """Handles cases where Name attribute access raises exception."""

        # Arrange - Create a mock that raises when accessing Name
        class FailingDocument:
            @property
            def Name(self) -> None:
                raise AttributeError("Access error")

        doc = FailingDocument()
        freecad_port = FakeFreeCadPort(active_document=doc)
        repo = InMemorySnapshotRepository()

        mock_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDocument",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        extractor = MagicMock(extract_tree=MagicMock(return_value=mock_snapshot))

        action = TakeSnapshotAction(
            freecad_port=freecad_port,
            extractor=extractor,
            snapshot_repo=repo,
        )

        # Act
        result = action.execute()

        # Assert - should fall back to timestamp-based name
        assert result.success is True
        assert isinstance(result.snapshot_name, str) and "snapshot_" in result.snapshot_name

    def test_execute_repository_failure(self) -> None:
        """Error: repository save fails."""
        # Arrange
        doc = MagicMock()
        doc.Name = "TestDocument"
        freecad_port = FakeFreeCadPort(active_document=doc)
        repo = InMemorySnapshotRepository()

        mock_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDocument",
            timestamp=datetime.datetime.now(),
            nodes=[
                TreeNode(
                    id=1,
                    name="TestObject",
                    type_id="Part::Feature",
                    label="TestObject",
                    path="TestObject",
                    after=None,
                    properties={},
                )
            ],
        )
        extractor = MagicMock(extract_tree=MagicMock(return_value=mock_snapshot))

        # Make add_snapshot raise an exception
        repo.add_snapshot = MagicMock(side_effect=RuntimeError("Save failed"))

        action = TakeSnapshotAction(
            freecad_port=freecad_port,
            extractor=extractor,
            snapshot_repo=repo,
        )

        # Act
        result = action.execute()

        # Assert
        assert result.success is False
        # RuntimeError is not in our specific exception list, so it falls through to catch-all
        assert "Unexpected error during snapshot save" in str(result.error_message)

    def test_execute_multiple_snapshots(self) -> None:
        """Tests creating multiple snapshots."""
        # Arrange
        doc = MagicMock()
        doc.Name = "TestDocument"
        freecad_port = FakeFreeCadPort(active_document=doc)
        repo = InMemorySnapshotRepository()

        mock_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDocument",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        extractor = MagicMock(extract_tree=MagicMock(return_value=mock_snapshot))

        action = TakeSnapshotAction(
            freecad_port=freecad_port,
            extractor=extractor,
            snapshot_repo=repo,
        )

        # Act: Create multiple snapshots
        result1 = action.execute()
        result2 = action.execute()
        result3 = action.execute()

        # Assert
        assert result1.success is True
        assert result2.success is True
        assert result3.success is True
        assert len(repo.list_snapshots()) == 3
        assert result1.snapshot_id != result2.snapshot_id

    def test_execute_auto_generates_name_with_timestamp(self) -> None:
        """Verifies timestamp is always included in auto-generated name."""
        # Arrange
        doc = MagicMock()
        doc.Name = "TestDocument"
        freecad_port = FakeFreeCadPort(active_document=doc)
        repo = InMemorySnapshotRepository()

        mock_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDocument",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        extractor = MagicMock(extract_tree=MagicMock(return_value=mock_snapshot))

        action = TakeSnapshotAction(
            freecad_port=freecad_port,
            extractor=extractor,
            snapshot_repo=repo,
        )

        # Act
        result = action.execute()

        # Assert - timestamp should always be present
        assert result.success is True
        assert result.snapshot_name is not None
        # Name should contain underscore followed by timestamp pattern
        assert "_" in result.snapshot_name

    def test_name_format_is_document_timestamp(self) -> None:
        """Verify name format includes document name and timestamp only.

        Format should be: {doc_name}_{YYYYMMDD_HHMMSS}
        Example: MyPart_20240319_143022
        """
        # Arrange
        mock_doc = MagicMock()
        mock_doc.Name = "MyPart"
        freecad_port = FakeFreeCadPort(active_document=mock_doc)
        repo = InMemorySnapshotRepository()

        mock_snapshot = Snapshot(
            snapshot_id="",
            document_name="MyPart",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        extractor = MagicMock(extract_tree=MagicMock(return_value=mock_snapshot))

        action = TakeSnapshotAction(
            freecad_port=freecad_port,
            extractor=extractor,
            snapshot_repo=repo,
        )

        # Act
        result = action.execute()

        # Assert - format should be: MyPart_20240319_143022
        assert result.success is True
        assert result.snapshot_name is not None
        assert result.snapshot_name.startswith("MyPart_")
        # Verify timestamp pattern (8 digits _ 6 digits)
        parts = result.snapshot_name.split("_")
        assert len(parts) == 3  # doc_name + date + time
        # Verify date part is 8 digits
        assert len(parts[1]) == 8
        assert parts[1].isdigit()
        # Verify time part is 6 digits
        assert len(parts[2]) == 6
        assert parts[2].isdigit()

    def test_name_uses_fallback_when_no_doc_name(self) -> None:
        """Uses 'snapshot' as fallback when doc has no Name attribute."""

        # Arrange - Create document without Name attribute
        class DocumentWithoutName:
            pass

        doc = DocumentWithoutName()
        freecad_port = FakeFreeCadPort(active_document=doc)
        repo = InMemorySnapshotRepository()

        mock_snapshot = Snapshot(
            snapshot_id="",
            document_name="fallback",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        extractor = MagicMock(extract_tree=MagicMock(return_value=mock_snapshot))

        action = TakeSnapshotAction(
            freecad_port=freecad_port,
            extractor=extractor,
            snapshot_repo=repo,
        )

        # Act
        result = action.execute()

        # Assert - should use "snapshot" as base with timestamp
        assert result.success is True
        assert result.snapshot_name is not None
        assert result.snapshot_name.startswith("snapshot_")
        # Should have timestamp parts after "snapshot_"
        parts = result.snapshot_name.split("_")
        assert len(parts) >= 2  # "snapshot" + at least date


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
