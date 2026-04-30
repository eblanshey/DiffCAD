# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for FindActiveGitRepositoryAction using fake
# implementations of FreeCadPort and GitService. Tests cover all success and failure
# scenarios including no document, unsaved document, and no git repository found.
"""Unit tests for FindActiveGitRepositoryAction."""

import os
from unittest.mock import MagicMock

from freecad.diff_wb.application.actions.find_active_git_repository import (
    FindActiveGitRepositoryAction,
)
from freecad.diff_wb.application.actions.result_models import Result
from freecad.diff_wb.domain.git.git_service import GitService
from freecad.diff_wb.domain.git.models import GitRepository
from tests.fakes.fake_freecad_port import FakeFreeCadPort
from tests.fakes.fake_git_port import FakeGitPort


class TestFindActiveGitRepositoryActionSuccess:
    """Tests for successful git repository detection."""

    def test_execute_returns_repository_when_document_in_git_repo(self) -> None:
        """Test that action returns repository when document is in a git repo."""
        # Setup
        fake_freecad_port = FakeFreeCadPort()
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/my_project")

        # Create a mock document with FileName
        mock_doc = MagicMock()
        mock_doc.FileName = "/home/user/my_project/src/file.FCStd"
        fake_freecad_port._open_documents = [mock_doc]

        git_service = GitService(fake_git_port)
        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute()

        # Assert
        assert result.is_success is True
        assert result.data is not None
        assert isinstance(result.data, GitRepository)
        assert result.data.name == "my_project"
        assert result.data.absolute_path == "/home/user/my_project"
        assert result.message is None

    def test_execute_returns_repository_for_nested_path(self) -> None:
        """Test that action works with deeply nested file paths."""
        # Setup
        fake_freecad_port = FakeFreeCadPort()
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/workbench")

        mock_doc = MagicMock()
        mock_doc.FileName = "/home/user/workbench/freecad/diff_wb/application/actions/file.FCStd"
        fake_freecad_port._open_documents = [mock_doc]

        git_service = GitService(fake_git_port)
        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute()

        # Assert
        assert result.is_success is True
        assert result.data.name == "workbench"
        assert result.data.absolute_path == "/home/user/workbench"

    def test_execute_returns_repository_with_special_chars_in_name(self) -> None:
        """Test that action handles repository names with special characters."""
        # Setup
        fake_freecad_port = FakeFreeCadPort()
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/my-project_v2.0")

        mock_doc = MagicMock()
        mock_doc.FileName = "/home/user/my-project_v2.0/src/main.FCStd"
        fake_freecad_port._open_documents = [mock_doc]

        git_service = GitService(fake_git_port)
        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute()

        # Assert
        assert result.is_success is True
        assert result.data.name == "my-project_v2.0"
        assert result.data.absolute_path == "/home/user/my-project_v2.0"


class TestFindActiveGitRepositoryActionFailureNoDocument:
    """Tests for failure when no documents are open."""

    def test_execute_fails_when_no_documents_open(self) -> None:
        """Test that action fails when FreeCAD has no open documents."""
        # Setup
        fake_freecad_port = FakeFreeCadPort(open_documents=[])
        fake_git_port = FakeGitPort()
        git_service = GitService(fake_git_port)
        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute()

        # Assert
        assert result.is_success is False
        assert result.data is None
        assert result.message == "No documents are open"

    def test_execute_returns_failure_result_object(self) -> None:
        """Test that failure returns proper Result object structure."""
        fake_freecad_port = FakeFreeCadPort(open_documents=[])
        fake_git_port = FakeGitPort()
        git_service = GitService(fake_git_port)
        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        result = action.execute()

        assert isinstance(result, Result)
        assert result.is_success is False
        assert result.data is None
        assert result.message is not None


class TestFindActiveGitRepositoryActionUnsavedDocumentHandling:
    """Tests for handling unsaved documents (they should be skipped)."""

    def test_execute_skips_unsaved_document_and_finds_saved_one(self) -> None:
        """Test that action skips unsaved documents and finds a saved one."""
        # Setup
        fake_freecad_port = FakeFreeCadPort()
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/saved_project")

        # Create unsaved document (empty FileName)
        unsaved_doc = MagicMock()
        unsaved_doc.FileName = ""

        # Create saved document in git repo
        saved_doc = MagicMock()
        saved_doc.FileName = "/home/user/saved_project/file.FCStd"

        # Both documents open, but only saved one should be checked
        fake_freecad_port._open_documents = [unsaved_doc, saved_doc]

        git_service = GitService(fake_git_port)
        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute()

        # Assert - should succeed by finding the saved document
        assert result.is_success is True
        assert result.data.name == "saved_project"
        assert result.data.absolute_path == "/home/user/saved_project"

    def test_execute_skips_all_unsaved_documents_then_fails(self) -> None:
        """Test that action fails when all documents are unsaved."""
        # Setup
        fake_freecad_port = FakeFreeCadPort()
        fake_git_port = FakeGitPort()

        # All documents are unsaved
        unsaved_doc1 = MagicMock()
        unsaved_doc1.FileName = ""
        unsaved_doc2 = MagicMock()
        unsaved_doc2.FileName = ""
        fake_freecad_port._open_documents = [unsaved_doc1, unsaved_doc2]

        git_service = GitService(fake_git_port)
        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute()

        # Assert - should fail after skipping all unsaved docs
        assert result.is_success is False
        assert result.message == "No git repository found for open documents"


