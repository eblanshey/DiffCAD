# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Tests for FreeCAD command entry points.

These tests verify that commands correctly delegate to actions and presenters.
Focused command files (test_commit_command.py, test_open_all_documents_command.py)
own Commit and OpenAll routing behavior; this file covers commands without dedicated
test files.
"""

from unittest.mock import MagicMock, Mock, patch

from freecad.history_wb.entrypoints.commands import (
    _RecomputeAllOpenDocumentsCommand,
    _RefreshRepositoryCommand,
    _UpdateGitIgnoreCommand,
)
from freecad.history_wb.domain.git.models import GitRepository


class TestRefreshRepositoryCommand:
    """Tests for _RefreshRepositoryCommand."""

    @patch("freecad.history_wb.ui.registry.ui_registry")
    def test_refresh_repository_command_calls_git_repository_presenter(
        self,
        mock_ui_registry: Mock,
    ) -> None:
        """Activated delegates to GitRepositoryPresenter refresh API."""
        mock_presenter = MagicMock()
        mock_ui_registry.git_repository_presenter = mock_presenter

        command = _RefreshRepositoryCommand()

        command.Activated()

        mock_presenter.refresh_repository_and_commits.assert_called_once_with()


class TestRecomputeAllOpenDocumentsCommand:
    """Tests for _RecomputeAllOpenDocumentsCommand."""

    @patch("freecad.history_wb._container.get_container")
    def test_activated_calls_application_action(self, mock_get_container: Mock) -> None:
        """Activated delegates to application action execute API."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container

        command = _RecomputeAllOpenDocumentsCommand()

        command.Activated()

        mock_container.recompute_all_open_documents_action.execute.assert_called_once_with()


class TestRecomputeActiveDocumentCommand:
    """Tests for _RecomputeActiveDocumentCommand."""


class TestOpenDiffWindowCommand:
    """Tests for _OpenDiffWindowCommand."""


class TestUpdateGitIgnoreCommand:
    """Tests for _UpdateGitIgnoreCommand."""

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
    def test_activated_with_no_repository_shows_warning(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """Activated shows warning when no project is detected."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_ui_registry.ui_state.git_repository = None

        command = _UpdateGitIgnoreCommand()

        command.Activated()

        mock_message_box.warning.assert_called_once()
        mock_container.get_gitignore_content_action.execute.assert_not_called()

    @patch("freecad.history_wb.entrypoints.commands.QtWidgets")
    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
    def test_activated_saves_dialog_content_when_user_confirms(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_qt_widgets: Mock,
    ) -> None:
        """Activated persists text edit content when dialog accepted."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        repo = GitRepository(name="repo", absolute_path="/home/user/repo")
        mock_ui_registry.ui_state.git_repository = repo
        mock_container.get_gitignore_content_action.execute.return_value = MagicMock(
            is_success=True,
            data="*.FCBak\n",
        )
        mock_container.update_gitignore_action.execute.return_value = MagicMock(is_success=True)

        dialog_instance = MagicMock()
        dialog_instance.exec.return_value = 1
        mock_qt_widgets.QDialog.return_value = dialog_instance
        mock_qt_widgets.QVBoxLayout.return_value = MagicMock()
        mock_qt_widgets.QLabel.return_value = MagicMock()
        text_edit = MagicMock()
        text_edit.toPlainText.return_value = "*.FCBak\n"
        mock_qt_widgets.QPlainTextEdit.return_value = text_edit

        button_box = MagicMock()
        save_button = MagicMock()
        cancel_button = MagicMock()
        button_box.addButton.side_effect = [save_button, cancel_button]
        mock_qt_widgets.QDialogButtonBox.return_value = button_box
        mock_qt_widgets.QDialogButtonBox.ButtonRole.AcceptRole = 0
        mock_qt_widgets.QDialogButtonBox.ButtonRole.RejectRole = 1

        command = _UpdateGitIgnoreCommand()

        command.Activated()

        mock_container.update_gitignore_action.execute.assert_called_once()
        call_args = mock_container.update_gitignore_action.execute.call_args[0]
        assert call_args[0] == repo
        assert isinstance(call_args[1], str)
