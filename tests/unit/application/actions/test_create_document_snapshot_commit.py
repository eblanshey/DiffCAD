# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for CreateDocumentSnapshotForCommitAction application action.
"""Unit tests for CreateDocumentSnapshotForCommitAction."""

from unittest.mock import MagicMock

from freecad.diff_wb.application.actions.create_document_snapshot_commit import (
    CreateDocumentSnapshotForCommitAction,
)
from freecad.diff_wb.domain.git.git_service import GitService
from freecad.diff_wb.domain.git.models import GitRepository
from freecad.diff_wb.domain.snapshots import Snapshot


class TestCreateDocumentSnapshotForCommitAction:
    """Tests for CreateDocumentSnapshotForCommitAction class."""

    def test_execute_with_commit_none_returns_index_snapshot(self) -> None:
        """Test: Execute with commit=None returns snapshot from index."""
        # Given a GitService that returns YAML content from index
        mock_git_service = MagicMock(spec=GitService)
        yaml_content = """v: 1
timestamp: 2024-01-15T10:30:00+00:00
uid: test-uuid-index
objects:
- id: 1
  name: Body
  type_id: PartDesign::Body
  label: Body
  path: Body
  after: null
  properties: {}
"""
        mock_git_service.get_file_contents.return_value = yaml_content

        action = CreateDocumentSnapshotForCommitAction(git_service=mock_git_service)
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called with commit=None and fcstd_git_path
        result = action.execute(repo, None, "path/to/doc.FCStd")

        # Then the snapshot is created from the index content
        assert result.is_success is True
        assert result.data is not None
        assert isinstance(result.data, Snapshot)
        assert result.data.snapshot_id == "test-uuid-index"
        assert len(result.data.nodes) == 1
        assert result.data.git_path == "path/to/doc.FCStd"
        assert result.data.document_name == "doc.FCStd"

    def test_execute_with_commit_hash_returns_commit_snapshot(self) -> None:
        """Test: Execute with commit hash returns snapshot from that commit."""
        # Given a GitService that returns YAML content from HEAD
        mock_git_service = MagicMock(spec=GitService)
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

        action = CreateDocumentSnapshotForCommitAction(git_service=mock_git_service)
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called with commit="HEAD"
        result = action.execute(repo, "HEAD", "path/to/doc.FCStd")

        # Then the snapshot is created from that commit's content
        assert result.is_success is True
        assert result.data is not None
        assert result.data.snapshot_id == "test-uuid-commit"
        assert result.data.git_path == "path/to/doc.FCStd"
        assert result.data.document_name == "doc.FCStd"

    def test_execute_with_nested_path_preserves_git_path_and_filename(self) -> None:
        """Test: Nested git paths are preserved while document name uses filename."""
        # Given a GitService that returns YAML content
        mock_git_service = MagicMock(spec=GitService)
        yaml_content = """v: 1
timestamp: 2024-02-20T14:00:00+00:00
uid: test-uuid-nested
objects: []
"""
        mock_git_service.get_file_contents.return_value = yaml_content

        action = CreateDocumentSnapshotForCommitAction(git_service=mock_git_service)
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called with a nested path
        result = action.execute(repo, "HEAD", "assemblies/sub/Widget.FCStd")

        # Then full git_path is preserved and document_name is filename
        assert result.is_success is True
        assert result.data is not None
        assert result.data.git_path == "assemblies/sub/Widget.FCStd"
        assert result.data.document_name == "Widget.FCStd"

    def test_execute_returns_none_when_no_content(self) -> None:
        """Test: Execute returns None when file doesn't exist in git."""
        # Given a GitService that returns None
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.get_file_contents.return_value = None

        action = CreateDocumentSnapshotForCommitAction(git_service=mock_git_service)
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called
        result = action.execute(repo, None, "path/to/nonexistent.FCStd")

        # Then Result.success(None) is returned
        assert result.is_success is True
        assert result.data is None

    def test_execute_returns_failure_on_deserialization_error(self) -> None:
        """Test: Execute returns failure when YAML deserialization fails."""
        # Given a GitService that returns invalid YAML
        mock_git_service = MagicMock(spec=GitService)
        mock_git_service.get_file_contents.return_value = "invalid: yaml: content: ["

        action = CreateDocumentSnapshotForCommitAction(git_service=mock_git_service)
        repo = GitRepository(name="test-repo", absolute_path="/path/to/repo")

        # When execute is called
        result = action.execute(repo, None, "path/to/doc.FCStd")

        # Then Result.failure is returned
        assert result.is_success is False
        assert "Failed to deserialize snapshot" in result.message
