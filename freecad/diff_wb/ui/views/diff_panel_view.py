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
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...application.actions.result_models import SnapshotSummary
from ...domain.diff.models import DiffState
from ...utils import Log
from ..presenters.presentation_models import NodePresentation, PropertyPresentation
from ..translation_strings import (
    DIFF_SUMMARY_ADDED_LABEL,
    DIFF_SUMMARY_DELETED_LABEL,
    DIFF_SUMMARY_MODIFIED_LABEL,
)
from .property_tree import _camelcase_to_spaces, get_property_children, is_expandable


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

        # Column 3: Properties tree widget (replaces QTableWidget)
        self.properties_tree = QTreeWidget()
        self.properties_tree.setColumnCount(3)
        self.properties_tree.setHeaderLabels(["Property", "Value Left", "Value Right"])
        self.properties_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.properties_tree.header().setStretchLastSection(True)
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

        # Expand only nodes that have children with changes
        self._expand_nodes_with_changes(self.tree_widget.invisibleRootItem())

        # Ensure tree widget is visible (in case it was hidden)
        self.tree_widget.show()

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
        Log.debug(f"[DEBUG] _create_property_tree_item: property={prop.name!r}, group={prop.group!r}")
        Log.debug(f"  old_value type: {type(prop.old_value).__name__ if prop.old_value is not None else None}")
        Log.debug(f"  new_value type: {type(prop.new_value).__name__ if prop.new_value is not None else None}")

        # Get display values based on state
        bg_color, left_value, right_value = self._get_property_display_values(prop.state, prop)

        # Convert CamelCase to spaced name for display
        display_name = _camelcase_to_spaces(prop.name)

        item = QTreeWidgetItem([display_name, left_value, right_value])

        # Check if the property value is expandable and add children with diff comparison
        has_changed_children = self._add_child_items_with_diffs(
            item,
            prop.name,
            prop.old_value,
            prop.new_value,
        )

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

    def _add_child_items_with_diffs(
        self,
        parent_item: QTreeWidgetItem,
        child_name: str,
        old_value: Any,
        new_value: Any,
        visited: set[int] | None = None,
        depth: int = 0,
    ) -> bool:
        """Add child items with diff comparison for expandable properties.

        Recursively expands children that are themselves expandable (e.g., Placement -> Base -> x,y,z).

        Args:
            parent_item: The parent QTreeWidgetItem to add children to.
            child_name: The name of the property/child to expand.
            old_value: The old value to expand.
            new_value: The new value to expand.
            visited: Set of object IDs already visited (to prevent circular references).
            depth: Current recursion depth.

        Returns:
            True if any child has MODIFIED/ADDED/DELETED state, False otherwise.
        """
        # Max depth to prevent infinite recursion (safety limit)
        MAX_DEPTH = 10
        if depth >= MAX_DEPTH:
            Log.debug("[DEBUG] _add_child_items_with_diffs: max depth reached")
            return False

        Log.debug(f"[DEBUG] _add_child_items_with_diffs: property={child_name!r}, depth={depth}")
        Log.debug(f"  old_value: {old_value!r} (type: {type(old_value).__name__ if old_value is not None else None})")
        Log.debug(f"  new_value: {new_value!r} (type: {type(new_value).__name__ if new_value is not None else None})")

        # Initialize visited set on first call
        if visited is None:
            visited = set()

        # Track this level's objects to prevent circular references
        current_visited = visited | {id(old_value), id(new_value)} - {None}

        has_changed_children = False

        # Get children from both old and new values
        old_is_expandable = is_expandable(old_value, "", child_name)
        new_is_expandable = is_expandable(new_value, "", child_name)
        Log.debug(f"  is_expandable: old={old_is_expandable}, new={new_is_expandable}")

        old_children = get_property_children(child_name, old_value) if old_value is not None else []
        new_children = get_property_children(child_name, new_value) if new_value is not None else []
        Log.debug(f"  children count: old={len(old_children)}, new={len(new_children)}")

        # Create dictionaries for easy lookup by child name
        old_child_map = dict(old_children)
        new_child_map = dict(new_children)

        # Get all unique child names
        all_child_names = set(old_child_map.keys()) | set(new_child_map.keys())

        for grandchild_name in sorted(all_child_names):
            old_grandchild_value = old_child_map.get(grandchild_name)
            new_grandchild_value = new_child_map.get(grandchild_name)

            # Determine grandchild state by comparing old and new values
            grandchild_state = self._determine_child_state(old_grandchild_value, new_grandchild_value)

            # Track if any grandchild has changes
            if grandchild_state in (DiffState.MODIFIED, DiffState.ADDED, DiffState.DELETED):
                has_changed_children = True

            # Check if this grandchild is itself expandable
            old_is_expandable = is_expandable(old_grandchild_value)
            new_is_expandable = is_expandable(new_grandchild_value)

            # Check for circular references - skip if already visited
            old_id = id(old_grandchild_value) if old_grandchild_value is not None else None
            new_id = id(new_grandchild_value) if new_grandchild_value is not None else None
            old_already_visited = old_id in current_visited
            new_already_visited = new_id in current_visited

            # Skip expansion if either value has been visited (prevents circular refs)
            is_expandable_grandchild = (old_is_expandable or new_is_expandable) and not (
                old_already_visited or new_already_visited
            )

            grandchild_display_name = _camelcase_to_spaces(grandchild_name)

            if is_expandable_grandchild:
                # Grandchild is expandable - show empty values and recurse
                grandchild_item = QTreeWidgetItem([grandchild_display_name, "", ""])
                Log.debug(f"  Recursing into expandable grandchild: {grandchild_name!r}")
                # Recursively add great-grandchildren with updated visited set and depth
                deeper_has_changes = self._add_child_items_with_diffs(
                    grandchild_item,
                    grandchild_name,
                    old_grandchild_value,
                    new_grandchild_value,
                    current_visited,
                    depth + 1,
                )
                # If deeper levels have changes, this grandchild also has changes
                if deeper_has_changes:
                    has_changed_children = True
                    self._apply_child_background(grandchild_item, DiffState.MODIFIED)
            else:
                # Leaf node - show actual values
                old_value_str = str(old_grandchild_value) if old_grandchild_value is not None else ""
                new_value_str = str(new_grandchild_value) if new_grandchild_value is not None else ""
                grandchild_item = QTreeWidgetItem([grandchild_display_name, old_value_str, new_value_str])
                self._apply_child_background(grandchild_item, grandchild_state)

            parent_item.addChild(grandchild_item)

        Log.debug(f"[DEBUG] _add_child_items_with_diffs returning: has_changed_children={has_changed_children}")
        return has_changed_children

    def _apply_background_to_all_columns(self, item: QTreeWidgetItem, color: QColor) -> None:
        """Apply background color to all 3 columns of a tree item.

        Args:
            item: The QTreeWidgetItem to apply background to.
            color: The QColor to use as background.
        """
        item.setBackground(0, QBrush(color))
        item.setBackground(1, QBrush(color))
        item.setBackground(2, QBrush(color))

    def _apply_child_background(self, child_item: QTreeWidgetItem, child_state: DiffState) -> None:
        """Apply background color to a child item based on its state.

        Only applies color for MODIFIED/ADDED/DELETED states.
        UNCHANGED children use default background (no coloring).

        Args:
            child_item: The child QTreeWidgetItem.
            child_state: The state of the child (DiffState enum).
        """
        if child_state == DiffState.ADDED:
            self._apply_background_to_all_columns(child_item, self.ADDED_COLOR)
        elif child_state == DiffState.DELETED:
            self._apply_background_to_all_columns(child_item, self.DELETED_COLOR)
        elif child_state == DiffState.MODIFIED:
            self._apply_background_to_all_columns(child_item, self.MODIFIED_COLOR)
        # UNCHANGED: no background color (use default)

    def _determine_child_state(self, old_value: Any, new_value: Any) -> DiffState:
        """Determine the state of a child property by comparing old and new values.

        Args:
            old_value: The old child value (None if not present).
            new_value: The new child value (None if not present).

        Returns:
            DiffState enum value.
        """
        # Both None: should not happen in normal usage
        if old_value is None and new_value is None:
            return DiffState.UNCHANGED

        # Old is None but new has value: ADDED
        if old_value is None and new_value is not None:
            return DiffState.ADDED

        # New is None but old has value: DELETED
        if old_value is not None and new_value is None:
            return DiffState.DELETED

        # Both have values: compare them
        # Use equality comparison for simple types
        if old_value == new_value:
            return DiffState.UNCHANGED

        # For complex objects
        # check if they're the same object
        if old_value is new_value:
            return DiffState.UNCHANGED

        # For complex objects where == returns False even when identical
        # (e.g., FreeCAD C++ wrapped objects), compare string representations
        if str(old_value) == str(new_value):
            return DiffState.UNCHANGED

        # Values differ: MODIFIED
        return DiffState.MODIFIED

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
