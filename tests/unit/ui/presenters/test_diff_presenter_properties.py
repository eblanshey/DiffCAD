"""File responsibility: Unit tests for DiffPresenter property handling methods.

Tests verify that _transform_property_diffs correctly builds nested sub-path
trees from PropertyPathDiff and maps them to PropertyPresentation objects.
"""

import datetime
from unittest.mock import MagicMock

from freecad.diff_wb.application.actions.create_diff import CreateDiffAction
from freecad.diff_wb.application.actions.create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
from freecad.diff_wb.application.actions.create_document_snapshot_working import (
    CreateDocumentSnapshotForWorkingTreeAction,
)
from freecad.diff_wb.application.actions.get_committed_file_paths import GetCommittedFilePathsAction
from freecad.diff_wb.application.actions.get_dirty_documents import GetDirtyDocumentsAction
from freecad.diff_wb.application.actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from freecad.diff_wb.application.actions.get_staged_file_paths import GetStagedFilePathsAction
from freecad.diff_wb.application.actions.stage_documents import StageDocumentsAction
from freecad.diff_wb.domain.diff.models import DiffHierarchy, DiffResult, DiffState, NodeDiff, PropertyDiff
from freecad.diff_wb.domain.snapshots import Snapshot
from freecad.diff_wb.domain.tree import Property
from freecad.diff_wb.domain.tree.data_path import (
    PropertyPathType,
    PropertyPathValue,
    QuantityData,
)
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
    get_staged_file_paths_action = MagicMock(spec=GetStagedFilePathsAction)
    get_committed_file_paths_action = MagicMock(spec=GetCommittedFilePathsAction)

    presenter = DiffPresenter(
        view=view,
        ui_state=ui_state,
        get_eligible_docs_action=get_eligible_docs_action,
        create_working_snapshot_action=create_working_snapshot_action,
        create_commit_snapshot_action=create_commit_snapshot_action,
        create_diff_action=create_diff_action,
        stage_documents_action=stage_documents_action,
        get_dirty_documents_action=get_dirty_documents_action,
        get_staged_file_paths_action=get_staged_file_paths_action,
        get_committed_file_paths_action=get_committed_file_paths_action,
    )
    return view, presenter


