"""File responsibility: Diff panel view with 3-column layout, implementing DiffView and SnapshotView protocols."""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from PySide6.QtCore import QCoreApplication, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


# Module-level icon loading for refresh button and warning icon
# This is done once at import time rather than per-instance to avoid repeated imports
try:
    import FreeCADGui as Gui

    _REFRESH_ICON: QIcon | None = Gui.getIcon("view-refresh.svg")
    _WARNING_ICON: QIcon | None = Gui.getIcon("Warning.svg")
except (ImportError, AttributeError):
    # FreeCADGui not available (e.g., during unit tests or non-GUI environments)
    _REFRESH_ICON = None
    _WARNING_ICON = None

from ...application.actions.result_models import SnapshotSummary
from ...domain.diff.models import DiffState
from ...domain.git.models import GitCommit, GitRepository
from ..presenters.presentation_models import (
    DiffTreePresentation,
    NodePresentation,
    PropertyPresentation,
)
from ..translation_strings import (
    DIFF_SUMMARY_ADDED_LABEL,
    DIFF_SUMMARY_DELETED_LABEL,
    DIFF_SUMMARY_MODIFIED_LABEL,
    HISTORY_LABEL,
    REPOSITORY_INFO_TEMPLATE,
    REPOSITORY_NO_REPO_MESSAGE,
)
from .models import HistorySelection


def _camelcase_to_spaces(name: str) -> str:
    """Insert spaces before uppercase letters and digits, matching FreeCAD display.

    This function converts CamelCase property names to space-separated names
    to match how FreeCAD displays property names in its UI (e.g., "Saved Geometry"
    instead of "SavedGeometry").

    Args:
        name: The CamelCase property name to convert.

    Returns:
        The property name with spaces inserted before uppercase letters or digits
        (except at the start or when following another uppercase or digit).
    """
    if not name:
        return name

    result = [name[0]]  # Start with first character
    upper_sequence_start = 0 if name[0].isupper() else -1

    for i in range(1, len(name)):
        char = name[i]
        prev_char = name[i - 1]

        if char.isupper():
            # If we hit an uppercase after lowercase, add space (e.g., "SavedGeometry" -> before G)
            if prev_char.islower():
                result.append(" ")
            # If we were in an uppercase sequence and now at end of sequence (next is lowercase),
            # add space. This handles "XMLDoc" -> "XML Doc"
            elif upper_sequence_start >= 0 and i + 1 < len(name) and name[i + 1].islower():
                result.append(" ")
                upper_sequence_start = -1  # Reset
            upper_sequence_start = i
        elif char.islower():
            upper_sequence_start = -1
        elif char.isdigit():
            # Add space before digit if preceded by letter
            if prev_char.isalpha():
                result.append(" ")
            upper_sequence_start = -1
        else:
            upper_sequence_start = -1

        result.append(char)

    return "".join(result)


class _PropertyValueDelegate(QStyledItemDelegate):
    """Custom delegate for property value cells that allows double-click to select text.

    This delegate enables double-click editing on value columns (columns 1 and 2)
    to allow users to select and copy text. The editing is a no-op - it just
    enables text selection without actually saving any changes.
    """

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index) -> QWidget | None:
        """Create a line editor for the cell.

        Args:
            parent: The parent widget.
            option: The style option.
            index: The model index.

        Returns:
            A QLineEdit widget for text selection.
        """
        editor = QLineEdit(parent)
        editor.setFrame(False)
        editor.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        return editor

    def setEditorData(self, editor: QLineEdit, index) -> None:
        """Set the current text in the editor.

        Args:
            editor: The line edit widget.
            index: The model index.
        """
        text = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        if text is not None:
            editor.setText(str(text))
            # Select all text for easy copying
            editor.selectAll()

    def setModelData(self, editor: QLineEdit, model, index) -> None:
        """Do nothing - prevent actual changes to the data.

        This allows the user to double-click and select text for copying,
        but any edits are discarded so the values cannot be changed.

        Args:
            editor: The line edit widget.
            model: The model.
            index: The model index.
        """
        # No-op: don't save any changes
        pass

    def updateEditorGeometry(self, editor: QLineEdit, option: QStyleOptionViewItem, index) -> None:
        """Update the editor geometry to match the cell.

        Args:
            editor: The line edit widget.
            option: The style option.
            index: The model index.
        """
        editor.setGeometry(option.rect)


