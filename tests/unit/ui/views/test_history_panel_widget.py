"""File responsibility: Unit tests for HistoryPanelWidget methods including show_commits() and commit selection.

These tests verify that the HistoryPanelWidget correctly populates the commit list
with special items (Working Tree, Staging), proper formatting, selection callbacks,
and infinite scroll support.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest
from freecad.history_wb.qt import QtCore, QtGui, QtWidgets
from freecad.history_wb.ui.views.history_panel_widget import HistoryPanelWidget


def _history_row_text(panel, row: int) -> str:  # type: ignore[no-untyped-def]
    """Return visible text for a history row, including custom item widgets."""
    item = panel.history_list.item(row)
    widget = panel.history_list.itemWidget(item)
    if widget is None:
        return item.text()

    labels = widget.findChildren(QtWidgets.QLabel)
    if len(labels) == 1:
        return labels[0].text()
    if len(labels) >= 4:
        top_line = f"{labels[0].text()} {labels[1].text()} {labels[2].text()}"
        return f"{top_line}\n{labels[3].text()}"
    return item.text()


@pytest.fixture(scope="module")
def widget() -> object:
    """Create a HistoryPanelWidget instance for testing.

    Note: This uses module scope to ensure QApplication is created once
    and reused across all tests in this module.
    """
    # Ensure QApplication exists before creating widgets
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    return HistoryPanelWidget()


class TestHistoryPanelWidgetRefreshButton:
    """Tests for HistoryPanelWidget refresh button functionality."""

    def test_set_refresh_callback_connects_to_button_clicked(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_refresh_callback() connects the callback to the button's clicked signal."""
        # Track if callback was called
        callback_called = False

        def mock_callback() -> None:
            nonlocal callback_called
            callback_called = True

        # When: Set the refresh callback
        widget.set_refresh_callback(mock_callback)

        # Then: Callback should be connected (we verify by simulating a click)
        # Simulate button click
        widget._refresh_button.click()

        # Verify callback was invoked
        assert callback_called is True

    def test_refresh_button_has_tooltip(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Refresh button has a tooltip."""
        tooltip = widget._refresh_button.toolTip()
        assert "refresh" in tooltip.lower() or "git" in tooltip.lower()


class TestHistoryPanelWidgetShowRepository:
    """Tests for HistoryPanelWidget.show_repository() method."""

    def test_show_repository_with_none_shows_no_repo_message(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_repository(None) displays the 'no repository' message with italic gray style."""
        # When: Call show_repository with None
        widget.show_repository(None)

        # Then: Label shows no repo message with italic gray styling
        text = widget._repository_label.text()
        assert "no git repository" in text.lower() or "detected" in text.lower()
        stylesheet = widget._repository_label.styleSheet()
        assert "italic" in stylesheet
        assert "gray" in stylesheet

    def test_show_repository_with_valid_repo_shows_info(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_repository() displays repository name with tooltip containing path and bold/underline styling."""
        # Given: A valid GitRepository
        from freecad.history_wb.domain.git.models import GitRepository

        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")

        # When: Call show_repository with a valid repository
        widget.show_repository(repo)

        # Then: Label shows project name with path in tooltip
        text = widget._repository_label.text()
        assert "test_project" in text
        assert "Project:" in text
        # Path should be in tooltip, not in displayed text
        assert widget._repository_label.toolTip() == "/home/user/test_project"
        stylesheet = widget._repository_label.styleSheet()
        assert "bold" in stylesheet
        assert "underline" in stylesheet

    def test_show_repository_overwrites_previous_display(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_repository() overwrites previous repository display."""
        # Given: Previous repository displayed
        from freecad.history_wb.domain.git.models import GitRepository

        repo1 = GitRepository(name="old_project", absolute_path="/home/old")
        widget.show_repository(repo1)
        assert "old_project" in widget._repository_label.text()

        # When: Call show_repository with a different repository
        repo2 = GitRepository(name="new_project", absolute_path="/home/new")
        widget.show_repository(repo2)

        # Then: New repository info replaces old one
        text = widget._repository_label.text()
        assert "new_project" in text
        assert "old_project" not in text
        # Tooltip should also be updated
        assert widget._repository_label.toolTip() == "/home/new"

    def test_show_repository_none_after_repo_resets_style(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_repository(None) after showing a repo resets to italic gray style and clears tooltip."""
        # Given: Repository previously displayed
        from freecad.history_wb.domain.git.models import GitRepository

        repo = GitRepository(name="test_project", absolute_path="/home/test")
        widget.show_repository(repo)

        # When: Call show_repository with None
        widget.show_repository(None)

        # Then: Style is reset to italic gray and tooltip is cleared
        stylesheet = widget._repository_label.styleSheet()
        assert "italic" in stylesheet
        assert "gray" in stylesheet
        assert widget._repository_label.toolTip() == ""

    def test_repository_label_click_opens_project_directory(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Clicking repository label opens project directory in native file browser."""
        from freecad.history_wb.domain.git.models import GitRepository

        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")
        widget.show_repository(repo)

        with patch.object(QtGui.QDesktopServices, "openUrl", return_value=True) as open_url:
            widget._repository_label.open_repository_directory()

        open_url.assert_called_once_with(QtCore.QUrl.fromLocalFile("/home/user/test_project"))

    def test_repository_label_click_does_nothing_without_project(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Clicking label does not try to open directory when no project is shown."""
        widget.show_repository(None)

        with patch.object(QtGui.QDesktopServices, "openUrl", return_value=True) as open_url:
            widget._repository_label.open_repository_directory()

        open_url.assert_not_called()


class TestShowCommitsSpecialItems:
    """Tests for the special "Working Tree" and "Staging" items in show_commits."""

    def test_show_commits_always_shows_in_progress_and_reviewed_at_top(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that In Progress and Reviewed items are always present at the top of the list."""
        from freecad.history_wb.domain.git.models import GitCommit

        commits = [
            GitCommit(
                id="a1b2c3d4e5f6789012345678901234567890abcd",
                message="Test commit",
                author="Test Author",
                timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
            ),
        ]

        widget.show_commits(commits)

        # Verify there are 3 items: In Progress, Reviewed, and the commit
        assert widget.history_list.count() == 3

        # Verify In Progress is first
        working_tree_item = widget.history_list.item(0)
        assert working_tree_item is not None
        assert _history_row_text(widget, 0) == "In Progress"

        # Verify Reviewed is second
        staging_item = widget.history_list.item(1)
        assert staging_item is not None
        assert _history_row_text(widget, 1) == "Reviewed"

        # Verify commit is third
        commit_item = widget.history_list.item(2)
        assert commit_item is not None
        assert "a1b2c3d" in _history_row_text(widget, 2)

    def test_show_commits_shows_special_items_even_with_empty_commits(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that In Progress and Reviewed items are present even when no commits are provided."""
        widget.show_commits([])

        # Verify there are exactly 2 items: In Progress and Reviewed
        assert widget.history_list.count() == 2

        # Verify In Progress is first
        working_tree_item = widget.history_list.item(0)
        assert working_tree_item is not None
        assert _history_row_text(widget, 0) == "In Progress"

        # Verify Reviewed is second
        staging_item = widget.history_list.item(1)
        assert staging_item is not None
        assert _history_row_text(widget, 1) == "Reviewed"

    def test_show_commits_without_special_items_shows_no_iterations_message(self, widget) -> None:  # type: ignore[no-untyped-def]
        """When special items disabled and commits empty, show a no-iterations placeholder."""
        widget.show_commits([], show_special_items=False)

        assert widget.history_list.count() == 1
        assert _history_row_text(widget, 0) == "No iterations to display."
        item = widget.history_list.item(0)
        item_widget = widget.history_list.itemWidget(item)
        labels = item_widget.findChildren(QtWidgets.QLabel)
        assert len(labels) == 1
        assert "italic" in labels[0].styleSheet()

    def test_show_commits_working_tree_has_correct_user_role(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that Working Tree item has UserRole set to HistorySelection with WORKING_TREE kind."""
        from freecad.history_wb.ui.views.models import HistorySelection

        widget.show_commits([])

        working_tree_item = widget.history_list.item(0)
        assert working_tree_item is not None

        user_role = working_tree_item.data(QtCore.Qt.ItemDataRole.UserRole)
        assert isinstance(user_role, HistorySelection)
        assert user_role.item_kind == "WORKING_TREE"
        assert user_role.commit_hash is None

    def test_show_commits_staging_has_correct_user_role(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that Staging item has UserRole set to HistorySelection with STAGING kind."""
        from freecad.history_wb.ui.views.models import HistorySelection

        widget.show_commits([])

        staging_item = widget.history_list.item(1)
        assert staging_item is not None

        user_role = staging_item.data(QtCore.Qt.ItemDataRole.UserRole)
        assert isinstance(user_role, HistorySelection)
        assert user_role.item_kind == "STAGING"
        assert user_role.commit_hash is None

    def test_show_commits_commits_have_commit_history_selection(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that actual commits have HistorySelection with COMMIT kind and commit hash."""
        from freecad.history_wb.domain.git.models import GitCommit
        from freecad.history_wb.ui.views.models import HistorySelection

        commit_hash = "a1b2c3d4e5f67890"
        commits = [
            GitCommit(
                id=commit_hash,
                message="Test commit",
                author="Test Author",
                timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
            ),
        ]

        widget.show_commits(commits)

        # Commit item should be at row 2 (after special items)
        commit_item = widget.history_list.item(2)
        assert commit_item is not None

        user_role = commit_item.data(QtCore.Qt.ItemDataRole.UserRole)
        assert isinstance(user_role, HistorySelection)
        assert user_role.item_kind == "COMMIT"
        assert user_role.commit_hash == commit_hash

    def test_show_commits_refresh_clears_and_readds_special_items(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that refreshing the list with new commits re-adds special items correctly."""
        from freecad.history_wb.domain.git.models import GitCommit

        # First call with commits
        commits1 = [
            GitCommit(
                id="commit1",
                message="First commit",
                author="Author 1",
                timestamp=datetime.fromisoformat("2024-01-01T10:00:00+00:00"),
            ),
        ]
        widget.show_commits(commits1)
        assert widget.history_list.count() == 3
        assert _history_row_text(widget, 0) == "In Progress"
        assert _history_row_text(widget, 1) == "Reviewed"

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
        widget.show_commits(commits2)

        # Verify special items are still at top
        assert widget.history_list.count() == 4  # 2 special + 2 commits
        assert _history_row_text(widget, 0) == "In Progress"
        assert _history_row_text(widget, 1) == "Reviewed"
        assert "Second commit" in _history_row_text(widget, 2)
        assert "Third commit" in _history_row_text(widget, 3)


class TestShowCommits:
    """Tests for HistoryPanelWidget.show_commits method."""

    def test_show_commits_displays_commits_correctly(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that commits are displayed with correct format."""
        from freecad.history_wb.domain.git.models import GitCommit

        commits = [
            GitCommit(
                id="a1b2c3d4e5f6789012345678901234567890abcd",
                message="Fix bug in snapshot comparison\n\nThis fixes the issue where...",
                author="John Doe",
                timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
            ),
        ]

        widget.show_commits(commits)

        # Verify there are 3 items total (Working Tree, Staging, and the commit)
        assert widget.history_list.count() == 3
        # Verify the commit is at position 2 (after special items)
        assert "a1b2c3d" in _history_row_text(widget, 2)  # 7-char hash
        assert "John Doe" in _history_row_text(widget, 2)  # Author
        assert widget._format_commit_timestamp(commits[0].timestamp) in _history_row_text(widget, 2)

    def test_show_commits_empty_list(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that empty commit list shows only special items."""
        widget.show_commits([])
        # Special items (In Progress, Reviewed) are always present
        assert widget.history_list.count() == 2
        assert _history_row_text(widget, 0) == "In Progress"
        assert _history_row_text(widget, 1) == "Reviewed"

    def test_show_commits_tooltip_has_full_message(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that tooltip contains full commit message."""
        from freecad.history_wb.domain.git.models import GitCommit

        full_message = "Fix bug\n\nDetailed explanation..."
        commit = GitCommit(
            id="a1b2c3d4e5f67890",
            message=full_message,
            author="Test",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )

        widget.show_commits([commit])
        # Commit is at row 2 (after special items)
        item = widget.history_list.item(2)

        assert item.toolTip() == full_message

    def test_show_commits_clears_existing_list(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that show_commits replaces any existing list content."""
        from freecad.history_wb.domain.git.models import GitCommit

        # First populate with one commit
        old_commit = GitCommit(
            id="old1234567890",
            message="Old commit",
            author="Old Author",
            timestamp=datetime.fromisoformat("2024-01-01T10:00:00+00:00"),
        )
        widget.show_commits([old_commit])
        assert widget.history_list.count() == 3

        # Now call show_commits with different commit
        new_commit = GitCommit(
            id="a1b2c3d4e5f67890",
            message="Test commit",
            author="Test",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )
        widget.show_commits([new_commit])

        # List should contain special items + new commit (not old commit)
        assert widget.history_list.count() == 3
        assert _history_row_text(widget, 0) == "In Progress"
        assert _history_row_text(widget, 1) == "Reviewed"
        assert "Test commit" in _history_row_text(widget, 2)

    def test_show_commits_two_line_format(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that commits display with two-line format."""
        from freecad.history_wb.domain.git.models import GitCommit

        commit = GitCommit(
            id="abc123def456",
            message="This is the subject line\n\nThis is the body of the commit message.",
            author="Alice Smith",
            timestamp=datetime.fromisoformat("2024-03-20T14:45:00+00:00"),
        )

        widget.show_commits([commit])
        # Commit is at row 2 (after special items)
        text = _history_row_text(widget, 2)

        # Check that there's a newline in the display text (two lines)
        assert "\n" in text
        # Line 1 should have hash, author, timestamp
        lines = text.split("\n")
        assert len(lines) == 2
        assert "abc123d" in lines[0]  # 7-char hash
        assert "Alice Smith" in lines[0]  # Author
        assert widget._format_commit_timestamp(commit.timestamp) in lines[0]
        # Line 2 should have first line of message
        assert "This is the subject line" in lines[1]

    def test_show_commits_multiple_commits_newest_first(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that multiple commits are displayed in the order provided (assumed pre-sorted by adapter).

        Note: The view does not sort commits; it displays them as provided. The GitPortAdapter
        returns commits in DESC order (newest first), so the caller should ensure commits are
        sorted before passing to this method.
        """
        from freecad.history_wb.domain.git.models import GitCommit

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

        widget.show_commits(commits)

        # Verify order matches input (pre-sorted) + special items at top
        assert widget.history_list.count() == 5  # 2 special + 3 commits
        # Special items at top
        assert _history_row_text(widget, 0) == "In Progress"
        assert _history_row_text(widget, 1) == "Reviewed"
        # Commits start at row 2
        assert "New commit" in _history_row_text(widget, 2)
        assert "Middle commit" in _history_row_text(widget, 3)
        assert "Old commit" in _history_row_text(widget, 4)

    def test_show_commits_short_hash_truncation(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that long commit hashes are truncated to 7 characters."""
        from freecad.history_wb.domain.git.models import GitCommit

        commit = GitCommit(
            id="a1b2c3d4e5f6789012345678901234567890abcd",
            message="Test",
            author="Test",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )

        widget.show_commits([commit])
        # Commit is at row 2 (after special items)
        text = _history_row_text(widget, 2)

        # Should have 7-char hash, not the full hash
        assert "a1b2c3d" in text
        assert "e5f6789" not in text  # Full hash should not appear

    def test_show_commits_leaves_history_unselected_without_previous_selection(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_commits() leaves history unselected when user had no selection."""
        from freecad.history_wb.domain.git.models import GitCommit

        widget._current_selection = None
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

        widget.show_commits(commits)

        selected_items = widget.history_list.selectedItems()
        assert selected_items == []
        assert widget._current_selection is None

    def test_show_commits_refresh_restores_previous_selection_if_it_still_exists(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Refreshing commits re-selects the same commit when still present."""
        from freecad.history_wb.domain.git.models import GitCommit

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

        widget.set_history_selection_callback(lambda selection: None)
        widget.show_commits(initial_commits)

        selected_item = widget.history_list.item(2)
        assert selected_item is not None
        widget.history_list.itemClicked.emit(selected_item)

        refreshed_commits = [
            GitCommit(
                id=selected_commit_hash,
                message="Selected commit (updated message)",
                author="Test",
                timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
            ),
        ]
        widget.show_commits(refreshed_commits)

        selected_items = widget.history_list.selectedItems()
        assert len(selected_items) == 1
        selected_selection = selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        from freecad.history_wb.ui.views.models import HistorySelection

        assert selected_selection == HistorySelection(item_kind="COMMIT", commit_hash=selected_commit_hash)

    def test_show_commits_refresh_clears_selection_when_previous_selection_missing(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Refreshing commits clears selection when prior commit selection disappears."""
        from freecad.history_wb.domain.git.models import GitCommit

        removed_commit_hash = "a1b2c3d4e5f67890"
        widget.set_history_selection_callback(lambda selection: None)
        widget.show_commits(
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
        selected_item = widget.history_list.item(2)
        assert selected_item is not None
        widget.history_list.itemClicked.emit(selected_item)

        # Refresh with commit list that no longer contains the selected commit.
        widget.show_commits(
            [
                GitCommit(
                    id="b2c3d4e5f6789012",
                    message="Different commit",
                    author="Test",
                    timestamp=datetime.fromisoformat("2024-01-16T10:30:00+00:00"),
                ),
            ]
        )

        selected_items = widget.history_list.selectedItems()
        assert selected_items == []
        assert widget._current_selection is None

    def test_show_commits_long_message_wraps(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that long commit messages wrap within the list item."""
        from freecad.history_wb.domain.git.models import GitCommit

        # Create a commit with a very long first line
        long_message = "A" * 200  # 200 character message
        commit = GitCommit(
            id="a1b2c3d4e5f67890",
            message=long_message,
            author="Test Author",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )

        widget.show_commits([commit])
        # Commit is at row 2 (after special items)
        # Verify the full message is in the text
        assert "A" * 100 in _history_row_text(widget, 2)  # Should contain the long message

        # Verify word wrap is enabled on the list
        assert widget.history_list.wordWrap() is True

    def test_show_commits_empty_message_handles_gracefully(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Test that empty or whitespace-only commit messages are handled gracefully."""
        from freecad.history_wb.domain.git.models import GitCommit

        # Test with empty message
        commit_empty = GitCommit(
            id="a1b2c3d4e5f67890",
            message="",
            author="Test Author",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )

        widget.show_commits([commit_empty])
        # Commit is at row 2 (after special items)
        assert "a1b2c3d" in _history_row_text(widget, 2)
        # First line of message should be empty
        lines = _history_row_text(widget, 2).split("\n")
        assert len(lines) == 2
        assert lines[1] == ""

        # Test with whitespace-only message
        commit_whitespace = GitCommit(
            id="b2c3d4e5f6789012",
            message="   \n\n   ",
            author="Test Author",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )

        widget.show_commits([commit_whitespace])
        lines = _history_row_text(widget, 2).split("\n")
        assert len(lines) == 2
        assert lines[1] == ""  # Whitespace should be stripped to empty


class TestHistorySelectionCallback:
    """Tests for history selection callback mechanism."""

    def test_set_history_selection_callback_connects_handler(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_history_selection_callback() sets the callback and connects itemClicked signal."""
        from freecad.history_wb.ui.views.models import HistorySelection

        callback_called = False
        received_selection = None

        def mock_callback(selection) -> None:  # type: ignore[no-untyped-def]
            nonlocal callback_called, received_selection
            callback_called = True
            received_selection = selection

        widget.set_history_selection_callback(mock_callback)

        # Trigger callback by clicking on an item
        widget.show_commits([])
        item = widget.history_list.item(0)
        assert item is not None
        widget.history_list.itemClicked.emit(item)

        # Verify callback was invoked with HistorySelection
        assert callback_called is True
        assert isinstance(received_selection, HistorySelection)
        assert received_selection.item_kind == "WORKING_TREE"  # Internal enum unchanged
        assert received_selection.commit_hash is None

    def test_callback_receives_commit_selection(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Callback receives correct HistorySelection when clicking on a commit."""
        from freecad.history_wb.domain.git.models import GitCommit
        from freecad.history_wb.ui.views.models import HistorySelection

        callback_called = False
        received_selection = None

        def mock_callback(selection) -> None:  # type: ignore[no-untyped-def]
            nonlocal callback_called, received_selection
            callback_called = True
            received_selection = selection

        widget.set_history_selection_callback(mock_callback)

        commit_hash = "a1b2c3d4e5f67890"
        commit = GitCommit(
            id=commit_hash,
            message="Test commit",
            author="Test",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )
        widget.show_commits([commit])

        # Click on the commit item (row 2)
        item = widget.history_list.item(2)
        assert item is not None
        widget.history_list.itemClicked.emit(item)

        # Verify callback was invoked with correct commit selection
        assert callback_called is True
        assert isinstance(received_selection, HistorySelection)
        assert received_selection.item_kind == "COMMIT"
        assert received_selection.commit_hash == commit_hash

    def test_callback_not_invoked_when_not_set(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Callback is not invoked when no callback is set."""

        widget.show_commits([])
        item = widget.history_list.item(0)
        assert item is not None

        # Should not raise any exception
        widget.history_list.itemClicked.emit(item)


class TestHistoryInfiniteScroll:
    """Tests for history infinite scroll support."""

    def test_append_commits_keeps_special_rows(self, widget) -> None:  # type: ignore[no-untyped-def]
        """append_commits() appends without clearing existing In Progress/Reviewed rows."""
        from freecad.history_wb.domain.git.models import GitCommit

        widget.show_commits([])
        commits = [
            GitCommit(
                id="abc1234",
                message="Older commit",
                author="Author",
                timestamp=datetime.fromisoformat("2024-01-01T10:00:00+00:00"),
            )
        ]

        widget.append_commits(commits)

        assert widget.history_list.count() == 3
        assert _history_row_text(widget, 0) == "In Progress"
        assert _history_row_text(widget, 1) == "Reviewed"
        assert "Older commit" in _history_row_text(widget, 2)

    def test_scroll_bottom_callback_fires_near_bottom(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Bottom-scroll callback fires when scrollbar enters bottom threshold."""
        from unittest.mock import MagicMock, patch

        fired = {"count": 0}

        def on_bottom() -> None:
            fired["count"] += 1

        widget.set_history_scroll_bottom_callback(on_bottom)

        mock_scrollbar = MagicMock()
        mock_scrollbar.maximum.return_value = 100
        with patch.object(widget.history_list, "verticalScrollBar", return_value=mock_scrollbar):
            widget._on_history_scrollbar_value_changed(90)

        assert fired["count"] >= 1


class TestHistoryPanelWidgetSelection:
    """Tests for history selection management."""

    def test_get_current_history_selection_returns_none_when_no_selection(self, widget) -> None:  # type: ignore[no-untyped-def]
        """get_current_history_selection() returns None when nothing is selected."""
        # Reset selection to ensure clean state
        widget._current_selection = None
        assert widget.get_current_history_selection() is None

    def test_get_current_history_selection_returns_selection_after_click(self, widget) -> None:  # type: ignore[no-untyped-def]
        """get_current_history_selection() returns the selection after clicking an item."""
        from freecad.history_wb.domain.git.models import GitCommit

        commit_hash = "a1b2c3d4e5f67890"
        commit = GitCommit(
            id=commit_hash,
            message="Test commit",
            author="Test",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )
        widget.show_commits([commit])

        # Click on the commit item (row 2)
        item = widget.history_list.item(2)
        assert item is not None
        widget.history_list.itemClicked.emit(item)

        # Verify selection is stored
        selection = widget.get_current_history_selection()
        assert selection is not None
        assert selection.item_kind == "COMMIT"
        assert selection.commit_hash == commit_hash

    def test_set_selection_changed_callback_notifies_on_selection_change(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_selection_changed_callback() notifies when selection changes."""
        from freecad.history_wb.domain.git.models import GitCommit
        from freecad.history_wb.ui.views.models import HistorySelection

        callback_called = False
        received_selection = None

        def mock_callback(selection) -> None:  # type: ignore[no-untyped-def]
            nonlocal callback_called, received_selection
            callback_called = True
            received_selection = selection

        widget.set_selection_changed_callback(mock_callback)

        commit_hash = "a1b2c3d4e5f67890"
        commit = GitCommit(
            id=commit_hash,
            message="Test commit",
            author="Test",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )
        widget.show_commits([commit])

        # Click on the commit item (row 2)
        item = widget.history_list.item(2)
        assert item is not None
        widget.history_list.itemClicked.emit(item)

        # Verify callback was invoked with correct selection
        assert callback_called is True
        assert isinstance(received_selection, HistorySelection)
        assert received_selection.item_kind == "COMMIT"
        assert received_selection.commit_hash == commit_hash
