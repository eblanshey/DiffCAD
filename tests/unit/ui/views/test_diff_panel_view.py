"""File responsibility: Unit tests for DiffPanelView.show_snapshots() and snapshot selection implementation.

These tests verify that the DiffPanelView correctly populates the snapshot list
with SnapshotSummary data, including proper sorting, formatting, and ID storage.
Additional tests cover the snapshot selection mechanism with role-based coloring.
"""

from __future__ import annotations

import pytest


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

        # Snapshot list should be empty
        assert panel.snapshot_list.count() == 0

    def test_show_snapshots_clears_existing_items(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() clears existing items before populating."""
        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        # Add initial items
        panel.show_snapshots(
            [
                SnapshotSummary(id="old-1", name="Old Snapshot 1", created_at="2024-01-01T10:00:00", node_count=10),
            ]
        )
        assert panel.snapshot_list.count() == 1

        # Replace with new list
        panel.show_snapshots(
            [
                SnapshotSummary(id="new-1", name="New Snapshot 1", created_at="2024-02-01T10:00:00", node_count=20),
            ]
        )

        # Should only have the new item
        assert panel.snapshot_list.count() == 1
        assert panel.snapshot_list.item(0).text() == "New Snapshot 1 - Feb 1, 2024 10:00AM"

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
        assert panel.snapshot_list.count() == 3
        assert panel.snapshot_list.item(0).text().startswith("Newest")
        assert panel.snapshot_list.item(1).text().startswith("Middle")
        assert panel.snapshot_list.item(2).text().startswith("Oldest")

    def test_show_snapshots_stores_id_in_user_role(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() stores snapshot ID in Qt.UserRole for each item."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        snapshots = [
            SnapshotSummary(id="test-id-123", name="Test Snapshot", created_at="2024-01-15T10:30:00", node_count=42),
        ]

        panel.show_snapshots(snapshots)

        # Verify ID is stored in UserRole
        item = panel.snapshot_list.item(0)
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
        item_text = panel.snapshot_list.item(0).text()
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
        assert panel.snapshot_list.item(0).data(Qt.ItemDataRole.UserRole) == "id-3"
        assert panel.snapshot_list.item(1).data(Qt.ItemDataRole.UserRole) == "id-2"
        assert panel.snapshot_list.item(2).data(Qt.ItemDataRole.UserRole) == "id-1"


class TestSnapshotSelection:
    """Tests for snapshot selection mechanism (Phase 10)."""

    def test_single_click_selects_one_with_red_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Single click selects one snapshot as 'from' with red background."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        # Given: 2 snapshots in list
        panel.show_snapshots(
            [
                SnapshotSummary(id="snap-1", name="First", created_at="2024-01-01T10:00:00", node_count=10),
                SnapshotSummary(id="snap-2", name="Second", created_at="2024-01-02T10:00:00", node_count=20),
            ]
        )

        # When: User clicks first snapshot (row 0) - use setCurrentItem to simulate click
        item0 = panel.snapshot_list.item(0)
        assert item0 is not None
        panel.snapshot_list.setCurrentItem(item0)

        # Then: First snapshot has red background ("from" role)
        assert item0.background().color() == QColor(255, 200, 200)
        # Verify only one item selected
        assert len(panel._selected_items) == 1
        assert 0 in panel._selected_items
        assert panel._selected_items[0].role == "from"

    def test_ctrl_click_selects_two_with_different_colors(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Ctrl+click selects second snapshot as 'to' with green background."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        # Given: First snapshot already selected (red, "from")
        panel.show_snapshots(
            [
                SnapshotSummary(id="snap-1", name="First", created_at="2024-01-01T10:00:00", node_count=10),
                SnapshotSummary(id="snap-2", name="Second", created_at="2024-01-02T10:00:00", node_count=20),
            ]
        )
        item0 = panel.snapshot_list.item(0)
        assert item0 is not None
        panel.snapshot_list.setCurrentItem(item0)

        # When: User Ctrl+clicks second snapshot (row 1) - use setSelected to add to selection
        item1 = panel.snapshot_list.item(1)
        assert item1 is not None
        item1.setSelected(True)

        # Then: Second snapshot has green background ("to" role)
        assert item1.background().color() == QColor(200, 255, 200)
        # Verify two items selected
        assert len(panel._selected_items) == 2
        assert 1 in panel._selected_items
        assert panel._selected_items[1].role == "to"

    def test_ctrl_click_deselects_already_selected_preserves_other_role(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Ctrl+click on selected item toggles it off; other item keeps its role."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        # Given: Two snapshots selected (red="from" + green="to")
        panel.show_snapshots(
            [
                SnapshotSummary(id="snap-1", name="First", created_at="2024-01-01T10:00:00", node_count=10),
                SnapshotSummary(id="snap-2", name="Second", created_at="2024-01-02T10:00:00", node_count=20),
            ]
        )
        item0 = panel.snapshot_list.item(0)
        item1 = panel.snapshot_list.item(1)
        assert item0 is not None
        assert item1 is not None
        panel.snapshot_list.setCurrentItem(item0)
        item1.setSelected(True)

        # When: User Ctrl+clicks first (red/"from") snapshot again to deselect
        item0.setSelected(False)

        # Then: Only second remains selected with GREEN background (keeps "to" role)
        assert len(panel._selected_items) == 1
        assert 1 in panel._selected_items
        assert panel._selected_items[1].role == "to"
        assert item1.background().color() == QColor(200, 255, 200)

    def test_deselected_item_can_be_reselected_with_original_role(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Deselected item can be reselected and regains its original role."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        # Given: Row 0 selected as "from" (red), then deselected
        panel.show_snapshots(
            [
                SnapshotSummary(id="snap-1", name="First", created_at="2024-01-01T10:00:00", node_count=10),
                SnapshotSummary(id="snap-2", name="Second", created_at="2024-01-02T10:00:00", node_count=20),
            ]
        )
        item0 = panel.snapshot_list.item(0)
        assert item0 is not None
        panel.snapshot_list.setCurrentItem(item0)
        panel.snapshot_list.clearSelection()

        # When: User clicks row 0 again
        panel.snapshot_list.setCurrentItem(item0)

        # Then: Row 0 becomes "from" again (red background)
        assert len(panel._selected_items) == 1
        assert 0 in panel._selected_items
        assert panel._selected_items[0].role == "from"
        assert item0.background().color() == QColor(255, 200, 200)

    def test_new_selection_gets_next_available_role(self, panel) -> None:  # type: ignore[no-untyped-def]
        """New selection gets appropriate role based on available slots."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        # Given: Row 0 selected as "from" (red), row 1 deselected
        panel.show_snapshots(
            [
                SnapshotSummary(id="snap-1", name="First", created_at="2024-01-01T10:00:00", node_count=10),
                SnapshotSummary(id="snap-2", name="Second", created_at="2024-01-02T10:00:00", node_count=20),
            ]
        )
        item0 = panel.snapshot_list.item(0)
        item1 = panel.snapshot_list.item(1)
        assert item0 is not None
        assert item1 is not None
        panel.snapshot_list.setCurrentItem(item0)
        item0.setSelected(False)
        item0.setSelected(True)  # Re-select row 0 as "from"

        # When: User selects row 1
        item1.setSelected(True)

        # Then: Row 1 becomes "to" (green background)
        assert len(panel._selected_items) == 2
        assert 1 in panel._selected_items
        assert panel._selected_items[1].role == "to"
        assert item1.background().color() == QColor(200, 255, 200)

    def test_third_selection_is_rejected(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Attempting to select third snapshot is silently rejected."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        # Given: Two snapshots already selected (red + green)
        panel.show_snapshots(
            [
                SnapshotSummary(id="snap-1", name="First", created_at="2024-01-01T10:00:00", node_count=10),
                SnapshotSummary(id="snap-2", name="Second", created_at="2024-01-02T10:00:00", node_count=20),
                SnapshotSummary(id="snap-3", name="Third", created_at="2024-01-03T10:00:00", node_count=30),
            ]
        )
        item0 = panel.snapshot_list.item(0)
        item1 = panel.snapshot_list.item(1)
        assert item0 is not None
        assert item1 is not None
        panel.snapshot_list.setCurrentItem(item0)
        item1.setSelected(True)

        # Remember the state before attempting third selection
        selected_before = set(panel._selected_items.keys())

        # When: User attempts to select third snapshot (row 2)
        item2 = panel.snapshot_list.item(2)
        assert item2 is not None
        item2.setSelected(True)

        # Then: Selection unchanged, no visual feedback
        assert len(panel._selected_items) == 2
        assert set(panel._selected_items.keys()) == selected_before
        # Third item should NOT have custom color (should be default)
        # Check it's not red or green
        bg_color = item2.background().color()
        assert bg_color != QColor(255, 200, 200)
        assert bg_color != QColor(200, 255, 200)

    def test_get_selected_snapshot_ids_returns_from_then_to(self, panel) -> None:  # type: ignore[no-untyped-def]
        """get_selected_snapshot_ids() returns IDs in role order: [from_id, to_id]."""
        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        # Given: Two snapshots selected (row 5="from", row 2="to")
        # Note: Snapshots are sorted by timestamp (newest first), so:
        # Row 0 = snap-6 (newest), Row 1 = snap-5, Row 2 = snap-4, Row 3 = snap-3, Row 4 = snap-2, Row 5 = snap-1 (oldest)
        panel.show_snapshots(
            [
                SnapshotSummary(id="snap-1", name="First", created_at="2024-01-01T10:00:00", node_count=10),
                SnapshotSummary(id="snap-2", name="Second", created_at="2024-01-02T10:00:00", node_count=20),
                SnapshotSummary(id="snap-3", name="Third", created_at="2024-01-03T10:00:00", node_count=30),
                SnapshotSummary(id="snap-4", name="Fourth", created_at="2024-01-04T10:00:00", node_count=40),
                SnapshotSummary(id="snap-5", name="Fifth", created_at="2024-01-05T10:00:00", node_count=50),
                SnapshotSummary(id="snap-6", name="Sixth", created_at="2024-01-06T10:00:00", node_count=60),
            ]
        )
        # Select row 5 first (gets "from") - this is snap-1 (oldest)
        item5 = panel.snapshot_list.item(5)
        assert item5 is not None
        panel.snapshot_list.setCurrentItem(item5)
        # Select row 2 second (gets "to") - this is snap-4
        item2 = panel.snapshot_list.item(2)
        assert item2 is not None
        item2.setSelected(True)

        # When: Call get_selected_snapshot_ids()
        ids = panel.get_selected_snapshot_ids()

        # Then: Returns [snap-1, snap-4] (from before to, regardless of row order)
        assert len(ids) == 2
        assert ids[0] == "snap-1"  # "from" role (row 5, oldest)
        assert ids[1] == "snap-4"  # "to" role (row 2)

    def test_get_selected_ids_empty_when_nothing_selected(self, panel) -> None:  # type: ignore[no-untyped-def]
        """get_selected_snapshot_ids() returns empty list when nothing selected."""
        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        # Given: No snapshots selected
        panel.show_snapshots(
            [
                SnapshotSummary(id="snap-1", name="First", created_at="2024-01-01T10:00:00", node_count=10),
            ]
        )

        # When: Call get_selected_snapshot_ids()
        ids = panel.get_selected_snapshot_ids()

        # Then: Returns []
        assert ids == []

    def test_clear_selection_resets_all(self, panel) -> None:  # type: ignore[no-untyped-def]
        """clear_selection() deselects all and resets backgrounds."""

        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        # Given: Two snapshots selected with custom colors
        panel.show_snapshots(
            [
                SnapshotSummary(id="snap-1", name="First", created_at="2024-01-01T10:00:00", node_count=10),
                SnapshotSummary(id="snap-2", name="Second", created_at="2024-01-02T10:00:00", node_count=20),
            ]
        )
        item0 = panel.snapshot_list.item(0)
        item1 = panel.snapshot_list.item(1)
        assert item0 is not None
        assert item1 is not None
        panel.snapshot_list.setCurrentItem(item0)
        item1.setSelected(True)

        default_bg = panel._get_default_background()

        # When: Call clear_selection()
        panel.clear_selection()

        # Then: All backgrounds reset to default, no roles tracked
        assert len(panel._selected_items) == 0
        assert panel.snapshot_list.selectedItems() == []
        assert item0.background().color() == default_bg
        assert item1.background().color() == default_bg

    def test_selection_cleared_on_refresh(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Selections cleared when snapshot list refreshed."""
        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        # Given: Snapshot selected
        panel.show_snapshots(
            [
                SnapshotSummary(id="snap-1", name="First", created_at="2024-01-01T10:00:00", node_count=10),
                SnapshotSummary(id="snap-2", name="Second", created_at="2024-01-02T10:00:00", node_count=20),
            ]
        )
        item0 = panel.snapshot_list.item(0)
        assert item0 is not None
        panel.snapshot_list.setCurrentItem(item0)
        assert len(panel._selected_items) == 1

        # When: Call show_snapshots() with new snapshot list
        panel.show_snapshots(
            [
                SnapshotSummary(id="new-snap-1", name="New First", created_at="2024-02-01T10:00:00", node_count=15),
                SnapshotSummary(id="new-snap-2", name="New Second", created_at="2024-02-02T10:00:00", node_count=25),
                SnapshotSummary(id="new-snap-3", name="New Third", created_at="2024-02-03T10:00:00", node_count=35),
            ]
        )

        # Then: All selections and roles cleared
        assert len(panel._selected_items) == 0
        assert panel.snapshot_list.selectedItems() == []


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
