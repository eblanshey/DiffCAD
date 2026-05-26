# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: FreeCAD command entry points for the Diff Workbench.

This module defines the FreeCAD commands that bridge user interactions
(toolbar/menu clicks) with application layer actions and UI presenters.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

from ..qt import QtCore, QtWidgets
from ..resources import ICONPATH
from ..utils import translate


if TYPE_CHECKING:
    QWidget = QtWidgets.QWidget

    from ..domain.git.models import GitRepositoryInitCandidate


def _main_window_parent(container) -> QWidget | None:
    """Get the FreeCAD main window as a parent widget for dialogs.

    Args:
        container: The application container with _freecad_port attribute

    Returns:
        QWidget parent or None if not available
    """
    main_window = container._freecad_port.get_main_window()
    return main_window  # type: ignore[return-value]


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


class _ConfigureAuthorCommand:
    """Command to configure author identity."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QtCore.QT_TRANSLATE_NOOP("HistoryConfigureAuthorCommand", "Configure Author"),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP("HistoryConfigureAuthorCommand", "Configure author name and email"),
            "Pixmap": os.path.join(ICONPATH, "ConfigureGit.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from .._container import get_container
        from ..ui.registry import ui_registry

        container = get_container()
        parent = _main_window_parent(container)
        repo = ui_registry.ui_state.git_repository
        if repo is None:
            QtWidgets.QMessageBox.warning(
                parent,  # type: ignore[arg-type]
                translate("History", "No Project"),
                translate("History", "No project detected. Please open a document from a project."),
            )
            return

        self.configure_repository(container, repo, parent)

    def configure_repository(self, container, repo, parent: QWidget | None) -> bool:
        """Show git config dialog and save identity for a repository."""
        from ..domain.git.models import GitIdentity

        retry_message: str | None = None
        initial_values = self._configured_identity_dialog_values(container, repo)
        global_config_writable = self._can_write_global_identity(container)
        while True:
            dialog_result = self._show_git_config_dialog(
                container,
                parent=parent,
                message=retry_message,
                initial_values=initial_values,
                global_config_writable=global_config_writable,
            )
            if dialog_result is None:
                return False

            if not dialog_result.author_name or not dialog_result.author_email:
                QtWidgets.QMessageBox.warning(
                    parent,  # type: ignore[arg-type]
                    translate("History", "Save Iteration Failed"),
                    translate("History", "Name and email are required to save iteration"),
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
                QtWidgets.QMessageBox.critical(
                    parent,  # type: ignore[arg-type]
                    translate("History", "Save Iteration Failed"),
                    translate("History", "Git identity could not be saved"),
                )
                return False

            retry_message = translate(
                "History",
                "Could not save git identity for all projects. "
                "Uncheck the global option to save it only for this project.",
            )
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
        parent: QWidget | None = None,
        message: str | None = None,
        initial_values: GitConfigDialogResult | None = None,
        global_config_writable: bool = True,
    ) -> GitConfigDialogResult | None:
        """Show git identity configuration dialog."""
        dialog = QtWidgets.QDialog(parent)  # type: ignore[arg-type]
        dialog.setWindowTitle(translate("History", "Configure Author"))
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(
            QtWidgets.QLabel(
                translate(
                    "History",
                    "Enter the name and email you'd like to use for your git identity, "
                    "which is used for authoring project iterations.",
                ),
                dialog,
            )
        )
        if message:
            message_label = QtWidgets.QLabel(message, dialog)
            message_label.setStyleSheet("color: red;")
            layout.addWidget(message_label)
        form_layout = QtWidgets.QFormLayout()
        name_edit = QtWidgets.QLineEdit(dialog)
        email_edit = QtWidgets.QLineEdit(dialog)
        remember_checkbox = QtWidgets.QCheckBox(
            translate("History", "Configure globally for all projects"),
            dialog,
        )
        if initial_values is not None:
            name_edit.setText(initial_values.author_name)
            email_edit.setText(initial_values.author_email)
            remember_checkbox.setChecked(initial_values.should_save_globally)
        if not global_config_writable:
            remember_checkbox.setChecked(False)
            remember_checkbox.setEnabled(False)

        form_layout.addRow(translate("History", "Name:"), name_edit)
        form_layout.addRow(translate("History", "Email:"), email_edit)
        layout.addLayout(form_layout)
        layout.addWidget(remember_checkbox)
        if not global_config_writable:
            global_config_label = QtWidgets.QLabel(
                translate(
                    "History",
                    "Global configuration option disabled because global config file not writable.",
                ),
                dialog,
            )
            global_config_label.setStyleSheet("color: red;")
            layout.addWidget(global_config_label)

        button_layout = QtWidgets.QHBoxLayout()
        ok_button = QtWidgets.QPushButton(translate("History", "OK"))
        cancel_button = QtWidgets.QPushButton(translate("History", "Cancel"))
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
            "MenuText": QtCore.QT_TRANSLATE_NOOP("HistoryCommit", "Save Iteration"),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP("HistoryCommit", "Save reviewed changes as an iteration"),
            "Pixmap": os.path.join(ICONPATH, "Commit.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True  # Always enabled; validation happens in Activated()

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from .._container import get_container
        from ..ui.registry import ui_registry

        container = get_container()
        parent = _main_window_parent(container)

        # Check if we have a git repository via UIState in registry
        repo = ui_registry.ui_state.git_repository

        if repo is None:
            QtWidgets.QMessageBox.warning(
                parent,  # type: ignore[arg-type]
                translate("History", "No Project"),
                translate("History", "No project detected. Please open a document from a project."),
            )
            return

        # Check for staged files
        staged_result = container.get_staged_file_paths_action.execute(repo)
        if not staged_result.is_success or not staged_result.data:
            QtWidgets.QMessageBox.information(
                parent,  # type: ignore[arg-type]
                translate("History", "No Reviewed Files"),
                translate("History", "There are no reviewed files to save."),
            )
            return

        identity_result = container.get_git_identity_action.execute(repo)
        if identity_result.data is None and not _ConfigureAuthorCommand().configure_repository(container, repo, parent):
            return

        dialog_result = self._show_commit_dialog(parent)

        if dialog_result is None:
            return

        if not self._validate_commit_dialog_result(parent, dialog_result):
            return

        # Execute commit action
        result = container.commit_staging_action.execute(repo, dialog_result.message.strip())

        if result.is_success:
            container.log("Commit successful")
            # Reload commits by triggering refresh
            ui_registry.git_repository_presenter.refresh_repository_and_commits()
        else:
            QtWidgets.QMessageBox.critical(
                parent,  # type: ignore[arg-type]
                translate("History", "Save Iteration Failed"),
                result.message or translate("History", "Git commit failed"),
            )

    def _validate_commit_dialog_result(self, parent: QWidget | None, dialog_result: CommitDialogResult) -> bool:
        """Validate commit dialog values and show warnings for invalid input."""
        if not dialog_result.message.strip():
            QtWidgets.QMessageBox.warning(
                parent,  # type: ignore[arg-type]
                translate("History", "Empty Notes"),
                translate("History", "Iteration notes cannot be empty"),
            )
            return False
        return True

    def _show_commit_dialog(self, parent: QWidget | None) -> CommitDialogResult | None:
        """Show the commit dialog and return the message or None if cancelled.

        Args:
            parent: Parent widget for the dialog.

        Returns:
            Commit dialog result if user confirmed, None if cancelled.
        """
        dialog = QtWidgets.QDialog(parent)  # type: ignore[arg-type]
        dialog.setWindowTitle(translate("History", "Save Iteration"))

        # Enable resize grip in bottom-right corner
        dialog.setSizeGripEnabled(True)

        # Create layout with text area and buttons
        layout = QtWidgets.QVBoxLayout(dialog)

        # Add label
        label = QtWidgets.QLabel(translate("History", "Enter iteration notes:"))
        layout.addWidget(label)

        # Create a multi-line text editor that can resize vertically
        text_edit = QtWidgets.QPlainTextEdit(dialog)
        text_edit.setPlaceholderText(translate("History", "Enter iteration notes (subject and optional body)..."))
        text_edit.setTabStopDistance(40)  # Tab spacing in pixels
        text_edit.setMinimumHeight(100)  # Minimum height for initial usability
        # Allow the text edit to expand vertically when dialog is resized
        text_edit.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        layout.addWidget(text_edit)

        # Add OK and Cancel buttons
        button_layout = QtWidgets.QHBoxLayout()
        ok_button = QtWidgets.QPushButton(translate("History", "OK"))
        cancel_button = QtWidgets.QPushButton(translate("History", "Cancel"))

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
            "MenuText": QtCore.QT_TRANSLATE_NOOP("HistoryRefreshRepository", "Refresh Project"),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP(
                "HistoryRefreshRepository",
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
            "MenuText": QtCore.QT_TRANSLATE_NOOP("HistoryInitializeGitRepository", "Initialize Git Repository"),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP(
                "HistoryInitializeGitRepository",
                "Initialize a git repository in the selected directory",
            ),
            "Pixmap": os.path.join(ICONPATH, "CreateGitRepository.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from .._container import get_container
        from ..ui.registry import ui_registry

        container = get_container()
        parent = _main_window_parent(container)
        candidates_result = container.get_git_repository_init_candidates_action.execute()
        if not candidates_result.is_success:
            QtWidgets.QMessageBox.information(
                parent,  # type: ignore[arg-type]
                translate("History", "No Directories Available"),
                translate(
                    "History",
                    "No open documents are available for project initialization. "
                    "Please open at least one saved document in the root location "
                    "you'd like to initialize a new project.",
                ),
            )
            return

        selected_directory = self._show_init_dialog(parent, candidates_result.data)
        if selected_directory is None:
            return

        init_result = container.initialize_git_repository_action.execute(selected_directory)
        if not init_result.is_success:
            QtWidgets.QMessageBox.critical(
                parent,  # type: ignore[arg-type]
                translate("History", "Initialization Failed"),
                init_result.message or translate("History", "Unknown error occurred"),
            )
            return

        repository = init_result.data
        self._store_initialized_repository(repository)

        success_template = translate("History", "Initialized project: %1")
        success_message = success_template.replace("%1", repository.absolute_path)
        QtWidgets.QMessageBox.information(
            parent,  # type: ignore[arg-type]
            translate("History", "Project Initialized"),
            success_message,
        )
        ui_registry.git_repository_presenter.refresh_repository_and_commits()

    def _show_init_dialog(self, parent: QWidget | None, candidates: list[GitRepositoryInitCandidate]) -> str | None:
        """Show initialization selection dialog and return selected directory."""
        dialog = QtWidgets.QDialog(parent)  # type: ignore[arg-type]
        dialog.setWindowTitle(translate("History", "Initialize Project"))
        dialog.setSizeGripEnabled(True)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(
            QtWidgets.QLabel(
                translate(
                    "History",
                    "Choose a directory to initialize based on currently open documents. "
                    "The selected directory will be the root of your project:",
                )
            )
        )

        button_group = QtWidgets.QButtonGroup(dialog)
        first_available_button = None

        for index, candidate in enumerate(candidates):
            row_layout = QtWidgets.QHBoxLayout()
            radio = QtWidgets.QRadioButton(candidate.path, dialog)
            radio.setEnabled(candidate.is_available)
            button_group.addButton(radio, index)
            row_layout.addWidget(radio)
            if candidate.is_available and first_available_button is None:
                first_available_button = radio

            if not candidate.is_available:
                reason_label = QtWidgets.QLabel(
                    translate("History", "Already inside project"),
                    dialog,
                )
                reason_label.setEnabled(False)
                row_layout.addWidget(reason_label)

            row_layout.addStretch()
            layout.addLayout(row_layout)

        if first_available_button is not None:
            first_available_button.setChecked(True)
        else:
            no_available_text = translate("History", "All listed directories are already inside projects.")
            layout.addWidget(QtWidgets.QLabel(no_available_text))

        button_layout = QtWidgets.QHBoxLayout()
        initialize_button = QtWidgets.QPushButton(translate("History", "Initialize"))
        initialize_button.setEnabled(first_available_button is not None)
        cancel_button = QtWidgets.QPushButton(translate("History", "Cancel"))
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
            "MenuText": QtCore.QT_TRANSLATE_NOOP(
                "HistoryOpenAllDocumentsInRepository",
                "Open All Documents in Project",
            ),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP(
                "HistoryOpenAllDocumentsInRepository",
                "Open every .FCStd file found in the project. Useful for generating en masse.",
            ),
            "Pixmap": os.path.join(ICONPATH, "OpenAllDocuments.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from .._container import get_container
        from ..ui.registry import ui_registry

        container = get_container()
        parent = _main_window_parent(container)
        repo = ui_registry.ui_state.git_repository

        if repo is None:
            QtWidgets.QMessageBox.warning(
                parent,  # type: ignore[arg-type]
                translate("History", "No Project"),
                translate("History", "No project detected. Open a FreeCAD document in a project first."),
            )
            return

        container.open_all_documents_in_repository_action.execute(repo)


class _RecomputeAllOpenDocumentsCommand:
    """Command to recompute all open documents in FreeCAD."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QtCore.QT_TRANSLATE_NOOP("HistoryRecomputeAllOpenDocuments", "Recompute All"),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP("HistoryRecomputeAllOpenDocuments", "Recompute every open document"),
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
            "MenuText": QtCore.QT_TRANSLATE_NOOP("HistoryRecomputeActiveDocument", "Recompute Active Document"),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP("HistoryRecomputeActiveDocument", "Recompute the active document"),
            "Pixmap": os.path.join(ICONPATH, "RecomputeActiveDocument.svg"),
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
            "MenuText": QtCore.QT_TRANSLATE_NOOP("HistoryOpenDiffWindow", "Open History Panel"),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP("HistoryOpenDiffWindow", "Open history panel view"),
            "Pixmap": os.path.join(ICONPATH, "Logo.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        import FreeCADGui as Gui  # pylint: disable=import-error

        # Get the History workbench instance and show/create the diff panel
        workbench = Gui.getWorkbench("HistoryWorkbench")
        if workbench is not None:
            workbench.create_or_show_diff_panel()


class _CloseDiffWindowsCommand:
    """Command to close all Diff_* windows without saving."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QtCore.QT_TRANSLATE_NOOP("HistoryCloseDiffWindows", "Close Comparison Windows"),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP(
                "HistoryCloseDiffWindows",
                "Close every document starting with 'Diff_' without saving",
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
        docs_to_close = [doc_name for doc_name in App.listDocuments() if doc_name.startswith("Diff_")]

        # Close each document without saving
        for doc_name in docs_to_close:
            App.closeDocument(doc_name)


def register_commands() -> None:
    """Register the Diff Workbench commands with FreeCAD."""
    import FreeCADGui as Gui  # pylint: disable=import-error

    Gui.addCommand("HistoryConfigureAuthorCommand", _ConfigureAuthorCommand())
    Gui.addCommand("HistoryCommit", _CommitCommand())
    Gui.addCommand("HistoryRefreshRepository", _RefreshRepositoryCommand())
    Gui.addCommand("HistoryInitializeGitRepository", _InitializeGitRepositoryCommand())
    Gui.addCommand("HistoryOpenAllDocumentsInRepository", _OpenAllDocumentsInRepositoryCommand())
    Gui.addCommand("HistoryRecomputeAllOpenDocuments", _RecomputeAllOpenDocumentsCommand())
    Gui.addCommand("HistoryRecomputeActiveDocument", _RecomputeActiveDocumentCommand())
    Gui.addCommand("HistoryOpenDiffWindow", _OpenDiffWindowCommand())
    Gui.addCommand("HistoryCloseDiffWindows", _CloseDiffWindowsCommand())
