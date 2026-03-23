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
