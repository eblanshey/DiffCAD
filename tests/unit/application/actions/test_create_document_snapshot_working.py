# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for CreateDocumentSnapshotForWorkingTreeAction using fake
# FreeCAD and Git service implementations. Tests cover success scenarios, failure when
# document not in git repo, and correct git_path, document_name, and nodes handling.
"""Unit tests for CreateDocumentSnapshotForWorkingTreeAction."""

from unittest.mock import MagicMock, patch

import pytest

from freecad.diff_wb.application.actions.create_document_snapshot_working import (
    CreateDocumentSnapshotForWorkingTreeAction,
)
from freecad.diff_wb.domain.freecad_ports import DocumentObjectLike
from freecad.diff_wb.domain.git.git_service import GitService
from freecad.diff_wb.domain.git.models import GitRepository
from freecad.diff_wb.domain.snapshots.gui_extractor import SnapshotExtractor
from freecad.diff_wb.domain.snapshots.models import Snapshot
from tests.fakes.fake_git_port import FakeGitPort


class MockDocument:
    """Mock document object for testing."""

    FileName: str
    Name: str
    Objects: list[DocumentObjectLike]

    def __init__(self, file_name: str, name: str = "TestDoc") -> None:
        self.FileName = file_name
        self.Name = name
        self.Objects = []

    def getObject(self, name: str) -> DocumentObjectLike | None:
        return None

    def recompute(self) -> None:
        pass


class TestCreateDocumentSnapshotForWorkingTreeActionSuccess:
    """Tests for successful snapshot creation."""

    def test_execute_returns_result_with_snapshot_on_success(self) -> None:
        """Test that action returns Result with Snapshot on success."""
        # Setup
        doc = MockDocument("/home/user/my_project/doc.FCStd", "TestDoc")

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/my_project")

        git_service = GitService(fake_git_port)
        extractor = SnapshotExtractor()

        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")
        action = CreateDocumentSnapshotForWorkingTreeAction(git_service, extractor)

        # Execute - use a mock document directly since we're testing the action logic
        result = action.execute(repo, doc)

        # Assert
        assert result.is_success is True
        assert result.data is not None
        assert isinstance(result.data, Snapshot)
        assert result.message is None

    def test_snapshot_has_correct_git_path_set(self) -> None:
        """Test that Snapshot has correct git_path set."""
        # Setup
        doc = MockDocument("/home/user/my_project/src/file.FCStd", "TestDoc")

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/my_project")

        git_service = GitService(fake_git_port)
        extractor = SnapshotExtractor()

        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")
        action = CreateDocumentSnapshotForWorkingTreeAction(git_service, extractor)

        # Execute
        result = action.execute(repo, doc)

        # Assert
        assert result.is_success is True
        assert result.data is not None
        assert result.data.git_path == "src/file.FCStd"

    def test_snapshot_has_normalized_windows_git_path_set(self) -> None:
        """Test Windows document paths are converted to Git-style relative paths."""
        doc = MockDocument("C:\\repo\\src\\file.FCStd", "TestDoc")

        git_service = MagicMock(spec=GitService)
        git_service.get_eligible_docs.return_value = [doc]
        extractor = SnapshotExtractor()

        repo = GitRepository(name="repo", absolute_path="C:\\repo")
        action = CreateDocumentSnapshotForWorkingTreeAction(git_service, extractor)

        with patch("freecad.diff_wb.domain.git.paths.relpath", lambda path, root: "src\\file.FCStd"):
            result = action.execute(repo, doc)

        assert result.is_success is True
        assert result.data is not None
        assert result.data.git_path == "src/file.FCStd"

    def test_snapshot_has_correct_document_name_and_nodes(self) -> None:
        """Test that Snapshot has correct document_name and nodes."""
        # Setup
        doc = MockDocument("/home/user/my_project/doc.FCStd", "MyDocument")

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/my_project")

        git_service = GitService(fake_git_port)
        extractor = SnapshotExtractor()

        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")
        action = CreateDocumentSnapshotForWorkingTreeAction(git_service, extractor)

        # Execute
        result = action.execute(repo, doc)

        # Assert
        assert result.is_success is True
        assert result.data is not None
        assert result.data.document_name == "MyDocument"
        assert isinstance(result.data.occurrences, list)


class TestCreateDocumentSnapshotForWorkingTreeActionFailure:
    """Tests for failure scenarios."""

    def test_execute_returns_failure_when_document_not_in_git_repo(self) -> None:
        """Test that action returns failure Result when document not in git repo."""
        # Setup - document outside the git repository
        doc = MockDocument("/home/user/other_project/doc.FCStd", "TestDoc")

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/my_project")

        git_service = GitService(fake_git_port)
        extractor = SnapshotExtractor()

        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")
        action = CreateDocumentSnapshotForWorkingTreeAction(git_service, extractor)

        # Execute
        result = action.execute(repo, doc)

        # Assert
        assert result.is_success is False
        assert result.message == "Document is not in the git repository"
        assert result.data is None

    def test_execute_returns_failure_when_document_has_no_file_path(self) -> None:
        """Test that action returns failure when document has no file path (unsaved)."""
        # Setup - unsaved document with empty FileName
        doc = MockDocument("", "UnsavedDoc")

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/my_project")

        git_service = GitService(fake_git_port)
        extractor = SnapshotExtractor()

        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")
        action = CreateDocumentSnapshotForWorkingTreeAction(git_service, extractor)

        # Execute
        result = action.execute(repo, doc)

        # Assert
        assert result.is_success is False
        assert result.message == "Document has no file path (unsaved)"
        assert result.data is None


class TestCreateDocumentSnapshotForWorkingTreeActionGitPath:
    """Tests for git_path calculation."""

    def test_snapshot_git_path_is_relative_to_repo_root(self) -> None:
        """Test that snapshot git_path is relative to repository root."""
        # Setup
        doc = MockDocument("/home/user/project/nested/deep/file.FCStd", "TestDoc")

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/project")

        git_service = GitService(fake_git_port)
        extractor = SnapshotExtractor()

        repo = GitRepository(name="project", absolute_path="/home/user/project")
        action = CreateDocumentSnapshotForWorkingTreeAction(git_service, extractor)

        # Execute
        result = action.execute(repo, doc)

        # Assert
        assert result.is_success is True
        assert result.data is not None
        assert result.data.git_path == "nested/deep/file.FCStd"

    def test_snapshot_git_path_handles_root_level_files(self) -> None:
        """Test that snapshot git_path handles files at repository root."""
        # Setup
        doc = MockDocument("/home/user/project/root.FCStd", "TestDoc")

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/project")

        git_service = GitService(fake_git_port)
        extractor = SnapshotExtractor()

        repo = GitRepository(name="project", absolute_path="/home/user/project")
        action = CreateDocumentSnapshotForWorkingTreeAction(git_service, extractor)

        # Execute
        result = action.execute(repo, doc)

        # Assert
        assert result.is_success is True
        assert result.data is not None
        assert result.data.git_path == "root.FCStd"
