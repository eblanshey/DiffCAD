"""File responsibility: Diff panel view with 3-column layout, implementing DiffView and SnapshotView protocols."""

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QListWidget,
    QSplitter,
    QTableWidget,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from ..presenters.presentation_models import NodePresentation


class DiffPanelView(QWidget):
    """Empty 3-column diff panel view implementing DiffView and SnapshotView protocols.

    Provides a horizontal QSplitter with:
    - Left: Placeholder for snapshots list (visible)
    - Middle: QTreeWidget for diff tree (hidden/empty)
    - Right: QTableWidget for properties (hidden/empty)

    Phase 8: Empty stubs - panel shows placeholder text only.

    Note: This class implements the DiffView and SnapshotView protocols through
    structural subtyping (duck typing) rather than explicit inheritance to avoid
    metaclass conflicts between QWidget and Protocol classes.
    """

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the 3-column layout with placeholders."""
        layout = QVBoxLayout(self)

        # Create horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Column 1: Snapshots list (always visible)
        self.snapshot_list = QListWidget()
        self.snapshot_list.setMinimumWidth(150)
        snapshot_placeholder = QLabel("Snapshots")
        snapshot_placeholder.setAlignment(Qt.AlignmentFlag.AlignLeft)
        snapshot_layout = QVBoxLayout()
        snapshot_layout.addWidget(snapshot_placeholder)
        snapshot_layout.addWidget(self.snapshot_list)
        snapshot_container = QWidget()
        snapshot_container.setLayout(snapshot_layout)

        # Column 2: Tree view (hidden initially)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Tree"])
        self.tree_widget.setColumnCount(1)
        self.tree_widget.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # self.tree_widget.hide()  # Hide until data available

        # Column 3: Properties table (hidden initially)
        self.properties_table = QTableWidget()
        self.properties_table.setColumnCount(2)
        self.properties_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.properties_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # self.properties_table.hide()  # Hide until data available

        # Add to splitter
        splitter.addWidget(snapshot_container)
        splitter.addWidget(self.tree_widget)
        splitter.addWidget(self.properties_table)

        # Set initial sizes (equal thirds)
        splitter.setSizes([200, 200, 200])

        # Set minimum size for the panel
        self.setMinimumSize(450, 200)

        layout.addWidget(splitter)

    # SnapshotView protocol methods (Phase 8 stubs)
    def show_success(self, snapshot_name: str) -> None:
        """Show success message after taking snapshot."""
        # Phase 8: No implementation - will populate list in Phase 9
        pass

    def show_error(self, error_message: str) -> None:
        """Show error message."""
        # Phase 8: No implementation
        pass

    def show_loading(
        self,
        message: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Show loading indicator."""
        # Phase 8: No implementation
        pass

    # DiffView protocol methods (Phase 8 stubs)
    def show_diff_tree(self, nodes: list[NodePresentation]) -> None:
        """Display the diff tree."""
        # Phase 8: No implementation - tree stays hidden
        pass

    def show_summary(self, added: int, deleted: int, modified: int) -> None:
        """Display the diff summary counts."""
        # Phase 8: No implementation
        pass
