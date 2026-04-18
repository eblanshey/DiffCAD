"""File responsibility: Unit tests for DiffPresenter property handling methods."""

import datetime
from unittest.mock import MagicMock

from freecad.diff_wb.application.actions.create_diff import CreateDiffAction
from freecad.diff_wb.application.actions.create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
from freecad.diff_wb.application.actions.create_document_snapshot_working import (
    CreateDocumentSnapshotForWorkingTreeAction,
)
from freecad.diff_wb.application.actions.get_dirty_documents import GetDirtyDocumentsAction
from freecad.diff_wb.application.actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from freecad.diff_wb.application.actions.stage_documents import StageDocumentsAction
from freecad.diff_wb.domain.diff.models import DiffHierarchy, DiffResult, DiffState, NodeDiff, PropertyDiff
from freecad.diff_wb.domain.snapshots import Snapshot
from freecad.diff_wb.domain.tree import Property, PropertyType
from freecad.diff_wb.ui.presenters.diff_presenter import DiffPresenter
from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation
from freecad.diff_wb.ui.state import UIState
from tests.fakes.fake_diff_view import FakeDiffView


def _create_test_presenter() -> tuple[FakeDiffView, DiffPresenter]:
    """Helper to create a DiffPresenter with mock dependencies.

    Returns:
        Tuple of (FakeDiffView, DiffPresenter) for test setup.
    """
    view = FakeDiffView()
    ui_state = UIState(git_repository=None)

    # Create mock actions
    get_eligible_docs_action = MagicMock(spec=GetOpenEligibleDocumentsAction)
    create_working_snapshot_action = MagicMock(spec=CreateDocumentSnapshotForWorkingTreeAction)
    create_commit_snapshot_action = MagicMock(spec=CreateDocumentSnapshotForCommitAction)
    create_diff_action = MagicMock(spec=CreateDiffAction)
    stage_documents_action = MagicMock(spec=StageDocumentsAction)
    get_dirty_documents_action = MagicMock(spec=GetDirtyDocumentsAction)

    presenter = DiffPresenter(
        view=view,
        ui_state=ui_state,
        get_eligible_docs_action=get_eligible_docs_action,
        create_working_snapshot_action=create_working_snapshot_action,
        create_commit_snapshot_action=create_commit_snapshot_action,
        create_diff_action=create_diff_action,
        stage_documents_action=stage_documents_action,
        get_dirty_documents_action=get_dirty_documents_action,
    )
    return view, presenter


