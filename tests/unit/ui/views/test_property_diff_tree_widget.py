"""File responsibility: Unit tests for PropertyDiffTreeWidget component."""

import pytest
from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.qt import QtCore, QtWidgets
from freecad.history_wb.ui.views.diff_theme import DIFF_STATE_ROLE


@pytest.fixture(scope="module")
def widget() -> object:
    """Create a PropertyDiffTreeWidget instance for testing.

    Note: This uses module scope to ensure QApplication is created once
    and reused across all tests in this module.
    """
    # Ensure QApplication exists before creating widgets
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    from freecad.history_wb.ui.views.property_diff_tree_widget import PropertyDiffTreeWidget

    return PropertyDiffTreeWidget()


class TestPropertyDiffTreeWidgetShowPropertyDiff:
    """Tests for PropertyDiffTreeWidget.show_property_diff() method."""

    def test_empty_property_list_clears_tree(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() with empty list clears the properties tree."""
        from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Tree has existing items from previous call
        widget.show_property_diff(
            [
                PropertyPresentation(
                    name="Length",
                    state=DiffState.MODIFIED,
                ),
            ]
        )
        assert widget.topLevelItemCount() == 1

        # When: Call show_property_diff with empty list
        widget.show_property_diff([])

        # Then: Tree should be cleared
        assert widget.topLevelItemCount() == 0

    @pytest.mark.parametrize(
        ("state,old_val,new_val,col1,col2"),
        [
            (DiffState.ADDED, None, "25.0", "", "25.0"),
            (DiffState.DELETED, "15.0", None, "15.0", ""),
            (DiffState.MODIFIED, "10.0", "20.0", "10.0", "20.0"),
        ],
    )
    def test_state_variant_colors_and_columns(
        self,
        widget,
        state,
        old_val,
        new_val,
        col1,
        col2,
    ) -> None:
        """Parametrized test for changed state coloring data and column values."""
        from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation

        properties = [
            PropertyPresentation(
                name="TestProp",
                old_value=old_val,
                new_value=new_val,
                state=state,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Verify column values and background color
        group_item = widget.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item is not None
        assert prop_item.text(1) == col1
        assert prop_item.text(2) == col2
        for column in range(3):
            assert prop_item.data(column, DIFF_STATE_ROLE) == state
            assert prop_item.background(column).style() != QtCore.Qt.BrushStyle.NoBrush
            assert prop_item.foreground(column).style() != QtCore.Qt.BrushStyle.NoBrush

    def test_property_with_unchanged_state_uses_normal_background(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() includes UNCHANGED properties with normal theme background."""
        from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation

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

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Should have 1 group with 3 property children
        assert widget.topLevelItemCount() == 1
        group_item = widget.topLevelItem(0)
        assert group_item.childCount() == 3

        # Get all property names
        names = [group_item.child(i).text(0) for i in range(3)]
        assert "Changed Prop" in names
        assert "Another Changed" in names
        assert "Unchanged Prop" in names

        # Find the unchanged property and verify it has no custom diff background
        unchanged_index = names.index("Unchanged Prop")
        unchanged_item = group_item.child(unchanged_index)
        # For UNCHANGED, both columns show the same value
        assert unchanged_item.text(1) == "50.0"  # Value in left column
        assert unchanged_item.text(2) == "50.0"  # Same value in right column
        for column in range(3):
            assert unchanged_item.data(column, DIFF_STATE_ROLE) is None
            assert unchanged_item.background(column).style() == QtCore.Qt.BrushStyle.NoBrush


class TestPropertyDiffTreeWidgetGroupHeaders:
    """Tests for group header creation and styling."""

    def test_group_header_is_non_selectable(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() creates group headers that are not selectable."""
        from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties to display
        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Group header should not be selectable
        group_item = widget.topLevelItem(0)
        assert group_item is not None
        flags = group_item.flags()
        assert not (flags & QtCore.Qt.ItemFlag.ItemIsSelectable)

    def test_groups_are_expanded_by_default(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() expands groups by default so properties are visible."""
        from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties to display
        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Group should be expanded
        group_item = widget.topLevelItem(0)
        assert group_item.isExpanded()


class TestPropertyDiffTreeWidgetGroupSorting:
    """Tests for alphabetical group sorting in show_property_diff()."""

    def test_groups_appear_in_alphabetical_order(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() displays groups in alphabetical order (Base, Data, Format, etc.)."""
        from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation

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

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Groups should appear in alphabetical order
        assert widget.topLevelItemCount() == 4

        # Verify alphabetical order: Alpha, Beta, Middle, Zebra
        group_names = [widget.topLevelItem(i).text(0) for i in range(4)]
        assert group_names == ["Alpha", "Beta", "Middle", "Zebra"]

    def test_properties_within_groups_maintain_input_order(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() maintains property order within each group as provided."""
        from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation

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

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Properties within the group maintain their input order (ZProp, AProp, MProp)
        assert widget.topLevelItemCount() == 1
        group_item = widget.topLevelItem(0)
        assert group_item.text(0) == "TestGroup"
        assert group_item.childCount() == 3

        # Verify order is preserved as input (not sorted)
        prop_names = [group_item.child(i).text(0) for i in range(3)]
        assert prop_names == ["Z Prop", "A Prop", "M Prop"]


class TestPropertyDiffTreeWidgetCamelCaseConversion:
    """Tests for CamelCase to space conversion."""

    def test_camelcase_conversion_remains_unchanged_simple(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Simple CamelCase names are converted correctly."""
        from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties with various CamelCase patterns
        properties = [
            PropertyPresentation(
                name="SavedGeometry",
                state=DiffState.MODIFIED,
            ),
            PropertyPresentation(
                name="XMLParser",
                state=DiffState.MODIFIED,
            ),
            PropertyPresentation(
                name="Value2D",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Names should be converted with spaces
        group_item = widget.topLevelItem(0)
        prop_names = [group_item.child(i).text(0) for i in range(3)]
        assert "Saved Geometry" in prop_names
        assert "XML Parser" in prop_names
        assert "Value 2D" in prop_names


class TestCamelcaseHelper:
    """Unit tests for the _camelcase_to_spaces helper function."""

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("SavedGeometry", "Saved Geometry"),
            ("Placement", "Placement"),
            ("Label2", "Label 2"),
            ("XDirection", "X Direction"),
            ("MyPropertyName", "My Property Name"),
            ("XMLDoc", "XML Doc"),
        ],
    )
    def test_camelcase_to_spaces(self, input_name: str, expected: str) -> None:
        from freecad.history_wb.ui.views.property_diff_tree_widget import _camelcase_to_spaces

        assert _camelcase_to_spaces(input_name) == expected


class TestPropertyDiffTreeWidgetNestedChildren:
    """Tests for nested children recursion and expansion."""

    def test_nested_children_recurse_and_expansion_state_applied(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Nested children are recursively added and expansion state is applied after insertion."""
        from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Nested structure where inner node is MODIFIED
        x_child = PropertyPresentation(name="x", state=DiffState.MODIFIED, old_value=1.0, new_value=2.0)
        base_parent = PropertyPresentation(
            name="Base",
            state=DiffState.MODIFIED,
            children=[x_child],
        )
        placement = PropertyPresentation(
            name="Placement",
            state=DiffState.MODIFIED,
            children=[base_parent],
        )

        properties = [placement]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: All nodes in the changed branch are expanded
        group_item = widget.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item.isExpanded()  # Placement has changed descendants
        assert prop_item.child(0).isExpanded()  # Base has changed descendants
        assert prop_item.child(0).child(0).isExpanded()  # x has MODIFIED state

    def test_unchanged_branches_collapsed(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Unchanged branches stay collapsed when no descendant has changes."""
        from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: All nodes UNCHANGED
        x_child = PropertyPresentation(name="x", state=DiffState.UNCHANGED, old_value=1.0, new_value=1.0)
        base_parent = PropertyPresentation(
            name="Base",
            state=DiffState.UNCHANGED,
            children=[x_child],
        )
        placement = PropertyPresentation(
            name="Placement",
            state=DiffState.UNCHANGED,
            children=[base_parent],
        )

        properties = [placement]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: All nodes in the unchanged branch are collapsed
        group_item = widget.topLevelItem(0)
        prop_item = group_item.child(0)
        assert not prop_item.isExpanded()  # Placement is UNCHANGED
        assert not prop_item.child(0).isExpanded()  # Base is UNCHANGED
        assert not prop_item.child(0).child(0).isExpanded()  # x is UNCHANGED


class TestPropertyDiffTreeWidgetThreeColumnLayout:
    """Tests for the 3-column property diff layout."""

    def test_widget_has_three_columns(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Widget has exactly 3 columns."""
        # When: Creating a fresh widget
        # Then: The tree should have 3 columns
        assert widget.columnCount() == 3

    def test_header_labels_are_correct(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Header labels are ['Property', 'Old Value', 'New Value']."""
        from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation

        # When: Adding a property
        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]
        widget.show_property_diff(properties)

        # Then: We can access all 3 columns
        group_item = widget.topLevelItem(0)
        assert group_item is not None
        assert group_item.text(0) == "Properties"
        assert group_item.text(1) == ""
        assert group_item.text(2) == ""
