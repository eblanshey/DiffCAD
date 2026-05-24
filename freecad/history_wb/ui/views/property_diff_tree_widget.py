"""File responsibility: Property diff tree widget for displaying grouped old/new property values."""

from typing import Any

from ...domain.config import FLOAT_PRECISION as DEFAULT_FLOAT_PRECISION
from ...domain.diff.models import DiffState
from ...domain.settings import SettingsRepository
from ...qt import QtCore, QtGui, QtWidgets
from ...utils import format_float, translate
from ..presenters.presentation_models import PropertyPresentation
from .diff_theme import DIFF_STATE_ROLE, DiffItemDelegate, background_for_state, foreground_for_background


__all__ = ["PropertyDiffTreeWidget"]


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

    result = [name[0]]
    upper_sequence_start = 0 if name[0].isupper() else -1
    for i in range(1, len(name)):
        char = name[i]
        prev_char = name[i - 1]
        should_insert_space = _should_insert_space_before_char(char, prev_char, upper_sequence_start, i, name)
        if should_insert_space:
            result.append(" ")
        upper_sequence_start = _update_upper_sequence_start(char, upper_sequence_start, i, name)
        result.append(char)
    return "".join(result)


def _should_insert_space_before_char(
    char: str, prev_char: str, upper_sequence_start: int, index: int, name: str
) -> bool:
    """Determine if a space should be inserted before the current character."""
    if char.isupper():
        if prev_char.islower():
            return True
        if upper_sequence_start >= 0 and index + 1 < len(name) and name[index + 1].islower():
            return True
    elif char.isdigit():
        if prev_char.isalpha():
            return True
    return False


def _update_upper_sequence_start(char: str, upper_sequence_start: int, index: int, name: str) -> int:
    """Update the upper sequence start position based on current character."""
    if char.isupper():
        return index
    return -1


class _PropertyValueDelegate(DiffItemDelegate):
    """Delegate allowing double-click text selection without persisting edits."""

    def createEditor(
        self, parent: QtWidgets.QWidget, option: QtWidgets.QStyleOptionViewItem, index
    ) -> QtWidgets.QWidget:  # type: ignore[override]
        """Create editor widget for inline editing.

        Creates a QLineEdit configured for text selection without frame styling.

        Args:
            parent: Parent widget for the editor.
            option: Style options for the editor.
            index: Model index being edited.

        Returns:
            QLineEdit configured for value display and selection.
        """
        editor = QtWidgets.QLineEdit(parent)
        editor.setFrame(False)
        editor.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft)
        return editor

    def setEditorData(self, editor: QtWidgets.QLineEdit, index) -> None:  # type: ignore[override]
        """Populate editor with current model data.

        Extracts the display text from the model and sets it in the editor,
        automatically selecting all text for easy copying.

        Args:
            editor: The QLineEdit editor widget.
            index: Model index containing the data to display.
        """
        text = index.model().data(index, QtCore.Qt.ItemDataRole.DisplayRole)
        if text is not None:
            editor.setText(str(text))
            editor.selectAll()

    def setModelData(self, editor: QtWidgets.QLineEdit, model, index) -> None:  # type: ignore[override]
        """Ignore editor data changes (read-only mode).

        This delegate is used for read-only display with text selection.
        Override prevents any user edits from being written back to the model.

        Args:
            editor: The QLineEdit editor widget (ignored).
            model: The item model (ignored).
            index: Model index (ignored).
        """
        pass

    def updateEditorGeometry(
        self,
        editor: QtWidgets.QWidget,
        option: QtWidgets.QStyleOptionViewItem,
        index,
    ) -> None:  # type: ignore[override]
        """Position editor widget over the cell being edited.

        Args:
            editor: The QLineEdit editor widget.
            option: Style options containing the cell rectangle.
            index: Model index being edited.
        """
        editor.setGeometry(option.rect)  # type: ignore[attr-defined]