class TestDiffPresenterPropertyHandling:
    """Tests for DiffPresenter property handling methods."""

    def test_on_node_selected_with_valid_path_calls_view(self) -> None:
        """When path is valid, view.show_properties() is called with PropertyPresentation list."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

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
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        # Present diff to store the result
        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

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
        assert prop_presentation.state == DiffState.MODIFIED

    def test_on_node_selected_with_invalid_path_clears_properties(self) -> None:
        """When path not found in diff, clears properties."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            _force_state=DiffState.UNCHANGED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        # Present diff to store the result
        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "NonExistentPath")

        # Assert
        calls = fake_view.get_calls()
        # Verify show_properties was called with empty list
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None, "show_properties should be called"
        assert prop_call["properties"] == []

    def test_on_node_selected_with_no_diff_result_clears_properties(self) -> None:
        """When no diff computed, clears properties."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        # No diff result has been presented

        # Act
        presenter.on_node_selected("", "Part")

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
        fake_view, presenter = _create_test_presenter()

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
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        # Present diff to store the result
        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

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
        assert value_pres.state == DiffState.MODIFIED
        assert value_pres.old_value == 10.0
        assert value_pres.new_value == 20.0

        # Second row is expression row
        expr_pres = properties[1]
        assert expr_pres.name == "-> Expression"
        assert expr_pres.state == DiffState.DELETED
        assert expr_pres.old_value == "Sketch.X"
        assert expr_pres.new_value is None

    def test_property_presentation_when_expression_removed_but_value_same(self) -> None:
        """When expression is removed but value stays same, value row shows UNCHANGED.

        Scenario: Pad length had expression "Sketch.X" evaluating to 3mm. Expression is
        removed but value is manually set to 3mm. The value should show UNCHANGED,
        only the expression row should show DELETED.
        """
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Old property has expression, new property has same value but no expression
        old_prop = Property.create(PropertyType.FLOAT, 3.0, expression="Sketch.X")
        new_prop = Property.create(PropertyType.FLOAT, 3.0, expression=None)
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        # Should have 2 rows: value row + expression row
        assert len(properties) == 2

        # Value row should be UNCHANGED (value is the same)
        value_pres = properties[0]
        assert value_pres.name == "Length"
        assert value_pres.state == DiffState.UNCHANGED
        assert value_pres.old_value == 3.0
        assert value_pres.new_value == 3.0

        # Expression row should show DELETED
        expr_pres = properties[1]
        assert expr_pres.name == "-> Expression"
        assert expr_pres.state == DiffState.DELETED
        assert expr_pres.old_value == "Sketch.X"
        assert expr_pres.new_value is None

    def test_property_presentation_for_added_property(self) -> None:
        """PropertyDiff transforms to PropertyPresentation correctly for added property."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

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
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        assert len(properties) == 1

        prop_pres = properties[0]
        assert prop_pres.name == "Label"
        assert prop_pres.state == DiffState.ADDED
        # old_value should be None for added property
        assert prop_pres.old_value is None
        # new_value should contain the actual value
        assert prop_pres.new_value == "NewValue"

    def test_property_presentation_for_deleted_property(self) -> None:
        """PropertyDiff transforms to PropertyPresentation correctly for deleted property."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

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
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        assert len(properties) == 1

        prop_pres = properties[0]
        assert prop_pres.name == "Count"
        assert prop_pres.state == DiffState.DELETED
        # old_value should contain the actual value
        assert prop_pres.old_value == 42
        # new_value should be None for deleted property
        assert prop_pres.new_value is None

    def test_on_node_selected_finds_nested_path(self) -> None:
        """on_node_selected finds node in nested tree structure."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

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
        # Add nodes in order from root to leaf so hierarchy is built correctly
        hierarchy = DiffHierarchy()
        hierarchy.add_node(parent)  # Add parent first
        hierarchy.add_node(child)  # Then child
        hierarchy.add_node(grandchild)  # Then grandchild
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )

        presenter.present_diff(diff_result)

        # Act - select nested path
        presenter.on_node_selected("v2", "Part/Body/Pad")

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
        fake_view, presenter = _create_test_presenter()

        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            _force_state=DiffState.UNCHANGED,
            property_diffs=[],  # No property diffs
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None
        assert prop_call["properties"] == []


