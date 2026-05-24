# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GetOpenEligibleDocumentsAction using fake
# FreeCAD and Git service implementations. Tests cover success scenarios, empty
# results, and filtering behavior.
"""Unit tests for GetOpenEligibleDocumentsAction."""

from freecad.history_wb.application.actions.get_open_eligible_documents import (
    GetOpenEligibleDocumentsAction,
)
from freecad.history_wb.domain.freecad_ports import DocumentObjectLike
from freecad.history_wb.domain.git.git_service import GitService
from freecad.history_wb.domain.git.models import GitRepository

from tests.fakes.fake_freecad_port import FakeFreeCadPort
from tests.fakes.fake_git_port import FakeGitPort


class MockDocument:
    """Mock document object for testing."""

    FileName: str
    Objects: list[DocumentObjectLike]

    def __init__(self, file_name: str) -> None:
        self.FileName = file_name
        self.Objects = []

    def getObject(self, name: str) -> DocumentObjectLike | None:
        return None

    def recompute(self) -> None:
        pass


class TestGetOpenEligibleDocumentsActionSuccess:
    """Tests for successful document retrieval."""

    def test_execute_returns_result_with_list_of_documents_on_success(self) -> None:
        """Test that action returns Result with list of DocumentLike on success."""
        # Setup
        fake_freecad_port = FakeFreeCadPort(
            open_documents=[
                MockDocument("/home/user/my_project/doc1.FCStd"),
                MockDocument("/home/user/my_project/doc2.FCStd"),
            ]
        )
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/my_project")

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")
        action = GetOpenEligibleDocumentsAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute(repo)

        # Assert
        assert result.is_success is True
        assert result.data is not None
        assert isinstance(result.data, list)
        assert len(result.data) == 2
        assert result.message is None

    def test_execute_returns_documents_with_correct_attributes(self) -> None:
        """Test that returned documents have correct FileName attribute."""
        # Setup
        doc1 = MockDocument("/home/user/project/file1.FCStd")
        doc2 = MockDocument("/home/user/project/subdir/file2.FCStd")
        fake_freecad_port = FakeFreeCadPort(open_documents=[doc1, doc2])

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/project")

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="project", absolute_path="/home/user/project")
        action = GetOpenEligibleDocumentsAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute(repo)

        # Assert
        assert result.is_success is True
        assert result.data[0].FileName == "/home/user/project/file1.FCStd"
        assert result.data[1].FileName == "/home/user/project/subdir/file2.FCStd"


class TestGetOpenEligibleDocumentsActionEmptyResults:
    """Tests for empty result scenarios."""

    def test_execute_returns_empty_list_when_no_documents_open(self) -> None:
        """Test that action returns empty list when no documents are open."""
        # Setup
        fake_freecad_port = FakeFreeCadPort(open_documents=[])

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/project")

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="project", absolute_path="/home/user/project")
        action = GetOpenEligibleDocumentsAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute(repo)

        # Assert
        assert result.is_success is True
        assert result.data == []

    def test_execute_returns_empty_list_when_no_documents_eligible(self) -> None:
        """Test that action returns empty list when no documents are in git repo."""
        # Setup - documents outside the git repository
        fake_freecad_port = FakeFreeCadPort(
            open_documents=[
                MockDocument("/home/user/other_project/doc.FCStd"),
                MockDocument("/tmp/doc.FCStd"),
            ]
        )

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/my_project")

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")
        action = GetOpenEligibleDocumentsAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute(repo)

        # Assert - still success but with empty list
        assert result.is_success is True
        assert result.data == []

    def test_execute_returns_success_with_empty_list_for_new_repo_no_commits(self) -> None:
        """Test that action returns success with empty list for new repository."""
        # Setup
        fake_freecad_port = FakeFreeCadPort(open_documents=[])

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/new_project")

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="new_project", absolute_path="/home/user/new_project")
        action = GetOpenEligibleDocumentsAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute(repo)

        # Assert
        assert result.is_success is True
        assert isinstance(result.data, list)
        assert len(result.data) == 0


class TestGetOpenEligibleDocumentsActionFiltering:
    """Tests for document filtering behavior."""

    def test_execute_filters_correctly_using_git_service(self) -> None:
        """Test that action filters correctly using GitService.get_eligible_docs()."""
        # Setup - mix of documents inside and outside git repo
        fake_freecad_port = FakeFreeCadPort(
            open_documents=[
                MockDocument("/home/user/my_project/in_repo.FCStd"),  # In repo
                MockDocument("/home/user/other_project/outside.FCStd"),  # Outside
                MockDocument("/home/user/my_project/subdir/nested.FCStd"),  # In repo
                MockDocument("/tmp/temp.FCStd"),  # Outside
            ]
        )

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/my_project")

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")
        action = GetOpenEligibleDocumentsAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute(repo)

        # Assert - should only return documents within git repo
        assert result.is_success is True
        assert len(result.data) == 2
        filenames = [doc.FileName for doc in result.data]
        assert "/home/user/my_project/in_repo.FCStd" in filenames
        assert "/home/user/my_project/subdir/nested.FCStd" in filenames

    def test_execute_filters_documents_outside_git_repo(self) -> None:
        """Test that documents outside git repo are filtered out."""
        # Setup
        fake_freecad_port = FakeFreeCadPort(
            open_documents=[
                MockDocument("/home/user/project/doc.FCStd"),
                MockDocument("/home/user/other/doc.FCStd"),
            ]
        )

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/project")

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="project", absolute_path="/home/user/project")
        action = GetOpenEligibleDocumentsAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute(repo)

        # Assert - should only return the one in the project
        assert result.is_success is True
        assert len(result.data) == 1
        assert result.data[0].FileName == "/home/user/project/doc.FCStd"

    def test_execute_includes_all_documents_when_all_in_repo(self) -> None:
        """Test that all documents are included when all are in git repo."""
        # Setup
        fake_freecad_port = FakeFreeCadPort(
            open_documents=[
                MockDocument("/home/user/project/root.FCStd"),
                MockDocument("/home/user/project/dir1/file.FCStd"),
                MockDocument("/home/user/project/dir2/deep/file.FCStd"),
            ]
        )

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/project")

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="project", absolute_path="/home/user/project")
        action = GetOpenEligibleDocumentsAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute(repo)

        # Assert - should return all documents
        assert result.is_success is True
        assert len(result.data) == 3


class TestGetOpenEligibleDocumentsActionFileNameHandling:
    """Tests for handling documents with empty or missing FileName attribute."""

    def test_execute_excludes_documents_without_file_name(self) -> None:
        """Test that documents without FileName (unsaved) are excluded from eligible documents."""
        # Setup - mix of documents with and without FileName
        unsaved_doc = MockDocument("")  # Empty FileName simulates unsaved document
        saved_doc = MockDocument("/home/user/my_project/saved.FCStd")

        fake_freecad_port = FakeFreeCadPort(open_documents=[unsaved_doc, saved_doc])

        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/my_project")

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")
        action = GetOpenEligibleDocumentsAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute(repo)

        # Assert - should only return the saved document
        assert result.is_success is True
        assert len(result.data) == 1
        assert result.data[0].FileName == "/home/user/my_project/saved.FCStd"