class PropertyDiffTreeWidget(QtWidgets.QTreeWidget):
    """Widget that renders grouped property diffs in three columns."""

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings_repo = settings_repo
        self._default_precision = DEFAULT_FLOAT_PRECISION
        self._property_value_delegate = _PropertyValueDelegate(self)
        self._setup_tree()

    def _setup_tree(self) -> None:
        self.setColumnCount(3)
        self.setHeaderLabels(
            [
                translate("History", "Property"),
                translate("History", "Old Value"),
                translate("History", "New Value"),
            ]
        )
        self.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.header().setStretchLastSection(True)
        self.setItemDelegate(self._property_value_delegate)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked)

    def clear_property_diff(self) -> None:
        """Clear all property diff entries from the tree widget."""
        self.clear()

    def show_property_diff(self, properties: list[PropertyPresentation]) -> None:
        """Render property diffs grouped by their group name.

        Groups properties by their 'group' attribute (defaulting to "Properties"),
        creates group headers with gray backgrounds, and displays each property
        with old/new values colored according to their diff state.

        Args:
            properties: List of PropertyPresentation objects to display.
        """
        self.clear_property_diff()
        if not properties:
            return

        groups: dict[str, list[PropertyPresentation]] = {}
        for prop in properties:
            group_name = getattr(prop, "group", None) or translate("History", "Properties")
            groups.setdefault(group_name, []).append(prop)

        for group_name in sorted(groups.keys()):
            group_item = self._create_group_header_item(group_name)
            self.addTopLevelItem(group_item)
            for prop in groups[group_name]:
                group_item.addChild(self._create_property_tree_item(prop))
            group_item.setExpanded(True)

        self._apply_expansion_state()

    def _get_precision(self) -> int:
        if self._settings_repo is not None:
            try:
                return self._settings_repo.get_settings().float_precision
            except (AttributeError, RuntimeError):
                pass
        return self._default_precision

    def _create_group_header_item(self, group_name: str) -> QtWidgets.QTreeWidgetItem:
        """Create a non-selectable group header item with gray background.

        Args:
            group_name: The name of the group (e.g., "Base", "Format").

        Returns:
            QTreeWidgetItem configured as a group header.
        """
        item = QtWidgets.QTreeWidgetItem([group_name, "", ""])
        # Make header non-selectable
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
        self._apply_group_header_colors(item)
        # Make the group header bold
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        item.setFont(1, font)
        item.setFont(2, font)
        return item

    def _presentation_has_changes(self, prop: PropertyPresentation) -> bool:
        """Check if a property or any descendant has non-UNCHANGED state.

        Used to determine whether a tree item should be auto-expanded.
        The presenter already computes derived state for parent nodes,
        so this simply recurses through the tree.

        Args:
            prop: The PropertyPresentation to check.

        Returns:
            True if this node or any descendant has a non-UNCHANGED state.
        """
        if prop.state != DiffState.UNCHANGED:
            return True
        return any(self._presentation_has_changes(c) for c in prop.children)

    def _create_property_tree_item(self, prop: PropertyPresentation) -> QtWidgets.QTreeWidgetItem:
        """Create a property tree item with diff coloring and conditional expansion.

        Children are pre-computed by the presenter. Expansion intent is stored
        on the item and applied after the tree is fully built. Row coloring
        comes from PropertyPresentation.state.

        Args:
            prop: The PropertyPresentation to display.

        Returns:
            QTreeWidgetItem with text, color, and children if expandable.
        """
        # Get display values based on state
        bg_color, left_value, right_value = self._get_property_display_values(prop.state, prop)

        # Convert CamelCase to spaced name for display
        display_name = _camelcase_to_spaces(prop.name)

        item = QtWidgets.QTreeWidgetItem([display_name, left_value, right_value])
        # Enable editing on double-click to allow text selection for copying
        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)

        # Set tooltip for the whole row using already-calculated values
        tooltip = self._create_property_tooltip(left_value, right_value)
        item.setToolTip(0, tooltip)
        item.setToolTip(1, tooltip)
        item.setToolTip(2, tooltip)

        # Store expansion intent (will be applied after tree is built)
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, self._presentation_has_changes(prop))

        # Use pre-computed children from domain instead of computing diffs
        self._add_child_items(item, prop.children)

        self._apply_diff_state_to_all_columns(item, prop.state, bg_color)

        return item

    def _format_value_for_display(self, value: Any) -> str:
        """Format a value for display, rounding floats to configured precision.

        Args:
            value: The value to format.

        Returns:
            Formatted string matching FreeCAD's property viewer display.
        """
        precision = self._get_precision()
        if isinstance(value, float):
            return format_float(value, precision)
        return str(value)

    def _get_property_display_values(
        self,
        state: DiffState,
        prop: PropertyPresentation,
    ) -> tuple[QtGui.QColor | None, str, str]:
        """Get background color and display values based on property state.

        For UNCHANGED state, the same value is shown in both columns for
        quick comparison consistency. For ADDED/DELETED/MODIFIED, values
        are shown in the appropriate column.

        Args:
            state: The property state (DiffState enum).
            prop: The PropertyPresentation object.

        Returns:
            Tuple of (background_color, left_column_value, right_column_value).
        """
        if state == DiffState.ADDED:
            new_val = self._format_value_for_display(prop.new_value) if prop.new_value is not None else ""
            return background_for_state(state, self.palette()), "", new_val
        if state == DiffState.DELETED:
            old_val = self._format_value_for_display(prop.old_value) if prop.old_value is not None else ""
            return background_for_state(state, self.palette()), old_val, ""
        if state == DiffState.MODIFIED:
            old_str = self._format_value_for_display(prop.old_value) if prop.old_value is not None else ""
            new_str = self._format_value_for_display(prop.new_value) if prop.new_value is not None else ""
            return background_for_state(state, self.palette()), old_str, new_str
        # UNCHANGED - show same value in both columns
        new_str = self._format_value_for_display(prop.new_value) if prop.new_value is not None else ""
        return None, new_str, new_str

    def _add_child_items(
        self,
        parent_item: QtWidgets.QTreeWidgetItem,
        children: list[PropertyPresentation],
    ) -> None:
        """Add pre-computed child items to the tree.

        Expansion intent is stored on each child item and applied after
        the tree is fully built in show_property_diff.

        Args:
            parent_item: The parent QTreeWidgetItem to add children to.
            children: Pre-computed PropertyPresentation children from domain.
        """
        for child in children:
            # Get display values based on state
            left_value, right_value = self._get_child_display_values(child)

            # Create child item with CamelCase conversion for display
            display_name = _camelcase_to_spaces(child.name)
            child_item = QtWidgets.QTreeWidgetItem([display_name, left_value, right_value])
            # Enable editing on double-click to allow text selection for copying
            child_item.setFlags(child_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)

            # Set tooltip for the whole row using already-calculated values
            tooltip = self._create_property_tooltip(left_value, right_value)
            child_item.setToolTip(0, tooltip)
            child_item.setToolTip(1, tooltip)
            child_item.setToolTip(2, tooltip)

            # Store expansion intent (will be applied after tree is built)
            child_item.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, self._presentation_has_changes(child))

            self._apply_child_diff_state(child_item, child.state)

            # Recursively add grandchildren (pre-computed, no diffing needed)
            self._add_child_items(child_item, child.children)

            parent_item.addChild(child_item)

    def _get_child_display_values(self, child: PropertyPresentation) -> tuple[str, str]:
        """Get display values for a child based on its state.

        Intentionally show the same value in both columns for UNCHANGED rows.
        This matches existing 3-column diff behavior where unchanged values are mirrored
        left/right for quick comparison consistency.

        Args:
            child: The PropertyPresentation child.

        Returns:
            Tuple of (left_value, right_value) for display.
        """
        old_val = self._format_value_for_display(child.old_value) if child.old_value is not None else ""
        new_val = self._format_value_for_display(child.new_value) if child.new_value is not None else ""
        if child.state == DiffState.ADDED:
            return "", new_val
        if child.state == DiffState.DELETED:
            return old_val, ""
        if child.state == DiffState.MODIFIED:
            return old_val, new_val
        return new_val, new_val

    def _apply_child_diff_state(self, child_item: QtWidgets.QTreeWidgetItem, state: DiffState) -> None:
        """Apply semantic diff color to a child item based on its state.

        Args:
            child_item: The child QTreeWidgetItem.
            state: The state of the child (DiffState enum).
        """
        self._apply_diff_state_to_all_columns(child_item, state, background_for_state(state, self.palette()))

    def _apply_diff_state_to_all_columns(
        self, item: QtWidgets.QTreeWidgetItem, state: DiffState, color: QtGui.QColor | None
    ) -> None:
        """Apply diff state data and optional background to all 3 columns.

        Args:
            item: The QTreeWidgetItem to apply background to.
            color: The QColor to use as background.
        """
        if color is None:
            return
        foreground = foreground_for_background(color, self.palette())
        for column in range(3):
            item.setData(column, DIFF_STATE_ROLE, state)
            item.setBackground(column, QtGui.QBrush(color))
            item.setForeground(column, QtGui.QBrush(foreground))

    def _apply_group_header_colors(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Apply theme palette colors to group header row."""
        background = self.palette().color(QtGui.QPalette.ColorRole.AlternateBase)
        if not background.isValid() or background == self.palette().color(QtGui.QPalette.ColorRole.Base):
            background = self.palette().color(QtGui.QPalette.ColorRole.Button)
        foreground = foreground_for_background(background, self.palette())
        for column in range(3):
            item.setBackground(column, QtGui.QBrush(background))
            item.setForeground(column, QtGui.QBrush(foreground))

    def _create_property_tooltip(self, old_value_str: str, new_value_str: str) -> str:
        """Create tooltip text for a property row.

        Format:
            [old value]
            -----
            [new value]

        Args:
            old_value_str: Already-formatted old value string.
            new_value_str: Already-formatted new value string.

        Returns:
            Tooltip text string.
        """
        return f"{old_value_str}\n-----\n{new_value_str}"

    def _apply_expansion_state(self) -> None:
        """Apply stored expansion state to all items in the tree.

        This is called after the tree is fully built because QTreeWidgetItem.setExpanded()
        only works on items that are already part of a visible tree widget.
        """
        for i in range(self.topLevelItemCount()):
            self._apply_expansion_recursive(self.topLevelItem(i))

    def _apply_expansion_recursive(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Recursively apply expansion state to an item and its children.

        Args:
            item: The QTreeWidgetItem to apply expansion to.
        """
        expand = item.data(0, QtCore.Qt.ItemDataRole.UserRole + 1)
        if expand:
            item.setExpanded(True)
        for i in range(item.childCount()):
            self._apply_expansion_recursive(item.child(i))