class TestPropertyValueTypeExtraction:
    """Tests for property value extraction - ensures .value is extracted from Property object.

    This tests that the presenter extracts the underlying value from Property objects
    correctly, storing them in old_value/new_value fields for proper UI expansion.
    """

    def test_property_with_list_value_expands_correctly(self) -> None:
        """Property with list value passes the list (not Property) to presentation.new_value.

        For a property like Constraints containing a list of Constraint objects,
        the new_value field should contain the list itself, not the Property wrapper.
        """
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Simulate a list of constraint objects as property value
        # Using UNKNOWN type preserves the raw list value (as FreeCAD integration does)
        constraint_values = ["Constraint1", "Constraint2", "Constraint3"]
        old_prop = Property(type_=PropertyType.UNKNOWN, value=constraint_values, group="Sketch")
        new_prop = Property(type_=PropertyType.UNKNOWN, value=constraint_values + ["Constraint4"], group="Sketch")
        node_diff = NodeDiff(
            path="Sketch",
            type_id="Sketcher::SketchObject",
            property_diffs=[
                PropertyDiff(property_name="Constraints", old_value=old_prop, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Sketch")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        assert len(properties) == 1

        prop_pres = properties[0]
        assert prop_pres.name == "Constraints"

        # CRITICAL: The new_value should be the actual list, NOT the Property object
        # If it were the Property object, str(new_value) would show "Property(type_=...)"
        # Instead, it should show the list itself
        assert prop_pres.new_value == ["Constraint1", "Constraint2", "Constraint3", "Constraint4"]
        # Verify it's NOT a Property object
        assert not isinstance(prop_pres.new_value, Property)

    def test_property_with_dict_value_expands_correctly(self) -> None:
        """Property with dict value passes the dict (not Property) to presentation.new_value."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Simulate a dict value using UNKNOWN type to preserve raw dict
        old_dict = {"key1": "value1", "key2": "value2"}
        new_dict = {"key1": "value1", "key2": "modified"}
        old_prop = Property(type_=PropertyType.UNKNOWN, value=old_dict)
        new_prop = Property(type_=PropertyType.UNKNOWN, value=new_dict)
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Data", old_value=old_prop, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        assert len(properties) == 1

        prop_pres = properties[0]
        assert prop_pres.name == "Data"

        # CRITICAL: The new_value should be the actual dict, NOT the Property object
        assert prop_pres.new_value == {"key1": "value1", "key2": "modified"}
        # Verify it's a dict, not a Property
        assert isinstance(prop_pres.new_value, dict)

    def test_property_with_vector_expands_correctly(self) -> None:
        """Property with Vector value passes the Vector (not Property) to presentation.new_value."""
        # Arrange
        from freecad.diff_wb.domain.tree import Vector

        fake_view, presenter = _create_test_presenter()

        old_vec = Vector(x=1.0, y=2.0, z=3.0)
        new_vec = Vector(x=4.0, y=5.0, z=6.0)
        old_prop = Property(type_=PropertyType.VECTOR, value=old_vec)
        new_prop = Property(type_=PropertyType.VECTOR, value=new_vec)
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Position", old_value=old_prop, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        assert len(properties) == 1

        prop_pres = properties[0]
        assert prop_pres.name == "Position"

        # CRITICAL: The new_value should be the Vector object, NOT the Property wrapper
        assert isinstance(prop_pres.new_value, Vector)
        assert prop_pres.new_value.x == 4.0
        assert prop_pres.new_value.y == 5.0
        assert prop_pres.new_value.z == 6.0
        # Verify it's NOT a Property object
        assert not hasattr(prop_pres.new_value, "expression")

    def test_property_with_placement_expands_correctly(self) -> None:
        """Property with Placement value passes the Placement (not Property) to presentation.new_value."""
        # Arrange
        from freecad.diff_wb.domain.tree import Placement, Rotation, Vector

        fake_view, presenter = _create_test_presenter()

        old_placement = Placement(position=Vector(0, 0, 0), rotation=Rotation(0, 0, 1, 0))
        new_placement = Placement(position=Vector(10, 20, 30), rotation=Rotation(0, 0, 1, 90))
        old_prop = Property(type_=PropertyType.PLACEMENT, value=old_placement)
        new_prop = Property(type_=PropertyType.PLACEMENT, value=new_placement)
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Placement", old_value=old_prop, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        assert len(properties) == 1

        prop_pres = properties[0]
        assert prop_pres.name == "Placement"

        # CRITICAL: The new_value should be the Placement object, NOT the Property wrapper
        assert isinstance(prop_pres.new_value, Placement)
        assert prop_pres.new_value.position.x == 10
        assert prop_pres.new_value.position.y == 20
        assert prop_pres.new_value.position.z == 30
        assert prop_pres.new_value.rotation.angle_degrees == 90
        # Verify it's NOT a Property object
        assert not hasattr(prop_pres.new_value, "expression")

    def test_property_deleted_uses_old_value_for_expansion(self) -> None:
        """When property is deleted (new_value is None), uses old_value.value for expansion."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_list = ["item1", "item2"]
        old_prop = Property(type_=PropertyType.UNKNOWN, value=old_list)
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Items", old_value=old_prop, new_value=None),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        assert len(properties) == 1

        prop_pres = properties[0]
        assert prop_pres.state == DiffState.DELETED

        # Should have old_value but no new_value
        assert prop_pres.old_value == ["item1", "item2"]
        assert isinstance(prop_pres.old_value, list)
        assert prop_pres.new_value is None

    def test_property_added_uses_new_value_for_expansion(self) -> None:
        """When property is added (old_value is None), uses new_value.value for expansion."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        new_list = ["new_item"]
        new_prop = Property(type_=PropertyType.UNKNOWN, value=new_list)
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Items", old_value=None, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        assert len(properties) == 1

        prop_pres = properties[0]
        assert prop_pres.state == DiffState.ADDED

        # Should have new_value but no old_value
        assert prop_pres.new_value == ["new_item"]
        assert isinstance(prop_pres.new_value, list)
        assert prop_pres.old_value is None

    def test_property_both_none_has_no_value(self) -> None:
        """When both old and new values are None, presentation.value is None."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Empty", old_value=None, new_value=None),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        assert len(properties) == 1

        prop_pres = properties[0]
        # When both values are None, both should be None
        assert prop_pres.old_value is None
        assert prop_pres.new_value is None


class TestPhase2OldValueAndExpression:
    """Tests for Phase 2: old_value/new_value fields and expression display name."""

    def test_property_presentation_includes_old_value(self) -> None:
        """PropertyPresentation includes old_value field with actual old value."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

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
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        prop_pres = properties[0]

        # Verify old_value is set to the extracted value (not Property wrapper)
        assert prop_pres.old_value == 10.0
        assert prop_pres.new_value == 20.0

    def test_expandable_property_passes_both_old_and_new_values(self) -> None:
        """Expandable properties pass both old and new dict values for child diff computation."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_dict = {"x": 1.0, "y": 2.0, "z": 3.0}
        new_dict = {"x": 4.0, "y": 5.0, "z": 6.0}
        old_prop = Property(type_=PropertyType.UNKNOWN, value=old_dict)
        new_prop = Property(type_=PropertyType.UNKNOWN, value=new_dict)
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Vector", old_value=old_prop, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        prop_pres = properties[0]

        # Both old and new values should be the actual dicts
        assert prop_pres.old_value == {"x": 1.0, "y": 2.0, "z": 3.0}
        assert prop_pres.new_value == {"x": 4.0, "y": 5.0, "z": 6.0}

    def test_expression_row_has_correct_display_name(self) -> None:
        """Expression rows have name "-> Expression" instead of just "Expression"."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_prop = Property.create(PropertyType.FLOAT, 10.0, expression="Sketch.X")
        new_prop = Property.create(PropertyType.FLOAT, 20.0, expression="Sketch.Y")
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        # Second row should be the expression row
        expr_pres = properties[1]

        # Verify display name is "-> Expression"
        assert expr_pres.name == "-> Expression"

    def test_expression_row_passes_actual_expression_strings(self) -> None:
        """Expression rows pass actual expression strings as old_value/new_value (not display strings)."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_expr_str = "Sketch.X"
        new_expr_str = "Sketch.Y"
        old_prop = Property.create(PropertyType.FLOAT, 10.0, expression=old_expr_str)
        new_prop = Property.create(PropertyType.FLOAT, 20.0, expression=new_expr_str)
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        expr_pres = properties[1]

        # old_value and new_value should be the actual expression strings
        assert expr_pres.old_value == "Sketch.X"
        assert expr_pres.new_value == "Sketch.Y"

    def test_expression_added_has_correct_values(self) -> None:
        """When expression is added, old_value is None and new_value is the expression string."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_prop = Property.create(PropertyType.FLOAT, 10.0, expression=None)
        new_prop = Property.create(PropertyType.FLOAT, 10.0, expression="Sketch.X")
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        expr_pres = properties[1]

        assert expr_pres.name == "-> Expression"
        assert expr_pres.state == DiffState.ADDED
        assert expr_pres.old_value is None
        assert expr_pres.new_value == "Sketch.X"

    def test_expression_deleted_has_correct_values(self) -> None:
        """When expression is deleted, old_value is the expression string and new_value is None."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_prop = Property.create(PropertyType.FLOAT, 10.0, expression="Sketch.X")
        new_prop = Property.create(PropertyType.FLOAT, 10.0, expression=None)
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("", "Part")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        expr_pres = properties[1]

        assert expr_pres.name == "-> Expression"
        assert expr_pres.state == DiffState.DELETED
        assert expr_pres.old_value == "Sketch.X"
        assert expr_pres.new_value is None
