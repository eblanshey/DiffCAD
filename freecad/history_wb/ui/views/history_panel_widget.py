"""File responsibility: History panel widget for project info, snapshots, and iterations."""

from collections.abc import Callable
from datetime import datetime, timedelta

from ...application.actions.result_models import SnapshotSummary
from ...domain.git.models import GitCommit, GitRepository
from ...qt import QtCore, QtGui, QtWidgets
from ...resources import get_icon_path
from ...utils import translate
from .models import HistorySelection


__all__ = ["HistoryPanelWidget"]

_REFRESH_ICON: QtGui.QIcon = QtGui.QIcon(str(get_icon_path("RefreshRepository.svg")))


class _HistoryListItemWidget(QtWidgets.QWidget):
    """Styled widget used for history list items."""

    def __init__(
        self,
        *,
        left_text: str = "",
        center_text: str = "",
        right_text: str = "",
        bottom_text: str = "",
        is_bottom_bold: bool = False,
        centered_text: str | None = None,
    ) -> None:
        QtWidgets.QWidget.__init__(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 0)
        layout.setSpacing(6)

        if centered_text is not None:
            centered_label = QtWidgets.QLabel(centered_text)
            centered_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(centered_label)
        else:
            top_row = QtWidgets.QHBoxLayout()
            top_row.setContentsMargins(0, 0, 0, 0)
            top_row.setSpacing(8)

            left_label = QtWidgets.QLabel(left_text)
            left_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            left_label.setStyleSheet("font-weight: 700;")

            center_label = QtWidgets.QLabel(center_text)
            center_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            right_label = QtWidgets.QLabel(right_text)
            right_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)

            top_row.addWidget(left_label, 1)
            top_row.addWidget(center_label, 1)
            top_row.addWidget(right_label, 1)
            layout.addLayout(top_row)

            bottom_label = QtWidgets.QLabel(bottom_text)
            bottom_label.setWordWrap(True)
            bottom_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            if is_bottom_bold:
                bottom_label.setStyleSheet("font-weight: 700;")
            layout.addWidget(bottom_label)

        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: black;")
        layout.addWidget(separator)


