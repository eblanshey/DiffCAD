# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Unit tests for _CommitCommand.

These tests verify the commit command's UI flow: repository detection,
commit message dialog, validation, and result handling.
"""

from unittest.mock import MagicMock, Mock, patch

from freecad.history_wb.application.actions.result_models import Result
from freecad.history_wb.domain.git.models import GitIdentity, GitRepository
from freecad.history_wb.entrypoints.commands import (
    CommitDialogResult,
    GitConfigDialogResult,
    _CommitCommand,
    _ConfigureGitCommand,
)


class TestCommitCommand:
    """Tests for _CommitCommand."""

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
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
        with patch.object(command, "_show_commit_dialog", return_value=CommitDialogResult(message="Add new feature")):
            command.Activated()

        # Verify
        mock_action.execute.assert_called_once_with(mock_repo, "Add new feature")
        mock_container.log.assert_called_once_with("Commit successful")
        mock_presenter.refresh_repository_and_commits.assert_called_once()
        mock_message_box.critical.assert_not_called()

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
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
        assert call_args[0][1] == "No Project"
        assert "project" in call_args[0][2].lower()
        mock_message_box.critical.assert_not_called()

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
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

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
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
        with patch.object(command, "_show_commit_dialog", return_value=CommitDialogResult(message="")):
            command.Activated()

        # Verify
        mock_message_box.warning.assert_called_once()
        call_args = mock_message_box.warning.call_args
        assert call_args[0][1] == "Empty Notes"
        mock_message_box.critical.assert_not_called()

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
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
        with patch.object(command, "_show_commit_dialog", return_value=CommitDialogResult(message="   \t  ")):
            command.Activated()

        # Verify
        mock_message_box.warning.assert_called_once()
        call_args = mock_message_box.warning.call_args
        assert call_args[0][1] == "Empty Notes"
        mock_message_box.critical.assert_not_called()

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
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
        with patch.object(command, "_show_commit_dialog", return_value=CommitDialogResult(message="Add new feature")):
            command.Activated()

        # Verify
        mock_message_box.critical.assert_called_once()
        call_args = mock_message_box.critical.call_args
        assert call_args[0][1] == "Save Iteration Failed"
        assert "git commit failed" in call_args[0][2].lower()
        mock_message_box.warning.assert_not_called()

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
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
        with patch.object(command, "_show_commit_dialog", return_value=CommitDialogResult(message="Add new feature")):
            command.Activated()

        # Verify
        mock_message_box.critical.assert_called_once()
        call_args = mock_message_box.critical.call_args
        assert call_args[0][2] == "No staged files"

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
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
        assert call_args[0][1] == "No Reviewed Files"
        assert "reviewed" in call_args[0][2].lower()
        mock_message_box.warning.assert_not_called()
        mock_message_box.critical.assert_not_called()

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
    def test_commit_command_configures_missing_identity_before_commit(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """Missing identity opens configure command, then commit dialog runs."""
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_container.get_staged_file_paths_action.execute.return_value = Result.success(["file.FCStd"])
        mock_container.get_git_identity_action.execute.return_value = Result.success(None)
        mock_container.commit_staging_action.execute.return_value = Result.success(True)
        mock_container.log = MagicMock()
        mock_get_container.return_value = mock_container

        mock_repo = MagicMock(spec=GitRepository)
        mock_ui_registry.ui_state.git_repository = mock_repo
        mock_ui_registry.git_repository_presenter = MagicMock()

        command = _CommitCommand()
        dialog_result = CommitDialogResult(message="Add feature")

        with (
            patch.object(_ConfigureGitCommand, "configure_repository", return_value=True) as mock_configure,
            patch.object(command, "_show_commit_dialog", return_value=dialog_result) as mock_dialog,
        ):
            command.Activated()

        mock_configure.assert_called_once_with(
            mock_container, mock_repo, mock_container._freecad_port.get_main_window()
        )
        mock_dialog.assert_called_once_with(mock_container._freecad_port.get_main_window())
        mock_container.commit_staging_action.execute.assert_called_once_with(mock_repo, "Add feature")
        mock_message_box.warning.assert_not_called()
        mock_message_box.critical.assert_not_called()

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
    def test_commit_command_stops_when_configure_identity_cancelled(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """Missing identity stops commit when configure command is cancelled."""
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_container.get_staged_file_paths_action.execute.return_value = Result.success(["file.FCStd"])
        mock_container.get_git_identity_action.execute.return_value = Result.success(None)
        mock_get_container.return_value = mock_container

        mock_repo = MagicMock(spec=GitRepository)
        mock_ui_registry.ui_state.git_repository = mock_repo

        command = _CommitCommand()
        with (
            patch.object(_ConfigureGitCommand, "configure_repository", return_value=False) as mock_configure,
            patch.object(command, "_show_commit_dialog") as mock_dialog,
        ):
            command.Activated()

        mock_configure.assert_called_once_with(
            mock_container, mock_repo, mock_container._freecad_port.get_main_window()
        )
        mock_dialog.assert_not_called()
        mock_container.commit_staging_action.execute.assert_not_called()

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
        assert resources["MenuText"] == "Save Iteration"
        assert "iteration" in resources["ToolTip"].lower()
        assert "Commit.svg" in resources["Pixmap"]

    def test_commit_is_active_returns_true(self) -> None:
        """Command is always active."""
        # Setup
        command = _CommitCommand()

        # Execute
        result = command.IsActive()

        # Verify
        assert result is True

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
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
        with patch.object(
            command,
            "_show_commit_dialog",
            return_value=CommitDialogResult(message="  Add feature with spaces  "),
        ):
            command.Activated()

        # Verify - message should be trimmed
        mock_action.execute.assert_called_once()
        call_args = mock_action.execute.call_args
        assert call_args[0][1] == "Add feature with spaces"


class TestConfigureGitCommand:
    """Tests for _ConfigureGitCommand."""

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    def test_configure_repository_saves_identity(
        self,
        mock_message_box: Mock,
    ) -> None:
        """Configure dialog values are saved through application action."""
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_container.get_git_identity_action.execute.return_value = Result.success(None)
        mock_container.save_git_identity_action.execute.return_value = Result.success(True)
        mock_container.can_write_global_git_identity_action.execute.return_value = Result.success(True)
        mock_repo = MagicMock(spec=GitRepository)
        command = _ConfigureGitCommand()
        dialog_result = GitConfigDialogResult(
            author_name="Test User",
            author_email="test@example.com",
            should_save_globally=True,
        )

        with patch.object(command, "_show_git_config_dialog", return_value=dialog_result):
            result = command.configure_repository(mock_container, mock_repo, None)

        assert result is True
        mock_container.save_git_identity_action.execute.assert_called_once_with(
            mock_repo,
            GitIdentity(name="Test User", email="test@example.com"),
            True,
        )
        mock_message_box.warning.assert_not_called()
        mock_message_box.critical.assert_not_called()

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    def test_configure_repository_requires_name_and_email(self, mock_message_box: Mock) -> None:
        """Configure dialog requires both name and email."""
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_container.get_git_identity_action.execute.return_value = Result.success(None)
        mock_container.can_write_global_git_identity_action.execute.return_value = Result.success(True)
        mock_repo = MagicMock(spec=GitRepository)
        command = _ConfigureGitCommand()
        dialog_result = GitConfigDialogResult(
            author_name="",
            author_email="test@example.com",
            should_save_globally=False,
        )

        with patch.object(command, "_show_git_config_dialog", return_value=dialog_result):
            result = command.configure_repository(mock_container, mock_repo, None)

        assert result is False
        mock_message_box.warning.assert_called_once()
        mock_container.save_git_identity_action.execute.assert_not_called()

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    def test_configure_repository_cancel_returns_false(self, mock_message_box: Mock) -> None:
        """Canceling configure dialog does not save identity."""
        mock_container = MagicMock()
        mock_container.get_git_identity_action.execute.return_value = Result.success(None)
        mock_container.can_write_global_git_identity_action.execute.return_value = Result.success(True)
        mock_repo = MagicMock(spec=GitRepository)
        command = _ConfigureGitCommand()

        with patch.object(command, "_show_git_config_dialog", return_value=None):
            result = command.configure_repository(mock_container, mock_repo, None)

        assert result is False
        mock_message_box.warning.assert_not_called()
        mock_message_box.critical.assert_not_called()
        mock_container.save_git_identity_action.execute.assert_not_called()

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    def test_configure_repository_reopens_after_global_save_failure(self, mock_message_box: Mock) -> None:
        """Global save failure reopens dialog and allows local save retry."""
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_container.get_git_identity_action.execute.return_value = Result.success(None)
        mock_container.can_write_global_git_identity_action.execute.return_value = Result.success(True)
        mock_container.save_git_identity_action.execute.side_effect = [
            Result.failure("Cannot save global git identity"),
            Result.success(True),
        ]
        mock_repo = MagicMock(spec=GitRepository)
        command = _ConfigureGitCommand()
        global_dialog_result = GitConfigDialogResult(
            author_name="Test User",
            author_email="test@example.com",
            should_save_globally=True,
        )
        local_dialog_result = GitConfigDialogResult(
            author_name="Test User",
            author_email="test@example.com",
            should_save_globally=False,
        )

        with patch.object(
            command,
            "_show_git_config_dialog",
            side_effect=[global_dialog_result, local_dialog_result],
        ) as mock_dialog:
            result = command.configure_repository(mock_container, mock_repo, None)

        assert result is True
        assert mock_dialog.call_count == 2
        assert mock_dialog.call_args_list[0].kwargs == {
            "parent": None,
            "message": None,
            "initial_values": None,
            "global_config_writable": True,
        }
        assert "Uncheck the global option" in mock_dialog.call_args_list[1].kwargs["message"]
        assert mock_dialog.call_args_list[1].kwargs["initial_values"] == global_dialog_result
        assert mock_container.save_git_identity_action.execute.call_args_list[0].args[2] is True
        assert mock_container.save_git_identity_action.execute.call_args_list[1].args[2] is False
        mock_message_box.critical.assert_not_called()

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    def test_configure_repository_prefills_existing_identity(self, mock_message_box: Mock) -> None:
        """Existing git identity is passed to config dialog as initial values."""
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_container.get_git_identity_action.execute.return_value = Result.success(
            GitIdentity(name="Existing User", email="existing@example.com")
        )
        mock_container.save_git_identity_action.execute.return_value = Result.success(True)
        mock_container.can_write_global_git_identity_action.execute.return_value = Result.success(True)
        mock_repo = MagicMock(spec=GitRepository)
        command = _ConfigureGitCommand()
        dialog_result = GitConfigDialogResult(
            author_name="Updated User",
            author_email="updated@example.com",
            should_save_globally=False,
        )

        with patch.object(command, "_show_git_config_dialog", return_value=dialog_result) as mock_dialog:
            result = command.configure_repository(mock_container, mock_repo, None)

        assert result is True
        assert mock_dialog.call_args.kwargs["initial_values"] == GitConfigDialogResult(
            author_name="Existing User",
            author_email="existing@example.com",
            should_save_globally=False,
        )
        mock_message_box.warning.assert_not_called()

    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    def test_configure_repository_disables_global_option_when_global_config_not_writable(
        self,
        mock_message_box: Mock,
    ) -> None:
        """Unwritable global config disables global save option before dialog opens."""
        mock_container = MagicMock()
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_container.get_git_identity_action.execute.return_value = Result.success(None)
        mock_container.can_write_global_git_identity_action.execute.return_value = Result.success(False)
        mock_container.save_git_identity_action.execute.return_value = Result.success(True)
        mock_repo = MagicMock(spec=GitRepository)
        command = _ConfigureGitCommand()
        dialog_result = GitConfigDialogResult(
            author_name="Test User",
            author_email="test@example.com",
            should_save_globally=False,
        )

        with patch.object(command, "_show_git_config_dialog", return_value=dialog_result) as mock_dialog:
            result = command.configure_repository(mock_container, mock_repo, None)

        assert result is True
        assert mock_dialog.call_args.kwargs["global_config_writable"] is False
        mock_container.save_git_identity_action.execute.assert_called_once_with(
            mock_repo,
            GitIdentity(name="Test User", email="test@example.com"),
            False,
        )
        mock_message_box.warning.assert_not_called()
