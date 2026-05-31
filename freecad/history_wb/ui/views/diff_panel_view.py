"""File responsibility: History panel view with 3-column layout, implementing DiffView protocol."""

from collections.abc import Callable

from ...domain.git.models import GitCommit, GitRepository
from ...domain.settings import SettingsRepository
from ...qt import QtCore, QtWidgets
from ...utils import translate
from ..presenters.presentation_models import (
    DiffTreePresentation,
    NodePresentation,
    PropertyPresentation,
)
from .document_diff_tree_widget import DocumentDiffTreeWidget
from .history_panel_widget import HistoryPanelWidget
from .models import GitConfigDialogResult, HistorySelection
from .property_diff_tree_widget import PropertyDiffTreeWidget


__all__ = ["DiffPanelView", "HistorySelection"]


class DiffPanelView(QtWidgets.QWidget):
    """3-column diff panel view implementing DiffView protocol.

    Provides a horizontal QSplitter with:
    - Left: HistoryPanelWidget for repository info and history list
    - Middle: DocumentDiffTreeWidget for document diffs and staging
    - Right: PropertyDiffTreeWidget for property diffs

    Protocol Implementation:
        This class implements the DiffView protocol through
        structural subtyping (duck typing) rather than explicit inheritance to avoid
        metaclass conflicts between QWidget and Protocol classes.

        Implemented protocols:
        - DiffView (freecad.history_wb.ui.protocols.diff_view): show_doc_diff,
          show_summary, show_property_diff, show_repository

    """

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        QtWidgets.QWidget.__init__(self, parent)
        self._settings_repo = settings_repo
        self._current_selection: HistorySelection | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the 3-column layout with child widgets."""
        layout = QtWidgets.QVBoxLayout(self)

        # Create horizontal splitter
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        # Column 1: History panel widget
        self._history_panel = HistoryPanelWidget(self)
        self._history_panel.set_selection_changed_callback(self._on_history_panel_selection_changed)

        # Column 2: Document diff tree widget
        self._document_diff_tree = DocumentDiffTreeWidget(self)

        # Column 3: Property diff tree widget
        self._property_diff_tree = PropertyDiffTreeWidget(self, settings_repo=self._settings_repo)

        # Add to splitter
        splitter.addWidget(self._history_panel)
        splitter.addWidget(self._document_diff_tree)
        splitter.addWidget(self._property_diff_tree)

        # Set initial sizes: narrower history, narrower document diff, wider property table
        splitter.setSizes([150, 150, 400])

        # Set minimum size for the panel
        self.setMinimumSize(450, 200)

        layout.addWidget(splitter)

    def _on_history_panel_selection_changed(self, selection: HistorySelection | None) -> None:
        """Handle history panel selection changes to update document widget state."""
        self._current_selection = selection
        self._document_diff_tree.set_current_history_selection(selection)

    def show_commits(self, commits: list[GitCommit], show_special_items: bool = True) -> None:
        """Display git commits in the history list.

        Delegates to HistoryPanelWidget.

        Args:
            commits: List of GitCommit objects to display. Commits are shown
                in DESC order (newest first) with 7-char hash, author, timestamp
                on line 1, and first line of message on line 2. Full commit
                message is shown in tooltip.
            show_special_items: Whether to include top "Current Files" and
                "Reviewed" rows before commit rows.
        """
        self._history_panel.show_commits(commits, show_special_items=show_special_items)

    def append_commits(self, commits: list[GitCommit]) -> None:
        """Append commit entries after existing history rows.

        Delegates to HistoryPanelWidget.

        Args:
            commits: List of GitCommit objects to append.
        """
        self._history_panel.append_commits(commits)

    def set_force_diff_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to invoke when force diff button is clicked.

        Delegates to DocumentDiffTreeWidget.

        Args:
            callback: A no-argument callable to invoke on force diff.
        """
        self._document_diff_tree.set_force_diff_callback(callback)

    def set_force_diff_button_visible(self, visible: bool) -> None:
        """Show or hide the force diff button.

        Delegates to DocumentDiffTreeWidget.

        Args:
            visible: Whether the force diff button should be visible.
        """
        self._document_diff_tree.set_force_diff_button_visible(visible)

    def set_refresh_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to invoke when refresh button is clicked.

        Delegates to HistoryPanelWidget.

        Args:
            callback: A no-argument callable to invoke on refresh.
        """
        self._history_panel.set_refresh_callback(callback)

    def set_save_iteration_callback(self, callback: Callable[[], None]) -> None:
        """Set callback fired by Save Iteration panel button."""
        self._history_panel.set_save_iteration_callback(callback)

    def set_history_selection_callback(self, callback: Callable[[HistorySelection], None]) -> None:
        """Set the callback for history list selection.

        Delegates to HistoryPanelWidget.

        Args:
            callback: A callable that receives HistorySelection with item_kind and commit_hash
        """
        self._history_panel.set_history_selection_callback(callback)

    def set_history_scroll_bottom_callback(self, callback: Callable[[], None]) -> None:
        """Set callback invoked when history list is near scroll bottom.

        Delegates to HistoryPanelWidget.
        """
        self._history_panel.set_history_scroll_bottom_callback(callback)

    def get_current_history_selection(self) -> HistorySelection | None:
        """Return currently selected history entry.

        Delegates to HistoryPanelWidget.
        """
        return self._history_panel.get_current_history_selection()

    def show_repository(self, repo: GitRepository | None) -> None:
        """Display git repository info above snapshot list.

        Delegates to HistoryPanelWidget.

        Args:
            repo: GitRepository object if detected, or None if no repository found.
                  If None, shows "No git repository detected".
        """
        self._history_panel.show_repository(repo)

    def set_add_button_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback for when the '+ Reviewed' button is clicked.

        Delegates to DocumentDiffTreeWidget.

        Args:
            callback: A callable that receives the git_path (str) of the
                      document whose '+ Reviewed' button was clicked.
        """
        self._document_diff_tree.set_add_button_callback(callback)

    def set_remove_from_reviewed_button_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for per-file Remove button in Reviewed view."""
        self._document_diff_tree.set_remove_from_reviewed_button_callback(callback)

    def set_remove_all_from_reviewed_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for Reviewed context action Remove All from Reviewed."""
        self._history_panel.set_remove_all_from_reviewed_callback(callback)

    def set_mark_all_reviewed_from_in_progress_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for Current Files context action Mark All Reviewed."""
        self._history_panel.set_mark_all_reviewed_from_in_progress_callback(callback)

    def set_restore_all_from_history_context_callback(self, callback: Callable[[HistorySelection], None]) -> None:
        """Set callback for restore actions from history context menu."""
        self._history_panel.set_restore_all_from_history_context_callback(callback)

    def set_stage_all_button_visible(self, visible: bool) -> None:
        """Show or hide the Mark All Reviewed button.

        Delegates to DocumentDiffTreeWidget.

        Args:
            visible: Whether the button should be visible.
        """
        self._document_diff_tree.set_stage_all_button_visible(visible)

    def set_stage_all_button_enabled(self, enabled: bool) -> None:
        """Enable or disable the Mark All Reviewed button.

        Delegates to DocumentDiffTreeWidget.

        Args:
            enabled: Whether the button should be enabled.
        """
        self._document_diff_tree.set_stage_all_button_enabled(enabled)

    def set_stage_all_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback for Mark All Reviewed button.

        Delegates to DocumentDiffTreeWidget.

        Args:
            callback: A no-argument callable to invoke on click.
        """
        self._document_diff_tree.set_stage_all_callback(callback)

    def set_remove_all_button_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for summary-bar Remove All button."""
        self._document_diff_tree.set_remove_all_button_callback(callback)

    def set_remove_all_button_visible(self, visible: bool) -> None:
        """Show or hide summary-bar Remove All button."""
        self._document_diff_tree.set_remove_all_button_visible(visible)

    def set_remove_all_button_enabled(self, enabled: bool) -> None:
        """Enable or disable summary-bar Remove All button."""
        self._document_diff_tree.set_remove_all_button_enabled(enabled)

    def set_restore_button_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for per-file restore action."""
        self._document_diff_tree.set_restore_button_callback(callback)

    def set_restore_all_button_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for summary-bar restore-all action."""
        self._document_diff_tree.set_restore_all_button_callback(callback)

    def set_restore_all_button_visible(self, visible: bool) -> None:
        """Show or hide summary-bar restore-all button."""
        self._document_diff_tree.set_restore_all_button_visible(visible)

    def set_restore_all_button_enabled(self, enabled: bool) -> None:
        """Enable or disable summary-bar restore-all button."""
        self._document_diff_tree.set_restore_all_button_enabled(enabled)

    def set_node_selection_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for node selection with (git_path, node_path).

        Delegates to DocumentDiffTreeWidget.

        Args:
            callback: A callable receiving (git_path, node_path) when a node is clicked.
        """
        self._document_diff_tree.set_node_selection_callback(callback)

    def set_visual_diff_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for visual diff click with (git_path, node_path)."""
        self._document_diff_tree.set_visual_diff_callback(callback)

    def set_open_document_for_comparison_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for open-document indicator click with git_path."""
        self._document_diff_tree.set_open_document_for_comparison_callback(callback)

    def focus_window(self) -> None:
        """Bring the top-level history panel window to foreground."""
        window = self.window()
        window.show()
        window.raise_()
        window.activateWindow()
        window.setFocus()

    # DiffView protocol methods
    def show_doc_diff(self, nodes: list[NodePresentation], git_path: str = "") -> None:
        """Display the diff tree with color-coded nodes.

        Delegates to DocumentDiffTreeWidget.

        Args:
            nodes: List of root-level NodePresentation objects with nested children.
            git_path: The git path to display as top-level item
        """
        self._document_diff_tree.set_current_history_selection(self._current_selection)
        self._document_diff_tree.show_doc_diff(nodes, git_path)

    def show_doc_diffs(self, diffs: list[DiffTreePresentation]) -> None:
        """Display multiple diff trees in the tree widget.

        Delegates to DocumentDiffTreeWidget.

        Args:
            diffs: List of DiffTreePresentation objects, each representing
                  a diff tree for one document with its metadata.
        """
        self._document_diff_tree.set_current_history_selection(self._current_selection)
        self._document_diff_tree.show_doc_diffs(diffs)

    def clear_property_diff(self) -> None:
        """Clear property diff panel content."""
        self._property_diff_tree.clear_property_diff()

    def clear_doc_diffs(self) -> None:
        """Clear document diff tree and related controls.

        Also clears property diff panel to avoid stale node/property pairing.
        """
        self._document_diff_tree.clear_doc_diffs()
        self.clear_property_diff()

    def show_summary(self, modified_docs: int, deleted_docs: int, added_docs: int) -> None:
        """Display per-status document counts.

        Delegates to DocumentDiffTreeWidget.

        Args:
            modified_docs: Number of modified documents.
            deleted_docs: Number of deleted documents.
            added_docs: Number of added documents.
        """
        self._document_diff_tree.show_summary(modified_docs, deleted_docs, added_docs)

    def show_property_diff(self, properties: list[PropertyPresentation]) -> None:
        """Display property diffs in the properties tree widget.

        Delegates to the child PropertyDiffTreeWidget.

        Args:
            properties: List of PropertyPresentation objects to display.
        """
        self._property_diff_tree.show_property_diff(properties)

    def collapse_tree_item(self, git_path: str) -> None:
        """Collapse the root tree item for the given git_path.

        Delegates to DocumentDiffTreeWidget.

        Args:
            git_path: The git_path of the root tree item to collapse.
        """
        self._document_diff_tree.collapse_tree_item(git_path)

    def set_stage_button_enabled(self, git_path: str, enabled: bool) -> None:
        """Enable or disable the '+ Reviewed' button for a given git_path.

        Delegates to DocumentDiffTreeWidget.

        Args:
            git_path: The git_path of the document whose button to update.
            enabled: Whether the reviewed button should be enabled.
        """
        self._document_diff_tree.set_stage_button_enabled(git_path, enabled)

    def show_warning_message(self, title: str, message: str) -> None:
        """Show warning dialog."""
        QtWidgets.QMessageBox.warning(self, title, message)

    def show_info_message(self, title: str, message: str) -> None:
        """Show informational dialog."""
        QtWidgets.QMessageBox.information(self, title, message)

    def show_error_message(self, title: str, message: str) -> None:
        """Show error dialog."""
        QtWidgets.QMessageBox.critical(self, title, message)

    def show_save_iteration_dialog(self) -> str | None:
        """Show Save Iteration dialog and return notes when accepted."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(translate("History", "Save Iteration"))
        dialog.setSizeGripEnabled(True)

        layout = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel(translate("History", "Enter iteration notes:"))
        layout.addWidget(label)

        text_edit = QtWidgets.QPlainTextEdit(dialog)
        text_edit.setPlaceholderText(translate("History", "Enter iteration notes (subject and optional body)..."))
        text_edit.setTabStopDistance(40)
        text_edit.setMinimumHeight(100)
        text_edit.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        layout.addWidget(text_edit)

        button_layout = QtWidgets.QHBoxLayout()
        ok_button = QtWidgets.QPushButton(translate("History", "OK"))
        cancel_button = QtWidgets.QPushButton(translate("History", "Cancel"))
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.resize(500, 300)
        accepted = dialog.exec() == 1
        if not accepted:
            return None
        return text_edit.toPlainText()

    def show_configure_author_dialog(
        self,
        *,
        message: str | None = None,
        initial_values: GitConfigDialogResult | None = None,
        global_config_writable: bool = True,
    ) -> GitConfigDialogResult | None:
        """Show configure-author dialog and return entered values."""
        dialog = QtWidgets.QDialog(self)
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

        ok = dialog.exec() == 1
        if not ok:
            return None
        return GitConfigDialogResult(
            author_name=name_edit.text().strip(),
            author_email=email_edit.text().strip(),
            should_save_globally=remember_checkbox.isChecked(),
        )

    def show_restore_file_confirmation_dialog(self, _git_path: str) -> bool:
        """Show destructive confirmation dialog for file restore."""
        title = translate("History", "Restore")
        message = translate(
            "History",
            "This operation will overwrite the current files on disk with the selected saved copies.\n\nOpen FreeCAD "
            "documents will be closed and reopened to ensure links are updated.\n\n"
            "Unsaved in-memory changes in open files will be lost.\n\nSaved history is not affected.",
        )
        restore_button_text = translate("History", "Restore")
        cancel_button_text = translate("History", "Cancel")
        dialog = QtWidgets.QMessageBox(self)
        dialog.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        restore_button = dialog.addButton(restore_button_text, QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
        dialog.addButton(cancel_button_text, QtWidgets.QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Cancel)
        dialog.exec()
        return dialog.clickedButton() == restore_button

    def show_restore_scope_dialog(self) -> str | None:
        """Show bulk scope picker for restore-all action."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(translate("History", "Restore All"))
        dialog.setMinimumWidth(620)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setSpacing(10)
        title_label = QtWidgets.QLabel(translate("History", "Which files would you like to restore?"))
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        listed = QtWidgets.QRadioButton(translate("History", "Listed FreeCAD files"))
        listed_desc = QtWidgets.QLabel(
            translate(
                "History",
                "Restore only the FreeCAD files changed in the selected iteration. "
                "Other files on disk are left unchanged.",
            )
        )
        listed_desc.setWordWrap(True)
        all_fcstd = QtWidgets.QRadioButton(translate("History", "All FreeCAD files"))
        all_desc = QtWidgets.QLabel(
            translate(
                "History",
                "Restore all previously saved FreeCAD files to how they were in this iteration. "
                "Any previously saved FreeCAD files that did not exist in this iteration are removed. "
                "New files not yet saved to history are kept.",
            )
        )
        all_desc.setWordWrap(True)
        listed_desc.setIndent(22)
        all_desc.setIndent(22)
        scope_group = QtWidgets.QButtonGroup(dialog)
        scope_group.setExclusive(True)
        scope_group.addButton(listed)
        scope_group.addButton(all_fcstd)
        listed.setChecked(True)

        listed_group = QtWidgets.QWidget(dialog)
        listed_group_layout = QtWidgets.QVBoxLayout(listed_group)
        listed_group_layout.setContentsMargins(0, 0, 0, 0)
        listed_group_layout.setSpacing(2)
        listed_group_layout.addWidget(listed)
        listed_group_layout.addWidget(listed_desc)

        all_group = QtWidgets.QWidget(dialog)
        all_group_layout = QtWidgets.QVBoxLayout(all_group)
        all_group_layout.setContentsMargins(0, 0, 0, 0)
        all_group_layout.setSpacing(2)
        all_group_layout.addWidget(all_fcstd)
        all_group_layout.addWidget(all_desc)

        layout.addWidget(listed_group)
        layout.addWidget(all_group)
        buttons = QtWidgets.QDialogButtonBox(self)
        restore_button = buttons.addButton(
            translate("History", "Restore"),
            QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole,
        )
        cancel_button = buttons.addButton(
            translate("History", "Cancel"),
            QtWidgets.QDialogButtonBox.ButtonRole.RejectRole,
        )
        cancel_button.setDefault(True)
        cancel_button.setAutoDefault(True)
        restore_button.clicked.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.resize(700, dialog.sizeHint().height())
        if dialog.exec() != 1:
            return None
        return "listed_fcstd" if listed.isChecked() else "all_fcstd"
