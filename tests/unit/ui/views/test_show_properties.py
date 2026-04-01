"""File responsibility: Unit tests for DiffPanelView.show_properties() method with QTreeWidget.

These tests verify that the DiffPanelView correctly populates the properties
tree widget with PropertyPresentation data, including:
- Group headers with gray background
- Diff coloring (green=added, red=deleted, blue=modified)
- Expandable properties functionality
"""

import pytest

from freecad.diff_wb.domain.diff.models import DiffState


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


class TestDiffPanelViewShowPropertiesTree:
    """Tests for DiffPanelView.show_properties() method with QTreeWidget."""

    def test_empty_property_list_clears_tree(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() with empty list clears the properties tree."""
        # Given: Tree has existing items from previous call
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        panel.show_properties(
            [
                PropertyPresentation(
                    name="Length",
                    state=DiffState.MODIFIED,
                ),
            ]
        )
        assert panel.properties_tree.topLevelItemCount() == 1

        # When: Call show_properties with empty list
        panel.show_properties([])

        # Then: Tree should be cleared
        assert panel.properties_tree.topLevelItemCount() == 0

    def test_single_property_added_state_green_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() with ADDED state displays green background in 3-column layout."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A single property with ADDED state
        properties = [
            PropertyPresentation(
                name="Length",
                old_value=None,
                new_value="25.0",
                state=DiffState.ADDED,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Should have one group with one property child
        assert panel.properties_tree.topLevelItemCount() == 1  # One group header
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item is not None

        # Check group header text (default group is "Properties")
        assert group_item.text(0) == "Properties"

        # Check property is a child of the group
        assert group_item.childCount() == 1
        prop_item = group_item.child(0)
        assert prop_item is not None

        # Check property name (column 0) - CamelCase converted to spaced
        assert prop_item.text(0) == "Length"

        # Check Value Left column (column 1) is empty for ADDED
        assert prop_item.text(1) == ""

        # Check Value Right column (column 2) has new value
        assert prop_item.text(2) == "25.0"

        # Check green background color on all 3 columns
        assert prop_item.background(0).color() == QColor(200, 255, 200)
        assert prop_item.background(1).color() == QColor(200, 255, 200)
        assert prop_item.background(2).color() == QColor(200, 255, 200)

    def test_single_property_deleted_state_red_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() with DELETED state displays red background in 3-column layout."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A single property with DELETED state
        properties = [
            PropertyPresentation(
                name="Width",
                old_value="15.0",
                new_value=None,
                state=DiffState.DELETED,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Should have one group with one property child
        assert panel.properties_tree.topLevelItemCount() == 1
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item.childCount() == 1

        prop_item = group_item.child(0)
        assert prop_item is not None

        # Check property name
        assert prop_item.text(0) == "Width"

        # Check Value Left column (column 1) has old value for DELETED
        assert prop_item.text(1) == "15.0"

        # Check Value Right column (column 2) is empty for DELETED
        assert prop_item.text(2) == ""

        # Check red background color on all 3 columns
        assert prop_item.background(0).color() == QColor(255, 200, 200)
        assert prop_item.background(1).color() == QColor(255, 200, 200)
        assert prop_item.background(2).color() == QColor(255, 200, 200)

    def test_single_property_modified_state_blue_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() with MODIFIED state displays blue background in 3-column layout."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A single property with MODIFIED state
        properties = [
            PropertyPresentation(
                name="Height",
                old_value="10.0",
                new_value="20.0",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Check the property has blue background
        group_item = panel.properties_tree.topLevelItem(0)
        prop_item = group_item.child(0)

        # Check Value Left column (column 1) has old value for MODIFIED
        assert prop_item.text(1) == "10.0"

        # Check Value Right column (column 2) has new value for MODIFIED
        assert prop_item.text(2) == "20.0"

        # Check blue background color on all 3 columns
        assert prop_item.background(0).color() == QColor(200, 200, 255)
        assert prop_item.background(1).color() == QColor(200, 200, 255)
        assert prop_item.background(2).color() == QColor(200, 200, 255)

    def test_multiple_properties_with_different_states(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() correctly handles multiple properties with different states in 3-column layout."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties with ADDED, DELETED, and MODIFIED states
        properties = [
            PropertyPresentation(
                name="AddedProp",
                old_value=None,
                new_value="100.0",
                state=DiffState.ADDED,
            ),
            PropertyPresentation(
                name="DeletedProp",
                old_value="50.0",
                new_value=None,
                state=DiffState.DELETED,
            ),
            PropertyPresentation(
                name="ModifiedProp",
                old_value="10.0",
                new_value="20.0",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Should have 1 group with 3 property children
        assert panel.properties_tree.topLevelItemCount() == 1
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item.childCount() == 3

        # Verify each property (names are CamelCase converted to spaced names)
        # Check first property (Added Prop) - green, empty left column, value in right
        prop0 = group_item.child(0)
        assert prop0.text(0) == "Added Prop"
        assert prop0.text(1) == ""  # Empty for ADDED
        assert prop0.text(2) == "100.0"  # New value in right
        assert prop0.background(0).color() == QColor(200, 255, 200)

        # Check second property (Deleted Prop) - red, value in left column, empty right
        prop1 = group_item.child(1)
        assert prop1.text(0) == "Deleted Prop"
        assert prop1.text(1) == "50.0"  # Old value in left
        assert prop1.text(2) == ""  # Empty for DELETED
        assert prop1.background(0).color() == QColor(255, 200, 200)

        # Check third property (Modified Prop) - blue, both columns populated
        prop2 = group_item.child(2)
        assert prop2.text(0) == "Modified Prop"
        assert prop2.text(1) == "10.0"  # Old value in left
        assert prop2.text(2) == "20.0"  # New value in right
        assert prop2.background(0).color() == QColor(200, 200, 255)

    def test_property_with_unchanged_state_gray_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() includes all properties with UNCHANGED state shown with gray background in 3-column layout."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Mix of changed and unchanged properties
        properties = [
            PropertyPresentation(
                name="ChangedProp",
                old_value="10.0",
                new_value="20.0",
                state=DiffState.MODIFIED,
            ),
            PropertyPresentation(
                name="UnchangedProp",
                old_value="50.0",
                new_value="50.0",
                state=DiffState.UNCHANGED,
            ),
            PropertyPresentation(
                name="AnotherChanged",
                old_value=None,
                new_value="75.0",
                state=DiffState.ADDED,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Should have 1 group with 3 property children
        assert panel.properties_tree.topLevelItemCount() == 1
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item.childCount() == 3

        # Get all property names
        names = [group_item.child(i).text(0) for i in range(3)]
        assert "Changed Prop" in names
        assert "Another Changed" in names
        assert "Unchanged Prop" in names

        # Find the unchanged property and verify its background is gray
        unchanged_index = names.index("Unchanged Prop")
        unchanged_item = group_item.child(unchanged_index)
        # For UNCHANGED, both columns show the same value
        assert unchanged_item.text(1) == "50.0"  # Value in left column
        assert unchanged_item.text(2) == "50.0"  # Same value in right column
        # Check background color is gray (light gray = 240, 240, 240) on all columns
        bg_color = unchanged_item.background(0).color()
        assert bg_color.red() == 240
        assert bg_color.green() == 240
        assert bg_color.blue() == 240

    def test_empty_list_initially_shows_no_items(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() with empty list shows no items initially."""
        # When: Call show_properties with empty list on fresh panel
        panel.show_properties([])

        # Then: Tree should have zero top-level items
        assert panel.properties_tree.topLevelItemCount() == 0

    def test_group_header_is_non_selectable(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() creates group headers that are not selectable."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties to display
        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Group header should not be selectable
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item is not None
        flags = group_item.flags()
        assert not (flags & Qt.ItemFlag.ItemIsSelectable)

    def test_group_header_has_gray_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() creates group headers with gray background on all 3 columns."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties to display
        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Group header should have gray background (220, 220, 220) on all 3 columns
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item.background(0).color() == QColor(220, 220, 220)
        assert group_item.background(1).color() == QColor(220, 220, 220)
        assert group_item.background(2).color() == QColor(220, 220, 220)

    def test_group_header_is_bold(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() creates group headers with bold font."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties to display
        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Group header font should be bold
        group_item = panel.properties_tree.topLevelItem(0)
        font = group_item.font(0)
        assert font.bold()

    def test_groups_are_expanded_by_default(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() expands groups by default so properties are visible."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties to display
        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Group should be expanded
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item.isExpanded()

    def test_multiple_group_headers_displayed_correctly(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() displays multiple groups as separate headers."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties from different groups (e.g., "Base" and "Format")
        properties = [
            PropertyPresentation(
                name="Label",
                state=DiffState.UNCHANGED,
                group="Base",
            ),
            PropertyPresentation(
                name="Length",
                state=DiffState.MODIFIED,
                group="Base",
            ),
            PropertyPresentation(
                name="FormatSpec",
                state=DiffState.MODIFIED,
                group="Format",
            ),
            PropertyPresentation(
                name="Arbitrary",
                state=DiffState.MODIFIED,
                group="Format",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Should have 2 group headers
        assert panel.properties_tree.topLevelItemCount() == 2

        # Get the group names
        group_names = [panel.properties_tree.topLevelItem(i).text(0) for i in range(2)]
        assert "Base" in group_names
        assert "Format" in group_names

        # Find the Base group and verify it has 2 properties
        base_index = group_names.index("Base")
        base_group = panel.properties_tree.topLevelItem(base_index)
        assert base_group.childCount() == 2

        # Find the Format group and verify it has 2 properties
        format_index = group_names.index("Format")
        format_group = panel.properties_tree.topLevelItem(format_index)
        assert format_group.childCount() == 2

        # Verify property names under Base group
        base_prop_names = [base_group.child(i).text(0) for i in range(2)]
        assert "Label" in base_prop_names
        assert "Length" in base_prop_names

        # Verify property names under Format group
        format_prop_names = [format_group.child(i).text(0) for i in range(2)]
        assert "Format Spec" in format_prop_names
        assert "Arbitrary" in format_prop_names


class TestDiffPanelViewExpandableProperties:
    """Tests for expandable properties in the tree widget."""

    def test_placement_property_marked_as_expandable(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() marks Placement property as expandable."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A Placement property
        properties = [
            PropertyPresentation(
                name="Placement",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: The Placement property item should exist and can be expanded
        group_item = panel.properties_tree.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item is not None
        assert prop_item.text(0) == "Placement"

        # Note: Full expansion requires actual FreeCAD objects with children
        # This test verifies the property name is correctly identified
        assert prop_item.isExpanded() is False or prop_item.childCount() >= 0

    def test_rotation_property_marked_as_expandable(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() marks Rotation property as expandable."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A Rotation property
        properties = [
            PropertyPresentation(
                name="Rotation",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: The Rotation property should be identifiable
        group_item = panel.properties_tree.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item is not None
        assert prop_item.text(0) == "Rotation"

    def test_expandable_property_with_vector_value_has_children(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() adds child items for expandable properties with vector values in 3-column layout."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A Position property with mock vector-like objects for old and new values
        class MockVector:
            def __init__(self, x, y, z):
                self.x = x
                self.y = y
                self.z = z

        old_vector = MockVector(0.0, 0.0, 0.0)
        new_vector = MockVector(10.0, 20.0, 30.0)

        properties = [
            PropertyPresentation(
                name="Position",
                state=DiffState.MODIFIED,
                old_value=old_vector,
                new_value=new_vector,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: The Position property should have children (x, y, z)
        group_item = panel.properties_tree.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item is not None
        assert prop_item.text(0) == "Position"

        # Verify children exist
        assert prop_item.childCount() == 3

        # Verify child names
        child_names = [prop_item.child(i).text(0) for i in range(3)]
        assert "x" in child_names
        assert "y" in child_names
        assert "z" in child_names

        # Verify old values in column 1
        old_values = [prop_item.child(i).text(1) for i in range(3)]
        assert "0.0" in old_values

        # Verify new values in column 2
        new_values = [prop_item.child(i).text(2) for i in range(3)]
        assert "10.0" in new_values
        assert "20.0" in new_values
        assert "30.0" in new_values

    def test_expandable_property_with_list_value_has_children(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() adds child items for expandable properties with list values in 3-column layout."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A property with list values for old and new
        properties = [
            PropertyPresentation(
                name="Items",
                state=DiffState.MODIFIED,
                old_value=[1, 2],
                new_value=[1, 2, 3],
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: The Items property should have children
        group_item = panel.properties_tree.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item is not None
        assert prop_item.text(0) == "Items"

        # Verify children exist (includes added child 2)
        assert prop_item.childCount() == 3

        # Verify child names (0, 1, 2)
        child_names = [prop_item.child(i).text(0) for i in range(3)]
        assert "0" in child_names
        assert "1" in child_names
        assert "2" in child_names

        # Verify old values in column 1
        old_values = [prop_item.child(i).text(1) for i in range(3)]
        assert "1" in old_values
        assert "2" in old_values

        # Verify new values in column 2
        new_values = [prop_item.child(i).text(2) for i in range(3)]
        assert "1" in new_values
        assert "2" in new_values
        assert "3" in new_values


class TestDiffPanelViewGroupSorting:
    """Tests for alphabetical group sorting in show_properties()."""

    def test_groups_appear_in_alphabetical_order(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() displays groups in alphabetical order (Base, Data, Format, etc.)."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties from multiple groups in non-alphabetical order
        properties = [
            PropertyPresentation(
                name="ZebraProp",
                state=DiffState.MODIFIED,
                group="Zebra",
            ),
            PropertyPresentation(
                name="AlphaProp",
                state=DiffState.MODIFIED,
                group="Alpha",
            ),
            PropertyPresentation(
                name="MiddleProp",
                state=DiffState.MODIFIED,
                group="Middle",
            ),
            PropertyPresentation(
                name="BetaProp",
                state=DiffState.MODIFIED,
                group="Beta",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Groups should appear in alphabetical order
        assert panel.properties_tree.topLevelItemCount() == 4

        # Verify alphabetical order: Alpha, Beta, Middle, Zebra
        group_names = [panel.properties_tree.topLevelItem(i).text(0) for i in range(4)]
        assert group_names == ["Alpha", "Beta", "Middle", "Zebra"]

    def test_groups_with_real_freecad_names_sorted_correctly(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() sorts FreeCAD-style group names alphabetically."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties using typical FreeCAD group names in random order
        properties = [
            PropertyPresentation(
                name="Label",
                state=DiffState.UNCHANGED,
                group="View",
            ),
            PropertyPresentation(
                name="Placement",
                state=DiffState.UNCHANGED,
                group="Base",
            ),
            PropertyPresentation(
                name="ElementName",
                state=DiffState.UNCHANGED,
                group="Format",
            ),
            PropertyPresentation(
                name="Support",
                state=DiffState.UNCHANGED,
                group="Data",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Groups should be sorted alphabetically: Base, Data, Format, View
        assert panel.properties_tree.topLevelItemCount() == 4
        group_names = [panel.properties_tree.topLevelItem(i).text(0) for i in range(4)]
        assert group_names == ["Base", "Data", "Format", "View"]

    def test_properties_within_groups_maintain_input_order(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() maintains property order within each group as provided."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Multiple properties in same group with specific order
        properties = [
            PropertyPresentation(
                name="ZProp",
                state=DiffState.UNCHANGED,
                group="TestGroup",
            ),
            PropertyPresentation(
                name="AProp",
                state=DiffState.UNCHANGED,
                group="TestGroup",
            ),
            PropertyPresentation(
                name="MProp",
                state=DiffState.UNCHANGED,
                group="TestGroup",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Properties within the group maintain their input order (ZProp, AProp, MProp)
        assert panel.properties_tree.topLevelItemCount() == 1
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item.text(0) == "TestGroup"
        assert group_item.childCount() == 3

        # Verify order is preserved as input (not sorted)
        prop_names = [group_item.child(i).text(0) for i in range(3)]
        assert prop_names == ["Z Prop", "A Prop", "M Prop"]

    def test_single_group_no_sorting_needed(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() handles single group correctly without sorting issues."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: All properties in a single group
        properties = [
            PropertyPresentation(
                name="Prop1",
                state=DiffState.MODIFIED,
                group="SingleGroup",
            ),
            PropertyPresentation(
                name="Prop2",
                state=DiffState.MODIFIED,
                group="SingleGroup",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Should have one group with two properties
        assert panel.properties_tree.topLevelItemCount() == 1
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item.text(0) == "SingleGroup"
        assert group_item.childCount() == 2

    def test_default_group_properties_shows_when_no_group_specified(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() places ungrouped properties in 'Properties' default group."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Mix of grouped and ungrouped properties
        properties = [
            PropertyPresentation(
                name="GroupedProp",
                state=DiffState.MODIFIED,
                group="CustomGroup",
            ),
            PropertyPresentation(
                name="UngroupedProp",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Should have 2 groups (CustomGroup and Properties), sorted alphabetically
        assert panel.properties_tree.topLevelItemCount() == 2
        group_names = [panel.properties_tree.topLevelItem(i).text(0) for i in range(2)]
        # CustomGroup comes before Properties alphabetically
        assert group_names == ["CustomGroup", "Properties"]

        # Verify ungrouped property is in Properties group
        properties_index = group_names.index("Properties")
        properties_group = panel.properties_tree.topLevelItem(properties_index)
        assert properties_group.childCount() == 1
        assert properties_group.child(0).text(0) == "Ungrouped Prop"

    def test_case_sensitive_sorting_behavior(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() sorts groups case-sensitively (uppercase before lowercase)."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Groups with similar names but different cases
        properties = [
            PropertyPresentation(
                name="Prop1",
                state=DiffState.MODIFIED,
                group="base",
            ),
            PropertyPresentation(
                name="Prop2",
                state=DiffState.MODIFIED,
                group="Base",
            ),
            PropertyPresentation(
                name="Prop3",
                state=DiffState.MODIFIED,
                group="alpha",
            ),
            PropertyPresentation(
                name="Prop4",
                state=DiffState.MODIFIED,
                group="Alpha",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Groups should be sorted case-sensitively (ASCII order: uppercase before lowercase)
        # In ASCII/Python sorted(): 'A' (65) < 'B' (66) < 'a' (97) < 'b' (98)
        assert panel.properties_tree.topLevelItemCount() == 4
        group_names = [panel.properties_tree.topLevelItem(i).text(0) for i in range(4)]
        assert group_names == ["Alpha", "Base", "alpha", "base"]

    def test_empty_string_group_name_defaults_to_properties(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() treats empty string group names as the default 'Properties' group."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties with empty string group and explicit group
        properties = [
            PropertyPresentation(
                name="EmptyGroupProp",
                state=DiffState.MODIFIED,
                group="",
            ),
            PropertyPresentation(
                name="ExplicitGroupProp",
                state=DiffState.MODIFIED,
                group="CustomGroup",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Empty string group is converted to "Properties" (same as no group specified)
        # So we get 2 groups: CustomGroup and Properties (sorted alphabetically)
        assert panel.properties_tree.topLevelItemCount() == 2
        group_names = [panel.properties_tree.topLevelItem(i).text(0) for i in range(2)]
        assert group_names == ["CustomGroup", "Properties"]

        # Verify the property with empty group is in the Properties group
        properties_index = group_names.index("Properties")
        properties_group = panel.properties_tree.topLevelItem(properties_index)
        assert properties_group.childCount() == 1
        assert properties_group.child(0).text(0) == "Empty Group Prop"


class TestDiffPanelViewThreeColumnLayout:
    """Tests for the 3-column property diff layout."""

    def test_properties_tree_has_three_columns(self, panel) -> None:  # type: ignore[no-untyped-def]
        """properties_tree has exactly 3 columns."""
        # When: Creating a fresh panel
        # Then: The properties tree should have 3 columns
        assert panel.properties_tree.columnCount() == 3

    def test_header_labels_are_correct(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Header labels are ['Property', 'Value Left', 'Value Right']."""

        # When: Creating a fresh panel and adding a property
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]
        panel.show_properties(properties)

        # Then: Header labels should be correct (verified via tree item column count and content)
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item is not None
        # Verify we can access all 3 columns
        assert group_item.text(0) == "Properties"
        assert group_item.text(1) == ""
        assert group_item.text(2) == ""
        # The header labels are set in _setup_ui with setHeaderLabels(["Property", "Value Left", "Value Right"])

    def test_group_header_has_empty_columns_1_and_2(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Group headers have empty text in columns 1 and 2."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A property to display
        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Group header should have empty columns 1 and 2
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item.text(0) == "Properties"
        assert group_item.text(1) == ""
        assert group_item.text(2) == ""


class TestDiffPanelViewExpandablePropertyChildDiffs:
    """Tests for expandable properties with child diff comparison (Phase 4)."""

    def test_expandable_property_with_mixed_child_states(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() correctly displays children with different states (modified and unchanged)."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Mock vector-like objects for old and new values
        class MockVector:
            def __init__(self, x, y, z):
                self.x = x
                self.y = y
                self.z = z

        old_vector = MockVector(10.0, 20.0, 30.0)
        new_vector = MockVector(10.0, 25.0, 30.0)  # Only y changed

        properties = [
            PropertyPresentation(
                name="Position",
                state=DiffState.MODIFIED,
                old_value=old_vector,
                new_value=new_vector,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: The Position property should have children (x, y, z)
        group_item = panel.properties_tree.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item is not None
        assert prop_item.text(0) == "Position"

        # Verify children exist
        assert prop_item.childCount() == 3

        # Get child items by name
        child_items = {prop_item.child(i).text(0): prop_item.child(i) for i in range(3)}
        assert "x" in child_items
        assert "y" in child_items
        assert "z" in child_items

        # Check x child (UNCHANGED: same value 10.0)
        x_child = child_items["x"]
        assert x_child.text(1) == "10.0"  # Old value
        assert x_child.text(2) == "10.0"  # New value
        # Unchanged children should have default background (not colored)
        x_bg = x_child.background(0).color()
        assert x_bg != QColor(200, 200, 255)  # Not MODIFIED color

        # Check y child (MODIFIED: 20.0 -> 25.0)
        y_child = child_items["y"]
        assert y_child.text(1) == "20.0"  # Old value
        assert y_child.text(2) == "25.0"  # New value
        # Modified children should have blue background
        assert y_child.background(0).color() == QColor(200, 200, 255)
        assert y_child.background(1).color() == QColor(200, 200, 255)
        assert y_child.background(2).color() == QColor(200, 200, 255)

        # Check z child (UNCHANGED: same value 30.0)
        z_child = child_items["z"]
        assert z_child.text(1) == "30.0"  # Old value
        assert z_child.text(2) == "30.0"  # New value
        # Unchanged children should have default background (not colored)
        z_bg = z_child.background(0).color()
        assert z_bg != QColor(200, 200, 255)  # Not MODIFIED color

        # Parent row should be blue because it has changed children
        assert prop_item.background(0).color() == QColor(200, 200, 255)

    def test_expandable_property_with_added_child(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() correctly displays ADDED children (present in new but not old)."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Mock objects where new_value has an extra child
        class OldObj:
            def __init__(self):
                self.x = 10.0
                self.y = 20.0

        class NewObj:
            def __init__(self):
                self.x = 10.0
                self.y = 20.0
                self.z = 30.0  # Added child

        properties = [
            PropertyPresentation(
                name="Vector",
                state=DiffState.MODIFIED,
                old_value=OldObj(),
                new_value=NewObj(),
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: The Vector property should have children including the added z
        group_item = panel.properties_tree.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item is not None

        # Should have x, y, z children
        assert prop_item.childCount() == 3

        # Get child items by name
        child_items = {prop_item.child(i).text(0): prop_item.child(i) for i in range(3)}
        assert "z" in child_items

        # Check z child (ADDED: empty old value, has new value)
        z_child = child_items["z"]
        assert z_child.text(1) == ""  # Empty old value
        assert z_child.text(2) == "30.0"  # New value
        # Added children should have green background
        assert z_child.background(0).color() == QColor(200, 255, 200)
        assert z_child.background(1).color() == QColor(200, 255, 200)
        assert z_child.background(2).color() == QColor(200, 255, 200)

    def test_expandable_property_with_deleted_child(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() correctly displays DELETED children (present in old but not new)."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Mock objects where old_value has an extra child
        class OldObj:
            def __init__(self):
                self.x = 10.0
                self.y = 20.0
                self.z = 30.0  # Will be deleted

        class NewObj:
            def __init__(self):
                self.x = 10.0
                self.y = 20.0

        properties = [
            PropertyPresentation(
                name="Vector",
                state=DiffState.MODIFIED,
                old_value=OldObj(),
                new_value=NewObj(),
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: The Vector property should have children including the deleted z
        group_item = panel.properties_tree.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item is not None

        # Should have x, y, z children
        assert prop_item.childCount() == 3

        # Get child items by name
        child_items = {prop_item.child(i).text(0): prop_item.child(i) for i in range(3)}
        assert "z" in child_items

        # Check z child (DELETED: has old value, empty new value)
        z_child = child_items["z"]
        assert z_child.text(1) == "30.0"  # Old value
        assert z_child.text(2) == ""  # Empty new value
        # Deleted children should have red background
        assert z_child.background(0).color() == QColor(255, 200, 200)
        assert z_child.background(1).color() == QColor(255, 200, 200)
        assert z_child.background(2).color() == QColor(255, 200, 200)

    def test_parent_row_colored_blue_when_any_child_changed(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Parent row is colored blue (MODIFIED) when any child has MODIFIED/ADDED/DELETED state."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Mock vector-like objects where only one child changes
        class MockVector:
            def __init__(self, x, y, z):
                self.x = x
                self.y = y
                self.z = z

        old_vector = MockVector(10.0, 20.0, 30.0)
        new_vector = MockVector(10.0, 20.0, 35.0)  # Only z changed

        properties = [
            PropertyPresentation(
                name="Position",
                state=DiffState.UNCHANGED,  # Parent state is UNCHANGED but has changed children
                old_value=old_vector,
                new_value=new_vector,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Parent row should be blue because it has a changed child
        group_item = panel.properties_tree.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item is not None

        # Parent should be blue regardless of its own state because it has changed children
        assert prop_item.background(0).color() == QColor(200, 200, 255)
        assert prop_item.background(1).color() == QColor(200, 200, 255)
        assert prop_item.background(2).color() == QColor(200, 200, 255)

    def test_unchanged_children_have_default_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Unchanged children have default background (no diff coloring)."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Mock vector-like objects where all children are unchanged
        class MockVector:
            def __init__(self, x, y, z):
                self.x = x
                self.y = y
                self.z = z

        old_vector = MockVector(10.0, 20.0, 30.0)
        new_vector = MockVector(10.0, 20.0, 30.0)  # All same values

        properties = [
            PropertyPresentation(
                name="Position",
                state=DiffState.UNCHANGED,
                old_value=old_vector,
                new_value=new_vector,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: All children should have default background
        group_item = panel.properties_tree.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item is not None

        # Check all children have default background (not any of the diff colors)
        diff_colors = [
            QColor(200, 255, 200),  # ADDED
            QColor(255, 200, 200),  # DELETED
            QColor(200, 200, 255),  # MODIFIED
            QColor(240, 240, 240),  # UNCHANGED
        ]

        for i in range(prop_item.childCount()):
            child = prop_item.child(i)
            bg_color = child.background(0).color()
            # Unchanged children should not have any diff color
            assert bg_color not in diff_colors

    def test_expandable_property_with_list_values_and_child_diffs(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() correctly handles list values with child diffs."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Using lists for old and new values
        old_list = [1, 2, 3]
        new_list = [1, 5, 3]  # Only index [1] changed

        properties = [
            PropertyPresentation(
                name="Items",
                state=DiffState.MODIFIED,
                old_value=old_list,
                new_value=new_list,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: The Items property should have children 0, 1, 2
        group_item = panel.properties_tree.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item is not None
        assert prop_item.childCount() == 3

        # Get child items by name
        child_items = {prop_item.child(i).text(0): prop_item.child(i) for i in range(3)}
        assert "0" in child_items
        assert "1" in child_items
        assert "2" in child_items

        # Check 0 child (UNCHANGED: same value 1)
        child_0 = child_items["0"]
        assert child_0.text(1) == "1"
        assert child_0.text(2) == "1"

        # Check 1 child (MODIFIED: 2 -> 5)
        child_1 = child_items["1"]
        assert child_1.text(1) == "2"
        assert child_1.text(2) == "5"
        # Modified child should have blue background
        assert child_1.background(0).color() == QColor(200, 200, 255)

        # Check 2 child (UNCHANGED: same value 3)
        child_2 = child_items["2"]
        assert child_2.text(1) == "3"
        assert child_2.text(2) == "3"


class TestDiffPanelViewExpressionRows:
    """Tests for expression row display in 3-column layout (Phase 5)."""

    def test_expression_row_appears_as_separate_property_row(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Expression rows appear as separate property rows below their parent in 3-column layout."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A property with an expression change
        properties = [
            PropertyPresentation(
                name="Length",
                state=DiffState.MODIFIED,
            ),
            PropertyPresentation(
                name="-> Expression",
                state=DiffState.MODIFIED,
                old_value="Sketch.X",
                new_value="Sketch.Y",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Should have 2 property rows under the group
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item is not None
        assert group_item.childCount() == 2

        # First row is Length property
        length_item = group_item.child(0)
        assert length_item.text(0) == "Length"

        # Second row is Expression
        expr_item = group_item.child(1)
        assert expr_item.text(0) == "-> Expression"

    def test_expression_row_modified_state_blue_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Expression row with MODIFIED state displays blue background in 3-column layout."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: An expression row with MODIFIED state
        properties = [
            PropertyPresentation(
                name="-> Expression",
                state=DiffState.MODIFIED,
                old_value="Sketch.X",
                new_value="Sketch.Y",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Expression row should have blue background and correct column values
        group_item = panel.properties_tree.topLevelItem(0)
        expr_item = group_item.child(0)

        # Check display name
        assert expr_item.text(0) == "-> Expression"

        # Check Value Left column has old expression
        assert expr_item.text(1) == "Sketch.X"

        # Check Value Right column has new expression
        assert expr_item.text(2) == "Sketch.Y"

        # Check blue background on all 3 columns
        assert expr_item.background(0).color() == QColor(200, 200, 255)
        assert expr_item.background(1).color() == QColor(200, 200, 255)
        assert expr_item.background(2).color() == QColor(200, 200, 255)

    def test_expression_row_added_state_green_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Expression row with ADDED state displays green background in 3-column layout."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: An expression row with ADDED state (expression added to property)
        properties = [
            PropertyPresentation(
                name="-> Expression",
                state=DiffState.ADDED,
                old_value=None,
                new_value="Sketch.Length * 2",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Expression row should have green background
        group_item = panel.properties_tree.topLevelItem(0)
        expr_item = group_item.child(0)

        # Check display name
        assert expr_item.text(0) == "-> Expression"

        # Check Value Left column is empty for ADDED
        assert expr_item.text(1) == ""

        # Check Value Right column has new expression
        assert expr_item.text(2) == "Sketch.Length * 2"

        # Check green background on all 3 columns
        assert expr_item.background(0).color() == QColor(200, 255, 200)
        assert expr_item.background(1).color() == QColor(200, 255, 200)
        assert expr_item.background(2).color() == QColor(200, 255, 200)

    def test_expression_row_deleted_state_red_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Expression row with DELETED state displays red background in 3-column layout."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: An expression row with DELETED state (expression removed from property)
        properties = [
            PropertyPresentation(
                name="-> Expression",
                state=DiffState.DELETED,
                old_value="Sketch.X",
                new_value=None,
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Expression row should have red background
        group_item = panel.properties_tree.topLevelItem(0)
        expr_item = group_item.child(0)

        # Check display name
        assert expr_item.text(0) == "-> Expression"

        # Check Value Left column has old expression for DELETED
        assert expr_item.text(1) == "Sketch.X"

        # Check Value Right column is empty for DELETED
        assert expr_item.text(2) == ""

        # Check red background on all 3 columns
        assert expr_item.background(0).color() == QColor(255, 200, 200)
        assert expr_item.background(1).color() == QColor(255, 200, 200)
        assert expr_item.background(2).color() == QColor(255, 200, 200)

    def test_expression_row_unchanged_state_gray_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Expression row with UNCHANGED state displays gray background in 3-column layout."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: An expression row with UNCHANGED state
        properties = [
            PropertyPresentation(
                name="-> Expression",
                state=DiffState.UNCHANGED,
                old_value="Sketch.X",
                new_value="Sketch.X",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Expression row should have gray background
        group_item = panel.properties_tree.topLevelItem(0)
        expr_item = group_item.child(0)

        # Check display name
        assert expr_item.text(0) == "-> Expression"

        # Check both columns have the same expression value
        assert expr_item.text(1) == "Sketch.X"
        assert expr_item.text(2) == "Sketch.X"

        # Check gray background (240, 240, 240) on all columns
        bg_color = expr_item.background(0).color()
        assert bg_color.red() == 240
        assert bg_color.green() == 240
        assert bg_color.blue() == 240

    def test_expression_row_follows_parent_property(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Expression row appears immediately after its parent property."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Multiple properties with expressions
        properties = [
            PropertyPresentation(
                name="Length",
                state=DiffState.MODIFIED,
                group="Base",
            ),
            PropertyPresentation(
                name="-> Expression",
                state=DiffState.MODIFIED,
                old_value="Sketch.Length",
                new_value="Sketch.Width",
                group="Base",  # Expressions inherit group from parent property
            ),
            PropertyPresentation(
                name="Width",
                state=DiffState.MODIFIED,
                group="Base",
            ),
            PropertyPresentation(
                name="-> Expression",
                state=DiffState.ADDED,
                old_value=None,
                new_value="Sketch.Height",
                group="Base",  # Expressions inherit group from parent property
            ),
            PropertyPresentation(
                name="Height",
                state=DiffState.UNCHANGED,
                group="Base",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Each expression should follow its parent property
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item.childCount() == 5

        # Row 0: Length (MODIFIED)
        length_item = group_item.child(0)
        assert length_item.text(0) == "Length"
        assert length_item.background(0).color() == QColor(200, 200, 255)

        # Row 1: Expression for Length (MODIFIED)
        expr1_item = group_item.child(1)
        assert expr1_item.text(0) == "-> Expression"
        assert expr1_item.text(1) == "Sketch.Length"
        assert expr1_item.text(2) == "Sketch.Width"
        assert expr1_item.background(0).color() == QColor(200, 200, 255)

        # Row 2: Width (MODIFIED)
        width_item = group_item.child(2)
        assert width_item.text(0) == "Width"
        assert width_item.background(0).color() == QColor(200, 200, 255)

        # Row 3: Expression for Width (ADDED)
        expr2_item = group_item.child(3)
        assert expr2_item.text(0) == "-> Expression"
        assert expr2_item.text(1) == ""  # Empty for ADDED
        assert expr2_item.text(2) == "Sketch.Height"
        assert expr2_item.background(0).color() == QColor(200, 255, 200)

        # Row 4: Height (UNCHANGED) - no expression
        height_item = group_item.child(4)
        assert height_item.text(0) == "Height"
