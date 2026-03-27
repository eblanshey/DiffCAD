"""File responsibility: Unit tests for DiffPanelView.show_properties() method.

These tests verify that the DiffPanelView correctly populates the properties
table with PropertyPresentation data, including proper color coding for
ADDED (green), DELETED (red), and MODIFIED (blue) states, and correctly
filters out properties with no changes (UNCHANGED state).
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


class TestDiffPanelViewShowProperties:
    """Tests for DiffPanelView.show_properties() method."""

    def test_empty_property_list_clears_table(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() with empty list clears the properties table."""
        # Given: Table has existing rows from previous call
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        panel.show_properties(
            [
                PropertyPresentation(
                    name="Length",
                    old_display="10.0",
                    new_display="20.0",
                    state="MODIFIED",
                ),
            ]
        )
        assert panel.properties_table.rowCount() == 1

        # When: Call show_properties with empty list
        panel.show_properties([])

        # Then: Table should be cleared
        assert panel.properties_table.rowCount() == 0

    def test_single_property_added_state_green_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() with ADDED state displays green background."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A single property with ADDED state
        properties = [
            PropertyPresentation(
                name="Length",
                old_display="",
                new_display="25.0",
                state="ADDED",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Should have one row
        assert panel.properties_table.rowCount() == 1

        # Check property name (column 0)
        name_item = panel.properties_table.item(0, 0)
        assert name_item is not None
        assert name_item.text() == "Length"

        # Check value column (column 1) - should show "+ value" format
        value_item = panel.properties_table.item(0, 1)
        assert value_item is not None
        assert value_item.text() == "+ 25.0"

        # Check green background color
        assert name_item.background().color() == QColor(200, 255, 200)
        assert value_item.background().color() == QColor(200, 255, 200)

    def test_single_property_deleted_state_red_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() with DELETED state displays red background."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A single property with DELETED state
        properties = [
            PropertyPresentation(
                name="Width",
                old_display="15.0",
                new_display="",
                state="DELETED",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Should have one row
        assert panel.properties_table.rowCount() == 1

        # Check property name (column 0)
        name_item = panel.properties_table.item(0, 0)
        assert name_item is not None
        assert name_item.text() == "Width"

        # Check value column (column 1) - should show "- value" format
        value_item = panel.properties_table.item(0, 1)
        assert value_item is not None
        assert value_item.text() == "- 15.0"

        # Check red background color
        assert name_item.background().color() == QColor(255, 200, 200)
        assert value_item.background().color() == QColor(255, 200, 200)

    def test_single_property_modified_state_blue_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() with MODIFIED state displays blue background."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A single property with MODIFIED state
        properties = [
            PropertyPresentation(
                name="Height",
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Should have one row
        assert panel.properties_table.rowCount() == 1

        # Check property name (column 0)
        name_item = panel.properties_table.item(0, 0)
        assert name_item is not None
        assert name_item.text() == "Height"

        # Check value column (column 1) - should show "old → new" format
        value_item = panel.properties_table.item(0, 1)
        assert value_item is not None
        assert value_item.text() == "10.0 → 20.0"

        # Check blue background color
        assert name_item.background().color() == QColor(200, 200, 255)
        assert value_item.background().color() == QColor(200, 200, 255)

    def _verify_row(  # type: ignore[no-untyped-def]
        self,
        panel: object,
        row: int,
        expected_name: str,
        expected_value: str,
        expected_color_rgb: tuple[int, int, int],
    ) -> None:
        """Helper to verify a single row in the properties table."""
        from PySide6.QtGui import QColor

        color = QColor(*expected_color_rgb)
        name_item = panel.properties_table.item(row, 0)
        value_item = panel.properties_table.item(row, 1)
        assert name_item is not None
        assert value_item is not None
        assert name_item.text() == expected_name
        assert value_item.text() == expected_value
        assert name_item.background().color() == color
        assert value_item.background().color() == color

    def test_multiple_properties_with_different_states(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() correctly handles multiple properties with different states."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties with ADDED, DELETED, and MODIFIED states
        properties = [
            PropertyPresentation(
                name="AddedProp",
                old_display="",
                new_display="100.0",
                state="ADDED",
            ),
            PropertyPresentation(
                name="DeletedProp",
                old_display="50.0",
                new_display="",
                state="DELETED",
            ),
            PropertyPresentation(
                name="ModifiedProp",
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Should have 3 rows
        assert panel.properties_table.rowCount() == 3

        # Verify each row using helper
        self._verify_row(panel, 0, "AddedProp", "+ 100.0", (200, 255, 200))
        self._verify_row(panel, 1, "DeletedProp", "- 50.0", (255, 200, 200))
        self._verify_row(panel, 2, "ModifiedProp", "10.0 → 20.0", (200, 200, 255))

    def test_property_with_no_changes_included_in_list(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() includes all properties with UNCHANGED state shown with gray background."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Mix of changed and unchanged properties
        properties = [
            PropertyPresentation(
                name="ChangedProp",
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
            ),
            PropertyPresentation(
                name="UnchangedProp",
                old_display="50.0",
                new_display="50.0",
                state="UNCHANGED",
            ),
            PropertyPresentation(
                name="AnotherChanged",
                old_display="",
                new_display="100.0",
                state="ADDED",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Should have 3 rows (including UNCHANGED)
        assert panel.properties_table.rowCount() == 3

        # Check the displayed properties include all
        names = [panel.properties_table.item(i, 0).text() for i in range(3)]
        assert "ChangedProp" in names
        assert "AnotherChanged" in names
        assert "UnchangedProp" in names

        # Check UNCHANGED property has gray background and displays just the value (no arrows)
        unchanged_row = names.index("UnchangedProp")
        value_item = panel.properties_table.item(unchanged_row, 1)
        assert value_item.text() == "50.0"  # Just the value, no arrows
        # Check background color is gray (light gray = 240, 240, 240)
        bg_brush = value_item.background()
        bg_color = bg_brush.color()
        assert bg_color.red() == 240
        assert bg_color.green() == 240
        assert bg_color.blue() == 240

    def test_empty_list_initially_shows_no_rows(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() with empty list shows no rows initially."""
        # When: Call show_properties with empty list on fresh panel
        panel.show_properties([])

        # Then: Table should have zero rows
        assert panel.properties_table.rowCount() == 0