class DiffPanelView(QWidget):
    """3-column diff panel view implementing DiffView and SnapshotView protocols.

    Provides a horizontal QSplitter with:
    - Left: Placeholder for snapshots list (visible)
    - Middle: QTreeWidget for diff tree (hidden/empty)
    - Right: QTableWidget for properties (hidden/empty)

    Protocol Implementation:
        This class implements the DiffView and SnapshotView protocols through
        structural subtyping (duck typing) rather than explicit inheritance to avoid
        metaclass conflicts between QWidget and Protocol classes.

        Implemented protocols:
        - DiffView (freecad.diff_wb.ui.protocols.diff_view): show_loading, show_diff_tree,
          show_summary, show_error, show_properties, show_repository
        - SnapshotView (freecad.diff_wb.ui.protocols.snapshot_view): show_success,
          show_error, show_loading, show_snapshots

        Protocol compliance is validated at runtime by tests in:
        tests/unit/ui/protocols/test_protocol_compliance.py
    """

    # Color palette for diff tree states
    ADDED_COLOR = QColor(200, 255, 200)  # Light green
    DELETED_COLOR = QColor(255, 200, 200)  # Light red
    MODIFIED_COLOR = QColor(200, 200, 255)  # Light blue
    UNCHANGED_COLOR = QColor(240, 240, 240)  # Light gray (neutral)

    def __init__(self, parent: QWidget | None = None) -> None:
        QWidget.__init__(self, parent)
        self._on_history_selection_callback: Callable[[HistorySelection], None] | None = None
        self._on_refresh_callback: Callable[[], None] | None = None
        self._on_add_button_callback: Callable[[str], None] | None = None
        self._on_node_selection_callback: Callable[[str, str], None] | None = None
        self._current_selection: HistorySelection | None = None
        # Create the delegate for property value double-click editing (for copying)
        self._property_value_delegate = _PropertyValueDelegate(self)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the 3-column layout with placeholders."""
        layout = QVBoxLayout(self)

        # Create horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Column 1: History/Commits list (always visible)
        self.history_list = QListWidget()
        self.history_list.setMinimumWidth(150)
        self.history_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.history_list.setWordWrap(True)  # Enable text wrapping for long messages
        history_placeholder = QLabel(HISTORY_LABEL)
        history_placeholder.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # Repository info label (shown above history list)
        self._repository_label = QLabel("")
        self._repository_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._repository_label.setStyleSheet("font-size: 11px; color: gray; font-style: italic;")
        # Refresh button with module-level cached icon
        self._refresh_button = QPushButton()
        if _REFRESH_ICON is not None:
            self._refresh_button.setIcon(_REFRESH_ICON)
            self._refresh_button.setIconSize(QSize(16, 24))
        self._refresh_button.setToolTip("Refresh git repository detection")
        # Create header layout with repository label on left and refresh button on right
        repository_header_layout = QHBoxLayout()
        repository_header_layout.addWidget(self._repository_label)
        repository_header_layout.addStretch()
        repository_header_layout.addWidget(self._refresh_button)
        repository_header_container = QWidget()
        repository_header_container.setLayout(repository_header_layout)
        # Reorder widgets: repository header FIRST, then placeholder, then history list
        snapshot_layout = QVBoxLayout()
        snapshot_layout.addWidget(repository_header_container)
        snapshot_layout.addWidget(history_placeholder)
        snapshot_layout.addWidget(self.history_list)
        snapshot_container = QWidget()
        snapshot_container.setLayout(snapshot_layout)

        # Summary labels container (above tree widget)
        summary_container = QWidget()
        summary_layout = QHBoxLayout(summary_container)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(16)

        self._added_label = QLabel("")
        self._added_label.setStyleSheet("font-weight: bold;")
        self._deleted_label = QLabel("")
        self._deleted_label.setStyleSheet("font-weight: bold;")
        self._modified_label = QLabel("")
        self._modified_label.setStyleSheet("font-weight: bold;")

        summary_layout.addWidget(self._added_label)
        summary_layout.addWidget(self._deleted_label)
        summary_layout.addWidget(self._modified_label)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Tree"])
        self.tree_widget.setColumnCount(1)
        self.tree_widget.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Note: Not calling hide() because QTreeWidget shows an empty column by default,
        # which provides visual structure. The show_diff_tree() method will populate
        # it with data and ensure visibility when needed.

        # Column 2: Tree view container (with summary labels above it)
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.addWidget(summary_container)
        tree_layout.addWidget(self.tree_widget)

        # Column 3: Properties tree widget (replaces QTableWidget)
        self.properties_tree = QTreeWidget()
        self.properties_tree.setColumnCount(3)
        self.properties_tree.setHeaderLabels(["Property", "Value Left", "Value Right"])
        self.properties_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.properties_tree.header().setStretchLastSection(True)
        # Set the custom delegate for value columns to allow double-click editing (for copying)
        self.properties_tree.setItemDelegate(self._property_value_delegate)
        # Enable edit triggers for double-click
        self.properties_tree.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        # self.properties_tree.hide()  # Hide until data available

        # Add to splitter
        splitter.addWidget(snapshot_container)
        splitter.addWidget(tree_container)
        splitter.addWidget(self.properties_tree)

        # Set initial sizes: narrower snapshot, narrower tree, wider property table
        splitter.setSizes([150, 150, 400])

        # Set minimum size for the panel
        self.setMinimumSize(450, 200)

        layout.addWidget(splitter)

    def set_refresh_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to invoke when refresh button is clicked.

        Args:
            callback: A no-argument callable to invoke on refresh.
        """
        self._on_refresh_callback = callback
        self._refresh_button.clicked.connect(callback)

    # SnapshotView protocol methods
    def show_snapshots(self, snapshots: list[SnapshotSummary]) -> None:
        """Display list of available snapshots.

        Populates the history list widget with snapshot information, sorted by
        timestamp (newest first). Each item displays the snapshot name and
        formatted timestamp, with the snapshot ID stored in Qt.UserRole for
        later selection.

        Args:
            snapshots: List of snapshot summaries containing id, name,
                created_at (ISO format), and node_count.
        """
        # Clear existing items
        self.history_list.clear()

        # Sort snapshots by timestamp (newest first)
        sorted_snapshots = sorted(
            snapshots,
            key=lambda s: datetime.fromisoformat(s.created_at),
            reverse=True,
        )

        # Add each snapshot to the list
        for snapshot in sorted_snapshots:
            # Format display text: "name - Month Day, Year Time"
            display_text = f"{snapshot.name} - {self._format_timestamp(snapshot.created_at)}"

            # Create list item
            item = QListWidgetItem(display_text)

            # Store snapshot ID in UserRole for later retrieval
            item.setData(Qt.ItemDataRole.UserRole, snapshot.id)

            # Add to list
            self.history_list.addItem(item)

    def show_commits(self, commits: list[GitCommit]) -> None:
        """Display git commits in the history list.

        The list always starts with two special items: "Working Tree" and "Staging"
        when displaying git commits. These items use HistorySelection dataclass
        to distinguish them from actual GitCommits.

        Args:
            commits: List of GitCommit objects to display. Commits are shown
                in DESC order (newest first) with 7-char hash, author, timestamp
                on line 1, and first line of message on line 2. Full commit
                message is shown in tooltip.
        """
        # Clear existing items
        self.history_list.clear()

        # Add special items first: "Working Tree" and "Staging"
        # These are always present, even if no commits are provided

        # Add "Working Tree" item
        working_tree_item = QListWidgetItem("Working Tree")
        working_tree_item.setData(Qt.ItemDataRole.TextAlignmentRole, Qt.AlignmentFlag.AlignCenter)
        working_tree_item.setData(
            Qt.ItemDataRole.UserRole,
            HistorySelection(item_kind="WORKING_TREE", commit_hash=None),
        )
        self.history_list.addItem(working_tree_item)

        # Add "Staging" item
        staging_item = QListWidgetItem("Staging")
        staging_item.setData(Qt.ItemDataRole.TextAlignmentRole, Qt.AlignmentFlag.AlignCenter)
        staging_item.setData(
            Qt.ItemDataRole.UserRole,
            HistorySelection(item_kind="STAGING", commit_hash=None),
        )
        self.history_list.addItem(staging_item)

        # Guard: no commits to display after adding special items
        if not commits:
            return

        # Note: Commits are already sorted by timestamp (newest first) by GitPortAdapter.get_commits()
        # using git log which returns commits in DESC order by default. No additional sorting needed.
        sorted_commits = commits

        # Add each commit to the list
        for commit in sorted_commits:
            # Truncate hash to 7 characters for display
            short_hash = commit.id[:7] if len(commit.id) >= 7 else commit.id

            # Format line 1: hash, author, timestamp
            timestamp_str = commit.timestamp.strftime("%Y-%m-%d %H:%M")

            # Get first line of message for line 2
            first_line = commit.message.split("\n")[0].strip() if commit.message and commit.message.strip() else ""

            # Create display text with newline for two-line format
            display_text = f"{short_hash} {commit.author} {timestamp_str}\n{first_line}"

            # Create list item
            item = QListWidgetItem(display_text)

            # Set tooltip to full commit message
            item.setToolTip(commit.message)

            # Set left alignment for commits
            item.setData(Qt.ItemDataRole.TextAlignmentRole, Qt.AlignmentFlag.AlignLeft)

            # Store HistorySelection with COMMIT kind
            item.setData(
                Qt.ItemDataRole.UserRole,
                HistorySelection(item_kind="COMMIT", commit_hash=commit.id),
            )

            # Add to list
            self.history_list.addItem(item)

    def set_history_selection_callback(self, callback: Callable[[HistorySelection], None]) -> None:
        """Set the callback for history list selection.

        Args:
            callback: A callable that receives HistorySelection with item_kind and commit_hash
        """
        self._on_history_selection_callback = callback
        # Connect to item clicked signal for immediate response
        self.history_list.itemClicked.connect(self._on_item_clicked)

    def set_add_button_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback for when the '+ Stage' button is clicked.

        Args:
            callback: A callable that receives the git_path (str) of the
                      document whose '+ Stage' button was clicked.
        """
        self._on_add_button_callback = callback

    def set_node_selection_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for node selection with (git_path, node_path).

        Args:
            callback: A callable receiving (git_path, node_path) when a node is clicked.
        """
        self._on_node_selection_callback = callback
        # Connect to internal handler that extracts both values
        self.tree_widget.itemClicked.connect(self._on_tree_item_clicked)

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Extract git_path from root and node_path from clicked item, then invoke callback.

        Args:
            item: The clicked tree item
            column: The column that was clicked
        """
        if self._on_node_selection_callback is None:
            return

        # Extract node_path from clicked item (set in _create_tree_item)
        node_path = item.data(0, Qt.ItemDataRole.UserRole)

        # Walk up to find root item and extract git_path
        root = item
        while root.parent():
            root = root.parent()
        git_path = root.data(0, Qt.ItemDataRole.UserRole)

        if git_path and node_path:
            self._on_node_selection_callback(git_path, node_path)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle item click by tracking selection and triggering callback."""
        if self._on_history_selection_callback is None:
            return

        item_data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(item_data, HistorySelection):
            # Track selection state for button visibility
            self._current_selection = item_data
            self._on_history_selection_callback(item_data)

    def _format_timestamp(self, iso_string: str) -> str:
        """Format ISO timestamp string for display.

        Converts an ISO format timestamp (e.g., "2024-01-15T10:30:00") to a
        human-readable format (e.g., "Jan 15, 2024 10:30 AM").

        Args:
            iso_string: ISO format timestamp string.

        Returns:
            Formatted timestamp string like "Jan 1, 2024 10:00 AM".
        """
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%b %d, %Y %I:%M%p").replace(" 0", " ")

    def show_success(self, snapshot_name: str) -> None:
        """Notify view of successful snapshot creation.

        Logging is handled by the presenter to maintain separation of concerns.
        This method can be extended in the future to provide UI feedback
        (e.g., status bar message, notification) without depending on the container.

        Args:
            snapshot_name: The name of the created snapshot.
        """
        # No-op: logging handled by presenter. Future UI feedback can be added here.
        pass

    def show_error(self, error_message: str) -> None:
        """Show error message."""
        pass

    def show_loading(
        self,
        message: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Show loading indicator."""
        pass

    # DiffView protocol methods
    def show_diff_tree(self, nodes: list[NodePresentation], git_path: str = "") -> None:
        """Display the diff tree with color-coded nodes.

        Args:
            nodes: List of root-level NodePresentation objects with nested children.
            git_path: The git path to display as top-level item
        """
        # Clear existing tree items
        self.tree_widget.clear()

        # Guard: no nodes to display
        if not nodes:
            return

        # Create top-level item with git_path (or document_name fallback)
        top_level_text = git_path or "Unnamed Document"
        root_item = QTreeWidgetItem([top_level_text])

        # Add child nodes from hierarchy
        for node in nodes:
            item = self._create_tree_item(node)
            root_item.addChild(item)

        self.tree_widget.addTopLevelItem(root_item)

        # Expand only nodes that have children with changes
        self._expand_nodes_with_changes(root_item)

        # Ensure tree widget is visible (in case it was hidden)
        self.tree_widget.show()

    def show_diff_trees(self, diffs: list[DiffTreePresentation]) -> None:
        """Display multiple diff trees in the tree widget.

        Args:
            diffs: List of DiffTreePresentation objects, each representing
                  a diff tree for one document with its metadata.
        """
        # Clear existing tree items
        self.tree_widget.clear()

        # Guard: no diffs to display
        if not diffs:
            return

        for diff in diffs:
            # Build top-level text (no emoji - icon will be shown separately)
            top_level_text = diff.git_path or "Unnamed Document"

            # Prepare warning text for tooltip (newline-separated)
            warning_tooltip = "\n".join(diff.warnings) if diff.warnings else ""

            # Create root item
            root_item = QTreeWidgetItem([top_level_text])
            # Store git_path in root item's UserRole for later retrieval when children are clicked
            root_item.setData(0, Qt.ItemDataRole.UserRole, diff.git_path)

            # Create container widget with layout
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(4, 2, 4, 2)

            # Add text label
            layout.addWidget(QLabel(top_level_text))

            # Add warning icon label if warnings exist
            if diff.warnings and _WARNING_ICON is not None:
                warning_icon_label = QLabel()
                warning_icon_label.setPixmap(_WARNING_ICON.pixmap(16, 16))
                warning_icon_label.setToolTip(warning_tooltip)
                layout.addWidget(warning_icon_label)

            layout.addStretch()

            # Only create "+ Stage" button when Working Tree is selected
            show_stage_button = (
                self._current_selection is not None and self._current_selection.item_kind == "WORKING_TREE"
            )

            if show_stage_button:
                # Create "+ Stage" button
                add_button = QPushButton("+ Stage")
                # Use pre-computed stage_button_enabled from presenter
                add_button.setEnabled(diff.stage_button_enabled)
                add_button.setFixedWidth(40)
                # Use default argument gp=diff.git_path to capture loop variable correctly.
                # Without this, all lambdas would reference the same 'diff' variable from the
                # enclosing scope, which would have its final value after the loop completes.
                # The default argument captures the current value of diff.git_path at iteration time.
                add_button.clicked.connect(lambda checked, gp=diff.git_path: self._on_add_button_clicked(gp))
                layout.addWidget(add_button)

            # Set the widget on the tree item
            self.tree_widget.addTopLevelItem(root_item)
            self.tree_widget.setItemWidget(root_item, 0, container)

            # Add child nodes from hierarchy
            for node in diff.nodes:
                item = self._create_tree_item(node)
                root_item.addChild(item)

            # Expand only nodes that have children with changes
            self._expand_nodes_with_changes(root_item)

        # Ensure tree widget is visible
        self.tree_widget.show()

    def _on_add_button_clicked(self, git_path: str) -> None:
        """Handle '+ Stage' button click by invoking the callback.

        Args:
            git_path: The git_path of the document whose button was clicked.
        """
        if self._on_add_button_callback:
            self._on_add_button_callback(git_path)

    def _expand_nodes_with_changes(self, item: QTreeWidgetItem) -> None:
        """Recursively expand nodes that have descendants with changes.

        Args:
            item: The tree item to check and expand if needed
        """
        child_count = item.childCount()
        has_changed_descendants = False

        for i in range(child_count):
            child = item.child(i)
            has_changes = child.data(0, Qt.ItemDataRole.UserRole + 1)
            if has_changes:
                has_changed_descendants = True
            self._expand_nodes_with_changes(child)

        if has_changed_descendants:
            item.setExpanded(True)

    def _create_tree_item(self, node: NodePresentation) -> QTreeWidgetItem:
        """Recursively create a QTreeWidgetItem from NodePresentation.

        Args:
            node: The NodePresentation to convert.

        Returns:
            QTreeWidgetItem with text, color, and children populated.
        """
        # Extract display name: last path segment (e.g., "Pad" from "Body/Pad")
        display_name = node.path.split("/")[-1] if node.path else node.type_id
        text = f"{display_name} ({node.type_id})"

        # Create tree item with display text
        item = QTreeWidgetItem([text])

        # Store path in UserRole for later property lookup
        item.setData(0, Qt.ItemDataRole.UserRole, node.path)
        # Store has_changes flag in UserRole+1 for expansion logic
        item.setData(0, Qt.ItemDataRole.UserRole + 1, node.has_changes)

        # Apply color based on state (only for changed nodes)
        if node.state == DiffState.ADDED:
            item.setBackground(0, QBrush(self.ADDED_COLOR))
        elif node.state == DiffState.DELETED:
            item.setBackground(0, QBrush(self.DELETED_COLOR))
        elif node.state == DiffState.MODIFIED:
            item.setBackground(0, QBrush(self.MODIFIED_COLOR))
        # UNCHANGED: no color (use default background)

        # Recursively add children using explicit children field
        for child in node.children:
            child_item = self._create_tree_item(child)
            item.addChild(child_item)

        return item

    def show_summary(self, added: int, deleted: int, modified: int) -> None:
        """Display the diff summary counts.

        Args:
            added: Number of added nodes.
            deleted: Number of deleted nodes.
            modified: Number of modified nodes.
        """
        # Translate labels
        added_text = QCoreApplication.translate("DiffView", DIFF_SUMMARY_ADDED_LABEL)
        deleted_text = QCoreApplication.translate("DiffView", DIFF_SUMMARY_DELETED_LABEL)
        modified_text = QCoreApplication.translate("DiffView", DIFF_SUMMARY_MODIFIED_LABEL)

        # Set text with counts
        if added == 0 and deleted == 0 and modified == 0:
            self._added_label.setText("No changes")
            self._deleted_label.setText("")
            self._modified_label.setText("")
        else:
            self._added_label.setText(f"{added_text} {added}")
            self._deleted_label.setText(f"{deleted_text} {deleted}")
            self._modified_label.setText(f"{modified_text} {modified}")

    def show_properties(self, properties: list[PropertyPresentation]) -> None:
        """Display property diffs in the properties tree widget.

        Args:
            properties: List of PropertyPresentation objects to display.
                       Properties are grouped by their group (or default to "Properties").
                       Each property row shows: Property Name | Value
                       Color coding: green=added, red=deleted, blue=modified, gray=unchanged
                       Expandable properties can be expanded to show their children.
        """
        # Clear existing tree items
        self.properties_tree.clear()

        # Guard: no properties to display
        if not properties:
            return

        # Group properties by group name (default to "Properties" if no group)
        groups: dict[str, list[PropertyPresentation]] = {}
        for prop in properties:
            # Use getattr to check for group attribute, default to "Properties" if not present
            group_name = getattr(prop, "group", None) or "Properties"
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(prop)

        # Create tree items for each group (sorted alphabetically)
        for group_name in sorted(groups.keys()):
            group_props = groups[group_name]
            # Create group header item
            group_item = self._create_group_header_item(group_name)
            self.properties_tree.addTopLevelItem(group_item)

            # Add properties under this group
            for prop in group_props:
                prop_item = self._create_property_tree_item(prop)
                group_item.addChild(prop_item)

            # Expand groups by default so properties are visible
            group_item.setExpanded(True)

    def show_repository(self, repo: GitRepository | None) -> None:
        """Display git repository info above snapshot list.

        Args:
            repo: GitRepository object if detected, or None if no repository found.
                  If None, shows "No git repository detected".
        """
        if repo is None:
            text = QCoreApplication.translate("Common", REPOSITORY_NO_REPO_MESSAGE)
            self._repository_label.setText(text)
            self._repository_label.setToolTip("")
            self._repository_label.setStyleSheet("font-size: 11px; color: gray; font-style: italic;")
        else:
            name = repo.name
            path = repo.absolute_path
            template = QCoreApplication.translate("Common", REPOSITORY_INFO_TEMPLATE)
            # Replace Qt-style placeholders (%1) with repository name
            text = template.replace("%1", name)
            self._repository_label.setText(text)
            # Set tooltip with full directory path
            self._repository_label.setToolTip(path)
            # Style with underline to indicate clickable/tooltip
            self._repository_label.setStyleSheet("font-size: 11px; font-weight: bold; text-decoration: underline;")

    def _create_group_header_item(self, group_name: str) -> QTreeWidgetItem:
        """Create a non-selectable group header item with gray background.

        Args:
            group_name: The name of the group (e.g., "Base", "Format").

        Returns:
            QTreeWidgetItem configured as a group header.
        """
        # Gray background for group headers (similar to FreeCAD's property panel)
        GROUP_HEADER_COLOR = QColor(220, 220, 220)

        item = QTreeWidgetItem([group_name, "", ""])
        # Make header non-selectable
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        # Apply gray background to all 3 columns
        item.setBackground(0, QBrush(GROUP_HEADER_COLOR))
        item.setBackground(1, QBrush(GROUP_HEADER_COLOR))
        item.setBackground(2, QBrush(GROUP_HEADER_COLOR))
        # Make the group header bold
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        item.setFont(1, font)
        item.setFont(2, font)
        return item

    def _create_property_tree_item(self, prop: PropertyPresentation) -> QTreeWidgetItem:
        """Create a property tree item with diff coloring and expandability.

        For expandable properties, children are compared between old_value and new_value
        to determine their individual state (MODIFIED/ADDED/DELETED/UNCHANGED).
        Only changed children receive background coloring; unchanged children use default.
        If any child has changes, the parent row is colored blue (MODIFIED).

        Args:
            prop: The PropertyPresentation to display.

        Returns:
            QTreeWidgetItem with text, color, and children if expandable.
        """

        # Get display values based on state
        bg_color, left_value, right_value = self._get_property_display_values(prop.state, prop)

        # Convert CamelCase to spaced name for display
        display_name = _camelcase_to_spaces(prop.name)

        item = QTreeWidgetItem([display_name, left_value, right_value])
        # Enable editing on double-click to allow text selection for copying
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

        # Use pre-computed children from domain instead of computing diffs
        has_changed_children = self._add_child_items(item, prop.children)

        # Always expand property items so their content is visible
        item.setExpanded(True)

        # If any child has MODIFIED/ADDED/DELETED state, color the parent row blue
        if has_changed_children:
            self._apply_background_to_all_columns(item, self.MODIFIED_COLOR)
        else:
            # Apply original diff coloring to all 3 columns
            self._apply_background_to_all_columns(item, bg_color)

        return item

    def _get_property_display_values(
        self,
        state: DiffState,
        prop: PropertyPresentation,
    ) -> tuple[QColor, str, str]:
        """Get background color and display values based on property state.

        Args:
            state: The property state (DiffState enum).
            prop: The PropertyPresentation object.

        Returns:
            Tuple of (background_color, left_column_value, right_column_value).
        """
        if state == DiffState.ADDED:
            return self.ADDED_COLOR, "", str(prop.new_value) if prop.new_value is not None else ""
        if state == DiffState.DELETED:
            return self.DELETED_COLOR, str(prop.old_value) if prop.old_value is not None else "", ""
        if state == DiffState.MODIFIED:
            old_str = str(prop.old_value) if prop.old_value is not None else ""
            new_str = str(prop.new_value) if prop.new_value is not None else ""
            return self.MODIFIED_COLOR, old_str, new_str
        # UNCHANGED
        new_str = str(prop.new_value) if prop.new_value is not None else ""
        return self.UNCHANGED_COLOR, new_str, new_str

    def _add_child_items(
        self,
        parent_item: QTreeWidgetItem,
        children: list[PropertyPresentation],
    ) -> bool:
        """Add pre-computed child items to the tree.

        Args:
            parent_item: The parent QTreeWidgetItem to add children to.
            children: Pre-computed PropertyPresentation children from domain.

        Returns:
            True if any child has MODIFIED/ADDED/DELETED state, False otherwise.
        """
        has_changed_children = False

        for child in children:
            # Determine if this child has changes
            if child.state in (DiffState.MODIFIED, DiffState.ADDED, DiffState.DELETED):
                has_changed_children = True

            # Get display values based on state
            left_value, right_value = self._get_child_display_values(child)

            # Create child item with CamelCase conversion for display
            display_name = _camelcase_to_spaces(child.name)
            child_item = QTreeWidgetItem([display_name, left_value, right_value])
            # Enable editing on double-click to allow text selection for copying
            child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsEditable)

            # Apply background color based on state
            self._apply_child_background_by_state(child_item, child.state)

            # Recursively add grandchildren (pre-computed, no diffing needed)
            if child.children:
                grandchild_has_changes = self._add_child_items(child_item, child.children)
                if grandchild_has_changes:
                    has_changed_children = True

            parent_item.addChild(child_item)

        return has_changed_children

    def _get_child_display_values(self, child: PropertyPresentation) -> tuple[str, str]:
        """Get display values for a child based on its state.

        Args:
            child: The PropertyPresentation child.

        Returns:
            Tuple of (left_value, right_value) for display.
        """
        old_val = child.old_value
        new_val = child.new_value

        # Format display values based on state
        if child.state == DiffState.ADDED:
            return ("", str(new_val) if new_val is not None else child.name)
        if child.state == DiffState.DELETED:
            return (str(old_val) if old_val is not None else child.name, "")
        if child.state == DiffState.MODIFIED:
            left = str(old_val) if old_val is not None else ""
            right = str(new_val) if new_val is not None else ""
            return (left, right)
        # UNCHANGED
        value = str(new_val) if new_val is not None else ""
        return (value, value)

    def _apply_child_background_by_state(self, child_item: QTreeWidgetItem, state: DiffState) -> None:
        """Apply background color to a child item based on its state.

        Args:
            child_item: The child QTreeWidgetItem.
            state: The state of the child (DiffState enum).
        """
        if state == DiffState.ADDED:
            self._apply_background_to_all_columns(child_item, self.ADDED_COLOR)
        elif state == DiffState.DELETED:
            self._apply_background_to_all_columns(child_item, self.DELETED_COLOR)
        elif state == DiffState.MODIFIED:
            self._apply_background_to_all_columns(child_item, self.MODIFIED_COLOR)
        # UNCHANGED: no background

    def _apply_background_to_all_columns(self, item: QTreeWidgetItem, color: QColor) -> None:
        """Apply background color to all 3 columns of a tree item.

        Args:
            item: The QTreeWidgetItem to apply background to.
            color: The QColor to use as background.
        """
        item.setBackground(0, QBrush(color))
        item.setBackground(1, QBrush(color))
        item.setBackground(2, QBrush(color))
