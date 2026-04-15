# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Integration tests for the FindActiveGitRepositoryAction.
# These tests verify that the action correctly detects git repositories using
# the actual FreeCAD runtime and git CLI.
"""Integration tests for FindActiveGitRepositoryAction."""

from pathlib import Path

from freecad.diff_wb.domain.freecad_ports import FreeCadContext
from freecad.diff_wb.domain.git.git_service import GitService
from freecad.diff_wb.infrastructure.freecad.ports import get_port
from freecad.diff_wb.infrastructure.git.git_port_adapter import GitPortAdapter


class TestFindActiveGitRepositoryAction:
    """Integration tests for git repository detection action."""

    def test_execute_returns_repository_for_saved_document_in_git_repo(
        self,
        project_root: Path,
        freecad_app,
    ):
        """Test that action returns a valid GitRepository for a saved document.

        This test:
        1. Opens a test document that is saved within the project's git repository
        2. Executes the FindActiveGitRepositoryAction
        3. Verifies the result contains a valid GitRepository with correct name and path
        """
        from freecad.diff_wb.application.actions.find_active_git_repository import (
            FindActiveGitRepositoryAction,
        )

        # Wire up dependencies directly - no container needed
        ctx = FreeCadContext(app=freecad_app)
        port = get_port(ctx)
        git_service = GitService(git_port=GitPortAdapter())

        action = FindActiveGitRepositoryAction(
            freecad_port=port,
            git_service=git_service,
        )

        # Open the test document (it's in the project root which is a git repo)
        test_doc_path = project_root / "tests" / "freecad" / "BasicFile.FCStd"
        doc = freecad_app.openDocument(str(test_doc_path))

        # Execute the action
        result = action.execute()

        # Verify success
        assert result.is_success, f"Expected success, got failure: {result.message}"

        # Verify we got a GitRepository
        repo = result.data
        assert repo is not None

        # Verify repository properties
        assert repo.name == "freecad_diff_workbench", f"Unexpected repo name: {repo.name}"
        assert repo.absolute_path == str(project_root), f"Unexpected repo path: {repo.absolute_path}"

        # Clean up
        freecad_app.closeDocument(doc.Name)

    def test_execute_returns_failure_for_unsaved_document(
        self,
        freecad_app,
    ):
        """Test that action returns failure when document is not saved."""
        from freecad.diff_wb.application.actions.find_active_git_repository import (
            FindActiveGitRepositoryAction,
        )

        # Wire up dependencies directly - no container needed
        ctx = FreeCadContext(app=freecad_app)
        port = get_port(ctx)
        git_service = GitService(git_port=GitPortAdapter())

        action = FindActiveGitRepositoryAction(
            freecad_port=port,
            git_service=git_service,
        )

        # Create a new unsaved document
        doc = freecad_app.newDocument("UnsavedTestDoc")

        # Execute the action
        result = action.execute()

        # Verify failure - unsaved documents have empty FileName
        assert not result.is_success
        assert "not saved" in result.message.lower() or "no file path" in result.message.lower()

        # Clean up
        freecad_app.closeDocument(doc.Name)

    def test_execute_returns_failure_when_no_active_document(
        self,
        freecad_app,
        freecad_gui,
    ):
        """Test that action returns failure when no document is active."""
        from freecad.diff_wb.application.actions.find_active_git_repository import (
            FindActiveGitRepositoryAction,
        )

        # Wire up dependencies directly - no container needed
        ctx = FreeCadContext(app=freecad_app)
        port = get_port(ctx)
        git_service = GitService(git_port=GitPortAdapter())

        action = FindActiveGitRepositoryAction(
            freecad_port=port,
            git_service=git_service,
        )

        # Close all documents to ensure no active document
        # Use Gui.documentManager() if available, otherwise try App approach
        if freecad_gui is not None:
            try:
                doc_manager = freecad_gui.documentManager()
                for doc_name in [d.Name for d in doc_manager.documents()]:
                    freecad_app.closeDocument(doc_name)
            except (AttributeError, TypeError):
                # Fallback: try to close via ActiveDocument
                pass

        # Execute the action
        result = action.execute()

        # Verify failure
        assert not result.is_success
        assert "no active document" in result.message.lower()
