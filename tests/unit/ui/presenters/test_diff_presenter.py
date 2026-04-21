"""File responsibility: Unit tests for DiffPresenter."""

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
from freecad.diff_wb.domain.git.models import GitRepository
from freecad.diff_wb.domain.snapshots import Snapshot
from freecad.diff_wb.domain.tree import Property
from freecad.diff_wb.ui.presenters.diff_presenter import DiffPresenter
from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation, PropertyPresentation
from freecad.diff_wb.ui.state import UIState
from freecad.diff_wb.ui.views.diff_panel_view import HistorySelection
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


class TestDiffPresenterGitPath:
    """Tests for DiffPresenter git_path display functionality."""

    def test_present_diff_passes_git_path_to_view(self) -> None:
        """Passes git_path from new_snapshot to show_diff_tree."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Part", type_id="Part::Feature"))
        diff_result = DiffResult(
            old_snapshot=Snapshot(
                snapshot_id="s1",
                document_name="snapshot_v1",
                timestamp=datetime.datetime.now(),
            ),
            new_snapshot=Snapshot(
                snapshot_id="s2",
                document_name="snapshot_v2",
                timestamp=datetime.datetime.now(),
                git_path="path/to/doc.FCStd",
            ),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - first call is set_history_selection_callback (wired in constructor)
        calls = fake_view.get_calls()
        assert calls[1]["method"] == "show_diff_tree"
        assert calls[1]["git_path"] == "path/to/doc.FCStd"

    def test_present_diff_uses_document_name_when_git_path_empty(self) -> None:
        """Falls back to document_name when git_path is empty."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Part", type_id="Part::Feature"))
        diff_result = DiffResult(
            old_snapshot=Snapshot(
                snapshot_id="s1",
                document_name="snapshot_v1",
                timestamp=datetime.datetime.now(),
            ),
            new_snapshot=Snapshot(
                snapshot_id="s2",
                document_name="MyDocument",
                timestamp=datetime.datetime.now(),
                git_path="",  # Empty git_path
            ),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - first call is set_history_selection_callback (wired in constructor)
        calls = fake_view.get_calls()
        assert calls[1]["method"] == "show_diff_tree"
        assert calls[1]["git_path"] == "MyDocument"


class TestDiffPresenter:
    """Tests for DiffPresenter."""

    def test_present_diff_calls_view_methods(self) -> None:
        """Calls set_history_selection_callback in constructor, then show_diff_tree and show_summary."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        # Create a node with no property changes so it's UNCHANGED
        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Part", type_id="Part::Feature"))
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="snapshot_v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="snapshot_v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - 3 calls: set_history_selection_callback (constructor), show_diff_tree, show_summary
        assert fake_view.get_call_count() == 3
        calls = fake_view.get_calls()
        assert calls[0]["method"] == "set_history_selection_callback"
        assert calls[1]["method"] == "show_diff_tree"
        assert calls[2]["method"] == "show_summary"

    def test_formats_node_diffs_correctly(self) -> None:
        """Transforms NodeDiff to NodePresentation correctly."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        node_diff = NodeDiff(
            path="Part001",
            type_id="Part::Feature",
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node_diff)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - first call is set_history_selection_callback (constructor)
        calls = fake_view.get_calls()
        nodes = calls[1]["nodes"]
        assert len(nodes) == 1
        presentation = nodes[0]
        assert isinstance(presentation, NodePresentation)
        assert presentation.path == "Part001"
        assert presentation.type_id == "Part::Feature"
        assert presentation.state == DiffState.MODIFIED
        assert presentation.has_changes is True

    def test_formats_property_changes(self) -> None:
        """Formats PropertyDiff with expressions correctly."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        old_prop = Property.from_freecad(10.0, {".": "Sketch.X"}, "Base")
        new_prop = Property.from_freecad(20.0, {".": None}, "Base")
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop)],
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node_diff)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - first call is set_history_selection_callback (constructor)
        calls = fake_view.get_calls()
        nodes = calls[1]["nodes"]
        presentation = nodes[0]
        assert presentation.has_changes is True
        assert presentation.state == DiffState.MODIFIED

    def test_handles_empty_diff(self) -> None:
        """Handles case with no changes."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=DiffHierarchy(),
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - first call is set_history_selection_callback (constructor)
        calls = fake_view.get_calls()
        assert calls[1]["method"] == "show_diff_tree"
        assert calls[1]["nodes"] == []
        assert calls[2]["method"] == "show_summary"
        assert calls[2]["added"] == 0
        assert calls[2]["deleted"] == 0
        assert calls[2]["modified"] == 0

    def test_calculates_summary_counts(self) -> None:
        """Calculates correct added/deleted/modified counts."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        added_node = NodeDiff(path="NewPart", type_id="Part::Feature", _force_state=DiffState.ADDED)
        deleted_node = NodeDiff(path="OldPart", type_id="Part::Feature", _force_state=DiffState.DELETED)
        modified_node = NodeDiff(
            path="ChangedPart",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(
                    property_name="Length",
                    old_value=Property.from_freecad(10.0, {}, "Base"),
                    new_value=Property.from_freecad(20.0, {}, "Base"),
                )
            ],
            _force_state=DiffState.MODIFIED,
        )
        unchanged_node = NodeDiff(path="UnchangedPart", type_id="Part::Feature")
        hierarchy = DiffHierarchy()
        hierarchy.add_node(added_node)
        hierarchy.add_node(deleted_node)
        hierarchy.add_node(modified_node)
        hierarchy.add_node(unchanged_node)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
            added_count=1,
            deleted_count=1,
            modified_count=1,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - first call is set_history_selection_callback (constructor)
        calls = fake_view.get_calls()
        summary_call = calls[2]
        assert summary_call["added"] == 1
        assert summary_call["deleted"] == 1
        assert summary_call["modified"] == 1


class TestDiffPresenterFormatsChildren:
    """Tests for _format_node() populating children recursively."""

    def test_format_node_populates_children_recursive(self) -> None:
        """Test _format_node() populates children recursively from NodeDiff.children."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Create a nested tree structure using factory functions
        grandchild = NodeDiff(
            path="Part/Body/Pad",
            type_id="PartDesign::Pad",
            _force_state=DiffState.UNCHANGED,
        )
        child = NodeDiff(
            path="Part/Body",
            type_id="PartDesign::Body",
            children=[grandchild],
            _force_state=DiffState.MODIFIED,
        )
        parent = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            children=[child],
            _force_state=DiffState.UNCHANGED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(parent)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - first call is set_history_selection_callback (constructor)
        calls = fake_view.get_calls()
        presentations = calls[1]["nodes"]
        assert len(presentations) == 1

        # Check parent presentation
        parent_pres = presentations[0]
        assert parent_pres.path == "Part"
        assert len(parent_pres.children) == 1

        # Check child presentation (recursive)
        child_pres = parent_pres.children[0]
        assert child_pres.path == "Part/Body"
        assert len(child_pres.children) == 1

        # Check grandchild presentation (deeply nested)
        grandchild_pres = child_pres.children[0]
        assert grandchild_pres.path == "Part/Body/Pad"
        assert len(grandchild_pres.children) == 0

    def test_complete_tree_structure_preserved_through_transformation(self) -> None:
        """Test complete tree structure is preserved through transformation."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Create a complex multi-level tree with multiple branches
        leaf1 = NodeDiff(path="Part/Body/Pad", type_id="PartDesign::Pad", _force_state=DiffState.ADDED)
        leaf2 = NodeDiff(path="Part/Body/Pocket", type_id="PartDesign::Pocket", _force_state=DiffState.DELETED)
        body = NodeDiff(
            path="Part/Body",
            type_id="PartDesign::Body",
            children=[leaf1, leaf2],
            _force_state=DiffState.MODIFIED,
        )
        leaf3 = NodeDiff(path="Part/Sketch", type_id="Sketcher::SketchObject", _force_state=DiffState.UNCHANGED)
        part = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            children=[body, leaf3],
            _force_state=DiffState.MODIFIED,
        )

        hierarchy = DiffHierarchy()
        hierarchy.add_node(part)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - first call is set_history_selection_callback (constructor)
        calls = fake_view.get_calls()
        presentations = calls[1]["nodes"]

        # Root level
        assert len(presentations) == 1
        root = presentations[0]
        assert root.path == "Part"
        assert root.state == DiffState.MODIFIED
        assert len(root.children) == 2

        # First branch - Body with two leaves
        body_pres = root.children[0]
        assert body_pres.path == "Part/Body"
        assert body_pres.state == DiffState.MODIFIED
        assert len(body_pres.children) == 2

        # Body's children
        pad_pres = body_pres.children[0]
        assert pad_pres.path == "Part/Body/Pad"
        assert pad_pres.state == DiffState.ADDED
        assert pad_pres.has_changes is True

        pocket_pres = body_pres.children[1]
        assert pocket_pres.path == "Part/Body/Pocket"
        assert pocket_pres.state == DiffState.DELETED
        assert pocket_pres.has_changes is True

        # Second branch - Sketch (unchanged leaf)
        sketch_pres = root.children[1]
        assert sketch_pres.path == "Part/Sketch"
        assert sketch_pres.state == DiffState.UNCHANGED
        assert sketch_pres.has_changes is False
        assert len(sketch_pres.children) == 0

    def test_format_node_handles_empty_children(self) -> None:
        """Test _format_node() handles nodes with no children."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        leaf_node = NodeDiff(
            path="Part/Leaf",
            type_id="Part::Feature",
            _force_state=DiffState.ADDED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(leaf_node)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - first call is set_history_selection_callback (constructor)
        calls = fake_view.get_calls()
        presentations = calls[1]["nodes"]
        assert len(presentations) == 1
        assert presentations[0].path == "Part/Leaf"
        assert presentations[0].children == []


