# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: FreeCAD command entry points for the Diff Workbench.

This module defines the FreeCAD commands that bridge user interactions
(toolbar/menu clicks) with application layer actions and UI presenters.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, TypedDict

from ..qt import QtCore, QtWidgets
from ..resources import ICONPATH
from ..utils import translate


if TYPE_CHECKING:
    QWidget = QtWidgets.QWidget

    from ..application.di.container import ApplicationContainer
    from ..domain.git.models import GitRepositoryInitCandidate
    from ..ui.presenters.git_repository_presenter import GitRepositoryPresenter


def _main_window_parent(container) -> QWidget | None:
    """Get the FreeCAD main window as a parent widget for dialogs.

    Args:
        container: The application container with _freecad_port attribute

    Returns:
        QWidget parent or None if not available
    """
    main_window = container._freecad_port.get_main_window()
    return main_window  # type: ignore[return-value]


def _ensure_git_repository_presenter_available(container: ApplicationContainer) -> GitRepositoryPresenter | None:
    """Return git repository presenter, composing UI panel first when needed."""
    from ..ui.registry import ui_registry

    try:
        return ui_registry.git_repository_presenter
    except RuntimeError:
        pass

    try:
        import FreeCADGui as Gui  # pylint: disable=import-error
    except ImportError:
        return None

    workbench = Gui.getWorkbench("HistoryWorkbench")
    if workbench is None:
        return None

    workbench.create_or_show_diff_panel()
    try:
        return ui_registry.git_repository_presenter
    except RuntimeError:
        return None


class CommandResources(TypedDict):
    """Shape of FreeCAD command metadata returned by GetResources."""

    MenuText: object
    ToolTip: object
    Pixmap: str


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

        container = get_container()
        presenter = _ensure_git_repository_presenter_available(container)
        if presenter is None:
            QtWidgets.QMessageBox.warning(
                _main_window_parent(container),  # type: ignore[arg-type]
                translate("History", "History Panel Unavailable"),
                translate("History", "Open History Panel before configuring author."),
            )
            return
        presenter.on_configure_author_requested()


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

        container = get_container()
        presenter = _ensure_git_repository_presenter_available(container)
        if presenter is None:
            QtWidgets.QMessageBox.warning(
                _main_window_parent(container),  # type: ignore[arg-type]
                translate("History", "History Panel Unavailable"),
                translate("History", "Open History Panel before saving an iteration."),
            )
            return

        presenter.on_save_iteration_requested()


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


class _UpdateGitIgnoreCommand:
    """Command to edit repository .gitignore content."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QtCore.QT_TRANSLATE_NOOP("HistoryUpdateGitIgnore", "Edit Ignored Files"),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP(
                "HistoryUpdateGitIgnore",
                "Edit project ignored files list (.gitignore)",
            ),
            "Pixmap": os.path.join(ICONPATH, "GitIgnore.svg"),
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

        content_result = container.get_gitignore_content_action.execute(repo)
        if not content_result.is_success:
            QtWidgets.QMessageBox.critical(
                parent,  # type: ignore[arg-type]
                translate("History", "Failed to Read Ignored Files"),
                content_result.message or translate("History", "Unknown error occurred"),
            )
            return

        dialog = QtWidgets.QDialog(parent)  # type: ignore[arg-type]
        dialog.setWindowTitle(translate("History", "Edit Ignored Files"))
        dialog.setMinimumWidth(680)
        dialog.setMinimumHeight(460)

        layout = QtWidgets.QVBoxLayout(dialog)
        help_template = translate(
            "History",
            'Update the ignored files list. Lines starting with a "#" are considered comments. '
            'Click <a href="%1">here</a> to learn about the full syntax.',
        )
        help_label = QtWidgets.QLabel(
            help_template.replace("%1", "https://www.w3schools.com/git/git_ignore.asp")
        )
        help_label.setOpenExternalLinks(True)
        layout.addWidget(help_label)

        text_edit = QtWidgets.QPlainTextEdit(dialog)
        text_edit.setPlainText(str(content_result.data))
        layout.addWidget(text_edit)

        button_box = QtWidgets.QDialogButtonBox(dialog)
        save_button = button_box.addButton(
            translate("History", "Save"),
            QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole,
        )
        cancel_button = button_box.addButton(
            translate("History", "Cancel"),
            QtWidgets.QDialogButtonBox.ButtonRole.RejectRole,
        )
        save_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() != 1:
            return

        save_result = container.update_gitignore_action.execute(repo, text_edit.toPlainText())
        if not save_result.is_success:
            QtWidgets.QMessageBox.critical(
                parent,  # type: ignore[arg-type]
                translate("History", "Failed to Save Ignored Files"),
                save_result.message or translate("History", "Unknown error occurred"),
            )
            return

        QtWidgets.QMessageBox.information(
            parent,  # type: ignore[arg-type]
            translate("History", "Ignored Files Updated"),
            translate("History", "Updated ignored files list."),
        )


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
    Gui.addCommand("HistoryUpdateGitIgnore", _UpdateGitIgnoreCommand())
    Gui.addCommand("HistoryOpenAllDocumentsInRepository", _OpenAllDocumentsInRepositoryCommand())
    Gui.addCommand("HistoryRecomputeAllOpenDocuments", _RecomputeAllOpenDocumentsCommand())
    Gui.addCommand("HistoryRecomputeActiveDocument", _RecomputeActiveDocumentCommand())
    Gui.addCommand("HistoryOpenDiffWindow", _OpenDiffWindowCommand())
    Gui.addCommand("HistoryCloseDiffWindows", _CloseDiffWindowsCommand())