class TestFindActiveGitRepositoryActionFailureNoGitRepo:
    """Tests for failure when document is not in a git repository."""

    def test_execute_fails_when_path_not_in_git_repo(self) -> None:
        """Test that action fails when document path is not in any git repo."""
        # Setup
        fake_freecad_port = FakeFreeCadPort()
        fake_git_port = FakeGitPort()
        # Don't add any git repos - simulate no git repository

        mock_doc = MagicMock()
        mock_doc.FileName = "/tmp/unsaved_project/file.FCStd"
        fake_freecad_port._open_documents = [mock_doc]

        git_service = GitService(fake_git_port)
        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        # Execute
        result = action.execute()

        # Assert
        assert result.is_success is False
        assert result.data is None
        assert result.message == "No git repository found for open documents"

    def test_execute_fails_for_temp_directory_path(self) -> None:
        """Test that action fails for paths in typical temp directories."""
        fake_freecad_port = FakeFreeCadPort()
        fake_git_port = FakeGitPort()

        mock_doc = MagicMock()
        mock_doc.FileName = "/tmp/random_file.FCStd"
        fake_freecad_port._open_documents = [mock_doc]

        git_service = GitService(fake_git_port)
        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        result = action.execute()

        assert result.is_success is False
        assert result.message == "No git repository found for open documents"


class TestFindActiveGitRepositoryActionDependencies:
    """Tests for action dependency injection and initialization."""

    def test_action_accepts_freecad_port_dependency(self) -> None:
        """Test that action can be initialized with FreeCadPort."""
        fake_freecad_port = FakeFreeCadPort(open_documents=[])
        fake_git_port = FakeGitPort()
        git_service = GitService(fake_git_port)

        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        assert action._freecad_port is fake_freecad_port

    def test_action_accepts_git_service_dependency(self) -> None:
        """Test that action can be initialized with GitService."""
        fake_freecad_port = FakeFreeCadPort(open_documents=[])
        fake_git_port = FakeGitPort()
        git_service = GitService(fake_git_port)

        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        assert action._git_service is git_service

    def test_action_dependencies_are_stored_correctly(self) -> None:
        """Test that both dependencies are stored and accessible."""
        fake_freecad_port = FakeFreeCadPort(open_documents=[])
        fake_git_port = FakeGitPort()
        git_service = GitService(fake_git_port)

        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        assert action._freecad_port is fake_freecad_port
        assert action._git_service is git_service


class TestFindActiveGitRepositoryActionWorkflow:
    """Integration-style tests for complete workflows."""

    def test_workflow_detects_repo_at_project_root(self) -> None:
        """Test workflow when document is at project root level."""
        fake_freecad_port = FakeFreeCadPort()
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/project")

        mock_doc = MagicMock()
        mock_doc.FileName = "/home/user/project/main.FCStd"
        fake_freecad_port._open_documents = [mock_doc]

        git_service = GitService(fake_git_port)
        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        result = action.execute()

        assert result.is_success is True
        assert result.data.name == "project"
        assert result.data.absolute_path == "/home/user/project"

    def test_workflow_finds_first_valid_repo_from_multiple_documents(self) -> None:
        """Test workflow with multiple documents - finds first one in a git repo."""
        fake_freecad_port = FakeFreeCadPort()
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/repo_a")
        fake_git_port.add_git_repo("/home/user/repo_b")

        # Multiple documents from different repos
        doc_from_repo_a = MagicMock()
        doc_from_repo_a.FileName = "/home/user/repo_a/file.FCStd"

        doc_from_repo_b = MagicMock()
        doc_from_repo_b.FileName = "/home/user/repo_b/other.FCStd"

        fake_freecad_port._open_documents = [doc_from_repo_a, doc_from_repo_b]

        git_service = GitService(fake_git_port)
        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        result = action.execute()

        # Should find the first document's repo (repo_a)
        assert result.is_success is True
        assert result.data.name == "repo_a"

    def test_workflow_with_windows_style_path(self) -> None:
        """Test workflow with Windows-style path (if on Windows)."""
        # Note: This test demonstrates the action handles paths correctly
        # The actual behavior depends on the OS and path format
        if os.sep == "\\":
            fake_freecad_port = FakeFreeCadPort()
            fake_git_port = FakeGitPort()
            fake_git_port.add_git_repo("C:/Users/Project")

            mock_doc = MagicMock()
            mock_doc.FileName = "C:/Users/Project/src/file.FCStd"
            fake_freecad_port._open_documents = [mock_doc]

            git_service = GitService(fake_git_port)
            action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

            result = action.execute()

            assert result.is_success is True


class TestFindActiveGitRepositoryActionEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_execute_with_document_filename_as_dot(self) -> None:
        """Test edge case where FileName is just '.'."""
        fake_freecad_port = FakeFreeCadPort()
        fake_git_port = FakeGitPort()

        mock_doc = MagicMock()
        mock_doc.FileName = "."
        fake_freecad_port._open_documents = [mock_doc]

        git_service = GitService(fake_git_port)
        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        result = action.execute()

        # Should fail since current dir is not in a configured git repo
        assert result.is_success is False

    def test_execute_preserves_path_case_sensitivity(self) -> None:
        """Test that path matching respects case sensitivity."""
        fake_freecad_port = FakeFreeCadPort()
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/MyProject")

        mock_doc = MagicMock()
        mock_doc.FileName = "/home/user/MyProject/file.FCStd"
        fake_freecad_port._open_documents = [mock_doc]

        git_service = GitService(fake_git_port)
        action = FindActiveGitRepositoryAction(fake_freecad_port, git_service)

        result = action.execute()

        assert result.is_success is True
        assert result.data.name == "MyProject"
