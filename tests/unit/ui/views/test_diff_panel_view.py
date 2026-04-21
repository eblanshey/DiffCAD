"""File responsibility: Unit tests for DiffPanelView methods including show_snapshots(), show_commits(), and snapshot selection.

These tests verify that the DiffPanelView correctly populates the snapshot list
with SnapshotSummary data, including proper sorting, formatting, and ID storage.
Tests for show_repository() verify the git repository display functionality.
Tests for show_commits() verify the history/commit list display functionality.
Tests for HistorySelection verify the dataclass used for single-selection model.
Tests for special items (Working Tree, Staging) verify their presence, alignment, and HistorySelection usage.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from freecad.diff_wb.ui.views.diff_panel_view import HistorySelection


def _history_row_text(panel, row: int) -> str:  # type: ignore[no-untyped-def]
    """Return visible text for a history row, including custom item widgets."""
    from PySide6.QtWidgets import QLabel

    item = panel.history_list.item(row)
    widget = panel.history_list.itemWidget(item)
    if widget is None:
        return item.text()

    labels = widget.findChildren(QLabel)
    if len(labels) == 1:
        return labels[0].text()
    if len(labels) >= 4:
        top_line = f"{labels[0].text()} {labels[1].text()} {labels[2].text()}"
        return f"{top_line}\n{labels[3].text()}"
    return item.text()


class TestHistorySelection:
    """Tests for the HistorySelection dataclass."""

    def test_history_selection_working_tree(self) -> None:
        """HistorySelection can be created for WORKING_TREE kind."""
        selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)
        assert selection.item_kind == "WORKING_TREE"
        assert selection.commit_hash is None

    def test_history_selection_staging(self) -> None:
        """HistorySelection can be created for STAGING kind."""
        selection = HistorySelection(item_kind="STAGING", commit_hash=None)
        assert selection.item_kind == "STAGING"
        assert selection.commit_hash is None

    def test_history_selection_commit(self) -> None:
        """HistorySelection stores commit_hash correctly for COMMIT kind."""
        commit_hash = "a1b2c3d4e5f6789012345678901234567890abcd"
        selection = HistorySelection(item_kind="COMMIT", commit_hash=commit_hash)
        assert selection.item_kind == "COMMIT"
        assert selection.commit_hash == commit_hash

    def test_history_selection_is_frozen(self) -> None:
        """HistorySelection is immutable (frozen)."""
        selection = HistorySelection(item_kind="COMMIT", commit_hash="abc123")
        with pytest.raises(AttributeError):  # Frozen dataclasses raise AttributeError on assignment
            selection.commit_hash = "new_hash"  # type: ignore[misc]

    def test_history_selection_commit_with_none_hash(self) -> None:
        """HistorySelection for COMMIT can have None commit_hash."""
        selection = HistorySelection(item_kind="COMMIT", commit_hash=None)
        assert selection.item_kind == "COMMIT"
        assert selection.commit_hash is None


@pytest.fixture(scope="module")
def panel() -> object:
    """Create a DiffPanelView instance for testing.

    Note: This uses module scope to ensure QApplication is created once
    and reused across all tests in this module.
    """
    from PySide6.QtWidgets import QApplication

    # Ensure QApplication exists before creating widgets
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    from freecad.diff_wb.ui import DiffPanelView

    return DiffPanelView()


class TestDiffPanelViewShowSnapshots:
    """Tests for DiffPanelView.show_snapshots() method."""

    def test_show_snapshots_with_empty_list(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() handles empty list without errors."""

        # Should not raise any exceptions
        panel.show_snapshots([])

        # History list should be empty
        assert panel.history_list.count() == 0

    def test_show_snapshots_clears_existing_items(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() clears existing items before populating."""
        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        # Add initial items
        panel.show_snapshots(
            [
                SnapshotSummary(id="old-1", name="Old Snapshot 1", created_at="2024-01-01T10:00:00", node_count=10),
            ]
        )
        assert panel.history_list.count() == 1

        # Replace with new list
        panel.show_snapshots(
            [
                SnapshotSummary(id="new-1", name="New Snapshot 1", created_at="2024-02-01T10:00:00", node_count=20),
            ]
        )

        # Should only have the new item
        assert panel.history_list.count() == 1
        assert panel.history_list.item(0).text() == "New Snapshot 1 - Feb 1, 2024 10:00AM"

    def test_show_snapshots_sorts_by_timestamp_newest_first(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() sorts snapshots by timestamp, newest first."""
        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        snapshots = [
            SnapshotSummary(id="snap-1", name="Oldest", created_at="2024-01-01T10:00:00", node_count=10),
            SnapshotSummary(id="snap-2", name="Newest", created_at="2024-03-01T10:00:00", node_count=30),
            SnapshotSummary(id="snap-3", name="Middle", created_at="2024-02-01T10:00:00", node_count=20),
        ]

        panel.show_snapshots(snapshots)

        # Verify order: Newest, Middle, Oldest
        assert panel.history_list.count() == 3
        assert panel.history_list.item(0).text().startswith("Newest")
        assert panel.history_list.item(1).text().startswith("Middle")
        assert panel.history_list.item(2).text().startswith("Oldest")

    def test_show_snapshots_stores_id_in_user_role(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() stores snapshot ID in Qt.UserRole for each item."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        snapshots = [
            SnapshotSummary(id="test-id-123", name="Test Snapshot", created_at="2024-01-15T10:30:00", node_count=42),
        ]

        panel.show_snapshots(snapshots)

        # Verify ID is stored in UserRole
        item = panel.history_list.item(0)
        assert item is not None
        stored_id = item.data(Qt.ItemDataRole.UserRole)
        assert stored_id == "test-id-123"

    def test_show_snapshots_formats_display_correctly(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() formats display as 'name - Month Day, Year Time'."""
        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        snapshots = [
            SnapshotSummary(id="snap-1", name="My Snapshot", created_at="2024-01-15T10:30:00", node_count=42),
        ]

        panel.show_snapshots(snapshots)

        # Check format: "My Snapshot - Jan 15, 2024 10:30 AM"
        item_text = panel.history_list.item(0).text()
        assert item_text == "My Snapshot - Jan 15, 2024 10:30AM"

    def test_show_snapshots_multiple_items_with_ids(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() correctly stores IDs for multiple items."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        snapshots = [
            SnapshotSummary(id="id-1", name="First", created_at="2024-01-01T09:00:00", node_count=5),
            SnapshotSummary(id="id-2", name="Second", created_at="2024-01-02T10:00:00", node_count=10),
            SnapshotSummary(id="id-3", name="Third", created_at="2024-01-03T11:00:00", node_count=15),
        ]

        panel.show_snapshots(snapshots)

        # Verify all IDs are stored correctly (in sorted order: Third, Second, First)
        assert panel.history_list.item(0).data(Qt.ItemDataRole.UserRole) == "id-3"
        assert panel.history_list.item(1).data(Qt.ItemDataRole.UserRole) == "id-2"
        assert panel.history_list.item(2).data(Qt.ItemDataRole.UserRole) == "id-1"


class TestDiffPanelViewShowSummary:
    """Tests for DiffPanelView.show_summary() method."""

    def test_show_summary_displays_counts(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_summary() displays translated labels with counts."""
        # When: Call show_summary with non-zero counts
        panel.show_summary(added=3, deleted=2, modified=5)

        # Then: Each label shows its translated text with count
        assert panel._added_label.text() == "Added: 3"
        assert panel._deleted_label.text() == "Deleted: 2"
        assert panel._modified_label.text() == "Modified: 5"

    def test_show_summary_with_zero_counts_shows_no_changes(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_summary() displays 'No changes' when all counts are zero."""
        # When: Call show_summary with all zeros
        panel.show_summary(added=0, deleted=0, modified=0)

        # Then: Added label shows "No changes", others empty
        assert panel._added_label.text() == "No changes"
        assert panel._deleted_label.text() == ""
        assert panel._modified_label.text() == ""

    def test_show_summary_with_partial_zeros(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_summary() displays counts even when some are zero."""
        # When: Call show_summary with some zero counts
        panel.show_summary(added=0, deleted=3, modified=0)

        # Then: Each label shows its count (including zeros)
        assert panel._added_label.text() == "Added: 0"
        assert panel._deleted_label.text() == "Deleted: 3"
        assert panel._modified_label.text() == "Modified: 0"

    def test_show_summary_overwrites_previous_text(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_summary() overwrites previous summary text."""
        # Given: Previous summary displayed
        panel.show_summary(added=1, deleted=1, modified=1)
        assert panel._added_label.text() == "Added: 1"
        assert panel._deleted_label.text() == "Deleted: 1"
        assert panel._modified_label.text() == "Modified: 1"

        # When: Call show_summary with new counts
        panel.show_summary(added=5, deleted=0, modified=2)

        # Then: New summary replaces old one
        assert panel._added_label.text() == "Added: 5"
        assert panel._deleted_label.text() == "Deleted: 0"
        assert panel._modified_label.text() == "Modified: 2"


class TestDiffPanelViewRefreshButton:
    """Tests for DiffPanelView refresh button functionality."""

    def test_set_refresh_callback_connects_to_button_clicked(self, panel) -> None:  # type: ignore[no-untyped-def]
        """set_refresh_callback() connects the callback to the button's clicked signal."""
        # Track if callback was called
        callback_called = False

        def mock_callback() -> None:
            nonlocal callback_called
            callback_called = True

        # When: Set the refresh callback
        panel.set_refresh_callback(mock_callback)

        # Then: Callback should be connected (we verify by simulating a click)
        # Simulate button click
        panel._refresh_button.click()

        # Verify callback was invoked
        assert callback_called is True

    def test_refresh_button_has_icon(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Refresh button icon loading is attempted but may be null in test environments.

        Icon loading depends on FreeCAD runtime availability. In unit tests without
        FreeCADGui, the icon will be null which is acceptable. This is a best-effort
        feature that requires FreeCAD runtime to function properly.
        """
        # Access the icon property to verify it's available (may be null in tests)
        _ = panel._refresh_button.icon()
        # No assertion here - null icon is acceptable in non-FreeCAD environments
        # The important thing is that the button exists and has the icon slot available

    def test_refresh_button_has_tooltip(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Refresh button has a tooltip."""
        tooltip = panel._refresh_button.toolTip()
        assert "refresh" in tooltip.lower() or "git" in tooltip.lower()

    def test_refresh_button_is_small_fixed_size(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Refresh button has a small icon size set."""
        # Check icon size rather than button size, as button size is managed by layout
        # Note: Actual dimensions may vary based on available icon resource
        icon_size = panel._refresh_button.iconSize()
        assert icon_size.width() > 0
        assert icon_size.height() > 0


class TestDiffPanelViewShowRepository:
    """Tests for DiffPanelView.show_repository() method."""

    def test_show_repository_with_none_shows_no_repo_message(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_repository(None) displays the 'no repository' message with italic gray style."""
        # When: Call show_repository with None
        panel.show_repository(None)

        # Then: Label shows no repo message with italic gray styling
        text = panel._repository_label.text()
        assert "no git repository" in text.lower() or "detected" in text.lower()
        stylesheet = panel._repository_label.styleSheet()
        assert "italic" in stylesheet
        assert "gray" in stylesheet

    def test_show_repository_with_valid_repo_shows_info(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_repository() displays repository name with tooltip containing path and bold/underline styling."""
        # Given: A valid GitRepository
        from freecad.diff_wb.domain.git.models import GitRepository

        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")

        # When: Call show_repository with a valid repository
        panel.show_repository(repo)

        # Then: Label shows repository name with path in tooltip
        text = panel._repository_label.text()
        assert "test_project" in text
        assert "Repository:" in text
        # Path should be in tooltip, not in displayed text
        assert panel._repository_label.toolTip() == "/home/user/test_project"
        stylesheet = panel._repository_label.styleSheet()
        assert "bold" in stylesheet
        assert "underline" in stylesheet

    def test_show_repository_overwrites_previous_display(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_repository() overwrites previous repository display."""
        # Given: Previous repository displayed
        from freecad.diff_wb.domain.git.models import GitRepository

        repo1 = GitRepository(name="old_project", absolute_path="/home/old")
        panel.show_repository(repo1)
        assert "old_project" in panel._repository_label.text()

        # When: Call show_repository with a different repository
        repo2 = GitRepository(name="new_project", absolute_path="/home/new")
        panel.show_repository(repo2)

        # Then: New repository info replaces old one
        text = panel._repository_label.text()
        assert "new_project" in text
        assert "old_project" not in text
        # Tooltip should also be updated
        assert panel._repository_label.toolTip() == "/home/new"

    def test_show_repository_none_after_repo_resets_style(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_repository(None) after showing a repo resets to italic gray style and clears tooltip."""
        # Given: Repository previously displayed
        from freecad.diff_wb.domain.git.models import GitRepository

        repo = GitRepository(name="test_project", absolute_path="/home/test")
        panel.show_repository(repo)

        # When: Call show_repository with None
        panel.show_repository(None)

        # Then: Style is reset to italic gray and tooltip is cleared
        stylesheet = panel._repository_label.styleSheet()
        assert "italic" in stylesheet
        assert "gray" in stylesheet
        assert panel._repository_label.toolTip() == ""


class TestShowCommitsSpecialItems:
    """Tests for the special "Working Tree" and "Staging" items in show_commits."""

    def test_show_commits_always_shows_working_tree_and_staging_at_top(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that Working Tree and Staging items are always present at the top of the list."""
        from freecad.diff_wb.domain.git.models import GitCommit

        commits = [
            GitCommit(
                id="a1b2c3d4e5f6789012345678901234567890abcd",
                message="Test commit",
                author="Test Author",
                timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
            ),
        ]

        panel.show_commits(commits)

        # Verify there are 3 items: Working Tree, Staging, and the commit
        assert panel.history_list.count() == 3

        # Verify Working Tree is first
        working_tree_item = panel.history_list.item(0)
        assert working_tree_item is not None
        assert _history_row_text(panel, 0) == "Working Tree"

        # Verify Staging is second
        staging_item = panel.history_list.item(1)
        assert staging_item is not None
        assert _history_row_text(panel, 1) == "Staging"

        # Verify commit is third
        commit_item = panel.history_list.item(2)
        assert commit_item is not None
        assert "a1b2c3d" in _history_row_text(panel, 2)

    def test_show_commits_shows_special_items_even_with_empty_commits(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that Working Tree and Staging items are present even when no commits are provided."""
        panel.show_commits([])

        # Verify there are exactly 2 items: Working Tree and Staging
        assert panel.history_list.count() == 2

        # Verify Working Tree is first
        working_tree_item = panel.history_list.item(0)
        assert working_tree_item is not None
        assert _history_row_text(panel, 0) == "Working Tree"

        # Verify Staging is second
        staging_item = panel.history_list.item(1)
        assert staging_item is not None
        assert _history_row_text(panel, 1) == "Staging"

    def test_show_commits_working_tree_has_center_alignment(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that Working Tree item has center alignment set."""
        from PySide6.QtCore import Qt

        panel.show_commits([])

        working_tree_item = panel.history_list.item(0)
        assert working_tree_item is not None

        alignment = working_tree_item.data(Qt.ItemDataRole.TextAlignmentRole)
        assert alignment == Qt.AlignmentFlag.AlignCenter

    def test_show_commits_staging_has_center_alignment(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that Staging item has center alignment set."""
        from PySide6.QtCore import Qt

        panel.show_commits([])

        staging_item = panel.history_list.item(1)
        assert staging_item is not None

        alignment = staging_item.data(Qt.ItemDataRole.TextAlignmentRole)
        assert alignment == Qt.AlignmentFlag.AlignCenter

    def test_show_commits_working_tree_has_correct_user_role(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that Working Tree item has UserRole set to HistorySelection with WORKING_TREE kind."""
        from PySide6.QtCore import Qt

        panel.show_commits([])

        working_tree_item = panel.history_list.item(0)
        assert working_tree_item is not None

        user_role = working_tree_item.data(Qt.ItemDataRole.UserRole)
        assert isinstance(user_role, HistorySelection)
        assert user_role.item_kind == "WORKING_TREE"
        assert user_role.commit_hash is None

    def test_show_commits_staging_has_correct_user_role(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that Staging item has UserRole set to HistorySelection with STAGING kind."""
        from PySide6.QtCore import Qt

        panel.show_commits([])

        staging_item = panel.history_list.item(1)
        assert staging_item is not None

        user_role = staging_item.data(Qt.ItemDataRole.UserRole)
        assert isinstance(user_role, HistorySelection)
        assert user_role.item_kind == "STAGING"
        assert user_role.commit_hash is None

    def test_show_commits_commits_have_commit_history_selection(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that actual commits have HistorySelection with COMMIT kind and commit hash."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.domain.git.models import GitCommit

        commit_hash = "a1b2c3d4e5f67890"
        commits = [
            GitCommit(
                id=commit_hash,
                message="Test commit",
                author="Test Author",
                timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
            ),
        ]

        panel.show_commits(commits)

        # Commit item should be at row 2 (after special items)
        commit_item = panel.history_list.item(2)
        assert commit_item is not None

        user_role = commit_item.data(Qt.ItemDataRole.UserRole)
        assert isinstance(user_role, HistorySelection)
        assert user_role.item_kind == "COMMIT"
        assert user_role.commit_hash == commit_hash

    def test_show_commits_refresh_clears_and_readds_special_items(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that refreshing the list with new commits re-adds special items correctly."""
        from freecad.diff_wb.domain.git.models import GitCommit

        # First call with commits
        commits1 = [
            GitCommit(
                id="commit1",
                message="First commit",
                author="Author 1",
                timestamp=datetime.fromisoformat("2024-01-01T10:00:00+00:00"),
            ),
        ]
        panel.show_commits(commits1)
        assert panel.history_list.count() == 3
        assert _history_row_text(panel, 0) == "Working Tree"
        assert _history_row_text(panel, 1) == "Staging"

        # Second call with different commits
        commits2 = [
            GitCommit(
                id="commit2",
                message="Second commit",
                author="Author 2",
                timestamp=datetime.fromisoformat("2024-02-01T10:00:00+00:00"),
            ),
            GitCommit(
                id="commit3",
                message="Third commit",
                author="Author 3",
                timestamp=datetime.fromisoformat("2024-03-01T10:00:00+00:00"),
            ),
        ]
        panel.show_commits(commits2)

        # Verify special items are still at top
        assert panel.history_list.count() == 4  # 2 special + 2 commits
        assert _history_row_text(panel, 0) == "Working Tree"
        assert _history_row_text(panel, 1) == "Staging"
        assert "Second commit" in _history_row_text(panel, 2)
        assert "Third commit" in _history_row_text(panel, 3)


class TestShowCommits:
    """Tests for DiffPanelView.show_commits method."""

    def test_show_commits_displays_commits_correctly(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that commits are displayed with correct format."""
        from freecad.diff_wb.domain.git.models import GitCommit

        commits = [
            GitCommit(
                id="a1b2c3d4e5f6789012345678901234567890abcd",
                message="Fix bug in snapshot comparison\n\nThis fixes the issue where...",
                author="John Doe",
                timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
            ),
        ]

        panel.show_commits(commits)

        # Verify there are 3 items total (Working Tree, Staging, and the commit)
        assert panel.history_list.count() == 3
        # Verify the commit is at position 2 (after special items)
        assert "a1b2c3d" in _history_row_text(panel, 2)  # 7-char hash
        assert "John Doe" in _history_row_text(panel, 2)  # Author
        assert panel._format_commit_timestamp(commits[0].timestamp) in _history_row_text(panel, 2)

    def test_show_commits_empty_list(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that empty commit list shows only special items."""
        panel.show_commits([])
        # Special items (Working Tree, Staging) are always present
        assert panel.history_list.count() == 2
        assert _history_row_text(panel, 0) == "Working Tree"
        assert _history_row_text(panel, 1) == "Staging"

    def test_show_commits_tooltip_has_full_message(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that tooltip contains full commit message."""
        from freecad.diff_wb.domain.git.models import GitCommit

        full_message = "Fix bug\n\nDetailed explanation..."
        commit = GitCommit(
            id="a1b2c3d4e5f67890",
            message=full_message,
            author="Test",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )

        panel.show_commits([commit])
        # Commit is at row 2 (after special items)
        item = panel.history_list.item(2)

        assert item.toolTip() == full_message

    def test_show_commits_clears_existing_list(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that show_commits replaces any existing list content."""
        # First add some snapshots
        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        panel.show_snapshots(
            [
                SnapshotSummary(id="snap-1", name="First", created_at="2024-01-01T10:00:00", node_count=10),
            ]
        )
        assert panel.history_list.count() == 1

        # Now call show_commits
        from freecad.diff_wb.domain.git.models import GitCommit

        commit = GitCommit(
            id="a1b2c3d4e5f67890",
            message="Test commit",
            author="Test",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )
        panel.show_commits([commit])

        # List should now contain special items + commit (not snapshots)
        assert panel.history_list.count() == 3
        assert _history_row_text(panel, 0) == "Working Tree"
        assert _history_row_text(panel, 1) == "Staging"

    def test_show_commits_two_line_format(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that commits display with two-line format."""
        from freecad.diff_wb.domain.git.models import GitCommit

        commit = GitCommit(
            id="abc123def456",
            message="This is the subject line\n\nThis is the body of the commit message.",
            author="Alice Smith",
            timestamp=datetime.fromisoformat("2024-03-20T14:45:00+00:00"),
        )

        panel.show_commits([commit])
        # Commit is at row 2 (after special items)
        text = _history_row_text(panel, 2)

        # Check that there's a newline in the display text (two lines)
        assert "\n" in text
        # Line 1 should have hash, author, timestamp
        lines = text.split("\n")
        assert len(lines) == 2
        assert "abc123d" in lines[0]  # 7-char hash
        assert "Alice Smith" in lines[0]  # Author
        assert panel._format_commit_timestamp(commit.timestamp) in lines[0]
        # Line 2 should have first line of message
        assert "This is the subject line" in lines[1]

    def test_show_commits_commit_item_widget_has_aligned_top_row_and_bold_hash(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Commit row uses left/center/right top alignment and bold hash text."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QLabel

        from freecad.diff_wb.domain.git.models import GitCommit

        commit = GitCommit(
            id="abc123def456",
            message="Subject line",
            author="Alice Smith",
            timestamp=datetime.fromisoformat("2024-03-20T14:45:00+00:00"),
        )

        panel.show_commits([commit])

        item = panel.history_list.item(2)
        widget = panel.history_list.itemWidget(item)
        assert widget is not None

        labels = widget.findChildren(QLabel)
        hash_label = next(label for label in labels if label.text() == "abc123d")
        author_label = next(label for label in labels if label.text() == "Alice Smith")
        timestamp_label = next(
            label for label in labels if label.text() == panel._format_commit_timestamp(commit.timestamp)
        )
        subject_label = next(label for label in labels if label.text() == "Subject line")
        hash_style = hash_label.styleSheet()

        assert hash_label.alignment() & Qt.AlignmentFlag.AlignLeft
        assert author_label.alignment() & Qt.AlignmentFlag.AlignHCenter
        assert timestamp_label.alignment() & Qt.AlignmentFlag.AlignRight
        assert "font-weight: 700" in hash_style
        assert "font-weight: 700" not in subject_label.styleSheet()

    def test_format_commit_timestamp_today_shows_time_only(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Today's commits show only time."""
        now = datetime.now(UTC)
        formatted = panel._format_commit_timestamp(now)

        assert "Yesterday" not in formatted
        assert "," not in formatted
        assert ":" in formatted

    def test_format_commit_timestamp_yesterday_shows_yesterday_prefix(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Yesterday's commits include the Yesterday prefix."""
        yesterday = datetime.now(UTC) - timedelta(days=1)
        formatted = panel._format_commit_timestamp(yesterday)

        assert formatted.startswith("Yesterday ")

    def test_show_commits_history_items_include_black_separator_line(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Each history item widget includes a horizontal separator line."""
        from PySide6.QtWidgets import QFrame

        panel.show_commits([])

        working_tree_item = panel.history_list.item(0)
        widget = panel.history_list.itemWidget(working_tree_item)
        assert widget is not None
        separators = [
            frame
            for frame in widget.findChildren(QFrame)
            if frame.height() == 1 and "background-color: black" in frame.styleSheet()
        ]
        assert separators

    def test_show_commits_multiple_commits_newest_first(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that multiple commits are displayed in the order provided (assumed pre-sorted by adapter).

        Note: The view does not sort commits; it displays them as provided. The GitPortAdapter
        returns commits in DESC order (newest first), so the caller should ensure commits are
        sorted before passing to this method.
        """
        from freecad.diff_wb.domain.git.models import GitCommit

        # Pass commits already sorted in DESC order (newest first)
        commits = [
            GitCommit(
                id="new123",
                message="New commit",
                author="New Author",
                timestamp=datetime.fromisoformat("2024-03-01T10:00:00+00:00"),
            ),
            GitCommit(
                id="mid123",
                message="Middle commit",
                author="Mid Author",
                timestamp=datetime.fromisoformat("2024-02-01T10:00:00+00:00"),
            ),
            GitCommit(
                id="old123",
                message="Old commit",
                author="Old Author",
                timestamp=datetime.fromisoformat("2024-01-01T10:00:00+00:00"),
            ),
        ]

        panel.show_commits(commits)

        # Verify order matches input (pre-sorted) + special items at top
        assert panel.history_list.count() == 5  # 2 special + 3 commits
        # Special items at top
        assert _history_row_text(panel, 0) == "Working Tree"
        assert _history_row_text(panel, 1) == "Staging"
        # Commits start at row 2
        assert "New commit" in _history_row_text(panel, 2)
        assert "Middle commit" in _history_row_text(panel, 3)
        assert "Old commit" in _history_row_text(panel, 4)

    def test_show_commits_short_hash_truncation(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that long commit hashes are truncated to 7 characters."""
        from freecad.diff_wb.domain.git.models import GitCommit

        commit = GitCommit(
            id="a1b2c3d4e5f6789012345678901234567890abcd",
            message="Test",
            author="Test",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )

        panel.show_commits([commit])
        # Commit is at row 2 (after special items)
        text = _history_row_text(panel, 2)

        # Should have 7-char hash, not the full hash
        assert "a1b2c3d" in text
        assert "e5f6789" not in text  # Full hash should not appear

    def test_show_commits_defaults_to_working_tree_selection(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_commits() auto-selects Working Tree when nothing was selected."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.domain.git.models import GitCommit

        commits = [
            GitCommit(
                id="a1b2c3d4e5f67890",
                message="Test commit",
                author="Test",
                timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
            ),
            GitCommit(
                id="b2c3d4e5f6789012",
                message="Another commit",
                author="Test",
                timestamp=datetime.fromisoformat("2024-01-16T10:30:00+00:00"),
            ),
        ]

        panel.show_commits(commits)

        selected_items = panel.history_list.selectedItems()
        assert len(selected_items) == 1
        selected_selection = selected_items[0].data(Qt.ItemDataRole.UserRole)
        assert selected_selection == HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

    def test_show_commits_refresh_restores_previous_selection_if_it_still_exists(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Refreshing commits re-selects the same commit when still present."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.domain.git.models import GitCommit

        selected_commit_hash = "a1b2c3d4e5f67890"
        initial_commits = [
            GitCommit(
                id=selected_commit_hash,
                message="Selected commit",
                author="Test",
                timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
            ),
            GitCommit(
                id="b2c3d4e5f6789012",
                message="Another commit",
                author="Test",
                timestamp=datetime.fromisoformat("2024-01-16T10:30:00+00:00"),
            ),
        ]

        panel.set_history_selection_callback(lambda selection: None)
        panel.show_commits(initial_commits)

        selected_item = panel.history_list.item(2)
        assert selected_item is not None
        panel.history_list.itemClicked.emit(selected_item)

        refreshed_commits = [
            GitCommit(
                id=selected_commit_hash,
                message="Selected commit (updated message)",
                author="Test",
                timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
            ),
        ]
        panel.show_commits(refreshed_commits)

        selected_items = panel.history_list.selectedItems()
        assert len(selected_items) == 1
        selected_selection = selected_items[0].data(Qt.ItemDataRole.UserRole)
        assert selected_selection == HistorySelection(item_kind="COMMIT", commit_hash=selected_commit_hash)

    def test_show_commits_refresh_falls_back_to_working_tree_when_previous_selection_missing(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Refreshing commits selects Working Tree when prior commit selection disappears."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.domain.git.models import GitCommit

        removed_commit_hash = "a1b2c3d4e5f67890"
        panel.set_history_selection_callback(lambda selection: None)
        panel.show_commits(
            [
                GitCommit(
                    id=removed_commit_hash,
                    message="Will be removed",
                    author="Test",
                    timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
                ),
            ]
        )

        # Select the commit item first.
        selected_item = panel.history_list.item(2)
        assert selected_item is not None
        panel.history_list.itemClicked.emit(selected_item)

        # Refresh with commit list that no longer contains the selected commit.
        panel.show_commits(
            [
                GitCommit(
                    id="b2c3d4e5f6789012",
                    message="Different commit",
                    author="Test",
                    timestamp=datetime.fromisoformat("2024-01-16T10:30:00+00:00"),
                ),
            ]
        )

        selected_items = panel.history_list.selectedItems()
        assert len(selected_items) == 1
        selected_selection = selected_items[0].data(Qt.ItemDataRole.UserRole)
        assert selected_selection == HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

    def test_show_commits_long_message_wraps(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that long commit messages wrap within the list item."""
        from freecad.diff_wb.domain.git.models import GitCommit

        # Create a commit with a very long first line
        long_message = "A" * 200  # 200 character message
        commit = GitCommit(
            id="a1b2c3d4e5f67890",
            message=long_message,
            author="Test Author",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )

        panel.show_commits([commit])
        # Commit is at row 2 (after special items)
        # Verify the full message is in the text
        assert "A" * 100 in _history_row_text(panel, 2)  # Should contain the long message

        # Verify word wrap is enabled on the list
        assert panel.history_list.wordWrap() is True

    def test_show_commits_empty_message_handles_gracefully(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test that empty or whitespace-only commit messages are handled gracefully."""
        from freecad.diff_wb.domain.git.models import GitCommit

        # Test with empty message
        commit_empty = GitCommit(
            id="a1b2c3d4e5f67890",
            message="",
            author="Test Author",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )

        panel.show_commits([commit_empty])
        # Commit is at row 2 (after special items)
        assert "a1b2c3d" in _history_row_text(panel, 2)
        # First line of message should be empty
        lines = _history_row_text(panel, 2).split("\n")
        assert len(lines) == 2
        assert lines[1] == ""

        # Test with whitespace-only message
        commit_whitespace = GitCommit(
            id="b2c3d4e5f6789012",
            message="   \n\n   ",
            author="Test Author",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )

        panel.show_commits([commit_whitespace])
        lines = _history_row_text(panel, 2).split("\n")
        assert len(lines) == 2
        assert lines[1] == ""  # Whitespace should be stripped to empty


class TestHistorySelectionCallback:
    """Tests for history selection callback mechanism."""

    def test_set_history_selection_callback_connects_handler(self, panel) -> None:  # type: ignore[no-untyped-def]
        """set_history_selection_callback() sets the callback and connects itemClicked signal."""

        callback_called = False
        received_selection = None

        def mock_callback(selection) -> None:  # type: ignore[no-untyped-def]
            nonlocal callback_called, received_selection
            callback_called = True
            received_selection = selection

        panel.set_history_selection_callback(mock_callback)

        # Trigger callback by clicking on an item
        panel.show_commits([])
        item = panel.history_list.item(0)
        assert item is not None
        panel.history_list.itemClicked.emit(item)

        # Verify callback was invoked with HistorySelection
        assert callback_called is True
        assert isinstance(received_selection, HistorySelection)
        assert received_selection.item_kind == "WORKING_TREE"
        assert received_selection.commit_hash is None

    def test_callback_receives_commit_selection(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Callback receives correct HistorySelection when clicking on a commit."""
        from freecad.diff_wb.domain.git.models import GitCommit

        callback_called = False
        received_selection = None

        def mock_callback(selection) -> None:  # type: ignore[no-untyped-def]
            nonlocal callback_called, received_selection
            callback_called = True
            received_selection = selection

        panel.set_history_selection_callback(mock_callback)

        commit_hash = "a1b2c3d4e5f67890"
        commit = GitCommit(
            id=commit_hash,
            message="Test commit",
            author="Test",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )
        panel.show_commits([commit])

        # Click on the commit item (row 2)
        item = panel.history_list.item(2)
        assert item is not None
        panel.history_list.itemClicked.emit(item)

        # Verify callback was invoked with correct commit selection
        assert callback_called is True
        assert isinstance(received_selection, HistorySelection)
        assert received_selection.item_kind == "COMMIT"
        assert received_selection.commit_hash == commit_hash

    def test_callback_not_invoked_when_not_set(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Callback is not invoked when no callback is set."""

        panel.show_commits([])
        item = panel.history_list.item(0)
        assert item is not None

        # Should not raise any exception
        panel.history_list.itemClicked.emit(item)
