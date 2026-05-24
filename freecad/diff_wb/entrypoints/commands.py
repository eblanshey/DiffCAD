# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: FreeCAD command entry points for the Diff Workbench.

This module defines the FreeCAD commands that bridge user interactions
(toolbar/menu clicks) with application layer actions and UI presenters.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

from PySide6.QtCore import QT_TRANSLATE_NOOP

from ..resources import ICONPATH


if TYPE_CHECKING:
    from ..domain.git.models import GitRepositoryInitCandidate


class CommandResources(TypedDict):
    """Shape of FreeCAD command metadata returned by GetResources."""

    MenuText: object
    ToolTip: object
    Pixmap: str


@dataclass(frozen=True)
class CommitDialogResult:
    """Commit dialog values collected from the user."""

    message: str


@dataclass(frozen=True)
class GitConfigDialogResult:
    """Git identity configuration values collected from the user."""

    author_name: str
    author_email: str
    should_save_globally: bool


class _SwapColumnsCommand:
    """Command to swap left/right columns in the diff view."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QT_TRANSLATE_NOOP("DiffSwapColumns", "Swap Columns"),
            "ToolTip": QT_TRANSLATE_NOOP("DiffSwapColumns", "Swap the left and right columns"),
            "Pixmap": os.path.join(ICONPATH, "SwapColumns.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """Execute the swap columns action.

        TODO: Phase 8 - Implement when UI view exists.
        """
        # Phase 8: Will call view method to swap columns when UI is implemented
        pass


class _ConfigureGitCommand:
    """Command to configure git author identity."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QT_TRANSLATE_NOOP("DiffConfigureGitCommand", "Configure Git"),
            "ToolTip": QT_TRANSLATE_NOOP("DiffConfigureGitCommand", "Configure git author name and email"),
            "Pixmap": os.path.join(ICONPATH, "ConfigureGit.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from PySide6.QtWidgets import QMessageBox

        from .._container import get_container
        from ..ui.registry import ui_registry
        from ..ui.translation_strings import COMMIT_NO_REPOSITORY_MESSAGE, COMMIT_NO_REPOSITORY_TITLE

        container = get_container()
        repo = ui_registry.ui_state.git_repository
        if repo is None:
            QMessageBox.warning(
                None,  # type: ignore[arg-type]
                container.translate("Commit", COMMIT_NO_REPOSITORY_TITLE),
                container.translate("Commit", COMMIT_NO_REPOSITORY_MESSAGE),
            )
            return

        self.configure_repository(container, repo)

    def configure_repository(self, container, repo) -> bool:
        """Show git config dialog and save identity for a repository."""
        from PySide6.QtWidgets import QMessageBox

        from ..domain.git.models import GitIdentity
        from ..ui.translation_strings import (
            COMMIT_FAILED_TITLE,
            COMMIT_IDENTITY_REQUIRED_MESSAGE,
            COMMIT_IDENTITY_SAVE_FAILED_MESSAGE,
            CONFIGURE_GIT_GLOBAL_SAVE_FAILED_MESSAGE,
        )

        retry_message: str | None = None
        initial_values = self._configured_identity_dialog_values(container, repo)
        global_config_writable = self._can_write_global_identity(container)
        while True:
            dialog_result = self._show_git_config_dialog(
                container,
                message=retry_message,
                initial_values=initial_values,
                global_config_writable=global_config_writable,
            )
            if dialog_result is None:
                return False

            if not dialog_result.author_name or not dialog_result.author_email:
                QMessageBox.warning(
                    None,  # type: ignore[arg-type]
                    container.translate("Commit", COMMIT_FAILED_TITLE),
                    container.translate("Commit", COMMIT_IDENTITY_REQUIRED_MESSAGE),
                )
                return False

            save_result = container.save_git_identity_action.execute(
                repo,
                GitIdentity(name=dialog_result.author_name, email=dialog_result.author_email),
                dialog_result.should_save_globally,
            )
            if save_result.is_success:
                return True

            if not dialog_result.should_save_globally:
                QMessageBox.critical(
                    None,  # type: ignore[arg-type]
                    container.translate("Commit", COMMIT_FAILED_TITLE),
                    container.translate("Commit", COMMIT_IDENTITY_SAVE_FAILED_MESSAGE),
                )
                return False

            retry_message = container.translate("Commit", CONFIGURE_GIT_GLOBAL_SAVE_FAILED_MESSAGE)
            initial_values = dialog_result

    def _can_write_global_identity(self, container) -> bool:
        """Return whether global git identity config can be written."""
        result = container.can_write_global_git_identity_action.execute()
        if not result.is_success:
            return False
        return bool(result.data)

    def _configured_identity_dialog_values(self, container, repo) -> GitConfigDialogResult | None:
        """Return existing git identity as dialog defaults when configured."""
        identity_result = container.get_git_identity_action.execute(repo)
        identity = identity_result.data
        if identity is None:
            return None
        return GitConfigDialogResult(
            author_name=identity.name,
            author_email=identity.email,
            should_save_globally=False,
        )

    def _show_git_config_dialog(
        self,
        container,
        *,
        message: str | None = None,
        initial_values: GitConfigDialogResult | None = None,
        global_config_writable: bool = True,
    ) -> GitConfigDialogResult | None:
        """Show git identity configuration dialog."""
        from PySide6.QtWidgets import (
            QCheckBox,
            QDialog,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QPushButton,
            QVBoxLayout,
        )

        from ..ui.translation_strings import (
            COMMIT_EMAIL_LABEL,
            COMMIT_NAME_LABEL,
            COMMIT_REMEMBER_IDENTITY_LABEL,
            CONFIGURE_GIT_DIALOG_TITLE,
            CONFIGURE_GIT_GLOBAL_CONFIG_NOT_WRITABLE_MESSAGE,
            CONFIGURE_GIT_IDENTITY_PROMPT,
            DIALOG_CANCEL,
            DIALOG_OK,
        )

        dialog = QDialog(None)  # type: ignore[arg-type]
        dialog.setWindowTitle(container.translate("Commit", CONFIGURE_GIT_DIALOG_TITLE))
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(container.translate("Commit", CONFIGURE_GIT_IDENTITY_PROMPT), dialog))
        if message:
            message_label = QLabel(message, dialog)
            message_label.setStyleSheet("color: red;")
            layout.addWidget(message_label)
        form_layout = QFormLayout()
        name_edit = QLineEdit(dialog)
        email_edit = QLineEdit(dialog)
        remember_checkbox = QCheckBox(container.translate("Commit", COMMIT_REMEMBER_IDENTITY_LABEL), dialog)
        if initial_values is not None:
            name_edit.setText(initial_values.author_name)
            email_edit.setText(initial_values.author_email)
            remember_checkbox.setChecked(initial_values.should_save_globally)
        if not global_config_writable:
            remember_checkbox.setChecked(False)
            remember_checkbox.setEnabled(False)

        form_layout.addRow(container.translate("Commit", COMMIT_NAME_LABEL), name_edit)
        form_layout.addRow(container.translate("Commit", COMMIT_EMAIL_LABEL), email_edit)
        layout.addLayout(form_layout)
        layout.addWidget(remember_checkbox)
        if not global_config_writable:
            global_config_label = QLabel(
                container.translate("Commit", CONFIGURE_GIT_GLOBAL_CONFIG_NOT_WRITABLE_MESSAGE),
                dialog,
            )
            global_config_label.setStyleSheet("color: red;")
            layout.addWidget(global_config_label)

        button_layout = QHBoxLayout()
        ok_button = QPushButton(container.translate("Common", DIALOG_OK))
        cancel_button = QPushButton(container.translate("Common", DIALOG_CANCEL))
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        ok = dialog.exec() == 1  # QDialog.Accepted = 1
        if not ok:
            return None
        return GitConfigDialogResult(
            author_name=name_edit.text().strip(),
            author_email=email_edit.text().strip(),
            should_save_globally=remember_checkbox.isChecked(),
        )