class TestTransformPropertyDiffsWithChildren:
    """Tests for _transform_property_diffs() including children transformation."""

    def test_transform_property_diffs_includes_children(self) -> None:
        """Test that property diffs with children are transformed correctly."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Create property with children (list property with indexed children)
        old_list = Property.from_freecad([1.0, 2.0, 3.0], {}, "Base")
        new_list = Property.from_freecad([10.0, 2.0, 30.0], {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Vector",
            old_value=old_list,
            new_value=new_list,
        )

        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[prop_diff],
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node_diff)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )
        presenter.present_diff(diff_result)

        # Act - use on_node_selected to trigger the transform
        presenter.on_node_selected("v2", "Part")

        # Assert
        calls = fake_view.get_calls()
        # Find show_properties call
        show_props_call = None
        for call in calls:
            if call["method"] == "show_properties":
                show_props_call = call
                break

        assert show_props_call is not None
        properties = show_props_call["properties"]
        assert len(properties) == 1

        prop_presentation = properties[0]
        assert isinstance(prop_presentation, PropertyPresentation)
        assert prop_presentation.name == "Vector"
        # Children should be populated from domain PropertyDiff (indexed list items)
        assert len(prop_presentation.children) > 0

    def test_list_items_appear_as_nested_children(self) -> None:
        """Test that list items appear as nested children with indexed names."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Create a list property with indexed children
        old_position = Property.from_freecad([0.0, 0.0, 0.0], {}, "Base")
        new_position = Property.from_freecad([10.0, 20.0, 30.0], {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Position",
            old_value=old_position,
            new_value=new_position,
        )

        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[prop_diff],
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node_diff)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )
        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("v2", "Part")

        # Assert
        calls = fake_view.get_calls()
        # Find show_properties call
        show_props_call = None
        for call in calls:
            if call["method"] == "show_properties":
                show_props_call = call
                break

        assert show_props_call is not None
        properties = show_props_call["properties"]
        position_pres = properties[0]

        # Should have children (indexed list items)
        assert len(position_pres.children) > 0
        child_names = {child.name for child in position_pres.children}
        assert "[0]" in child_names or "[1]" in child_names or "[2]" in child_names

    def test_transform_children_preserves_parent_values(self) -> None:
        """Test that parent old_value and new_value are preserved alongside children."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Create a property with both parent value and children
        old_placement = Property.from_freecad(
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)}, {}, "Base"
        )
        new_placement = Property.from_freecad(
            {"position": (10.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 45.0)}, {}, "Base"
        )

        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=old_placement,
            new_value=new_placement,
        )

        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[prop_diff],
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node_diff)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )
        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("v2", "Part")

        # Assert
        calls = fake_view.get_calls()
        # Find show_properties call
        show_props_call = None
        for call in calls:
            if call["method"] == "show_properties":
                show_props_call = call
                break

        assert show_props_call is not None
        properties = show_props_call["properties"]
        prop_pres = properties[0]

        # Parent should still have old_value and new_value for display
        assert prop_pres.old_value is not None
        assert prop_pres.new_value is not None

    def test_transform_children_empty_for_primitives(self) -> None:
        """Test that primitive properties have empty children list."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Need to set up a diff_result first because on_node_selected requires it
        old_prop = Property.from_freecad(10.0, {}, "Base")
        new_prop = Property.from_freecad(20.0, {}, "Base")
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=old_prop,
            new_value=new_prop,
        )
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[prop_diff],
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node_diff)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )
        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("v2", "Part")

        # Assert
        calls = fake_view.get_calls()
        # Find the show_properties call
        show_props_call = None
        for call in calls:
            if call["method"] == "show_properties":
                show_props_call = call
                break

        assert show_props_call is not None
        properties = show_props_call["properties"]
        prop_pres = properties[0]

        # Primitive should have empty children
        assert prop_pres.children == []


