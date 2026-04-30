# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Unit tests for _CommitCommand.

These tests verify the commit command's UI flow: repository detection,
commit message dialog, validation, and result handling.
"""

from unittest.mock import MagicMock, Mock, patch

from freecad.diff_wb.application.actions.result_models import Result
from freecad.diff_wb.domain.git.models import GitRepository
from freecad.diff_wb.entrypoints.commands import _CommitCommand


class TestCommitCommand:
    """Tests for _CommitCommand."""

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb.ui.registry.ui_registry")
    @patch("freecad.diff_wb._container.get_container")
    def test_commit_command_successful_commit(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """Happy path: user enters message, commit succeeds, refresh is triggered."""
        # Setup
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_action = MagicMock()
        mock_container.commit_staging_action = mock_action
        mock_container.log = MagicMock()
        mock_container.get_staged_file_paths_action.execute.return_value = Result.success(["file.FCStd"])
        mock_get_container.return_value = mock_container

        mock_repo = MagicMock(spec=GitRepository)
        mock_repo.absolute_path = "/home/user/project"
        mock_ui_registry.ui_state.git_repository = mock_repo

        mock_presenter = MagicMock()
        mock_ui_registry.git_repository_presenter = mock_presenter

        command = _CommitCommand()

        # Execute
        with patch.object(command, "_show_commit_dialog", return_value="Add new feature"):
            command.Activated()

        # Verify
        mock_action.execute.assert_called_once_with(mock_repo, "Add new feature")
        mock_container.log.assert_called_once_with("Commit successful")
        mock_presenter.refresh_repository_and_commits.assert_called_once()
        mock_message_box.critical.assert_not_called()

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb.ui.registry.ui_registry")
    @patch("freecad.diff_wb._container.get_container")
    def test_commit_command_no_repository(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When no git repository detected, shows warning and doesn't proceed."""
        # Setup
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_get_container.return_value = mock_container

        mock_ui_registry.ui_state.git_repository = None

        command = _CommitCommand()

        # Execute
        command.Activated()

        # Verify
        mock_message_box.warning.assert_called_once()
        call_args = mock_message_box.warning.call_args
        assert call_args[0][1] == "No Repository"
        assert "git repository" in call_args[0][2].lower()
        mock_message_box.critical.assert_not_called()

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb.ui.registry.ui_registry")
    @patch("freecad.diff_wb._container.get_container")
    def test_commit_command_user_cancelled(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When user cancels the dialog, no action is taken."""
        # Setup
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_get_container.return_value = mock_container

        mock_repo = MagicMock(spec=GitRepository)
        mock_ui_registry.ui_state.git_repository = mock_repo

        command = _CommitCommand()

        # Execute
        with patch.object(command, "_show_commit_dialog", return_value=None):
            command.Activated()

        # Verify
        mock_message_box.warning.assert_not_called()
        mock_message_box.critical.assert_not_called()

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb.ui.registry.ui_registry")
    @patch("freecad.diff_wb._container.get_container")
    def test_commit_command_empty_message(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When user enters empty message, shows warning and doesn't commit."""
        # Setup
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_get_container.return_value = mock_container

        mock_repo = MagicMock(spec=GitRepository)
        mock_ui_registry.ui_state.git_repository = mock_repo

        command = _CommitCommand()

        # Execute
        with patch.object(command, "_show_commit_dialog", return_value=""):
            command.Activated()

        # Verify
        mock_message_box.warning.assert_called_once()
        call_args = mock_message_box.warning.call_args
        assert call_args[0][1] == "Empty Message"
        assert "empty" in call_args[0][2].lower()
        mock_message_box.critical.assert_not_called()

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb.ui.registry.ui_registry")
    @patch("freecad.diff_wb._container.get_container")
    def test_commit_command_whitespace_only_message(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When user enters whitespace-only message, shows warning and doesn't commit."""
        # Setup
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_get_container.return_value = mock_container

        mock_repo = MagicMock(spec=GitRepository)
        mock_ui_registry.ui_state.git_repository = mock_repo

        command = _CommitCommand()

        # Execute
        with patch.object(command, "_show_commit_dialog", return_value="   \t  "):
            command.Activated()

        # Verify
        mock_message_box.warning.assert_called_once()
        call_args = mock_message_box.warning.call_args
        assert call_args[0][1] == "Empty Message"
        mock_message_box.critical.assert_not_called()

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb.ui.registry.ui_registry")
    @patch("freecad.diff_wb._container.get_container")
    def test_commit_command_failed_commit(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When commit fails, shows critical error with message."""
        # Setup
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_action = MagicMock()
        mock_container.commit_staging_action = mock_action
        mock_container.get_staged_file_paths_action.execute.return_value = Result.success(["file.FCStd"])
        mock_get_container.return_value = mock_container

        mock_repo = MagicMock(spec=GitRepository)
        mock_ui_registry.ui_state.git_repository = mock_repo

        mock_action.execute.return_value = Result.failure("Git commit failed")

        command = _CommitCommand()

        # Execute
        with patch.object(command, "_show_commit_dialog", return_value="Add new feature"):
            command.Activated()

        # Verify
        mock_message_box.critical.assert_called_once()
        call_args = mock_message_box.critical.call_args
        assert call_args[0][1] == "Commit Failed"
        assert "git commit failed" in call_args[0][2].lower()
        mock_message_box.warning.assert_not_called()

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb.ui.registry.ui_registry")
    @patch("freecad.diff_wb._container.get_container")
    def test_commit_command_failed_commit_with_custom_message(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When commit fails with a specific message, shows that message."""
        # Setup
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_action = MagicMock()
        mock_container.commit_staging_action = mock_action
        mock_container.get_staged_file_paths_action.execute.return_value = Result.success(["file.FCStd"])
        mock_get_container.return_value = mock_container

        mock_repo = MagicMock(spec=GitRepository)
        mock_ui_registry.ui_state.git_repository = mock_repo

        mock_action.execute.return_value = Result.failure("No staged files")

        command = _CommitCommand()

        # Execute
        with patch.object(command, "_show_commit_dialog", return_value="Add new feature"):
            command.Activated()

        # Verify
        mock_message_box.critical.assert_called_once()
        call_args = mock_message_box.critical.call_args
        assert call_args[0][2] == "No staged files"

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb.ui.registry.ui_registry")
    @patch("freecad.diff_wb._container.get_container")
    def test_commit_command_no_staged_files(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When there are no staged files, shows info message and doesn't proceed."""
        # Setup
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_container.get_staged_file_paths_action.execute.return_value = Result.success([])
        mock_get_container.return_value = mock_container

        mock_repo = MagicMock(spec=GitRepository)
        mock_ui_registry.ui_state.git_repository = mock_repo

        command = _CommitCommand()

        # Execute
        command.Activated()

        # Verify - no dialog shown, no commit attempted
        mock_message_box.information.assert_called_once()
        call_args = mock_message_box.information.call_args
        assert call_args[0][1] == "No Staged Files"
        assert "staged" in call_args[0][2].lower()
        mock_message_box.warning.assert_not_called()
        mock_message_box.critical.assert_not_called()

    def test_commit_command_resources_correct(self) -> None:
        """Menu text, tooltips, icons are correct."""
        # Setup
        command = _CommitCommand()

        # Execute
        resources = command.GetResources()

        # Verify
        assert "MenuText" in resources
        assert "ToolTip" in resources
        assert "Pixmap" in resources
        assert resources["MenuText"] == "Commit"
        assert "commit" in resources["ToolTip"].lower()
        assert "Commit.svg" in resources["Pixmap"]

    def test_commit_is_active_returns_true(self) -> None:
        """Command is always active."""
        # Setup
        command = _CommitCommand()

        # Execute
        result = command.IsActive()

        # Verify
        assert result is True

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb.ui.registry.ui_registry")
    @patch("freecad.diff_wb._container.get_container")
    def test_commit_command_trims_message_before_sending(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """Verifies message is stripped before being sent to action."""
        # Setup
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_action = MagicMock()
        mock_container.commit_staging_action = mock_action
        mock_container.get_staged_file_paths_action.execute.return_value = Result.success(["file.FCStd"])
        mock_get_container.return_value = mock_container

        mock_repo = MagicMock(spec=GitRepository)
        mock_ui_registry.ui_state.git_repository = mock_repo

        command = _CommitCommand()

        # Execute
        with patch.object(command, "_show_commit_dialog", return_value="  Add feature with spaces  "):
            command.Activated()

        # Verify - message should be trimmed
        mock_action.execute.assert_called_once()
        call_args = mock_action.execute.call_args
        assert call_args[0][1] == "Add feature with spaces"
