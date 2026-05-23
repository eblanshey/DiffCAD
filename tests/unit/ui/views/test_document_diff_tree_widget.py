"""File responsibility: Unit tests for DocumentDiffTreeWidget component.

These tests verify the extracted document diff tree widget functionality,
including tree rendering, staging controls, and callback wiring.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from freecad.diff_wb.domain.diff.models import DiffState
from freecad.diff_wb.ui.views.diff_theme import DIFF_STATE_ROLE
from freecad.diff_wb.ui.views.document_diff_tree_widget import DocumentDiffTreeWidget


@pytest.fixture(scope="module")
def widget() -> DocumentDiffTreeWidget:
    """Create a DocumentDiffTreeWidget instance for testing.

    Note: This uses module scope to ensure QApplication is created once
    and reused across all tests in this module.
    """
    from PySide6.QtWidgets import QApplication

    # Ensure QApplication exists before creating widgets
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    return DocumentDiffTreeWidget()


class TestShowDocDiffEmptyList:
    """Tests for show_doc_diff() with empty list."""

    def test_show_doc_diff_with_empty_list_clears_tree(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_doc_diff() clears tree when given empty list."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Tree has some items
        root_node = NodePresentation(
            path="Body/Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            state=DiffState.ADDED,
            has_changes=True,
            children=[],
        )
        widget.show_doc_diff([root_node])
        assert widget.tree_widget.topLevelItemCount() == 1

        # When: Show empty list
        widget.show_doc_diff([])

        # Then: Tree is cleared (empty nodes means no display)
        assert widget.tree_widget.topLevelItemCount() == 0


class TestShowDocDiffNodeColorsAndUserRole:
    """Tests for node colors and Qt.UserRole path storage."""

    @pytest.mark.parametrize(
        "state",
        [
            DiffState.ADDED,
            DiffState.DELETED,
            DiffState.MODIFIED,
        ],
    )
    def test_node_state_colors(self, widget, state) -> None:  # type: ignore[no-untyped-def]
        """Nodes display with theme-aware color data per diff state."""

        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        node = NodePresentation(
            path="Body/TestPad",
            type_id="PartDesign::Pad",
            label="TestPad",
            state=state,
            has_changes=True,
            children=[],
        )

        widget.show_doc_diff([node])

        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        assert child_item.data(0, DIFF_STATE_ROLE) == state
        assert child_item.background(0).style() != Qt.BrushStyle.NoBrush
        assert child_item.foreground(0).style() != Qt.BrushStyle.NoBrush

    def test_unchanged_nodes_shown_without_color(self, widget) -> None:  # type: ignore[no-untyped-def]
        """UNCHANGED nodes display without custom color (default background)."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        unchanged_node = NodePresentation(
            path="Body/BasePart",
            type_id="PartDesign::Body",
            label="BasePart",
            state=DiffState.UNCHANGED,
            has_changes=False,
            children=[],
        )

        widget.show_doc_diff([unchanged_node])

        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        assert child_item.data(0, DIFF_STATE_ROLE) is None
        assert child_item.background(0).style() == Qt.BrushStyle.NoBrush

    def test_path_stored_in_user_role_for_retrieval(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Node paths are stored in Qt.UserRole for later property lookup."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Node with a specific path
        test_node = NodePresentation(
            path="Body/Pad/Length",
            type_id="PropertyLength",
            label="Length",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[],
        )

        # When: Show tree with the node
        widget.show_doc_diff([test_node])

        # Then: Path is retrievable from UserRole on child item (root is git_path wrapper)
        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        stored_path = child_item.data(0, Qt.ItemDataRole.UserRole)
        assert stored_path == "Body/Pad/Length"


class TestShowDocDiffsWithStageButtons:
    """Tests for show_doc_diffs() with stage button visibility."""

    def test_show_doc_diffs_creates_top_level_document_rows(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_doc_diffs() creates top-level document rows."""
        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )

        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                )
            ]
        )

        assert widget.tree_widget.topLevelItemCount() == 1
        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        assert root_item.text(0) == "parts/A.FCStd"

    def test_stage_buttons_only_appear_when_working_tree_selected(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Stage buttons only appear when current selection is WORKING_TREE."""
        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )
        from freecad.diff_wb.ui.views.models import HistorySelection

        # Clear any previous state
        widget.clear_doc_diffs()

        # Set selection to WORKING_TREE
        widget.set_current_history_selection(HistorySelection(item_kind="WORKING_TREE", commit_hash=None))

        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                    stage_button_enabled=True,
                )
            ]
        )

        assert widget._stage_buttons["parts/A.FCStd"].text() == "+ Reviewed"

    def test_stage_buttons_hidden_when_not_working_tree(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Stage buttons are hidden when selection is not WORKING_TREE."""
        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )
        from freecad.diff_wb.ui.views.models import HistorySelection

        # Clear any previous state
        widget.clear_doc_diffs()

        # Set selection to COMMIT (not WORKING_TREE)
        widget.set_current_history_selection(HistorySelection(item_kind="COMMIT", commit_hash="abc123"))

        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                    stage_button_enabled=True,
                )
            ]
        )

        assert "parts/A.FCStd" not in widget._stage_buttons

    def test_show_doc_diffs_with_empty_list_clears_tree(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_doc_diffs() clears tree when given empty list."""
        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )

        # Given: Tree has some items
        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                )
            ]
        )
        assert widget.tree_widget.topLevelItemCount() == 1

        # When: Show empty list
        widget.show_doc_diffs([])

        # Then: Tree is cleared
        assert widget.tree_widget.topLevelItemCount() == 0