class TestDiffPresenterHistorySelection:
    """Tests for DiffPresenter history selection handling."""

    def test_on_history_item_selected_method_exists(self) -> None:
        """DiffPresenter has on_history_item_selected() method."""
        _, presenter = _create_test_presenter()
        assert hasattr(presenter, "on_history_item_selected")
        assert callable(presenter.on_history_item_selected)

    def test_on_history_item_selected_routes_working_tree(self) -> None:
        """on_history_item_selected() routes WORKING_TREE to _on_working_tree_selected()."""
        fake_view, presenter = _create_test_presenter()

        # Mock the internal methods
        with (
            MagicMock() as mock_working,
            MagicMock() as mock_staging,
            MagicMock() as mock_commit,
        ):
            presenter._on_working_tree_selected = mock_working
            presenter._on_staging_selected = mock_staging
            presenter._on_commit_selected = mock_commit

            # Act
            selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)
            presenter.on_history_item_selected(selection)

            # Assert
            mock_working.assert_called_once()
            mock_staging.assert_not_called()
            mock_commit.assert_not_called()

    def test_on_history_item_selected_routes_staging(self) -> None:
        """on_history_item_selected() routes STAGING to _on_staging_selected()."""
        fake_view, presenter = _create_test_presenter()

        with (
            MagicMock() as mock_working,
            MagicMock() as mock_staging,
            MagicMock() as mock_commit,
        ):
            presenter._on_working_tree_selected = mock_working
            presenter._on_staging_selected = mock_staging
            presenter._on_commit_selected = mock_commit

            # Act
            selection = HistorySelection(item_kind="STAGING", commit_hash=None)
            presenter.on_history_item_selected(selection)

            # Assert
            mock_working.assert_not_called()
            mock_staging.assert_called_once()
            mock_commit.assert_not_called()

    def test_on_history_item_selected_routes_commit(self) -> None:
        """on_history_item_selected() routes COMMIT to _on_commit_selected()."""
        fake_view, presenter = _create_test_presenter()

        with (
            MagicMock() as mock_working,
            MagicMock() as mock_staging,
            MagicMock() as mock_commit,
        ):
            presenter._on_working_tree_selected = mock_working
            presenter._on_staging_selected = mock_staging
            presenter._on_commit_selected = mock_commit

            # Act
            commit_hash = "abc123"
            selection = HistorySelection(item_kind="COMMIT", commit_hash=commit_hash)
            presenter.on_history_item_selected(selection)

            # Assert
            mock_working.assert_not_called()
            mock_staging.assert_not_called()
            mock_commit.assert_called_once_with(commit_hash)


