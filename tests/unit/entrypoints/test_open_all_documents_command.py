# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for open-all-repository-documents FreeCAD command entry point.
"""Unit tests for _OpenAllDocumentsInRepositoryCommand."""

from unittest.mock import MagicMock, Mock, patch

from freecad.diff_wb.domain.git.models import GitRepository
from freecad.diff_wb.entrypoints.commands import _OpenAllDocumentsInRepositoryCommand


class TestOpenAllDocumentsInRepositoryCommand:
    """Tests for _OpenAllDocumentsInRepositoryCommand."""

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb.ui.registry.ui_registry")
    @patch("freecad.diff_wb._container.get_container")
    def test_activated_no_repository_shows_warning(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When no repository in UI state, warning popup is shown."""
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda _ctx, text: text
        mock_get_container.return_value = mock_container
        mock_ui_registry.ui_state.git_repository = None

        command = _OpenAllDocumentsInRepositoryCommand()

        command.Activated()

        mock_message_box.warning.assert_called_once()
        call_args = mock_message_box.warning.call_args
        assert call_args[0][2] == ("No project detected. Open a FreeCAD document in a project first.")
        mock_container.open_all_documents_in_repository_action.execute.assert_not_called()

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb.ui.registry.ui_registry")
    @patch("freecad.diff_wb._container.get_container")
    def test_activated_calls_open_action_when_repository_present(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When repository exists in UI state, action is executed."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container

        repo = GitRepository(name="repo", absolute_path="/tmp/repo")
        mock_ui_registry.ui_state.git_repository = repo

        command = _OpenAllDocumentsInRepositoryCommand()

        command.Activated()

        mock_container.open_all_documents_in_repository_action.execute.assert_called_once_with(repo)
        mock_message_box.warning.assert_not_called()
