"""File responsibility: Unit tests for DiffPresenter property handling methods."""

from freecad.diff_wb.domain.diff.models import DiffResult, DiffState, NodeDiff, PropertyDiff
from freecad.diff_wb.domain.tree import Property, PropertyType
from freecad.diff_wb.ui.presenters.diff_presenter import DiffPresenter
from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation
from tests.fakes.fake_diff_view import FakeDiffView


class TestDiffPresenterPropertyHandling:
    """Tests for DiffPresenter property handling methods."""

    def test_on_node_selected_with_valid_path_calls_view(self) -> None:
        """When path is valid, view.show_properties() is called with PropertyPresentation list."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)

        old_prop = Property.create(PropertyType.FLOAT, 10.0)
        new_prop = Property.create(PropertyType.FLOAT, 20.0)
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot_name="v1",
            new_snapshot_name="v2",
            node_diffs=[node_diff],
        )

        # Present diff to store the result
        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("Part")

        # Assert
        calls = fake_view.get_calls()
        # Verify show_properties was called
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None, "show_properties should be called"
        properties = prop_call["properties"]
        assert len(properties) == 1
        # Verify the property presentation has correct fields
        prop_presentation = properties[0]
        assert isinstance(prop_presentation, PropertyPresentation)
        assert prop_presentation.name == "Length"
        assert prop_presentation.state == "MODIFIED"

    def test_on_node_selected_with_invalid_path_clears_properties(self) -> None:
        """When path not found in diff, clears properties."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)

        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            _force_state=DiffState.UNCHANGED,
        )
        diff_result = DiffResult(
            old_snapshot_name="v1",
            new_snapshot_name="v2",
            node_diffs=[node_diff],
        )

        # Present diff to store the result
        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("NonExistentPath")

        # Assert
        calls = fake_view.get_calls()
        # Verify show_properties was called with empty list
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None, "show_properties should be called"
        assert prop_call["properties"] == []

    def test_on_node_selected_with_no_diff_result_clears_properties(self) -> None:
        """When no diff computed, clears properties."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)
        # No diff result has been presented

        # Act
        presenter.on_node_selected("Part")

        # Assert
        calls = fake_view.get_calls()
        # Verify show_properties was called with empty list
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None, "show_properties should be called"
        assert prop_call["properties"] == []

    def test_property_presentation_transforms_correctly(self) -> None:
        """PropertyDiff transforms to PropertyPresentation with correct fields.

        Expression changes appear as separate rows per specification.
        """
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)

        # Test MODIFIED property with expression change (old has expression, new doesn't)
        old_prop = Property.create(PropertyType.FLOAT, 10.0, expression="Sketch.X")
        new_prop = Property.create(PropertyType.FLOAT, 20.0, expression=None)
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot_name="v1",
            new_snapshot_name="v2",
            node_diffs=[node_diff],
        )

        # Present diff to store the result
        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        # Should have 2 rows: one for value change, one for expression change
        assert len(properties) == 2

        # First row is value row
        value_pres = properties[0]
        assert value_pres.name == "Length"
        assert value_pres.state == "MODIFIED"
        assert "10.0" in value_pres.old_display
        assert "20.0" in value_pres.new_display

        # Second row is expression row
        expr_pres = properties[1]
        assert expr_pres.name == "Length (expr)"
        assert expr_pres.state == "DELETED"
        assert "Sketch.X" in expr_pres.old_display
        assert "(none)" in expr_pres.new_display

    def test_property_presentation_for_added_property(self) -> None:
        """PropertyDiff transforms to PropertyPresentation correctly for added property."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)

        # Test ADDED property (old_value is None)
        new_prop = Property.create(PropertyType.STRING, "NewValue")
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Label", old_value=None, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot_name="v1",
            new_snapshot_name="v2",
            node_diffs=[node_diff],
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        assert len(properties) == 1

        prop_pres = properties[0]
        assert prop_pres.name == "Label"
        assert prop_pres.state == "ADDED"
        # old_display should indicate no value
        assert prop_pres.old_display == "" or "none" in prop_pres.old_display.lower()
        # new_display should show the value
        assert "NewValue" in prop_pres.new_display

    def test_property_presentation_for_deleted_property(self) -> None:
        """PropertyDiff transforms to PropertyPresentation correctly for deleted property."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)

        # Test DELETED property (new_value is None)
        old_prop = Property.create(PropertyType.INT, 42)
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Count", old_value=old_prop, new_value=None),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot_name="v1",
            new_snapshot_name="v2",
            node_diffs=[node_diff],
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        assert len(properties) == 1

        prop_pres = properties[0]
        assert prop_pres.name == "Count"
        assert prop_pres.state == "DELETED"
        # old_display should show the value
        assert "42" in prop_pres.old_display
        # new_display should indicate no value
        assert prop_pres.new_display == "" or "none" in prop_pres.new_display.lower()

    def test_on_node_selected_finds_nested_path(self) -> None:
        """on_node_selected finds node in nested tree structure."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)

        grandchild = NodeDiff(
            path="Part/Body/Pad",
            type_id="PartDesign::Pad",
            property_diffs=[
                PropertyDiff(
                    property_name="Length",
                    old_value=Property.create(PropertyType.FLOAT, 5.0),
                    new_value=Property.create(PropertyType.FLOAT, 10.0),
                )
            ],
            _force_state=DiffState.MODIFIED,
        )
        child = NodeDiff(
            path="Part/Body",
            type_id="PartDesign::Body",
            children=[grandchild],
            _force_state=DiffState.UNCHANGED,
        )
        parent = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            children=[child],
            _force_state=DiffState.UNCHANGED,
        )
        diff_result = DiffResult(
            old_snapshot_name="v1",
            new_snapshot_name="v2",
            node_diffs=[parent],
        )

        presenter.present_diff(diff_result)

        # Act - select nested path
        presenter.on_node_selected("Part/Body/Pad")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None
        properties = prop_call["properties"]
        assert len(properties) == 1
        assert properties[0].name == "Length"

    def test_on_node_selected_with_unchanged_node_no_properties(self) -> None:
        """When selected node has no property diffs, shows empty properties."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)

        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            _force_state=DiffState.UNCHANGED,
            property_diffs=[],  # No property diffs
        )
        diff_result = DiffResult(
            old_snapshot_name="v1",
            new_snapshot_name="v2",
            node_diffs=[node_diff],
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None
        assert prop_call["properties"] == []