class TestDiffPresenterPresentDiffs:
    """Tests for DiffPresenter.present_diffs() method."""

    def test_present_diffs_accepts_list_of_diff_results(self) -> None:
        """present_diffs() accepts list[DiffResult]."""
        fake_view, presenter = _create_test_presenter()

        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=DiffHierarchy(),
        )

        # Act
        presenter.present_diffs([diff_result])

        # Assert
        assert fake_view.get_call_count() >= 1

    def test_present_diffs_transforms_to_diff_tree_presentation(self) -> None:
        """Each DiffResult is transformed to DiffTreePresentation."""
        from freecad.diff_wb.ui.presenters.presentation_models import DiffTreePresentation

        fake_view, presenter = _create_test_presenter()

        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Part", type_id="Part::Feature"))

        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(
                snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now(), git_path="test.FCStd"
            ),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diffs([diff_result])

        # Assert
        calls = fake_view.get_calls()
        show_trees_call = next((c for c in calls if c["method"] == "show_diff_trees"), None)
        assert show_trees_call is not None
        presentations = show_trees_call["diff_trees"]
        assert len(presentations) == 1
        assert isinstance(presentations[0], DiffTreePresentation)
        assert presentations[0].git_path == "test.FCStd"

    def test_present_diffs_handles_empty_list(self) -> None:
        """present_diffs() handles empty list."""
        fake_view, presenter = _create_test_presenter()

        # Act
        presenter.present_diffs([])

        # Assert
        calls = fake_view.get_calls()
        show_trees_call = next((c for c in calls if c["method"] == "show_diff_trees"), None)
        assert show_trees_call is not None
        assert show_trees_call["diff_trees"] == []