class HistoryPanelWidget(QtWidgets.QWidget):
    """Left-column widget for repository header and history list."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_history_selection_callback: Callable[[HistorySelection], None] | None = None
        self._on_history_scroll_bottom_callback: Callable[[], None] | None = None
        self._on_refresh_callback: Callable[[], None] | None = None
        self._on_selection_changed_callback: Callable[[HistorySelection | None], None] | None = None
        self._current_selection: HistorySelection | None = None
        self._history_scroll_bottom_armed = True
        self._setup_ui()

    @property
    def history_list(self) -> QtWidgets.QListWidget:
        """Expose list widget for facade compatibility and tests."""
        return self._history_list

    def _setup_ui(self) -> None:
        self._history_list = QtWidgets.QListWidget()
        self._history_list.setMinimumWidth(150)
        self._history_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._history_list.setWordWrap(True)
        self._history_list.setSpacing(0)

        history_placeholder = QtWidgets.QLabel(translate("History", "Iterations"))
        history_placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        self._repository_label = QtWidgets.QLabel("")
        self._repository_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self._repository_label.setStyleSheet("font-size: 11px; color: gray; font-style: italic;")

        self._refresh_button = QtWidgets.QPushButton()
        self._refresh_button.setIcon(_REFRESH_ICON)
        self._refresh_button.setIconSize(QtCore.QSize(24, 24))
        refresh_tooltip = translate("History", "Refresh Project and Iterations")
        self._refresh_button.setToolTip(refresh_tooltip)

        repository_header_layout = QtWidgets.QHBoxLayout()
        repository_header_layout.setContentsMargins(0, 0, 0, 0)
        repository_header_layout.setSpacing(6)
        repository_header_layout.addWidget(self._repository_label, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        repository_header_layout.addStretch()
        repository_header_layout.addWidget(self._refresh_button, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)

        repository_header_container = QtWidgets.QWidget()
        repository_header_container.setLayout(repository_header_layout)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(repository_header_container)
        layout.addWidget(history_placeholder)
        layout.addWidget(self._history_list)

    def set_selection_changed_callback(self, callback: Callable[[HistorySelection | None], None]) -> None:
        """Set internal callback used by DiffPanelView to mirror selection state."""
        self._on_selection_changed_callback = callback

    def get_current_history_selection(self) -> HistorySelection | None:
        """Return currently selected history entry."""
        return self._current_selection

    def set_refresh_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to invoke when refresh button is clicked.

        Args:
            callback: A no-argument callable to invoke on refresh.
        """
        self._on_refresh_callback = callback
        self._refresh_button.clicked.connect(callback)

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
        self._history_list.clear()

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
            item = QtWidgets.QListWidgetItem(display_text)

            # Store snapshot ID in UserRole for later retrieval
            item.setData(QtCore.Qt.ItemDataRole.UserRole, snapshot.id)

            # Add to list
            self._history_list.addItem(item)

    def show_commits(self, commits: list[GitCommit]) -> None:
        """Display git commits in the history list.

        The list always starts with two special items: "In Progress" and "Reviewed"
        when displaying git commits. These items use HistorySelection dataclass
        to distinguish them from actual GitCommits.

        Args:
            commits: List of GitCommit objects to display. Commits are shown
                in DESC order (newest first) with 7-char hash, author, timestamp
                on line 1, and first line of message on line 2. Full commit
                message is shown in tooltip.
        """
        # Preserve previous selection so refresh can restore it if still present.
        previous_selection = self._current_selection

        # Clear existing items
        self._history_list.clear()

        # Add special items first: "In Progress" and "Reviewed"
        # These are always present, even if no commits are provided

        # Add "In Progress" item
        working_tree_text = translate("History", "In Progress")
        staging_text = translate("History", "Reviewed")

        working_tree_item = QtWidgets.QListWidgetItem(working_tree_text)
        working_tree_item.setData(QtCore.Qt.ItemDataRole.TextAlignmentRole, QtCore.Qt.AlignmentFlag.AlignCenter)
        working_tree_item.setData(
            QtCore.Qt.ItemDataRole.UserRole,
            HistorySelection(item_kind="WORKING_TREE", commit_hash=None),
        )
        self._history_list.addItem(working_tree_item)
        self._history_list.setItemWidget(
            working_tree_item,
            _HistoryListItemWidget(centered_text=working_tree_text),
        )
        working_tree_item.setText("")
        working_tree_item.setSizeHint(self._history_list.itemWidget(working_tree_item).sizeHint())

        # Add "Reviewed" item
        staging_item = QtWidgets.QListWidgetItem(staging_text)
        staging_item.setData(QtCore.Qt.ItemDataRole.TextAlignmentRole, QtCore.Qt.AlignmentFlag.AlignCenter)
        staging_item.setData(
            QtCore.Qt.ItemDataRole.UserRole,
            HistorySelection(item_kind="STAGING", commit_hash=None),
        )
        self._history_list.addItem(staging_item)
        self._history_list.setItemWidget(staging_item, _HistoryListItemWidget(centered_text=staging_text))
        staging_item.setText("")
        staging_item.setSizeHint(self._history_list.itemWidget(staging_item).sizeHint())

        # Guard: no commits to display after adding special items
        if not commits:
            self._restore_history_selection(previous_selection)
            return

        # Note: Commits are already sorted by timestamp (newest first) by GitPortAdapter.get_commits()
        # using git log which returns commits in DESC order by default. No additional sorting needed.
        sorted_commits = commits

        self.append_commits(sorted_commits)

        # Restore previous user selection if possible; otherwise leave history unselected.
        self._restore_history_selection(previous_selection)

    def set_history_selection_callback(self, callback: Callable[[HistorySelection], None]) -> None:
        """Set the callback for history list selection.

        Args:
            callback: A callable that receives HistorySelection with item_kind and commit_hash
        """
        self._on_history_selection_callback = callback
        # Connect to item clicked signal for immediate response
        self._history_list.itemClicked.connect(self._on_item_clicked)

    def set_history_scroll_bottom_callback(self, callback: Callable[[], None]) -> None:
        """Set callback invoked when history list is near scroll bottom."""
        self._on_history_scroll_bottom_callback = callback
        self._history_scroll_bottom_armed = True
        self._history_list.verticalScrollBar().valueChanged.connect(self._on_history_scrollbar_value_changed)

    def append_commits(self, commits: list[GitCommit]) -> None:
        """Append commit entries after existing history rows."""
        for commit in commits:
            # Truncate hash to 7 characters for display
            short_hash = commit.id[:7] if len(commit.id) >= 7 else commit.id

            # Format line 1: hash, author, timestamp
            timestamp_str = self._format_commit_timestamp(commit.timestamp)

            # Get first line of message for line 2
            first_line = commit.message.split("\n")[0].strip() if commit.message and commit.message.strip() else ""

            # Create display text with newline for two-line format
            display_text = f"{short_hash} {commit.author} {timestamp_str}\n{first_line}"

            # Create list item
            item = QtWidgets.QListWidgetItem(display_text)

            # Set tooltip to full commit message
            item.setToolTip(commit.message)

            # Set left alignment for commits
            item.setData(QtCore.Qt.ItemDataRole.TextAlignmentRole, QtCore.Qt.AlignmentFlag.AlignLeft)

            # Store HistorySelection with COMMIT kind
            item.setData(
                QtCore.Qt.ItemDataRole.UserRole,
                HistorySelection(item_kind="COMMIT", commit_hash=commit.id),
            )

            # Add to list
            self._history_list.addItem(item)
            item.setText("")
            commit_widget = _HistoryListItemWidget(
                left_text=short_hash,
                center_text=commit.author,
                right_text=timestamp_str,
                bottom_text=first_line,
            )
            self._history_list.setItemWidget(item, commit_widget)
            item.setSizeHint(commit_widget.sizeHint())

    def _set_current_selection(self, selection: HistorySelection | None) -> None:
        """Set current selection and notify callbacks."""
        self._current_selection = selection
        if self._on_selection_changed_callback is not None:
            self._on_selection_changed_callback(selection)

    def _on_item_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
        """Handle item click by tracking selection and triggering callback."""
        item_data = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(item_data, HistorySelection):
            # Track selection state for button visibility
            self._set_current_selection(item_data)
            if self._on_history_selection_callback is not None:
                self._on_history_selection_callback(item_data)

    def _on_history_scrollbar_value_changed(self, value: int) -> None:
        """Notify callback when history scrollbar is near bottom."""
        if self._on_history_scroll_bottom_callback is None:
            return

        scrollbar = self._history_list.verticalScrollBar()
        maximum = scrollbar.maximum()
        if maximum <= 0:
            return

        # Re-arm once user scrolls out of bottom area.
        if value <= int(maximum * 0.7):
            self._history_scroll_bottom_armed = True

        # Fire near bottom (last ~15% of scroll range), once until re-armed.
        if self._history_scroll_bottom_armed and value >= int(maximum * 0.85):
            self._history_scroll_bottom_armed = False
            self._on_history_scroll_bottom_callback()

    def _select_history_item(self, selection: HistorySelection) -> bool:
        """Select a history item by ``HistorySelection`` and trigger callback.

        Args:
            selection: Selection model to locate in the history list.

        Returns:
            True if a matching item was found and selected, False otherwise.
        """
        for row in range(self._history_list.count()):
            item = self._history_list.item(row)
            if item is None:
                continue
            item_data = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if item_data == selection:
                self._history_list.setCurrentItem(item)
                self._set_current_selection(selection)
                if self._on_history_selection_callback is not None:
                    self._on_history_selection_callback(selection)
                return True

        return False

    def _restore_history_selection(self, previous_selection: HistorySelection | None) -> None:
        """Restore previous history selection if present in the refreshed list.

        Args:
            previous_selection: Previously selected history item, if any.
        """
        self._history_list.clearSelection()
        self._history_list.setCurrentRow(-1)

        if previous_selection is None:
            self._set_current_selection(None)
            return

        if not self._select_history_item(previous_selection):
            self._set_current_selection(None)

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

    def _format_commit_timestamp(self, timestamp: datetime) -> str:
        """Format commit timestamp in a human-friendly way.

        Rules:
        - Today: show only time (e.g., "2:45 PM")
        - Yesterday: show "Yesterday <time>"
        - This year: show "Mon D <time>"
        - Older years: show "Mon D, YYYY <time>"

        Args:
            timestamp: Commit datetime to format.

        Returns:
            Human-friendly timestamp string for commit rows.
        """
        local_timestamp = timestamp.astimezone() if timestamp.tzinfo is not None else timestamp
        now = datetime.now(local_timestamp.tzinfo) if local_timestamp.tzinfo is not None else datetime.now()

        def _time(dt: datetime) -> str:
            return dt.strftime("%I:%M %p").lstrip("0")

        if local_timestamp.date() == now.date():
            return _time(local_timestamp)

        if local_timestamp.date() == (now - timedelta(days=1)).date():
            yesterday_label = translate("History", "Yesterday")
            return f"{yesterday_label} {_time(local_timestamp)}"

        if local_timestamp.year == now.year:
            return local_timestamp.strftime("%b %d ").replace(" 0", " ") + _time(local_timestamp)

        return local_timestamp.strftime("%b %d, %Y ").replace(" 0", " ") + _time(local_timestamp)

    def show_repository(self, repo: GitRepository | None) -> None:
        """Display git repository info above snapshot list.

        Args:
            repo: GitRepository object if detected, or None if no repository found.
                  If None, shows "No git repository detected".
        """
        if repo is None:
            text = translate("History", "No project detected")
            self._repository_label.setText(text)
            self._repository_label.setToolTip("")
            self._repository_label.setStyleSheet("font-size: 11px; color: gray; font-style: italic;")
        else:
            name = repo.name
            path = repo.absolute_path
            template = translate("History", "Project: %1")
            # Replace Qt-style placeholders (%1) with repository name
            text = template.replace("%1", name)
            self._repository_label.setText(text)
            # Set tooltip with full directory path
            self._repository_label.setToolTip(path)
            # Style with underline to indicate clickable/tooltip
            self._repository_label.setStyleSheet("font-size: 11px; font-weight: bold; text-decoration: underline;")