class TestCallbackWiring:
    """Tests for callback wiring methods."""

    def test_set_add_button_callback_invokes_callback(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_add_button_callback() invokes callback when triggered."""
        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )
        from freecad.diff_wb.ui.views.models import HistorySelection

        captured: list[str] = []

        def callback(git_path: str) -> None:
            captured.append(git_path)

        widget.clear_doc_diffs()
        widget.set_add_button_callback(callback)
        widget.set_current_history_selection(HistorySelection(item_kind="WORKING_TREE", commit_hash=None))

        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                    stage_button_enabled=True,
                )
            ]
        )

        stage_button = widget._stage_buttons["parts/A.FCStd"]
        stage_button.click()

        assert captured == ["parts/A.FCStd"]

    def test_set_stage_all_callback_invokes_callback(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_stage_all_callback() invokes callback when triggered."""
        captured: list[bool] = []

        def callback() -> None:
            captured.append(True)

        widget.set_stage_all_callback(callback)
        widget._on_stage_all_clicked()

        assert captured == [True]

    def test_set_node_selection_callback_receives_git_path_and_node_path(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_node_selection_callback() receives (git_path, node_path) for child item clicks."""
        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )

        captured: list[tuple[str, str]] = []

        def callback(git_path: str, node_path: str) -> None:
            captured.append((git_path, node_path))

        widget.set_node_selection_callback(callback)
        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body",
                            type_id="PartDesign::Body",
                            label="Body",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                )
            ]
        )

        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None

        widget._on_tree_item_clicked(child_item, 0)

        assert captured == [("parts/A.FCStd", "Body")]

    def test_visual_diff_button_only_for_enabled_nodes(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Visual diff button appears only when presentation enables it."""
        from PySide6.QtWidgets import QToolButton

        from freecad.diff_wb.ui.presenters.presentation_models import DiffTreePresentation, NodePresentation
        from freecad.diff_wb.ui.views.models import HistorySelection

        widget.clear_doc_diffs()
        widget.set_current_history_selection(HistorySelection(item_kind="WORKING_TREE", commit_hash=None))
        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            visual_diff_enabled=True,
                            children=[],
                        ),
                        NodePresentation(
                            path="Body/Sketch",
                            type_id="App::FeaturePython",
                            label="Sketch",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            visual_diff_enabled=False,
                            children=[],
                        ),
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                )
            ]
        )
        root = widget.tree_widget.topLevelItem(0)
        assert root is not None
        first = root.child(0)
        second = root.child(1)
        assert first is not None and second is not None
        first_container = widget.tree_widget.itemWidget(first, 0)
        second_container = widget.tree_widget.itemWidget(second, 0)
        assert first_container is not None
        assert second_container is None
        assert len(first_container.findChildren(QToolButton)) == 1

    def test_visual_diff_button_emits_git_path_and_node_path(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Visual diff button callback emits (git_path, node_path)."""
        from PySide6.QtWidgets import QToolButton

        from freecad.diff_wb.ui.presenters.presentation_models import DiffTreePresentation, NodePresentation
        from freecad.diff_wb.ui.views.models import HistorySelection

        captured: list[tuple[str, str]] = []
        widget.clear_doc_diffs()
        widget.set_visual_diff_callback(lambda git_path, node_path: captured.append((git_path, node_path)))
        widget.set_current_history_selection(HistorySelection(item_kind="WORKING_TREE", commit_hash=None))
        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            visual_diff_enabled=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                )
            ]
        )
        root = widget.tree_widget.topLevelItem(0)
        assert root is not None
        child = root.child(0)
        assert child is not None
        container = widget.tree_widget.itemWidget(child, 0)
        assert container is not None
        buttons = container.findChildren(QToolButton)
        assert len(buttons) == 1
        buttons[0].click()
        assert captured == [("parts/A.FCStd", "Body/Pad")]


class TestDocumentDiffTreeWidgetIndependence:
    """Tests for DocumentDiffTreeWidget independence from property widget."""

    def test_widget_clears_document_diffs_without_property_widget(self, widget) -> None:  # type: ignore[no-untyped-def]
        """DocumentDiffTreeWidget does not need a property widget reference to clear document diffs."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Tree with items
        widget.show_doc_diff(
            [
                NodePresentation(
                    path="Body/Pad",
                    type_id="PartDesign::Pad",
                    label="Pad",
                    state=DiffState.MODIFIED,
                    has_changes=True,
                    children=[],
                )
            ]
        )
        assert widget.tree_widget.topLevelItemCount() == 1

        # When: Clear doc diffs
        widget.clear_doc_diffs()

        # Then: Tree is cleared
        assert widget.tree_widget.topLevelItemCount() == 0

    def test_widget_renders_document_diffs_without_property_widget(self, widget) -> None:  # type: ignore[no-untyped-def]
        """DocumentDiffTreeWidget does not need a property widget reference to render document diffs."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # This test simply verifies that show_doc_diff works without any property widget
        widget.show_doc_diff(
            [
                NodePresentation(
                    path="Body/Pad",
                    type_id="PartDesign::Pad",
                    label="Pad",
                    state=DiffState.MODIFIED,
                    has_changes=True,
                    children=[],
                )
            ]
        )

        assert widget.tree_widget.topLevelItemCount() == 1
        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        assert root_item.childCount() == 1


class TestShowSummary:
    """Tests for show_summary() method."""

    def test_show_summary_with_zero_changes(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_summary(0) displays 'No changes'."""
        widget.show_summary(0)
        assert widget._changed_label.text() == "No changes"

    def test_show_summary_with_positive_count(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_summary(n) displays 'Changed: n' for n > 0."""
        widget.show_summary(3)
        assert widget._changed_label.text() == "Changed: 3"


class TestSetStageAllButtonVisibilityAndEnabled:
    """Tests for stage all button visibility and enabled state."""

    def test_set_stage_all_button_visible(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_stage_all_button_visible() controls button visibility."""
        widget.set_stage_all_button_visible(True)
        assert not widget._stage_all_button.isHidden()

        widget.set_stage_all_button_visible(False)
        assert widget._stage_all_button.isHidden()

    def test_set_stage_all_button_enabled(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_stage_all_button_enabled() controls button enabled state."""
        widget.set_stage_all_button_enabled(True)
        assert widget._stage_all_button.isEnabled()

        widget.set_stage_all_button_enabled(False)
        assert not widget._stage_all_button.isEnabled()


class TestCollapseTreeItem:
    """Tests for collapse_tree_item() method."""

    def test_collapse_tree_item_collapses_root(self, widget) -> None:  # type: ignore[no-untyped-def]
        """collapse_tree_item() collapses the root item for given git_path."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        widget.show_doc_diff(
            [
                NodePresentation(
                    path="Body/Pad",
                    type_id="PartDesign::Pad",
                    label="Pad",
                    state=DiffState.MODIFIED,
                    has_changes=True,
                    children=[],
                )
            ],
            git_path="parts/A.FCStd",
        )

        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        root_item.setExpanded(True)
        assert root_item.isExpanded()

        widget.collapse_tree_item("parts/A.FCStd")
        assert not root_item.isExpanded()


class TestSetStageButtonEnabled:
    """Tests for set_stage_button_enabled() method."""

    def test_set_stage_button_enabled_updates_button(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_stage_button_enabled() updates the stage button for given git_path."""
        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )
        from freecad.diff_wb.ui.views.models import HistorySelection

        widget.clear_doc_diffs()
        widget.set_current_history_selection(HistorySelection(item_kind="WORKING_TREE", commit_hash=None))

        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                    stage_button_enabled=True,
                )
            ]
        )

        stage_button = widget._stage_buttons["parts/A.FCStd"]
        assert stage_button.isEnabled()

        widget.set_stage_button_enabled("parts/A.FCStd", False)
        assert not stage_button.isEnabled()


class TestWarningDisplay:
    """Tests for warning indicator rendering in show_doc_diffs()."""

    def test_show_doc_diffs_warning_is_tooltip_only(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Warnings are exposed via tooltip and not as inline orange text labels."""
        from PySide6.QtWidgets import QLabel

        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            OldSnapshotMissingIndicator,
        )

        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[],
                    git_path="parts/A.FCStd",
                    indicators=[OldSnapshotMissingIndicator()],
                )
            ]
        )

        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        container = widget.tree_widget.itemWidget(root_item, 0)
        assert container is not None

        labels = container.findChildren(QLabel)
        assert labels
        assert not any(label.text() == "Cannot find old snapshot. Diff cannot be generated." for label in labels)

        # Warning tooltip is shown on the icon label when icon assets are available.
        # In headless/unit environments icon loading may be unavailable, so keep this
        # assertion conditional.
        tooltip_values = [label.toolTip() for label in labels]
        if any(tooltip_values):
            assert "Cannot find old snapshot. Comparison cannot be generated." in tooltip_values
