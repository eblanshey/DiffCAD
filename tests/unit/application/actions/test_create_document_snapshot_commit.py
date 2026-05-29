# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for CreateDocumentSnapshotForCommitAction application action.
"""Unit tests for CreateDocumentSnapshotForCommitAction."""

from datetime import datetime
from unittest.mock import MagicMock

from freecad.history_wb.application.actions.create_document_snapshot_commit import (
    CreateDocumentSnapshotForCommitAction,
)
from freecad.history_wb.application.actions.result_models import SnapshotLoadStatus
from freecad.history_wb.domain.git.git_service import GitService
from freecad.history_wb.domain.git.models import GitRepository
from freecad.history_wb.domain.snapshots.models import Snapshot


def _snapshot(snapshot_id: str) -> Snapshot:
    return Snapshot(
        snapshot_id=snapshot_id,
        document_name="placeholder.FCStd",
        timestamp=datetime.now(),
        objects=[],
        occurrences=[],
    )


class TestCreateDocumentSnapshotForCommitAction:
    """Tests for CreateDocumentSnapshotForCommitAction class."""

    def test_execute_with_commit_none_returns_index_snapshot(self) -> None:
        """Test: Execute with commit=None returns snapshot from index."""
        # Given a GitService that returns YAML content from index
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.file_exists.return_value = True
        yaml_content = """v: 2
timestamp: 2024-01-15T10:30:00+00:00
uid: test-uuid-index
objects:
- id: 1
  name: Body
  type_id: PartDesign::Body
  properties: {}
occurrences:
- path: Body
  object: Body
  after: null
"""
        mock_git_service.get_file_contents.return_value = yaml_content
        mock_deserializer = MagicMock()
        mock_deserializer.from_yaml.return_value = _snapshot("test-uuid-index")

        action = CreateDocumentSnapshotForCommitAction(
            git_service=mock_git_service,
            snapshot_deserializer=mock_deserializer,
        )
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called with commit=None and fcstd_git_path
        result = action.execute(repo, None, "path/to/doc.FCStd")

        # Then the snapshot is created from the index content
        assert result.is_success is True
        assert result.data is not None
        assert result.data.status == SnapshotLoadStatus.FOUND
        assert result.data.snapshot is not None
        assert result.data.snapshot.snapshot_id == "test-uuid-index"
        assert result.data.snapshot.git_path == "path/to/doc.FCStd"
        assert result.data.snapshot.document_name == "doc.FCStd"
        mock_deserializer.from_yaml.assert_called_once_with(yaml_content)

    def test_execute_with_commit_hash_returns_commit_snapshot(self) -> None:
        """Test: Execute with commit hash returns snapshot from that commit."""
        # Given a GitService that returns YAML content from HEAD
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.file_exists.return_value = True
        yaml_content = """v: 1
timestamp: 2024-02-20T14:00:00+00:00
uid: test-uuid-commit
objects:
- id: 2
  name: Sketch
  type_id: Sketcher::SketchObject
  label: Sketch
  path: Body/Sketch
  after: Body
  properties: {}
"""
        mock_git_service.get_file_contents.return_value = yaml_content
        mock_deserializer = MagicMock()
        mock_deserializer.from_yaml.return_value = _snapshot("test-uuid-commit")

        action = CreateDocumentSnapshotForCommitAction(
            git_service=mock_git_service,
            snapshot_deserializer=mock_deserializer,
        )
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called with commit="HEAD"
        result = action.execute(repo, "HEAD", "path/to/doc.FCStd")

        # Then the snapshot is created from that commit's content
        assert result.is_success is True
        assert result.data is not None
        assert result.data.status == SnapshotLoadStatus.FOUND
        assert result.data.snapshot is not None
        assert result.data.snapshot.snapshot_id == "test-uuid-commit"
        assert result.data.snapshot.git_path == "path/to/doc.FCStd"
        assert result.data.snapshot.document_name == "doc.FCStd"

    def test_execute_with_nested_path_preserves_git_path_and_filename(self) -> None:
        """Test: Nested git paths are preserved while document name uses filename."""
        # Given a GitService that returns YAML content
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.file_exists.return_value = True
        yaml_content = """v: 1
timestamp: 2024-02-20T14:00:00+00:00
uid: test-uuid-nested
objects: []
"""
        mock_git_service.get_file_contents.return_value = yaml_content
        mock_deserializer = MagicMock()
        mock_deserializer.from_yaml.return_value = _snapshot("test-uuid-nested")

        action = CreateDocumentSnapshotForCommitAction(
            git_service=mock_git_service,
            snapshot_deserializer=mock_deserializer,
        )
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called with a nested path
        result = action.execute(repo, "HEAD", "assemblies/sub/Widget.FCStd")

        # Then full git_path is preserved and document_name is filename
        assert result.is_success is True
        assert result.data is not None
        assert result.data.status == SnapshotLoadStatus.FOUND
        assert result.data.snapshot is not None
        assert result.data.snapshot.git_path == "assemblies/sub/Widget.FCStd"
        assert result.data.snapshot.document_name == "Widget.FCStd"

    def test_execute_normalizes_windows_snapshot_path_for_git_lookup(self) -> None:
        """Test: Windows separators are normalized before git snapshot lookup."""
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.file_exists.return_value = True
        yaml_content = """v: 1
timestamp: 2024-02-20T14:00:00+00:00
uid: test-uuid-windows
objects: []
"""
        mock_git_service.get_file_contents.return_value = yaml_content
        mock_deserializer = MagicMock()
        mock_deserializer.from_yaml.return_value = _snapshot("test-uuid-windows")

        action = CreateDocumentSnapshotForCommitAction(
            git_service=mock_git_service,
            snapshot_deserializer=mock_deserializer,
        )
        repo = GitRepository(name="test-repo", absolute_path="C:/repo")

        result = action.execute(repo, "HEAD", "assemblies\\sub\\Widget.FCStd")

        assert result.is_success is True
        assert result.data is not None
        assert result.data.status == SnapshotLoadStatus.FOUND
        mock_git_service.get_file_contents.assert_called_once_with(
            repo,
            "HEAD",
            "assemblies/sub/.snapshots/Widget.yaml",
        )

    def test_yaml_missing_and_fcstd_missing_returns_document_missing(self) -> None:
        """Test: Missing YAML + missing FCStd returns DOCUMENT_MISSING."""
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.get_file_contents.return_value = None
        mock_git_service.file_exists.return_value = False

        action = CreateDocumentSnapshotForCommitAction(
            git_service=mock_git_service,
            snapshot_deserializer=MagicMock(),
        )
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        result = action.execute(repo, None, "path/to/nonexistent.FCStd")

        assert result.is_success is True
        assert result.data is not None
        assert result.data.snapshot is None
        assert result.data.status == SnapshotLoadStatus.DOCUMENT_MISSING
        mock_git_service.file_exists.assert_called_once_with(repo, None, "path/to/nonexistent.FCStd")

    def test_fcstd_missing_and_yaml_present_returns_document_missing_without_deserialization(self) -> None:
        """Test: FCStd missing returns DOCUMENT_MISSING even if YAML exists."""
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.file_exists.return_value = False
        mock_git_service.get_file_contents.return_value = "v: 2\nobjects: []\n"
        mock_deserializer = MagicMock()

        action = CreateDocumentSnapshotForCommitAction(
            git_service=mock_git_service,
            snapshot_deserializer=mock_deserializer,
        )
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        result = action.execute(repo, "HEAD", "path/to/deleted.FCStd")

        assert result.is_success is True
        assert result.data is not None
        assert result.data.snapshot is None
        assert result.data.status == SnapshotLoadStatus.DOCUMENT_MISSING
        mock_deserializer.from_yaml.assert_not_called()

    def test_yaml_missing_and_fcstd_exists_returns_snapshot_missing(self) -> None:
        """Test: Missing YAML + existing FCStd returns SNAPSHOT_MISSING."""
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.get_file_contents.return_value = None
        mock_git_service.file_exists.return_value = True

        action = CreateDocumentSnapshotForCommitAction(
            git_service=mock_git_service,
            snapshot_deserializer=MagicMock(),
        )
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        result = action.execute(repo, None, "path/to/doc.FCStd")

        assert result.is_success is True
        assert result.data is not None
        assert result.data.snapshot is None
        assert result.data.status == SnapshotLoadStatus.SNAPSHOT_MISSING
        mock_git_service.file_exists.assert_called_once_with(repo, None, "path/to/doc.FCStd")

    def test_yaml_invalid_returns_invalid_snapshot_status(self) -> None:
        """Test: Invalid YAML returns INVALID_SNAPSHOT success result."""
        # Given a GitService that returns invalid YAML
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.file_exists.return_value = True
        mock_git_service.get_file_contents.return_value = "invalid: yaml: content: ["
        mock_deserializer = MagicMock()
        mock_deserializer.from_yaml.side_effect = ValueError("invalid yaml")

        action = CreateDocumentSnapshotForCommitAction(
            git_service=mock_git_service,
            snapshot_deserializer=mock_deserializer,
        )
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called
        result = action.execute(repo, None, "path/to/doc.FCStd")

        # Then typed load result is returned with INVALID_SNAPSHOT
        assert result.is_success is True
        assert result.data is not None
        assert result.data.snapshot is None
        assert result.data.status == SnapshotLoadStatus.INVALID_SNAPSHOT