class TestDiffPresenterWorkingTreeOrchestration:
    """Tests for DiffPresenter._on_working_tree_selected() orchestration."""

    def test_on_working_tree_selected_calls_get_eligible_docs(self) -> None:
        """_on_working_tree_selected() calls GetOpenEligibleDocumentsAction.execute() with correct repo."""

        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup mock action
        mock_docs_result = MagicMock()
        mock_docs_result.is_success = True
        mock_docs_result.data = []
        mock_docs_result.message = ""
        presenter._get_eligible_docs.execute.return_value = mock_docs_result

        # Act
        presenter._on_working_tree_selected()

        # Assert
        presenter._get_eligible_docs.execute.assert_called_once_with(mock_repo)

    def test_on_working_tree_selected_creates_working_snapshots(self) -> None:
        """For each eligible document, creates working tree snapshot."""
        from tests.fakes.fake_freecad_port import DocumentLike

        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup mock documents
        mock_doc1 = MagicMock(spec=DocumentLike)
        mock_doc1.FileName = "/test/path/doc1.FCStd"
        mock_docs_result = MagicMock()
        mock_docs_result.is_success = True
        mock_docs_result.data = [mock_doc1]
        mock_docs_result.message = ""
        presenter._get_eligible_docs.execute.return_value = mock_docs_result

        # Setup mock working snapshot
        mock_working_snapshot = Snapshot(
            snapshot_id="ws1",
            document_name="doc1.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc1.FCStd",
        )
        mock_working_result = MagicMock()
        mock_working_result.is_success = True
        mock_working_result.data = mock_working_snapshot
        mock_working_result.message = ""
        presenter._create_working_tree_snapshot.execute.return_value = mock_working_result

        # Setup mock commit result (stub returns None)
        mock_commit_result = MagicMock()
        mock_commit_result.is_success = True
        mock_commit_result.data = None
        presenter._create_commit_snapshot.execute.return_value = mock_commit_result

        # Setup mock diff result
        mock_diff_result = DiffResult(
            old_snapshot=None,
            new_snapshot=mock_working_snapshot,
            hierarchy=DiffHierarchy(),
        )
        mock_create_diff_result = MagicMock()
        mock_create_diff_result.is_success = True
        mock_create_diff_result.data = mock_diff_result
        presenter._create_diff.execute.return_value = mock_create_diff_result

        # Act
        presenter._on_working_tree_selected()

        # Assert
        presenter._create_working_tree_snapshot.execute.assert_called_once_with(mock_repo, mock_doc1)

    def test_on_working_tree_selected_creates_diff_with_none_old_snapshot(self) -> None:
        """Creates diff with None old_snapshot and working tree snapshot as new."""
        from tests.fakes.fake_freecad_port import DocumentLike

        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup mock document
        mock_doc = MagicMock(spec=DocumentLike)
        mock_doc.FileName = "/test/path/doc.FCStd"
        mock_docs_result = MagicMock()
        mock_docs_result.is_success = True
        mock_docs_result.data = [mock_doc]
        mock_docs_result.message = ""
        presenter._get_eligible_docs.execute.return_value = mock_docs_result

        # Setup mock working snapshot
        mock_working_snapshot = Snapshot(
            snapshot_id="ws1",
            document_name="doc.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc.FCStd",
        )
        mock_working_result = MagicMock()
        mock_working_result.is_success = True
        mock_working_result.data = mock_working_snapshot
        presenter._create_working_tree_snapshot.execute.return_value = mock_working_result

        # Setup mock commit result
        mock_commit_result = MagicMock()
        mock_commit_result.is_success = True
        mock_commit_result.data = None
        presenter._create_commit_snapshot.execute.return_value = mock_commit_result

        # Mock the diff creation
        captured_old_snapshot = []

        def capture_diff(old, new):
            captured_old_snapshot.append(old)
            mock_diff_result = MagicMock()
            mock_diff_result.is_success = True
            mock_diff_result.data = DiffResult(
                old_snapshot=old,
                new_snapshot=new,
                hierarchy=DiffHierarchy(),
            )
            return mock_diff_result

        presenter._create_diff.execute.side_effect = capture_diff

        # Act
        presenter._on_working_tree_selected()

        # Assert
        assert len(captured_old_snapshot) == 1
        assert captured_old_snapshot[0] is None

    def test_on_working_tree_selected_logs_warning_and_continues_on_failure(self) -> None:
        """Logs warning for failed snapshots but continues processing."""
        from tests.fakes.fake_freecad_port import DocumentLike

        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup multiple documents
        mock_doc1 = MagicMock(spec=DocumentLike)
        mock_doc1.FileName = "/test/path/doc1.FCStd"
        mock_doc2 = MagicMock(spec=DocumentLike)
        mock_doc2.FileName = "/test/path/doc2.FCStd"
        mock_docs_result = MagicMock()
        mock_docs_result.is_success = True
        mock_docs_result.data = [mock_doc1, mock_doc2]
        mock_docs_result.message = ""
        presenter._get_eligible_docs.execute.return_value = mock_docs_result

        # First doc fails, second succeeds
        failed_result = MagicMock()
        failed_result.is_success = False
        failed_result.data = None
        failed_result.message = "Failed to extract"

        successful_snapshot = Snapshot(
            snapshot_id="ws2",
            document_name="doc2.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc2.FCStd",
        )
        successful_result = MagicMock()
        successful_result.is_success = True
        successful_result.data = successful_snapshot
        successful_result.message = ""

        call_count = [0]

        def create_working_side_effect(repo, doc):
            call_count[0] += 1
            if call_count[0] == 1:
                return failed_result
            return successful_result

        presenter._create_working_tree_snapshot.execute.side_effect = create_working_side_effect

        # Setup commit and diff mocks
        mock_commit_result = MagicMock()
        mock_commit_result.is_success = True
        mock_commit_result.data = None
        presenter._create_commit_snapshot.execute.return_value = mock_commit_result

        mock_diff_result = MagicMock()
        mock_diff_result.is_success = True
        mock_diff_result.data = DiffResult(
            old_snapshot=None,
            new_snapshot=successful_snapshot,
            hierarchy=DiffHierarchy(),
        )
        presenter._create_diff.execute.return_value = mock_diff_result

        # Act
        presenter._on_working_tree_selected()

        # Assert - both docs should have been processed
        assert presenter._create_working_tree_snapshot.execute.call_count == 2

    def test_on_working_tree_selected_collects_all_successful_diffs(self) -> None:
        """Collects all successful DiffResults and passes to present_diffs()."""
        from tests.fakes.fake_freecad_port import DocumentLike

        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup two documents
        mock_doc1 = MagicMock(spec=DocumentLike)
        mock_doc1.FileName = "/test/path/doc1.FCStd"
        mock_doc2 = MagicMock(spec=DocumentLike)
        mock_doc2.FileName = "/test/path/doc2.FCStd"
        mock_docs_result = MagicMock()
        mock_docs_result.is_success = True
        mock_docs_result.data = [mock_doc1, mock_doc2]
        mock_docs_result.message = ""
        presenter._get_eligible_docs.execute.return_value = mock_docs_result

        # Create snapshots for both docs
        snapshot1 = Snapshot(
            snapshot_id="ws1", document_name="doc1.FCStd", timestamp=datetime.datetime.now(), git_path="doc1.FCStd"
        )
        snapshot2 = Snapshot(
            snapshot_id="ws2", document_name="doc2.FCStd", timestamp=datetime.datetime.now(), git_path="doc2.FCStd"
        )

        def create_working_side_effect(repo, doc):
            result = MagicMock()
            result.is_success = True
            result.data = snapshot1 if doc == mock_doc1 else snapshot2
            result.message = ""
            return result

        presenter._create_working_tree_snapshot.execute.side_effect = create_working_side_effect

        # Setup commit and diff mocks
        mock_commit_result = MagicMock()
        mock_commit_result.is_success = True
        mock_commit_result.data = None
        presenter._create_commit_snapshot.execute.return_value = mock_commit_result

        def create_diff_side_effect(old, new):
            result = MagicMock()
            result.is_success = True
            result.data = DiffResult(
                old_snapshot=None,
                new_snapshot=new,
                hierarchy=DiffHierarchy(),
                added_count=1,
                deleted_count=0,
                modified_count=0,
            )
            return result

        presenter._create_diff.execute.side_effect = create_diff_side_effect

        # Act
        presenter._on_working_tree_selected()

        # Assert - show_diff_trees should be called with 2 presentations
        calls = fake_view.get_calls()
        show_trees_call = next((c for c in calls if c["method"] == "show_diff_trees"), None)
        assert show_trees_call is not None
        assert len(show_trees_call["diff_trees"]) == 2


