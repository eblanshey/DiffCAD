"""File responsibility: Document diff tree widget with summary and staging controls."""

from collections.abc import Callable

from ...domain.diff.models import DiffState
from ...qt import QtCore, QtGui, QtWidgets
from ...resources import get_icon_path
from ...utils import translate
from ..presenters.presentation_models import DiffTreePresentation, DocumentStatusIndicator, NodePresentation
from .diff_theme import DIFF_STATE_ROLE, DiffItemDelegate, background_for_state, foreground_for_background
from .models import HistorySelection


__all__ = ["DocumentDiffTreeWidget"]


# Tree rows use a 22px control box so text-only and icon rows stay the same height.
TREE_ITEM_HEIGHT = 22
# Icon stays 16px inside that 22px box, leaving 3px visual padding on each side.
TREE_ITEM_ICON_SIZE = 16
STAGE_BUTTON_WIDTH = 90
STAGE_ALL_BUTTON_WIDTH = 140
REMOVE_BUTTON_WIDTH = 90
REMOVE_REVIEWED_TOOLTIP = translate(
    "History",
    "Remove document(s) from Reviewed. The current file(s) stay unchanged "
    "and will not be saved in the next iteration until reviewed again.",
)


class DocumentDiffTreeWidget(QtWidgets.QWidget):
    """Middle-column widget that renders document/node diffs and staging actions."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_add_button_callback: Callable[[str], None] | None = None
        self._on_stage_all_callback: Callable[[], None] | None = None
        self._on_remove_all_callback: Callable[[], None] | None = None
        self._on_remove_from_reviewed_button_callback: Callable[[str], None] | None = None
        self._on_node_selection_callback: Callable[[str, str], None] | None = None
        self._current_selection: HistorySelection | None = None
        self._on_visual_diff_callback: Callable[[str, str], None] | None = None
        self._stage_buttons: dict[str, QtWidgets.QToolButton] = {}
        self._remove_from_reviewed_buttons: dict[str, QtWidgets.QToolButton] = {}
        self._diff_item_delegate: DiffItemDelegate | None = None
        self._setup_ui()

    @property
    def tree_widget(self) -> QtWidgets.QTreeWidget:
        """Expose underlying tree for facade compatibility and focused tests."""
        return self._tree_widget

    def _setup_ui(self) -> None:
        summary_container = QtWidgets.QWidget(self)
        summary_layout = QtWidgets.QHBoxLayout(summary_container)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(16)

        self._changed_label = QtWidgets.QLabel("")
        self._changed_label.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self._changed_label)

        self._stage_all_button = QtWidgets.QToolButton()
        self._stage_all_button.setText(translate("History", "+ Mark All Reviewed"))
        self._stage_all_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._stage_all_button.setFixedSize(STAGE_ALL_BUTTON_WIDTH, TREE_ITEM_HEIGHT)
        self._stage_all_button.hide()
        self._stage_all_button.clicked.connect(self._on_stage_all_clicked)
        summary_layout.addWidget(self._stage_all_button)

        self._remove_all_button = QtWidgets.QToolButton()
        self._remove_all_button.setText(translate("History", "- Remove All"))
        self._remove_all_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._remove_all_button.setFixedSize(STAGE_ALL_BUTTON_WIDTH, TREE_ITEM_HEIGHT)
        self._remove_all_button.setToolTip(REMOVE_REVIEWED_TOOLTIP)
        self._remove_all_button.hide()
        self._remove_all_button.clicked.connect(self._on_remove_all_clicked)
        summary_layout.addWidget(self._remove_all_button)

        self._tree_widget = QtWidgets.QTreeWidget()
        self._tree_widget.setHeaderLabels([translate("History", "Tree")])
        self._tree_widget.setColumnCount(1)
        self._tree_widget.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._diff_item_delegate = DiffItemDelegate(self._tree_widget)
        self._tree_widget.setItemDelegate(self._diff_item_delegate)
        self._tree_widget.itemClicked.connect(self._on_tree_item_clicked)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(summary_container)
        layout.addWidget(self._tree_widget)

    def set_current_history_selection(self, selection: HistorySelection | None) -> None:
        """Set current history selection for conditional Current Files controls."""
        self._current_selection = selection

    def set_node_selection_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for node selection with (git_path, node_path).

        Args:
            callback: A callable receiving (git_path, node_path) when a node is clicked.
        """
        self._on_node_selection_callback = callback

    def set_visual_diff_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for visual diff click with (git_path, node_path)."""
        self._on_visual_diff_callback = callback

    def set_add_button_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback for when the '+ Reviewed' button is clicked.

        Args:
            callback: A callable that receives the git_path (str) of the
                      document whose '+ Reviewed' button was clicked.
        """
        self._on_add_button_callback = callback

    def set_stage_all_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback for Mark All Reviewed button.

        Args:
            callback: A no-argument callable to invoke on click.
        """
        self._on_stage_all_callback = callback

    def set_remove_from_reviewed_button_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for Remove button in Reviewed selection."""
        self._on_remove_from_reviewed_button_callback = callback

    def set_stage_all_button_visible(self, visible: bool) -> None:
        """Show or hide the Mark All Reviewed button.

        Args:
            visible: Whether the button should be visible.
        """
        self._stage_all_button.setVisible(visible)

    def set_stage_all_button_enabled(self, enabled: bool) -> None:
        """Enable or disable the Mark All Reviewed button.

        Args:
            enabled: Whether the button should be enabled.
        """
        self._stage_all_button.setEnabled(enabled)

    def set_remove_all_button_visible(self, visible: bool) -> None:
        """Show or hide Remove All button for Reviewed selection."""
        self._remove_all_button.setVisible(visible)

    def set_remove_all_button_enabled(self, enabled: bool) -> None:
        """Enable or disable Remove All button for Reviewed selection."""
        self._remove_all_button.setEnabled(enabled)

    def set_remove_all_button_callback(self, callback: Callable[[], None]) -> None:
        """Set callback used by summary-bar Remove All button."""
        self._on_remove_all_callback = callback

    def show_doc_diff(self, nodes: list[NodePresentation], git_path: str = "") -> None:
        """Display the diff tree with color-coded nodes.

        Args:
            nodes: List of root-level NodePresentation objects with nested children.
            git_path: The git path to display as top-level item
        """
        self._tree_widget.clear()

        if not nodes:
            return

        top_level_text = git_path or translate("History", "Unnamed Document")
        root_item = QtWidgets.QTreeWidgetItem([top_level_text])
        root_item.setSizeHint(0, QtCore.QSize(0, TREE_ITEM_HEIGHT))
        root_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, git_path or top_level_text)

        for node in nodes:
            self._add_tree_item(root_item, node, git_path)

        self._tree_widget.addTopLevelItem(root_item)
        self._expand_nodes_with_changes(root_item)
        self._tree_widget.show()

    def show_doc_diffs(self, diffs: list[DiffTreePresentation]) -> None:
        """Display multiple diff trees in the tree widget.

        Args:
            diffs: List of DiffTreePresentation objects, each representing
                  a diff tree for one document with its metadata.
        """
        self._tree_widget.clear()
        self._stage_buttons.clear()
        self._remove_from_reviewed_buttons.clear()

        if not diffs:
            return

        for diff in diffs:
            top_level_text = diff.git_path or translate("History", "Unnamed Document")

            root_item = QtWidgets.QTreeWidgetItem([top_level_text])
            root_item.setSizeHint(0, QtCore.QSize(0, TREE_ITEM_HEIGHT))
            root_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, diff.git_path or top_level_text)
            container = self._create_doc_row_widget(diff, top_level_text)

            self._tree_widget.addTopLevelItem(root_item)
            self._tree_widget.setItemWidget(root_item, 0, container)

            for node in diff.nodes:
                self._add_tree_item(root_item, node, diff.git_path)

            self._expand_nodes_with_changes(root_item)

        self._tree_widget.show()

    def _create_doc_row_widget(self, diff: DiffTreePresentation, top_level_text: str) -> QtWidgets.QWidget:
        """Create top-level row widget for one document diff."""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)

        layout.addWidget(QtWidgets.QLabel(top_level_text))
        layout.addStretch()

        self._add_status_indicators(layout, diff.indicators)
        if self._is_working_tree_selected():
            self._add_stage_button(layout, diff)
        if self._is_staging_selected():
            self._add_remove_from_reviewed_button(layout, diff)
        return container

    def _is_working_tree_selected(self) -> bool:
        """Return True when Current Files history row selected."""
        return self._current_selection is not None and self._current_selection.item_kind == "WORKING_TREE"

    def _is_staging_selected(self) -> bool:
        """Return True when Reviewed history row selected."""
        return self._current_selection is not None and self._current_selection.item_kind == "STAGING"

    def _add_stage_button(self, layout: QtWidgets.QHBoxLayout, diff: DiffTreePresentation) -> None:
        """Add + Reviewed button for one document row."""
        add_button = QtWidgets.QToolButton()
        add_button.setText(translate("History", "+ Reviewed"))
        add_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
        add_button.setEnabled(diff.stage_button_enabled)
        add_button.setFixedSize(STAGE_BUTTON_WIDTH, TREE_ITEM_HEIGHT)
        add_button.clicked.connect(lambda checked, gp=diff.git_path: self._on_add_button_clicked(gp))
        layout.addWidget(add_button)
        if diff.git_path:
            self._stage_buttons[diff.git_path] = add_button

    def _add_remove_from_reviewed_button(self, layout: QtWidgets.QHBoxLayout, diff: DiffTreePresentation) -> None:
        """Add Remove button for one reviewed document row."""
        remove_button = QtWidgets.QToolButton()
        remove_button.setText(translate("History", "- Remove"))
        remove_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
        remove_button.setFixedSize(REMOVE_BUTTON_WIDTH, TREE_ITEM_HEIGHT)
        remove_button.setToolTip(REMOVE_REVIEWED_TOOLTIP)
        remove_button.clicked.connect(
            lambda checked, gp=diff.git_path: self._on_remove_from_reviewed_button_clicked(gp)
        )
        layout.addWidget(remove_button)
        if diff.git_path:
            self._remove_from_reviewed_buttons[diff.git_path] = remove_button

    def clear_doc_diffs(self) -> None:
        """Clear document diff tree and related controls."""
        self._tree_widget.clear()
        self._changed_label.setText(translate("History", "No changes"))
        self.set_stage_all_button_visible(False)
        self.set_stage_all_button_enabled(False)
        self.set_remove_all_button_visible(False)
        self.set_remove_all_button_enabled(False)
        self._stage_buttons.clear()
        self._remove_from_reviewed_buttons.clear()

    def _add_status_indicators(
        self,
        layout: QtWidgets.QHBoxLayout,
        indicators: list[DocumentStatusIndicator],
    ) -> None:
        """Add status indicators with tooltip to the layout.

        Args:
            layout: The QHBoxLayout to add widgets to.
            indicators: List of document status indicators to display.
        """
        if not indicators:
            return

        for indicator in indicators:
            icon_label = QtWidgets.QLabel()
            icon_label.setPixmap(indicator.icon.pixmap(16, 16))
            icon_label.setToolTip(translate("History", indicator.tooltip))
            layout.addWidget(icon_label)

    def _on_add_button_clicked(self, git_path: str) -> None:
        """Handle '+ Reviewed' button click by invoking the callback.

        Args:
            git_path: The git_path of the document whose button was clicked.
        """
        if self._on_add_button_callback:
            self._on_add_button_callback(git_path)

    def _expand_nodes_with_changes(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Recursively expand nodes that have descendants with changes.

        Args:
            item: The tree item to check and expand if needed
        """
        child_count = item.childCount()
        has_changed_descendants = False

        for i in range(child_count):
            child = item.child(i)
            has_changes = child.data(0, QtCore.Qt.ItemDataRole.UserRole + 1)
            if has_changes:
                has_changed_descendants = True
            self._expand_nodes_with_changes(child)

        if has_changed_descendants:
            item.setExpanded(True)

    def _add_tree_item(self, parent: QtWidgets.QTreeWidgetItem, node: NodePresentation, git_path: str) -> None:
        """Create, attach, and install optional row widget for a node."""
        item, row_widget = self._create_tree_item(node, git_path)
        parent.addChild(item)
        if row_widget is not None:
            self._tree_widget.setItemWidget(item, 0, row_widget)

    def _create_tree_item(
        self,
        node: NodePresentation,
        git_path: str,
    ) -> tuple[QtWidgets.QTreeWidgetItem, QtWidgets.QWidget | None]:
        """Recursively create a QTreeWidgetItem from NodePresentation.

        Args:
            node: The NodePresentation to convert.

        Returns:
            QTreeWidgetItem with text, color, and children populated.
        """
        name = node.path.split("/")[-1] if node.path else ""
        text = node.label if node.label == name else f"{node.label} ({name})"

        item = QtWidgets.QTreeWidgetItem([text])
        item.setSizeHint(0, QtCore.QSize(0, TREE_ITEM_HEIGHT))
        item.setToolTip(0, node.type_id)
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, node.path)
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, node.has_changes)

        self._apply_diff_state(item, node.state)

        row_widget = self._create_node_row_widget(item, node, text, git_path)

        for child in node.children:
            self._add_tree_item(item, child, git_path)

        return item, row_widget

    def _create_node_row_widget(
        self, item: QtWidgets.QTreeWidgetItem, node: NodePresentation, text: str, git_path: str
    ) -> QtWidgets.QWidget | None:
        """Create optional custom row widget with right-floating visual diff icon."""
        if not node.visual_diff_enabled:
            return None
        container = QtWidgets.QWidget()
        container.setFixedHeight(TREE_ITEM_HEIGHT)
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        label = QtWidgets.QLabel(text)
        label.setFixedHeight(TREE_ITEM_HEIGHT)
        label.setToolTip(node.type_id)
        layout.addWidget(label)
        layout.addStretch()

        icon_size = QtCore.QSize(TREE_ITEM_ICON_SIZE, TREE_ITEM_ICON_SIZE)

        button = QtWidgets.QToolButton()
        button.setIcon(QtGui.QIcon(str(get_icon_path("VisualDiff.svg"))))
        button.setIconSize(icon_size)
        button.setToolTip(translate("History", "Open 3D comparison"))
        button.setAutoRaise(True)
        button.setStyleSheet(
            """
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 3px;
            }
            QToolButton:hover {
                background-color: rgba(128, 128, 128, 35);
            }
            QToolButton:pressed {
                background-color: rgba(128, 128, 128, 60);
            }
            """
        )
        button.setFixedSize(TREE_ITEM_HEIGHT, TREE_ITEM_HEIGHT)
        button.clicked.connect(
            lambda checked=False, item=item, gp=git_path, np=node.path: self._on_visual_diff_clicked(item, gp, np)
        )
        layout.addWidget(button)
        return container

    def _apply_diff_state(self, item: QtWidgets.QTreeWidgetItem, state: DiffState) -> None:
        """Apply semantic diff coloring data to a tree item."""
        if state == DiffState.UNCHANGED:
            return
        item.setData(0, DIFF_STATE_ROLE, state)
        background = background_for_state(state, self._tree_widget.palette())
        if background is None:
            return
        item.setBackground(0, QtGui.QBrush(background))
        item.setForeground(0, QtGui.QBrush(foreground_for_background(background, self._tree_widget.palette())))

    def show_summary(self, changed_docs: int) -> None:
        """Display count of documents that contain changes.

        Args:
            changed_docs: Number of changed documents.
        """
        if changed_docs == 0:
            self._changed_label.setText(translate("History", "No changes"))
            return

        changed_text = translate("History", "Changed:")
        self._changed_label.setText(f"{changed_text} {changed_docs}")

    def _on_stage_all_clicked(self) -> None:
        """Handle Stage All button click by invoking the callback."""
        if self._on_stage_all_callback:
            self._on_stage_all_callback()

    def _on_remove_all_clicked(self) -> None:
        """Handle summary-bar Remove All button click by invoking callback."""
        if self._on_remove_all_callback:
            self._on_remove_all_callback()

    def _on_remove_from_reviewed_button_clicked(self, git_path: str) -> None:
        """Handle Remove button click by invoking callback."""
        if self._on_remove_from_reviewed_button_callback is not None:
            self._on_remove_from_reviewed_button_callback(git_path)

    def _on_tree_item_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        """Extract git_path from root and node_path from clicked item, then invoke callback.

        Args:
            item: The clicked tree item
            column: The column that was clicked
        """
        if self._on_node_selection_callback is None:
            return

        node_path = item.data(0, QtCore.Qt.ItemDataRole.UserRole)

        root = item
        while root.parent():
            root = root.parent()
        git_path = root.data(0, QtCore.Qt.ItemDataRole.UserRole)

        if git_path and node_path:
            self._on_node_selection_callback(git_path, node_path)

    def _on_visual_diff_clicked(self, item: QtWidgets.QTreeWidgetItem, git_path: str, node_path: str) -> None:
        self._tree_widget.setCurrentItem(item)
        self._on_tree_item_clicked(item, 0)
        if self._on_visual_diff_callback is not None:
            self._on_visual_diff_callback(git_path, node_path)

    def collapse_tree_item(self, git_path: str) -> None:
        """Collapse the root tree item for the given git_path.

        Args:
            git_path: The git_path of the root tree item to collapse.
        """
        for i in range(self._tree_widget.topLevelItemCount()):
            item = self._tree_widget.topLevelItem(i)
            item_git_path = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if item_git_path == git_path:
                item.setExpanded(False)
                break

    def set_stage_button_enabled(self, git_path: str, enabled: bool) -> None:
        """Enable or disable the '+ Reviewed' button for a given git_path.

        Args:
            git_path: The git_path of the document whose button to update.
            enabled: Whether the reviewed button should be enabled.
        """
        if git_path in self._stage_buttons:
            self._stage_buttons[git_path].setEnabled(enabled)