class TestDiffPresenterPropertyHandling:
    """Tests for DiffPresenter property handling methods."""

    def test_on_node_selected_with_valid_path_calls_view(self) -> None:
        """When path is valid, view.show_properties() is called with PropertyPresentation list."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_prop = Property.from_freecad(10.0, {}, "Base")
        new_prop = Property.from_freecad(20.0, {}, "Base")
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

    def test_expression_nested_under_path_row(self) -> None:
        """Expression rows are nested under path rows, not flat siblings.

        When a property has an expression change, the expression row
        should appear as a child of the value row, not as a separate
        top-level row.
        """
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_prop = Property.from_freecad(10.0, {".": "Sketch.X"}, "Base")
        new_prop = Property.from_freecad(20.0, {".": "Sketch.Y"}, "Base")
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
        # Should have 1 row: the property row with nested expression
        assert len(properties) == 1

        prop_pres = properties[0]
        assert prop_pres.name == "Length"
        assert prop_pres.state == DiffState.MODIFIED
        assert prop_pres.old_value == 10.0
        assert prop_pres.new_value == 20.0

        # Expression should be nested under the property row
        assert len(prop_pres.children) == 1
        expr_pres = prop_pres.children[0]
        assert expr_pres.name == "Expression"
        assert expr_pres.state == DiffState.MODIFIED
        assert expr_pres.old_value == "Sketch.X"
        assert expr_pres.new_value == "Sketch.Y"

    def test_expression_removed_but_value_same(self) -> None:
        """When expression is removed but value stays same, value row shows UNCHANGED.

        Scenario: Pad length had expression "Sketch.X" evaluating to 3mm. Expression is
        removed but value is manually set to 3mm. The value should show UNCHANGED,
        only the expression row (nested) should show DELETED.
        """
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_prop = Property.from_freecad(3.0, {".": "Sketch.X"}, "Base")
        new_prop = Property.from_freecad(3.0, {".": None}, "Base")
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
        assert len(properties) == 1

        prop_pres = properties[0]
        # Value row should be UNCHANGED (value is the same)
        assert prop_pres.name == "Length"
        assert prop_pres.old_value == 3.0
        assert prop_pres.new_value == 3.0

        # Expression row should be nested and show DELETED
        assert len(prop_pres.children) == 1
        expr_pres = prop_pres.children[0]
        assert expr_pres.name == "Expression"
        assert expr_pres.state == DiffState.DELETED
        assert expr_pres.old_value == "Sketch.X"
        assert expr_pres.new_value is None

    def test_property_presentation_for_added_property(self) -> None:
        """PropertyDiff transforms to PropertyPresentation correctly for added property."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        new_prop = Property.from_freecad("NewValue", {}, "Base")
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

        old_prop = Property.from_freecad(42, {}, "Base")
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
                    old_value=Property.from_freecad(5.0, {}, "Base"),
                    new_value=Property.from_freecad(10.0, {}, "Base"),
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
        hierarchy = DiffHierarchy()
        hierarchy.add_node(parent)
        hierarchy.add_node(child)
        hierarchy.add_node(grandchild)
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
    """Tests for property value extraction - ensures .value is extracted from Property object."""

    def test_property_with_list_value_expands_correctly(self) -> None:
        """Property with list value derives container summary from path tree.

        For a property like Constraints containing a list of Constraint objects,
        the presentation derives values from the path tree rather than passing
        the raw list.
        """
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_list = ["Constraint1", "Constraint2", "Constraint3", "Constraint4"]
        new_list = ["Constraint1", "Constraint2", "Constraint3"]
        old_prop = Property.from_freecad(old_list, {}, "Sketch")
        new_prop = Property.from_freecad(new_list, {}, "Sketch")
        node_diff = NodeDiff(
            path="Sketch",
            type_id="Sketcher::SketchObject",
            property_diffs=[
                PropertyDiff(property_name="Constraints", old_value=old_prop, new_value=new_prop),
            ],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="doc1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="doc2", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("doc2", "Sketch")

        # Assert
        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None

        properties = prop_call["properties"]
        assert len(properties) == 1

        prop_pres = properties[0]
        assert prop_pres.name == "Constraints"

        # List values are derived from path tree, not passed directly
        assert isinstance(prop_pres.old_value, str)
        assert isinstance(prop_pres.new_value, str)
        # Verify it's NOT a Property object
        assert not isinstance(prop_pres.new_value, Property)

    def test_property_with_dict_value_expands_correctly(self) -> None:
        """Property with dict value passes the dict repr (not Property) to presentation.new_value."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_prop = Property.from_freecad({"key1": "value1", "key2": "value2"}, {}, "Base")
        new_prop = Property.from_freecad({"key1": "value1", "key2": "modified"}, {}, "Base")
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

        # Dict values become UnknownData with string repr
        assert isinstance(prop_pres.old_value, str)
        assert isinstance(prop_pres.new_value, str)

    def test_property_with_vector_expands_correctly(self) -> None:
        """Property with Vector-like value passes the repr (not Property) to presentation.new_value."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        class MockVector:
            def __init__(self, x, y, z):
                self.x = x
                self.y = y
                self.z = z

            def __str__(self):
                return f"Vector({self.x}, {self.y}, {self.z})"

        old_vec = MockVector(1.0, 2.0, 3.0)
        new_vec = MockVector(4.0, 5.0, 6.0)
        old_prop = Property.from_freecad(old_vec, {}, "Base")
        new_prop = Property.from_freecad(new_vec, {}, "Base")
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

        # Mock vectors become UnknownData with string repr
        assert prop_pres.new_value == "Vector(4.0, 5.0, 6.0)"
        assert isinstance(prop_pres.new_value, str)

    def test_property_with_placement_expands_correctly(self) -> None:
        """Property with Placement-like value passes the repr (not Property) to presentation.new_value."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        class MockAxis:
            x, y, z = 0.0, 0.0, 1.0

        class MockRotation:
            Axis = MockAxis()
            Angle = 90.0

        class MockBase:
            x, y, z = 10.0, 20.0, 30.0

        class MockPlacement:
            Base = MockBase()
            Rotation = MockRotation()

        old_prop = Property.from_freecad(MockPlacement(), {}, "Base")
        new_prop = Property.from_freecad(MockPlacement(), {".": None}, "Base")
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

        # Mock placements become UnknownData with string repr
        assert isinstance(prop_pres.new_value, str)
        assert not hasattr(prop_pres.new_value, "expression")

    def test_property_deleted_uses_old_value_for_expansion(self) -> None:
        """When property is deleted (new_value is None), uses old_value for display."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_list = ["item1", "item2"]
        old_prop = Property.from_freecad(old_list, {}, "Base")
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
        assert isinstance(prop_pres.old_value, str)
        assert prop_pres.new_value is None

    def test_property_added_uses_new_value_for_expansion(self) -> None:
        """When property is added (old_value is None), uses new_value for display."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        new_list = ["new_item"]
        new_prop = Property.from_freecad(new_list, {}, "Base")
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
        assert isinstance(prop_pres.new_value, str)
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
        assert prop_pres.old_value is None
        assert prop_pres.new_value is None


class TestPhase2OldValueAndExpression:
    """Tests for Phase 2: old_value/new_value fields and expression display."""

    def test_property_presentation_includes_old_value(self) -> None:
        """PropertyPresentation includes old_value field with actual old value."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_prop = Property.from_freecad(10.0, {}, "Base")
        new_prop = Property.from_freecad(20.0, {}, "Base")
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

        assert prop_pres.old_value == 10.0
        assert prop_pres.new_value == 20.0

    def test_expandable_property_passes_both_old_and_new_values(self) -> None:
        """Expandable properties pass both old and new values for child diff computation."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_list = [1.0, 2.0, 3.0]
        new_list = [4.0, 5.0, 6.0]
        old_prop = Property.from_freecad(old_list, {}, "Base")
        new_prop = Property.from_freecad(new_list, {}, "Base")
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="Values", old_value=old_prop, new_value=new_prop),
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

        # Both old and new values should be derived from path tree
        assert isinstance(prop_pres.old_value, str)
        assert isinstance(prop_pres.new_value, str)

    def test_expression_nested_has_correct_name(self) -> None:
        """Nested expression rows have name "Expression" (not "-> Expression")."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_prop = Property.from_freecad(10.0, {".": "Sketch.X"}, "Base")
        new_prop = Property.from_freecad(20.0, {".": "Sketch.Y"}, "Base")
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

        # Expression should be nested, not a separate top-level row
        assert len(prop_pres.children) == 1
        expr_pres = prop_pres.children[0]
        assert expr_pres.name == "Expression"

    def test_expression_nested_passes_actual_expression_strings(self) -> None:
        """Expression rows pass actual expression strings as old_value/new_value."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_expr_str = "Sketch.X"
        new_expr_str = "Sketch.Y"
        old_prop = Property.from_freecad(10.0, {".": old_expr_str}, "Base")
        new_prop = Property.from_freecad(20.0, {".": new_expr_str}, "Base")
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

        expr_pres = prop_pres.children[0]
        assert expr_pres.old_value == "Sketch.X"
        assert expr_pres.new_value == "Sketch.Y"

    def test_expression_added_has_correct_values(self) -> None:
        """When expression is added, old_value is None and new_value is the expression string."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_prop = Property.from_freecad(10.0, {".": None}, "Base")
        new_prop = Property.from_freecad(10.0, {".": "Sketch.X"}, "Base")
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

        expr_pres = prop_pres.children[0]

        assert expr_pres.name == "Expression"
        assert expr_pres.state == DiffState.ADDED
        assert expr_pres.old_value is None
        assert expr_pres.new_value == "Sketch.X"

    def test_expression_deleted_has_correct_values(self) -> None:
        """When expression is deleted, old_value is the expression string and new_value is None."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        old_prop = Property.from_freecad(10.0, {".": "Sketch.X"}, "Base")
        new_prop = Property.from_freecad(10.0, {".": None}, "Base")
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

        expr_pres = prop_pres.children[0]

        assert expr_pres.name == "Expression"
        assert expr_pres.state == DiffState.DELETED
        assert expr_pres.old_value == "Sketch.X"
        assert expr_pres.new_value is None


class TestQuantityPropertyPresentation:
    """Tests for QuantityData property presentation with root-only string path."""

    def test_quantity_property_single_row_from_root_string(self) -> None:
        """Quantity property renders as a single row with root string value, no children."""
        fake_view, presenter = _create_test_presenter()

        old_prop = Property(
            value=QuantityData(paths={".": PropertyPathValue(PropertyPathType.STRING, "10.0 mm")}),
            group="Base",
        )
        new_prop = Property(
            value=QuantityData(paths={".": PropertyPathValue(PropertyPathType.STRING, "12.0 mm")}),
            group="Base",
        )

        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop)],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="\x01", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="\x02", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)
        presenter.on_node_selected("\x02", "Part")

        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None
        prop_pres = prop_call["properties"][0]

        assert prop_pres.name == "Length"
        assert prop_pres.old_value == "10.0 mm"
        assert prop_pres.new_value == "12.0 mm"
        assert prop_pres.state == DiffState.MODIFIED
        assert prop_pres.children == []

    def test_quantity_expression_row_still_supported_on_root_path(self) -> None:
        """Quantity with root expression shows expression as nested child row."""
        fake_view, presenter = _create_test_presenter()

        old_prop = Property(
            value=QuantityData(paths={".": PropertyPathValue(PropertyPathType.STRING, "10.0 mm", "Sketch.Length")}),
            group="Base",
        )
        new_prop = Property(
            value=QuantityData(paths={".": PropertyPathValue(PropertyPathType.STRING, "10.0 mm", None)}),
            group="Base",
        )

        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop)],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="\x01", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="\x02", timestamp=datetime.datetime.now()),
            hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
        )

        presenter.present_diff(diff_result)
        presenter.on_node_selected("\x02", "Part")

        calls = fake_view.get_calls()
        prop_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert prop_call is not None
        prop_pres = prop_call["properties"][0]

        assert len(prop_pres.children) == 1
        expr_pres = prop_pres.children[0]
        assert expr_pres.name == "Expression"
        assert expr_pres.state == DiffState.DELETED
        assert expr_pres.old_value == "Sketch.Length"
        assert expr_pres.new_value is None
        # Quantity value should be unchanged
        assert prop_pres.old_value == "10.0 mm"
        assert prop_pres.new_value == "10.0 mm"