class TestDiffPresenterPresentDiffsDirtyPaths:
    """Tests for DiffPresenter.present_diffs() with dirty_paths parameter."""

    def test_present_diffs_sets_stage_button_enabled_from_dirty_paths(self) -> None:
        """Stage button enabled is set to True when document is in dirty_paths."""
        fake_view, presenter = _create_test_presenter()

        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Part", type_id="Part::Feature"))

        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(
                snapshot_id="s2",
                document_name="v2",
                timestamp=datetime.datetime.now(),
                git_path="dirty.FCStd",
            ),
            hierarchy=hierarchy,
        )

        # Act - pass dirty_paths including this document
        presenter.present_diffs([diff_result], dirty_paths={"dirty.FCStd"})

        # Assert
        calls = fake_view.get_calls()
        show_trees_call = next((c for c in calls if c["method"] == "show_diff_trees"), None)
        assert show_trees_call is not None
        presentations = show_trees_call["diff_trees"]
        assert len(presentations) == 1
        # Stage button should be enabled because document has git-tracked changes
        assert presentations[0].stage_button_enabled is True


class TestDiffPresenterAddButton:
    """Tests for DiffPresenter.on_add_button_clicked() method."""

    def test_on_add_button_clicked_stages_document_successfully(self) -> None:
        """Stages document successfully when git repository and diff result exist."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup mock working snapshot
        mock_working_snapshot = Snapshot(
            snapshot_id="ws1",
            document_name="doc.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc.FCStd",
        )

        # Setup mock diff result
        mock_diff_result = DiffResult(
            old_snapshot=None,
            new_snapshot=mock_working_snapshot,
            hierarchy=DiffHierarchy(),
        )
        # Store in _diff_results_by_path as _on_working_tree_selected would
        presenter._diff_results_by_path = {"doc.FCStd": mock_diff_result}

        # Setup mock stage action
        mock_stage_result = MagicMock()
        mock_stage_result.is_success = True
        mock_stage_result.message = ""
        presenter._stage_documents.execute.return_value = mock_stage_result

        # Act
        presenter.on_add_button_clicked("doc.FCStd")

        # Assert - stage was called with correct arguments
        presenter._stage_documents.execute.assert_called_once_with(mock_repo, [mock_working_snapshot])

    def test_on_add_button_clicked_no_git_repository_returns_early(self) -> None:
        """Returns early without staging when no git repository is available."""
        fake_view, presenter = _create_test_presenter()

        # No git repository set (ui_state.git_repository is None by default)

        # Act
        presenter.on_add_button_clicked("doc.FCStd")

        # Assert - stage was never called
        presenter._stage_documents.execute.assert_not_called()

    def test_on_add_button_clicked_missing_diff_result_logs_warning(self) -> None:
        """Logs warning when diff result not found for the given git_path."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # No diff results stored (empty _diff_results_by_path)
        presenter._diff_results_by_path = {}

        # Act
        presenter.on_add_button_clicked("missing.FCStd")

        # Assert - stage was never called
        presenter._stage_documents.execute.assert_not_called()

    def test_on_add_button_clicked_refreshes_view_after_staging(self) -> None:
        """Refreshes view by calling _on_working_tree_selected after successful staging."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup mock working snapshot
        mock_working_snapshot = Snapshot(
            snapshot_id="ws1",
            document_name="doc.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc.FCStd",
        )

        # Setup mock diff result
        mock_diff_result = DiffResult(
            old_snapshot=None,
            new_snapshot=mock_working_snapshot,
            hierarchy=DiffHierarchy(),
        )
        presenter._diff_results_by_path = {"doc.FCStd": mock_diff_result}

        # Setup mock stage action
        mock_stage_result = MagicMock()
        mock_stage_result.is_success = True
        mock_stage_result.message = ""
        presenter._stage_documents.execute.return_value = mock_stage_result

        # Mock _on_working_tree_selected to verify it's called
        with MagicMock() as mock_refresh:
            presenter._on_working_tree_selected = mock_refresh

            # Act
            presenter.on_add_button_clicked("doc.FCStd")

            # Assert - refresh was called after staging
            mock_refresh.assert_called_once()


class TestDiffPresenterStagingSelection:
    """Tests for staging selection plumbing and node lookup."""

    def test_on_staging_selected_populates_diff_map_using_git_path(self) -> None:
        """Staging selection stores diff results keyed by snapshot git_path."""
        fake_view, presenter = _create_test_presenter()

        presenter._ui_state.git_repository = GitRepository(name="repo", absolute_path="/repo")
        presenter._get_staged_file_paths.execute.return_value = MagicMock(is_success=True, data=["a.FCStd"])

        index_snapshot = Snapshot(
            snapshot_id="idx-1",
            document_name="a.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="a.FCStd",
        )
        head_snapshot = Snapshot(
            snapshot_id="head-1",
            document_name="a.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="a.FCStd",
        )
        presenter._create_commit_snapshot.execute.side_effect = [
            MagicMock(is_success=True, data=index_snapshot),
            MagicMock(is_success=True, data=head_snapshot),
        ]

        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Body", type_id="PartDesign::Body", _force_state=DiffState.MODIFIED))
        presenter._create_diff.execute.return_value = MagicMock(
            is_success=True,
            data=DiffResult(old_snapshot=head_snapshot, new_snapshot=index_snapshot, hierarchy=hierarchy),
        )

        presenter._on_staging_selected()

        assert "a.FCStd" in presenter._diff_results_by_path

    def test_on_staging_selected_node_click_resolves_document_diff(self) -> None:
        """After staging selection, node click resolves and shows properties."""
        fake_view, presenter = _create_test_presenter()

        presenter._ui_state.git_repository = GitRepository(name="repo", absolute_path="/repo")
        presenter._get_staged_file_paths.execute.return_value = MagicMock(is_success=True, data=["a.FCStd"])

        index_snapshot = Snapshot(
            snapshot_id="idx-1",
            document_name="a.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="a.FCStd",
        )
        head_snapshot = Snapshot(
            snapshot_id="head-1",
            document_name="a.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="a.FCStd",
        )
        presenter._create_commit_snapshot.execute.side_effect = [
            MagicMock(is_success=True, data=index_snapshot),
            MagicMock(is_success=True, data=head_snapshot),
        ]

        old_prop = Property.from_freecad(10.0, {}, "Base")
        new_prop = Property.from_freecad(20.0, {}, "Base")
        node = NodeDiff(
            path="Body",
            type_id="PartDesign::Body",
            property_diffs=[PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop)],
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node)
        presenter._create_diff.execute.return_value = MagicMock(
            is_success=True,
            data=DiffResult(old_snapshot=head_snapshot, new_snapshot=index_snapshot, hierarchy=hierarchy),
        )

        presenter._on_staging_selected()
        presenter.on_node_selected("a.FCStd", "Body")

        prop_calls = [c for c in fake_view.get_calls() if c["method"] == "show_properties"]
        assert prop_calls
        assert len(prop_calls[-1]["properties"]) == 1

    def test_on_staging_selected_missing_git_path_key_clears_properties(self) -> None:
        """Node selection clears properties when staged diff has no keyable git_path."""
        fake_view, presenter = _create_test_presenter()

        presenter._ui_state.git_repository = GitRepository(name="repo", absolute_path="/repo")
        presenter._get_staged_file_paths.execute.return_value = MagicMock(is_success=True, data=["a.FCStd"])

        index_snapshot = Snapshot(
            snapshot_id="idx-1",
            document_name="a.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="",
        )
        presenter._create_commit_snapshot.execute.side_effect = [
            MagicMock(is_success=True, data=index_snapshot),
            MagicMock(is_success=True, data=None),
        ]

        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Body", type_id="PartDesign::Body", _force_state=DiffState.MODIFIED))
        presenter._create_diff.execute.return_value = MagicMock(
            is_success=True,
            data=DiffResult(old_snapshot=None, new_snapshot=index_snapshot, hierarchy=hierarchy),
        )

        presenter._on_staging_selected()
        presenter.on_node_selected("a.FCStd", "Body")

        prop_calls = [c for c in fake_view.get_calls() if c["method"] == "show_properties"]
        assert prop_calls
        assert prop_calls[-1]["properties"] == []
