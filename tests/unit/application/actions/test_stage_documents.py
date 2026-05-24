# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for StageDocumentsAction using mock dependencies.
# Tests cover empty list handling, snapshot YAML creation, staging both FCStd and YAML files,
# success returns, and failure handling on YAML serialization errors.
"""Unit tests for StageDocumentsAction."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from freecad.history_wb.application.actions.stage_documents import StageDocumentsAction
from freecad.history_wb.domain.freecad_ports import FreeCadPort
from freecad.history_wb.domain.git.git_service import GitService
from freecad.history_wb.domain.git.models import GitRepository
from freecad.history_wb.domain.snapshots.models import Snapshot


class TestStageDocumentsActionEmptyList:
    """Tests for empty list handling."""

    def test_stage_documents_empty_list_returns_success(self) -> None:
        """Test that execute returns Result.success(True) immediately for empty list (no-op)."""
        # Given an empty list of snapshots
        git_service = MagicMock(spec=GitService)
        freecad_port = MagicMock(spec=FreeCadPort)
        action = StageDocumentsAction(git_service=git_service, freecad_port=freecad_port)
        repo = GitRepository(name="test_repo", absolute_path="/tmp/test_repo")

        # When execute is called with empty snapshots
        result = action.execute(repo, [])

        # Then Result.success(True) is returned immediately
        assert result.is_success is True
        assert result.data is True
        assert result.message is None
        # And git_service.stage_files was never called
        git_service.stage_files.assert_not_called()


class TestStageDocumentsActionSnapshotYaml:
    """Tests for snapshot YAML creation."""

    def test_stage_documents_creates_snapshot_yaml(self) -> None:
        """Test that SnapshotYamlSerializer.to_yaml is called with correct path."""
        # Given a mock GitService that returns correct snapshot directory
        git_service = MagicMock(spec=GitService)
        freecad_port = MagicMock(spec=FreeCadPort)
        freecad_port.get_all_open_documents.return_value = []
        git_service.get_eligible_docs.return_value = []
        action = StageDocumentsAction(git_service=git_service, freecad_port=freecad_port)
        repo = GitRepository(name="test_repo", absolute_path="/tmp/test_repo")

        # Create a test snapshot
        snapshot = Snapshot(
            snapshot_id="test-uuid-123",
            document_name="MyDocument",
            timestamp=None,  # type: ignore
            objects=[],
            occurrences=[],
            git_path="path/to/mydoc.FCStd",
        )

        # Mock the SnapshotYamlSerializer
        with patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer") as mock_serializer:
            # When execute is called with repo and list of snapshots
            result = action.execute(repo, [snapshot])

            # Then SnapshotYamlSerializer.to_yaml is called with correct path
            expected_yaml_path = Path("/tmp/test_repo/path/to/.snapshots/mydoc.yaml")
            mock_serializer.to_yaml.assert_called_once_with(snapshot, expected_yaml_path)
            assert result.is_success is True


class TestStageDocumentsActionStaging:
    """Tests for staging both FCStd and YAML files."""

    def test_stage_documents_stages_both_fcstd_and_yaml(self) -> None:
        """Test that git_service.stage_files is called with both FCStd and YAML paths."""
        # Given snapshots with git_path "path/to/mydoc.FCStd"
        git_service = MagicMock(spec=GitService)
        git_service.stage_files.return_value = True
        freecad_port = MagicMock(spec=FreeCadPort)
        freecad_port.get_all_open_documents.return_value = []
        git_service.get_eligible_docs.return_value = []
        action = StageDocumentsAction(git_service=git_service, freecad_port=freecad_port)
        repo = GitRepository(name="test_repo", absolute_path="/tmp/test_repo")

        snapshot = Snapshot(
            snapshot_id="test-uuid-123",
            document_name="MyDocument",
            timestamp=None,  # type: ignore
            objects=[],
            occurrences=[],
            git_path="path/to/mydoc.FCStd",
        )

        # Mock directory creation and YAML serialization
        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer"),
            patch("pathlib.Path.mkdir"),
        ):
            # When execute is called
            result = action.execute(repo, [snapshot])

            # Then git_service.stage_files is called with ["path/to/mydoc.FCStd", "path/to/.snapshots/mydoc.yaml"]
            expected_paths = ["path/to/mydoc.FCStd", "path/to/.snapshots/mydoc.yaml"]
            git_service.stage_files.assert_called_once_with(repo, expected_paths)
            assert result.is_success is True

    def test_stage_documents_multiple_snapshots_stages_all(self) -> None:
        """Test that multiple snapshots stage all their files correctly."""
        # Given two snapshots
        git_service = MagicMock(spec=GitService)
        git_service.stage_files.return_value = True
        freecad_port = MagicMock(spec=FreeCadPort)
        freecad_port.get_all_open_documents.return_value = []
        git_service.get_eligible_docs.return_value = []
        action = StageDocumentsAction(git_service=git_service, freecad_port=freecad_port)
        repo = GitRepository(name="test_repo", absolute_path="/tmp/test_repo")

        snapshot1 = Snapshot(
            snapshot_id="uuid-1",
            document_name="Doc1",
            timestamp=None,  # type: ignore
            objects=[],
            occurrences=[],
            git_path="doc1.FCStd",
        )
        snapshot2 = Snapshot(
            snapshot_id="uuid-2",
            document_name="Doc2",
            timestamp=None,  # type: ignore
            objects=[],
            occurrences=[],
            git_path="subdir/doc2.FCStd",
        )

        # Mock directory creation and YAML serialization
        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer"),
            patch("pathlib.Path.mkdir"),
        ):
            # When execute is called
            result = action.execute(repo, [snapshot1, snapshot2])

            # Then git_service.stage_files is called with all paths
            expected_paths = [
                "doc1.FCStd",
                ".snapshots/doc1.yaml",
                "subdir/doc2.FCStd",
                "subdir/.snapshots/doc2.yaml",
            ]
            git_service.stage_files.assert_called_once_with(repo, expected_paths)
            assert result.is_success is True

    def test_stage_documents_saves_matching_open_document_before_staging(self) -> None:
        """Test that open document is saved before snapshot YAML and git add."""
        git_service = MagicMock(spec=GitService)
        git_service.stage_files.return_value = True
        freecad_port = MagicMock(spec=FreeCadPort)

        mock_doc = MagicMock()
        mock_doc.FileName = "/tmp/test_repo/path/to/mydoc.FCStd"
        freecad_port.get_all_open_documents.return_value = [mock_doc]
        git_service.get_eligible_docs.return_value = [mock_doc]

        action = StageDocumentsAction(git_service=git_service, freecad_port=freecad_port)
        repo = GitRepository(name="test_repo", absolute_path="/tmp/test_repo")
        snapshot = Snapshot(
            snapshot_id="test-uuid-123",
            document_name="MyDocument",
            timestamp=None,  # type: ignore
            objects=[],
            occurrences=[],
            git_path="path/to/mydoc.FCStd",
        )

        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer"),
            patch("pathlib.Path.mkdir"),
        ):
            result = action.execute(repo, [snapshot])

        assert result.is_success is True
        freecad_port.save_document_if_modified.assert_called_once_with(mock_doc)


class TestStageDocumentsActionSuccess:
    """Tests for success scenarios."""

    def test_stage_documents_returns_success_on_success(self) -> None:
        """Test that Result.success is returned when all operations succeed."""
        # Given all operations succeed
        git_service = MagicMock(spec=GitService)
        git_service.stage_files.return_value = True
        freecad_port = MagicMock(spec=FreeCadPort)
        freecad_port.get_all_open_documents.return_value = []
        git_service.get_eligible_docs.return_value = []
        action = StageDocumentsAction(git_service=git_service, freecad_port=freecad_port)
        repo = GitRepository(name="test_repo", absolute_path="/tmp/test_repo")

        snapshot = Snapshot(
            snapshot_id="test-uuid",
            document_name="MyDocument",
            timestamp=None,  # type: ignore
            objects=[],
            occurrences=[],
            git_path="mydoc.FCStd",
        )

        # Mock directory creation and YAML serialization
        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer"),
            patch("pathlib.Path.mkdir"),
        ):
            # When execute is called
            result = action.execute(repo, [snapshot])

            # Then Result.success is returned
            assert result.is_success is True
            assert result.data is True
            assert result.message is None


class TestStageDocumentsActionFailure:
    """Tests for failure scenarios."""

    def test_stage_documents_returns_failure_on_yaml_error(self) -> None:
        """Test that Result.failure is returned when SnapshotYamlSerializer.to_yaml raises."""
        # Given SnapshotYamlSerializer.to_yaml raises
        git_service = MagicMock(spec=GitService)
        freecad_port = MagicMock(spec=FreeCadPort)
        freecad_port.get_all_open_documents.return_value = []
        git_service.get_eligible_docs.return_value = []
        action = StageDocumentsAction(git_service=git_service, freecad_port=freecad_port)
        repo = GitRepository(name="test_repo", absolute_path="/tmp/test_repo")

        snapshot = Snapshot(
            snapshot_id="test-uuid",
            document_name="MyDocument",
            timestamp=None,  # type: ignore
            objects=[],
            occurrences=[],
            git_path="mydoc.FCStd",
        )

        # Mock YAML serialization to raise an exception
        with patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer") as mock_serializer:
            mock_serializer.to_yaml.side_effect = Exception("Serialization failed")
            # When execute is called
            result = action.execute(repo, [snapshot])

            # Then Result.failure is returned
            assert result.is_success is False
            assert result.message is not None
            assert "Failed to persist snapshot" in result.message
            # And git_service.stage_files was never called
            git_service.stage_files.assert_not_called()

    def test_stage_documents_returns_failure_on_save_error(self) -> None:
        """Test that Result.failure is returned when conditional save raises."""
        git_service = MagicMock(spec=GitService)
        freecad_port = MagicMock(spec=FreeCadPort)

        mock_doc = MagicMock()
        mock_doc.FileName = "/tmp/test_repo/mydoc.FCStd"
        freecad_port.get_all_open_documents.return_value = [mock_doc]
        git_service.get_eligible_docs.return_value = [mock_doc]
        freecad_port.save_document_if_modified.side_effect = Exception("save failed")

        action = StageDocumentsAction(git_service=git_service, freecad_port=freecad_port)
        repo = GitRepository(name="test_repo", absolute_path="/tmp/test_repo")
        snapshot = Snapshot(
            snapshot_id="test-uuid",
            document_name="MyDocument",
            timestamp=None,  # type: ignore
            objects=[],
            occurrences=[],
            git_path="mydoc.FCStd",
        )

        result = action.execute(repo, [snapshot])

        assert result.is_success is False
        assert result.message is not None
        assert "Failed to save document before staging" in result.message
        git_service.stage_files.assert_not_called()

    def test_stage_documents_returns_failure_on_directory_creation_error(self) -> None:
        """Test that Result.failure is returned when snapshot directory creation fails."""
        # Given snapshot directory creation fails
        git_service = MagicMock(spec=GitService)
        freecad_port = MagicMock(spec=FreeCadPort)
        freecad_port.get_all_open_documents.return_value = []
        git_service.get_eligible_docs.return_value = []
        action = StageDocumentsAction(git_service=git_service, freecad_port=freecad_port)
        repo = GitRepository(name="test_repo", absolute_path="/tmp/test_repo")

        snapshot = Snapshot(
            snapshot_id="test-uuid",
            document_name="MyDocument",
            timestamp=None,  # type: ignore
            objects=[],
            occurrences=[],
            git_path="mydoc.FCStd",
        )

        # Mock directory creation to raise an OSError
        with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
            # When execute is called
            result = action.execute(repo, [snapshot])

            # Then Result.failure is returned
            assert result.is_success is False
            assert result.message is not None
            assert "Failed to create snapshot directory" in result.message
            # And YAML serialization and git stage were never called
            git_service.stage_files.assert_not_called()

    def test_stage_documents_returns_failure_on_git_stage_error(self) -> None:
        """Test that Result.failure is returned when git staging fails."""
        # Given git staging fails
        git_service = MagicMock(spec=GitService)
        git_service.stage_files.return_value = False
        freecad_port = MagicMock(spec=FreeCadPort)
        freecad_port.get_all_open_documents.return_value = []
        git_service.get_eligible_docs.return_value = []
        action = StageDocumentsAction(git_service=git_service, freecad_port=freecad_port)
        repo = GitRepository(name="test_repo", absolute_path="/tmp/test_repo")

        snapshot = Snapshot(
            snapshot_id="test-uuid",
            document_name="MyDocument",
            timestamp=None,  # type: ignore
            objects=[],
            occurrences=[],
            git_path="mydoc.FCStd",
        )

        # Mock directory creation and YAML serialization
        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer"),
            patch("pathlib.Path.mkdir"),
        ):
            # When execute is called
            result = action.execute(repo, [snapshot])

            # Then Result.failure is returned
            assert result.is_success is False
            assert result.message == "Failed to stage one or more files"

    def test_stage_documents_skips_snapshot_without_git_path(self) -> None:
        """Test that snapshots without git_path are skipped with a warning."""
        # Given a snapshot with no git_path
        git_service = MagicMock(spec=GitService)
        git_service.stage_files.return_value = True
        freecad_port = MagicMock(spec=FreeCadPort)
        freecad_port.get_all_open_documents.return_value = []
        git_service.get_eligible_docs.return_value = []
        action = StageDocumentsAction(git_service=git_service, freecad_port=freecad_port)
        repo = GitRepository(name="test_repo", absolute_path="/tmp/test_repo")

        snapshot = Snapshot(
            snapshot_id="test-uuid",
            document_name="MyDocument",
            timestamp=None,  # type: ignore
            objects=[],
            occurrences=[],
            git_path="",  # Empty git_path
        )

        # Mock directory creation and YAML serialization
        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer"),
            patch("pathlib.Path.mkdir"),
        ):
            # When execute is called
            result = action.execute(repo, [snapshot])

            # Then Result.success is returned (skipped gracefully)
            assert result.is_success is True
            # And git_service.stage_files was never called since we had nothing to stage
            git_service.stage_files.assert_not_called()
