"""File responsibility: Diff panel view with 3-column layout, implementing DiffView and SnapshotView protocols."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...application.actions.result_models import SnapshotSummary
from ..presenters.presentation_models import NodePresentation, PropertyPresentation
from ..translation_strings import (
    DIFF_SUMMARY_ADDED_LABEL,
    DIFF_SUMMARY_DELETED_LABEL,
    DIFF_SUMMARY_MODIFIED_LABEL,
)


@dataclass
class _SelectedItem:
    """Tracks a selected snapshot with its assigned role."""

    row: int
    role: str  # "from" or "to"


class _SnapshotListItemDelegate(QStyledItemDelegate):
    """Custom item delegate for rendering snapshot list items with custom selection colors.

    This delegate overrides the paint method to apply custom background colors
    for selected items based on their role ("from" = red, "to" = green),
    overriding Qt's default blue selection highlight.
    """

    # Color mapping for roles
    FROM_COLOR = QColor(255, 200, 200)  # Light red
    TO_COLOR = QColor(200, 255, 200)  # Light green

    def __init__(self, parent: QListWidget, get_item_role_callback: Callable[[int], str | None]) -> None:
        """Initialize the delegate.

        Args:
            parent: The QListWidget this delegate belongs to.
            get_item_role_callback: A callable that takes a row number and returns
                the role ("from" or "to") if the item is selected, or None otherwise.
        """
        super().__init__(parent)
        self._get_item_role = get_item_role_callback
        self._parent = parent

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        """Paint the item with custom selection colors.

        Args:
            painter: The QPainter instance.
            option: The QStyleOptionViewItem containing display information.
            index: The model index.
        """
        # Get the row from the index
        row = index.row()

        # Check if this item is selected by checking the widget's selection
        is_selected = self._parent.item(row).isSelected() if self._parent.item(row) else False

        # If selected and we have a custom role, use custom color
        if is_selected:
            role = self._get_item_role(row)
            if role:
                # Get the selection color based on role
                selection_color = self.FROM_COLOR if role == "from" else self.TO_COLOR

                # Draw custom background
                painter.save()
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.fillRect(option.rect, QBrush(selection_color))

                # Get text and draw it
                item = self._parent.item(row)
                if item:
                    text_rect = option.rect.adjusted(4, 0, -4, 0)  # Add some padding
                    painter.setPen(option.palette.color(QPalette.ColorRole.Text))
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, item.text())
                painter.restore()
                return

        # Use default painting for non-selected items or when no custom role
        super().paint(painter, option, index)


class DiffPanelView(QWidget):
    """3-column diff panel view implementing DiffView and SnapshotView protocols.

    Provides a horizontal QSplitter with:
    - Left: Placeholder for snapshots list (visible)
    - Middle: QTreeWidget for diff tree (hidden/empty)
    - Right: QTableWidget for properties (hidden/empty)

    Note: This class implements the DiffView and SnapshotView protocols through
    structural subtyping (duck typing) rather than explicit inheritance to avoid
    metaclass conflicts between QWidget and Protocol classes.
    """

    # Color palette for diff tree states
    ADDED_COLOR = QColor(200, 255, 200)  # Light green
    DELETED_COLOR = QColor(255, 200, 200)  # Light red
    MODIFIED_COLOR = QColor(200, 200, 255)  # Light blue
    UNCHANGED_COLOR = QColor(240, 240, 240)  # Light gray (neutral)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self._selected_items: dict[int, _SelectedItem] = {}  # row -> _SelectedItem
        # Create the custom delegate for rendering selection colors
        self._delegate = _SnapshotListItemDelegate(None, self._get_item_role)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the 3-column layout with placeholders."""
        layout = QVBoxLayout(self)

        # Create horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Column 1: Snapshots list (always visible)
        self.snapshot_list = QListWidget()
        self.snapshot_list.setMinimumWidth(150)
        self.snapshot_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.snapshot_list.itemSelectionChanged.connect(self._on_selection_changed)
        # Set the custom delegate for rendering selection colors
        self.snapshot_list.setItemDelegate(self._delegate)
        # Update the delegate's parent reference now that snapshot_list exists
        self._delegate._parent = self.snapshot_list
        snapshot_placeholder = QLabel("Snapshots")
        snapshot_placeholder.setAlignment(Qt.AlignmentFlag.AlignLeft)
        snapshot_layout = QVBoxLayout()
        snapshot_layout.addWidget(snapshot_placeholder)
        snapshot_layout.addWidget(self.snapshot_list)
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

        # Column 3: Properties table (hidden initially)
        self.properties_table = QTableWidget()
        self.properties_table.setColumnCount(2)
        self.properties_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.properties_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # self.properties_table.hide()  # Hide until data available

        # Add to splitter
        splitter.addWidget(snapshot_container)
        splitter.addWidget(tree_container)
        splitter.addWidget(self.properties_table)

        # Set initial sizes (equal thirds)
        splitter.setSizes([200, 200, 200])

        # Set minimum size for the panel
        self.setMinimumSize(450, 200)

        layout.addWidget(splitter)

    # SnapshotView protocol methods
    def show_snapshots(self, snapshots: list[SnapshotSummary]) -> None:
        """Display list of available snapshots.

        Populates the snapshot list widget with snapshot information, sorted by
        timestamp (newest first). Each item displays the snapshot name and
        formatted timestamp, with the snapshot ID stored in Qt.UserRole for
        later selection.

        Args:
            snapshots: List of snapshot summaries containing id, name,
                created_at (ISO format), and node_count.
        """
        # Clear all selections and roles on refresh
        self.clear_selection()

        # Clear existing items
        self.snapshot_list.clear()

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
            self.snapshot_list.addItem(item)

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
    def show_diff_tree(self, nodes: list[NodePresentation]) -> None:
        """Display the diff tree with color-coded nodes.

        Args:
            nodes: List of root-level NodePresentation objects with nested children.
        """
        # Clear existing tree items
        self.tree_widget.clear()

        # Guard: no nodes to display
        if not nodes:
            return

        # Recursively build tree from root nodes
        for node in nodes:
            item = self._create_tree_item(node)
            self.tree_widget.addTopLevelItem(item)

        # Expand all nodes by default for immediate visibility
        self.tree_widget.expandAll()

        # Ensure tree widget is visible (in case it was hidden)
        self.tree_widget.show()

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

        # Apply color based on state (only for changed nodes)
        if node.state == "ADDED":
            item.setBackground(0, QBrush(self.ADDED_COLOR))
        elif node.state == "DELETED":
            item.setBackground(0, QBrush(self.DELETED_COLOR))
        elif node.state == "MODIFIED":
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
        """Display property diffs in the properties table.

        Args:
            properties: List of PropertyPresentation objects to display.
                       Each row shows: Property Name | Value
                       Color coding: green=added, red=deleted, blue=modified, gray=unchanged
        """
        # Clear existing rows
        self.properties_table.setRowCount(0)

        # Include all properties (including unchanged)
        all_properties = properties

        # Set row count to number of properties
        self.properties_table.setRowCount(len(all_properties))

        # Populate rows
        for row, prop in enumerate(all_properties):
            # Property name column (column 0)
            name_item = QTableWidgetItem(prop.name)

            # Determine color based on state
            if prop.state == "ADDED":
                bg_color = self.ADDED_COLOR
                value_text = f"+ {prop.new_display}"
            elif prop.state == "DELETED":
                bg_color = self.DELETED_COLOR
                value_text = f"- {prop.old_display}"
            elif prop.state == "MODIFIED":
                bg_color = self.MODIFIED_COLOR
                value_text = f"{prop.old_display} → {prop.new_display}"
            else:  # UNCHANGED
                bg_color = self.UNCHANGED_COLOR
                value_text = prop.new_display  # Just the value, no arrows

            # Value column (column 1)
            value_item = QTableWidgetItem(value_text)

            # Apply background color to both cells
            name_item.setBackground(QBrush(bg_color))
            value_item.setBackground(QBrush(bg_color))

            # Add items to table
            self.properties_table.setItem(row, 0, name_item)
            self.properties_table.setItem(row, 1, value_item)

    # Selection management methods
    def _get_default_background(self) -> QColor:
        """Get the default background color from the widget's palette.

        Returns:
            The default background color used by QListWidget items.
        """
        palette = QApplication.palette()
        return palette.color(QPalette.ColorRole.Base)

    def _get_item_role(self, row: int) -> str | None:
        """Get the role of a selected item by row.

        Args:
            row: The row number of the item.

        Returns:
            The role ("from" or "to") if the item is selected, None otherwise.
        """
        if row in self._selected_items:
            return self._selected_items[row].role
        return None

    def _on_selection_changed(self) -> None:
        """Handle selection changes with max-2 limit and stable color roles."""
        # Get currently selected rows from Qt
        current_selected_rows = {self.snapshot_list.row(item) for item in self.snapshot_list.selectedItems()}
        existing_rows = set(self._selected_items.keys())

        # Detect added/removed rows
        added_rows = current_selected_rows - existing_rows
        removed_rows = existing_rows - current_selected_rows

        # Handle deselection: remove from tracking
        self._handle_deselection(removed_rows)

        # Handle new selection: assign role, apply custom color
        self._handle_new_selections(added_rows)

    def _handle_deselection(self, removed_rows: set[int]) -> None:
        """Remove deselected items from tracking."""
        for row in removed_rows:
            if row in self._selected_items:
                del self._selected_items[row]

    def _handle_new_selections(self, added_rows: set[int]) -> None:
        """Handle newly selected items with role assignment and color application."""
        for row in added_rows:
            # Check if we already have 2 selections
            if len(self._selected_items) >= 2:
                self._reject_selection(row)
                return

            # Assign role and apply color
            role = self._assign_role()
            self._apply_selection_style(row, role)

    def _reject_selection(self, row: int) -> None:
        """Silently reject a selection attempt by deselecting the item."""
        item = self.snapshot_list.item(row)
        if item:
            item.setSelected(False)

    def _assign_role(self) -> str:
        """Assign a role to a new selection.

        Returns:
            "from" if no "from" selection exists, otherwise "to".
        """
        has_from = any(item.role == "from" for item in self._selected_items.values())
        return "to" if has_from else "from"

    def _apply_selection_style(self, row: int, role: str) -> None:
        """Apply visual style for a selected item.

        Args:
            row: The row number of the selected item.
            role: The assigned role ("from" or "to").
        """
        item = self.snapshot_list.item(row)
        if item:
            color = _SnapshotListItemDelegate.FROM_COLOR if role == "from" else _SnapshotListItemDelegate.TO_COLOR
            item.setBackground(QBrush(color))
        self._selected_items[row] = _SelectedItem(row=row, role=role)

    def get_selected_snapshot_ids(self) -> list[str]:
        """Return snapshot IDs in role order: [from_id, to_id].

        Returns:
            List of snapshot IDs ordered by role (from before to), not row order.
            Empty list if nothing selected, single-element list if only one selected.
        """
        ids: list[str] = []
        # First add "from" if exists
        for item in self._selected_items.values():
            if item.role == "from":
                widget_item = self.snapshot_list.item(item.row)
                if widget_item:
                    ids.append(widget_item.data(Qt.ItemDataRole.UserRole))
        # Then add "to" if exists
        for item in self._selected_items.values():
            if item.role == "to":
                widget_item = self.snapshot_list.item(item.row)
                if widget_item:
                    ids.append(widget_item.data(Qt.ItemDataRole.UserRole))
        return ids

    def clear_selection(self) -> None:
        """Clear all selections, reset backgrounds, and clear role tracking."""
        # Reset all tracked item backgrounds to default
        for row in self._selected_items:
            item = self.snapshot_list.item(row)
            if item:
                item.setBackground(QBrush(self._get_default_background()))

        # Clear selection and tracking
        self.snapshot_list.clearSelection()
        self._selected_items = {}
