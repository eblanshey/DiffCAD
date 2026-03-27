"""File responsibility: Unit tests for DiffPresenter."""

from freecad.diff_wb.domain.diff.models import DiffResult, DiffState, NodeDiff, PropertyDiff
from freecad.diff_wb.domain.tree import Property, PropertyType
from freecad.diff_wb.ui.presenters.diff_presenter import DiffPresenter
from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation
from tests.fakes.fake_diff_view import FakeDiffView


class TestDiffPresenter:
    """Tests for DiffPresenter."""

    def test_present_diff_calls_view_methods(self) -> None:
        """Calls show_diff_tree and show_summary on view."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)
        # Create a node with no property changes so it's UNCHANGED
        diff_result = DiffResult(
            old_snapshot_name="snapshot_v1",
            new_snapshot_name="snapshot_v2",
            node_diffs=[
                NodeDiff(path="/Part", type_id="Part::Feature"),
            ],
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert
        assert fake_view.get_call_count() == 2
        calls = fake_view.get_calls()
        assert calls[0]["method"] == "show_diff_tree"
        assert calls[1]["method"] == "show_summary"

    def test_formats_node_diffs_correctly(self) -> None:
        """Transforms NodeDiff to NodePresentation correctly."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)
        node_diff = NodeDiff(
            path="/Part001",
            type_id="Part::Feature",
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot_name="v1",
            new_snapshot_name="v2",
            node_diffs=[node_diff],
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert
        calls = fake_view.get_calls()
        nodes = calls[0]["nodes"]
        assert len(nodes) == 1
        presentation = nodes[0]
        assert isinstance(presentation, NodePresentation)
        assert presentation.path == "/Part001"
        assert presentation.type_id == "Part::Feature"
        assert presentation.state == "MODIFIED"
        assert presentation.has_changes is True

    def test_formats_property_changes(self) -> None:
        """Formats PropertyDiff with expressions correctly."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)
        old_prop = Property.create(PropertyType.FLOAT, 10.0, expression="Sketch.X")
        new_prop = Property.create(PropertyType.FLOAT, 20.0, expression=None)
        node_diff = NodeDiff(
            path="/Part",
            type_id="Part::Feature",
            property_diffs=[PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop)],
            _force_state=DiffState.MODIFIED,
        )
        diff_result = DiffResult(
            old_snapshot_name="v1",
            new_snapshot_name="v2",
            node_diffs=[node_diff],
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert
        calls = fake_view.get_calls()
        nodes = calls[0]["nodes"]
        presentation = nodes[0]
        assert presentation.has_changes is True
        assert presentation.state == "MODIFIED"

    def test_handles_empty_diff(self) -> None:
        """Handles case with no changes."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)
        diff_result = DiffResult(
            old_snapshot_name="v1",
            new_snapshot_name="v2",
            node_diffs=[],
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert
        calls = fake_view.get_calls()
        assert calls[0]["method"] == "show_diff_tree"
        assert calls[0]["nodes"] == []
        assert calls[1]["method"] == "show_summary"
        assert calls[1]["added"] == 0
        assert calls[1]["deleted"] == 0
        assert calls[1]["modified"] == 0

    def test_calculates_summary_counts(self) -> None:
        """Calculates correct added/deleted/modified counts."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)
        added_node = NodeDiff(path="/NewPart", type_id="Part::Feature", _force_state=DiffState.ADDED)
        deleted_node = NodeDiff(path="/OldPart", type_id="Part::Feature", _force_state=DiffState.DELETED)
        modified_node = NodeDiff(
            path="/ChangedPart",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(
                    property_name="Length",
                    old_value=Property.create(PropertyType.FLOAT, 10.0),
                    new_value=Property.create(PropertyType.FLOAT, 20.0),
                )
            ],
            _force_state=DiffState.MODIFIED,
        )
        unchanged_node = NodeDiff(path="/UnchangedPart", type_id="Part::Feature")
        diff_result = DiffResult(
            old_snapshot_name="v1",
            new_snapshot_name="v2",
            node_diffs=[added_node, deleted_node, modified_node, unchanged_node],
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert
        calls = fake_view.get_calls()
        summary_call = calls[1]
        assert summary_call["added"] == 1
        assert summary_call["deleted"] == 1
        assert summary_call["modified"] == 1


class TestDiffPresenterFormatsChildren:
    """Tests for _format_node() populating children recursively."""

    def test_format_node_populates_children_recursive(self) -> None:
        """Test _format_node() populates children recursively from NodeDiff.children."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)

        # Create a nested tree structure using factory functions
        grandchild = NodeDiff(
            path="/Part/Body/Pad",
            type_id="PartDesign::Pad",
            _force_state=DiffState.UNCHANGED,
        )
        child = NodeDiff(
            path="/Part/Body",
            type_id="PartDesign::Body",
            children=[grandchild],
            _force_state=DiffState.MODIFIED,
        )
        parent = NodeDiff(
            path="/Part",
            type_id="Part::Feature",
            children=[child],
            _force_state=DiffState.UNCHANGED,
        )
        diff_result = DiffResult(
            old_snapshot_name="v1",
            new_snapshot_name="v2",
            node_diffs=[parent],
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert
        calls = fake_view.get_calls()
        presentations = calls[0]["nodes"]
        assert len(presentations) == 1

        # Check parent presentation
        parent_pres = presentations[0]
        assert parent_pres.path == "/Part"
        assert len(parent_pres.children) == 1

        # Check child presentation (recursive)
        child_pres = parent_pres.children[0]
        assert child_pres.path == "/Part/Body"
        assert len(child_pres.children) == 1

        # Check grandchild presentation (deeply nested)
        grandchild_pres = child_pres.children[0]
        assert grandchild_pres.path == "/Part/Body/Pad"
        assert len(grandchild_pres.children) == 0

    def test_complete_tree_structure_preserved_through_transformation(self) -> None:
        """Test complete tree structure is preserved through transformation."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)

        # Create a complex multi-level tree with multiple branches
        leaf1 = NodeDiff(path="/Part/Body/Pad", type_id="PartDesign::Pad", _force_state=DiffState.ADDED)
        leaf2 = NodeDiff(path="/Part/Body/Pocket", type_id="PartDesign::Pocket", _force_state=DiffState.DELETED)
        body = NodeDiff(
            path="/Part/Body",
            type_id="PartDesign::Body",
            children=[leaf1, leaf2],
            _force_state=DiffState.MODIFIED,
        )
        leaf3 = NodeDiff(path="/Part/Sketch", type_id="Sketcher::SketchObject", _force_state=DiffState.UNCHANGED)
        part = NodeDiff(
            path="/Part",
            type_id="Part::Feature",
            children=[body, leaf3],
            _force_state=DiffState.MODIFIED,
        )

        diff_result = DiffResult(
            old_snapshot_name="old",
            new_snapshot_name="new",
            node_diffs=[part],
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert
        calls = fake_view.get_calls()
        presentations = calls[0]["nodes"]

        # Root level
        assert len(presentations) == 1
        root = presentations[0]
        assert root.path == "/Part"
        assert root.state == "MODIFIED"
        assert len(root.children) == 2

        # First branch - Body with two leaves
        body_pres = root.children[0]
        assert body_pres.path == "/Part/Body"
        assert body_pres.state == "MODIFIED"
        assert len(body_pres.children) == 2

        # Body's children
        pad_pres = body_pres.children[0]
        assert pad_pres.path == "/Part/Body/Pad"
        assert pad_pres.state == "ADDED"
        assert pad_pres.has_changes is True

        pocket_pres = body_pres.children[1]
        assert pocket_pres.path == "/Part/Body/Pocket"
        assert pocket_pres.state == "DELETED"
        assert pocket_pres.has_changes is True

        # Second branch - Sketch (unchanged leaf)
        sketch_pres = root.children[1]
        assert sketch_pres.path == "/Part/Sketch"
        assert sketch_pres.state == "UNCHANGED"
        assert sketch_pres.has_changes is False
        assert len(sketch_pres.children) == 0

    def test_format_node_handles_empty_children(self) -> None:
        """Test _format_node() handles nodes with no children."""
        # Arrange
        fake_view = FakeDiffView()
        presenter = DiffPresenter(fake_view)

        leaf_node = NodeDiff(
            path="/Part/Leaf",
            type_id="Part::Feature",
            _force_state=DiffState.ADDED,
        )
        diff_result = DiffResult(
            old_snapshot_name="old",
            new_snapshot_name="new",
            node_diffs=[leaf_node],
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert
        calls = fake_view.get_calls()
        presentations = calls[0]["nodes"]
        assert len(presentations) == 1
        assert presentations[0].path == "/Part/Leaf"
        assert presentations[0].children == []
