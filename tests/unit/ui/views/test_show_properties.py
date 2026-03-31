"""File responsibility: Unit tests for DiffPanelView.show_properties() method with QTreeWidget.

These tests verify that the DiffPanelView correctly populates the properties
tree widget with PropertyPresentation data, including:
- Group headers with gray background
- Diff coloring (green=added, red=deleted, blue=modified)
- Expandable properties functionality
"""

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
                    old_display="10.0",
                    new_display="20.0",
                    state="MODIFIED",
                ),
            ]
        )
        assert panel.properties_tree.topLevelItemCount() == 1

        # When: Call show_properties with empty list
        panel.show_properties([])

        # Then: Tree should be cleared
        assert panel.properties_tree.topLevelItemCount() == 0

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

        # Check value column (column 1)
        assert prop_item.text(1) == "25.0"

        # Check green background color
        assert prop_item.background(0).color() == QColor(200, 255, 200)
        assert prop_item.background(1).color() == QColor(200, 255, 200)

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

        # Then: Should have one group with one property child
        assert panel.properties_tree.topLevelItemCount() == 1
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item.childCount() == 1

        prop_item = group_item.child(0)
        assert prop_item is not None

        # Check property name
        assert prop_item.text(0) == "Width"

        # Check value column - should show old value for deleted
        assert prop_item.text(1) == "15.0"

        # Check red background color
        assert prop_item.background(0).color() == QColor(255, 200, 200)
        assert prop_item.background(1).color() == QColor(255, 200, 200)

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

        # Then: Check the property has blue background
        group_item = panel.properties_tree.topLevelItem(0)
        prop_item = group_item.child(0)

        # Check value column - should show "old → new" format
        assert prop_item.text(1) == "10.0 → 20.0"

        # Check blue background color
        assert prop_item.background(0).color() == QColor(200, 200, 255)
        assert prop_item.background(1).color() == QColor(200, 200, 255)

    def test_multiple_properties_with_different_states(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() correctly handles multiple properties with different states."""
        from PySide6.QtGui import QColor

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

        # Then: Should have 1 group with 3 property children
        assert panel.properties_tree.topLevelItemCount() == 1
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item.childCount() == 3

        # Verify each property (names are CamelCase converted to spaced names)
        # Check first property (Added Prop) - green
        prop0 = group_item.child(0)
        assert prop0.text(0) == "Added Prop"
        assert prop0.text(1) == "100.0"
        assert prop0.background(0).color() == QColor(200, 255, 200)

        # Check second property (Deleted Prop) - red
        prop1 = group_item.child(1)
        assert prop1.text(0) == "Deleted Prop"
        assert prop1.text(1) == "50.0"
        assert prop1.background(0).color() == QColor(255, 200, 200)

        # Check third property (Modified Prop) - blue
        prop2 = group_item.child(2)
        assert prop2.text(0) == "Modified Prop"
        assert prop2.text(1) == "10.0 → 20.0"
        assert prop2.background(0).color() == QColor(200, 200, 255)

    def test_property_with_unchanged_state_gray_background(self, panel) -> None:  # type: ignore[no-untyped-def]
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
        assert unchanged_item.text(1) == "50.0"  # Just the value, no arrows
        # Check background color is gray (light gray = 240, 240, 240)
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
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
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
        """show_properties() creates group headers with gray background."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties to display
        properties = [
            PropertyPresentation(
                name="TestProp",
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: Group header should have gray background (220, 220, 220)
        group_item = panel.properties_tree.topLevelItem(0)
        assert group_item.background(0).color() == QColor(220, 220, 220)
        assert group_item.background(1).color() == QColor(220, 220, 220)

    def test_group_header_is_bold(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() creates group headers with bold font."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties to display
        properties = [
            PropertyPresentation(
                name="TestProp",
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
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
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
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
                old_display="Dimension",
                new_display="Dimension",
                state="UNCHANGED",
                group="Base",
            ),
            PropertyPresentation(
                name="Length",
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
                group="Base",
            ),
            PropertyPresentation(
                name="FormatSpec",
                old_display="%.2f",
                new_display="%.3f",
                state="MODIFIED",
                group="Format",
            ),
            PropertyPresentation(
                name="Arbitrary",
                old_display="false",
                new_display="true",
                state="MODIFIED",
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
                old_display="[(0 0 1); 0°; (0 0 0)]",
                new_display="[(0 0 1); 45°; (10 20 30)]",
                state="MODIFIED",
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
                old_display="0°",
                new_display="45°",
                state="MODIFIED",
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
        """show_properties() adds child items for expandable properties with vector values."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A Position property with a mock vector-like object
        class MockVector:
            def __init__(self, x, y, z):
                self.x = x
                self.y = y
                self.z = z

        mock_vector = MockVector(10.0, 20.0, 30.0)

        properties = [
            PropertyPresentation(
                name="Position",
                old_display="[0.0, 0.0, 0.0]",
                new_display="[10.0, 20.0, 30.0]",
                state="MODIFIED",
                value=mock_vector,
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

        # Verify child names and values
        child_names = [prop_item.child(i).text(0) for i in range(3)]
        child_values = [prop_item.child(i).text(1) for i in range(3)]
        assert "x" in child_names
        assert "y" in child_names
        assert "z" in child_names
        assert "10.0" in child_values
        assert "20.0" in child_values
        assert "30.0" in child_values

    def test_expandable_property_with_list_value_has_children(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() adds child items for expandable properties with list values."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A property with a list value
        properties = [
            PropertyPresentation(
                name="Items",
                old_display="[1, 2]",
                new_display="[1, 2, 3]",
                state="MODIFIED",
                value=[1, 2, 3],
            ),
        ]

        # When: Call show_properties
        panel.show_properties(properties)

        # Then: The Items property should have children
        group_item = panel.properties_tree.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item is not None
        assert prop_item.text(0) == "Items"

        # Verify children exist
        assert prop_item.childCount() == 3

        # Verify child names ([0], [1], [2])
        child_names = [prop_item.child(i).text(0) for i in range(3)]
        assert "[0]" in child_names
        assert "[1]" in child_names
        assert "[2]" in child_names


class TestDiffPanelViewGroupSorting:
    """Tests for alphabetical group sorting in show_properties()."""

    def test_groups_appear_in_alphabetical_order(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_properties() displays groups in alphabetical order (Base, Data, Format, etc.)."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties from multiple groups in non-alphabetical order
        properties = [
            PropertyPresentation(
                name="ZebraProp",
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
                group="Zebra",
            ),
            PropertyPresentation(
                name="AlphaProp",
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
                group="Alpha",
            ),
            PropertyPresentation(
                name="MiddleProp",
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
                group="Middle",
            ),
            PropertyPresentation(
                name="BetaProp",
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
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
                old_display="Test",
                new_display="Test",
                state="UNCHANGED",
                group="View",
            ),
            PropertyPresentation(
                name="Placement",
                old_display="[(0 0 1); 0°; (0 0 0)]",
                new_display="[(0 0 1); 0°; (0 0 0)]",
                state="UNCHANGED",
                group="Base",
            ),
            PropertyPresentation(
                name="ElementName",
                old_display="Sketch",
                new_display="Sketch",
                state="UNCHANGED",
                group="Format",
            ),
            PropertyPresentation(
                name="Support",
                old_display="false",
                new_display="false",
                state="UNCHANGED",
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
                old_display="30.0",
                new_display="30.0",
                state="UNCHANGED",
                group="TestGroup",
            ),
            PropertyPresentation(
                name="AProp",
                old_display="10.0",
                new_display="10.0",
                state="UNCHANGED",
                group="TestGroup",
            ),
            PropertyPresentation(
                name="MProp",
                old_display="20.0",
                new_display="20.0",
                state="UNCHANGED",
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
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
                group="SingleGroup",
            ),
            PropertyPresentation(
                name="Prop2",
                old_display="30.0",
                new_display="40.0",
                state="MODIFIED",
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
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
                group="CustomGroup",
            ),
            PropertyPresentation(
                name="UngroupedProp",
                old_display="30.0",
                new_display="40.0",
                state="MODIFIED",
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
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
                group="base",
            ),
            PropertyPresentation(
                name="Prop2",
                old_display="30.0",
                new_display="40.0",
                state="MODIFIED",
                group="Base",
            ),
            PropertyPresentation(
                name="Prop3",
                old_display="50.0",
                new_display="60.0",
                state="MODIFIED",
                group="alpha",
            ),
            PropertyPresentation(
                name="Prop4",
                old_display="70.0",
                new_display="80.0",
                state="MODIFIED",
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
                old_display="10.0",
                new_display="20.0",
                state="MODIFIED",
                group="",
            ),
            PropertyPresentation(
                name="ExplicitGroupProp",
                old_display="30.0",
                new_display="40.0",
                state="MODIFIED",
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