class _CommitCommand:
    """Command to save iteration."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QT_TRANSLATE_NOOP("DiffCommit", "Save Iteration"),
            "ToolTip": QT_TRANSLATE_NOOP("DiffCommit", "Save reviewed changes as an iteration"),
            "Pixmap": os.path.join(ICONPATH, "Commit.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True  # Always enabled; validation happens in Activated()

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from PySide6.QtWidgets import QMessageBox

        from .._container import get_container
        from ..ui.registry import ui_registry
        from ..ui.translation_strings import (
            COMMIT_FAILED_TITLE,
            COMMIT_NO_REPOSITORY_MESSAGE,
            COMMIT_NO_REPOSITORY_TITLE,
            COMMIT_NO_STAGED_FILES_MESSAGE,
            COMMIT_NO_STAGED_FILES_TITLE,
        )

        container = get_container()

        # Check if we have a git repository via UIState in registry
        repo = ui_registry.ui_state.git_repository

        if repo is None:
            QMessageBox.warning(
                None,  # type: ignore[arg-type]
                container.translate("Commit", COMMIT_NO_REPOSITORY_TITLE),
                container.translate("Commit", COMMIT_NO_REPOSITORY_MESSAGE),
            )
            return

        # Check for staged files
        staged_result = container.get_staged_file_paths_action.execute(repo)
        if not staged_result.is_success or not staged_result.data:
            QMessageBox.information(
                None,  # type: ignore[arg-type]
                container.translate("Commit", COMMIT_NO_STAGED_FILES_TITLE),
                container.translate("Commit", COMMIT_NO_STAGED_FILES_MESSAGE),
            )
            return

        identity_result = container.get_git_identity_action.execute(repo)
        if identity_result.data is None and not _ConfigureGitCommand().configure_repository(container, repo):
            return

        dialog_result = self._show_commit_dialog(container)

        if dialog_result is None:
            return

        if not self._validate_commit_dialog_result(container, dialog_result):
            return

        # Execute commit action
        result = container.commit_staging_action.execute(repo, dialog_result.message.strip())

        if result.is_success:
            container.log("Commit successful")
            # Reload commits by triggering refresh
            ui_registry.git_repository_presenter.refresh_repository_and_commits()
        else:
            QMessageBox.critical(
                None,  # type: ignore[arg-type]
                container.translate("Commit", COMMIT_FAILED_TITLE),
                result.message or "Git commit failed",
            )

    def _validate_commit_dialog_result(self, container, dialog_result: CommitDialogResult) -> bool:
        """Validate commit dialog values and show warnings for invalid input."""
        from PySide6.QtWidgets import QMessageBox

        from ..ui.translation_strings import (
            COMMIT_EMPTY_MESSAGE,
            COMMIT_EMPTY_MESSAGE_TITLE,
        )

        if not dialog_result.message.strip():
            QMessageBox.warning(
                None,  # type: ignore[arg-type]
                container.translate("Commit", COMMIT_EMPTY_MESSAGE_TITLE),
                container.translate("Commit", COMMIT_EMPTY_MESSAGE),
            )
            return False
        return True

    def _show_commit_dialog(self, container) -> CommitDialogResult | None:
        """Show the commit dialog and return the message or None if cancelled.

        Args:
            container: The application container.

        Returns:
            Commit dialog result if user confirmed, None if cancelled.
        """
        from PySide6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QPlainTextEdit,
            QPushButton,
            QVBoxLayout,
        )

        from ..ui.translation_strings import (
            COMMIT_DIALOG_PLACEHOLDER,
            COMMIT_DIALOG_PROMPT,
            COMMIT_DIALOG_TITLE,
            DIALOG_CANCEL,
            DIALOG_OK,
        )

        dialog = QDialog(None)  # type: ignore[arg-type]
        dialog.setWindowTitle(container.translate("Commit", COMMIT_DIALOG_TITLE))

        # Enable resize grip in bottom-right corner
        dialog.setSizeGripEnabled(True)

        # Create layout with text area and buttons
        layout = QVBoxLayout(dialog)

        # Add label
        from PySide6.QtWidgets import QLabel

        label = QLabel(container.translate("Commit", COMMIT_DIALOG_PROMPT))
        layout.addWidget(label)

        # Create a multi-line text editor that can resize vertically
        from PySide6.QtWidgets import QSizePolicy

        text_edit = QPlainTextEdit(dialog)
        text_edit.setPlaceholderText(container.translate("Commit", COMMIT_DIALOG_PLACEHOLDER))
        text_edit.setTabStopDistance(40)  # Tab spacing in pixels
        text_edit.setMinimumHeight(100)  # Minimum height for initial usability
        # Allow the text edit to expand vertically when dialog is resized
        text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(text_edit)

        # Add OK and Cancel buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton(container.translate("Common", DIALOG_OK))
        cancel_button = QPushButton(container.translate("Common", DIALOG_CANCEL))

        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Make the dialog resizable with a reasonable size
        dialog.resize(500, 300)

        ok = dialog.exec() == 1  # QDialog.Accepted = 1
        if not ok:
            return None
        return CommitDialogResult(message=text_edit.toPlainText())


class _RefreshRepositoryCommand:
    """Command to refresh project detection and reload iterations."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QT_TRANSLATE_NOOP("DiffRefreshRepository", "Refresh Project"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "DiffRefreshRepository",
                "Refresh the detected project and reload iterations.\n"
                "Open at least one FreeCAD document "
                "located within a project before running this command.\n"
                "How it works: open FreeCAD "
                "documents are checked one by one until one is found to be located within a project.",
            ),
            "Pixmap": os.path.join(ICONPATH, "RefreshRepository.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from ..ui.registry import ui_registry

        ui_registry.git_repository_presenter.refresh_repository_and_commits()


class _InitializeGitRepositoryCommand:
    """Command to initialize a git repository from open document directories."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QT_TRANSLATE_NOOP("DiffInitializeGitRepository", "Initialize Git Repository"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "DiffInitializeGitRepository",
                "Initialize a git repository in the selected directory",
            ),
            "Pixmap": os.path.join(ICONPATH, "CreateGitRepository.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from PySide6.QtWidgets import QMessageBox

        from .._container import get_container
        from ..ui.registry import ui_registry
        from ..ui.translation_strings import (
            ERROR_UNKNOWN,
            INITIALIZE_REPOSITORY_FAILED_TITLE,
            INITIALIZE_REPOSITORY_NO_CANDIDATES_MESSAGE,
            INITIALIZE_REPOSITORY_NO_CANDIDATES_TITLE,
            INITIALIZE_REPOSITORY_SUCCESS_TEMPLATE,
            INITIALIZE_REPOSITORY_SUCCESS_TITLE,
        )

        container = get_container()
        candidates_result = container.get_git_repository_init_candidates_action.execute()
        if not candidates_result.is_success:
            QMessageBox.information(
                None,  # type: ignore[arg-type]
                container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_NO_CANDIDATES_TITLE),
                container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_NO_CANDIDATES_MESSAGE),
            )
            return

        selected_directory = self._show_init_dialog(container, candidates_result.data)
        if selected_directory is None:
            return

        init_result = container.initialize_git_repository_action.execute(selected_directory)
        if not init_result.is_success:
            QMessageBox.critical(
                None,  # type: ignore[arg-type]
                container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_FAILED_TITLE),
                init_result.message or container.translate("Common", ERROR_UNKNOWN),
            )
            return

        repository = init_result.data
        self._store_initialized_repository(repository)

        success_template = container.translate(
            "InitializeGitRepository",
            INITIALIZE_REPOSITORY_SUCCESS_TEMPLATE,
        )
        success_message = success_template.replace("%1", repository.absolute_path)
        QMessageBox.information(
            None,  # type: ignore[arg-type]
            container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_SUCCESS_TITLE),
            success_message,
        )
        ui_registry.git_repository_presenter.refresh_repository_and_commits()

    def _show_init_dialog(self, container, candidates: list[GitRepositoryInitCandidate]) -> str | None:
        """Show initialization selection dialog and return selected directory."""
        from PySide6.QtWidgets import (
            QButtonGroup,
            QDialog,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QRadioButton,
            QVBoxLayout,
        )

        from ..ui.translation_strings import (
            DIALOG_CANCEL,
            INITIALIZE_REPOSITORY_BUTTON,
            INITIALIZE_REPOSITORY_DIALOG_PROMPT,
            INITIALIZE_REPOSITORY_DIALOG_TITLE,
            INITIALIZE_REPOSITORY_DISABLED_REASON,
            INITIALIZE_REPOSITORY_NO_AVAILABLE_MESSAGE,
        )

        dialog = QDialog(None)  # type: ignore[arg-type]
        dialog.setWindowTitle(container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_DIALOG_TITLE))
        dialog.setSizeGripEnabled(True)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_DIALOG_PROMPT)))

        button_group = QButtonGroup(dialog)
        first_available_button = None

        for index, candidate in enumerate(candidates):
            row_layout = QHBoxLayout()
            radio = QRadioButton(candidate.path, dialog)
            radio.setEnabled(candidate.is_available)
            button_group.addButton(radio, index)
            row_layout.addWidget(radio)
            if candidate.is_available and first_available_button is None:
                first_available_button = radio

            if not candidate.is_available:
                reason_label = QLabel(
                    container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_DISABLED_REASON),
                    dialog,
                )
                reason_label.setEnabled(False)
                row_layout.addWidget(reason_label)

            row_layout.addStretch()
            layout.addLayout(row_layout)

        if first_available_button is not None:
            first_available_button.setChecked(True)
        else:
            no_available_text = container.translate(
                "InitializeGitRepository",
                INITIALIZE_REPOSITORY_NO_AVAILABLE_MESSAGE,
            )
            layout.addWidget(QLabel(no_available_text))

        button_layout = QHBoxLayout()
        initialize_button = QPushButton(container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_BUTTON))
        initialize_button.setEnabled(first_available_button is not None)
        cancel_button = QPushButton(container.translate("Common", DIALOG_CANCEL))
        initialize_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(initialize_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.setMinimumWidth(680)
        dialog.adjustSize()
        target_height = min(360, dialog.sizeHint().height() + 8)
        dialog.resize(dialog.width(), target_height)
        if dialog.exec() != 1:
            return None

        selected_id = button_group.checkedId()
        if selected_id < 0:
            return None
        return candidates[selected_id].path

    def _store_initialized_repository(self, repository) -> None:
        """Store initialized repository in UI state before refresh."""
        from ..ui.registry import ui_registry

        ui_registry.ui_state.git_repository = repository


class _OpenAllDocumentsInRepositoryCommand:
    """Command to open all .FCStd documents under detected repository."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QT_TRANSLATE_NOOP("DiffOpenAllDocumentsInRepository", "Open All Documents in Project"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "DiffOpenAllDocumentsInRepository",
                "Open every .FCStd file found in the project. Useful for generating en masse.",
            ),
            "Pixmap": os.path.join(ICONPATH, "OpenAllDocuments.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from PySide6.QtWidgets import QMessageBox

        from .._container import get_container
        from ..ui.registry import ui_registry
        from ..ui.translation_strings import (
            OPEN_ALL_DOCUMENTS_NO_REPOSITORY_MESSAGE,
            OPEN_ALL_DOCUMENTS_NO_REPOSITORY_TITLE,
        )

        container = get_container()
        repo = ui_registry.ui_state.git_repository

        if repo is None:
            QMessageBox.warning(
                None,  # type: ignore[arg-type]
                container.translate("OpenAllDocuments", OPEN_ALL_DOCUMENTS_NO_REPOSITORY_TITLE),
                container.translate("OpenAllDocuments", OPEN_ALL_DOCUMENTS_NO_REPOSITORY_MESSAGE),
            )
            return

        container.open_all_documents_in_repository_action.execute(repo)


class _RecomputeAllOpenDocumentsCommand:
    """Command to recompute all open documents in FreeCAD."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QT_TRANSLATE_NOOP("DiffRecomputeAllOpenDocuments", "Recompute All"),
            "ToolTip": QT_TRANSLATE_NOOP("DiffRecomputeAllOpenDocuments", "Recompute every open document"),
            "Pixmap": os.path.join(ICONPATH, "RecomputeAll.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from .._container import get_container

        container = get_container()
        container.recompute_all_open_documents_action.execute()


class _RecomputeActiveDocumentCommand:
    """Command to recompute the active document in FreeCAD."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QT_TRANSLATE_NOOP("DiffRecomputeActiveDocument", "Recompute Active Document"),
            "ToolTip": QT_TRANSLATE_NOOP("DiffRecomputeActiveDocument", "Recompute the active document"),
            "Pixmap": "view-refresh",  # FreeCAD's standard recompute icon (from Std_Recompute)
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from .._container import get_container

        container = get_container()

        # Use FreeCAD port to recompute the active document
        container._freecad_port.try_recompute_active_document()


class _OpenDiffWindowCommand:
    """Command to open or focus the history panel."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QT_TRANSLATE_NOOP("DiffOpenDiffWindow", "Open History Panel"),
            "ToolTip": QT_TRANSLATE_NOOP("DiffOpenDiffWindow", "Open project history view"),
            "Pixmap": os.path.join(ICONPATH, "Logo.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        import FreeCADGui as Gui  # pylint: disable=import-error

        # Get the Diff workbench instance and show/create the diff panel
        workbench = Gui.getWorkbench("DiffWorkbench")
        if workbench is not None:
            workbench.create_or_show_diff_panel()


class _CloseDiffWindowsCommand:
    """Command to close all Compare_* windows without saving."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QT_TRANSLATE_NOOP("DiffCloseDiffWindows", "Close Comparison Windows"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "DiffCloseDiffWindows",
                "Close every document starting with 'Compare_' without saving",
            ),
            "Pixmap": os.path.join(ICONPATH, "DiffCloseDiffWindows.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        import FreeCAD as App  # pylint: disable=import-error

        # Get list of document names to close (iterate over copy to avoid modification during iteration)
        docs_to_close = [doc_name for doc_name in App.listDocuments() if doc_name.startswith("Compare_")]

        # Close each document without saving
        for doc_name in docs_to_close:
            App.closeDocument(doc_name)


def register_commands() -> None:
    """Register the Diff Workbench commands with FreeCAD."""
    import FreeCADGui as Gui  # pylint: disable=import-error

    Gui.addCommand("DiffConfigureGitCommand", _ConfigureGitCommand())
    Gui.addCommand("DiffCommit", _CommitCommand())
    Gui.addCommand("DiffRefreshRepository", _RefreshRepositoryCommand())
    Gui.addCommand("DiffInitializeGitRepository", _InitializeGitRepositoryCommand())
    Gui.addCommand("DiffOpenAllDocumentsInRepository", _OpenAllDocumentsInRepositoryCommand())
    Gui.addCommand("DiffRecomputeAllOpenDocuments", _RecomputeAllOpenDocumentsCommand())
    Gui.addCommand("DiffRecomputeActiveDocument", _RecomputeActiveDocumentCommand())
    Gui.addCommand("DiffOpenDiffWindow", _OpenDiffWindowCommand())
    Gui.addCommand("DiffCloseDiffWindows", _CloseDiffWindowsCommand())
