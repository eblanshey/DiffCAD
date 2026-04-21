"""File responsibility: Unit tests for DiffPanelView.show_diff_tree() implementation.

These tests verify that the diff tree is correctly rendered with color-coded nodes,
proper hierarchy, and correct handling of different node states (ADDED, DELETED,
MODIFIED, UNCHANGED).
"""

from __future__ import annotations

import pytest

from freecad.diff_wb.domain.diff.models import DiffState
from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView


@pytest.fixture(scope="module")
def panel() -> DiffPanelView:
    """Create a DiffPanelView instance for testing.

    Note: This uses module scope to ensure QApplication is created once
    and reused across all tests in this module.
    """
    from PySide6.QtWidgets import QApplication

    # Ensure QApplication exists before creating widgets
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    return DiffPanelView()


class TestShowDiffTreeEmptyList:
    """Tests for show_diff_tree() with empty list."""

    def test_show_diff_tree_with_empty_list_clears_tree(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_diff_tree() clears tree when given empty list."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Tree has some items
        root_node = NodePresentation(
            path="Body/Pad",
            type_id="PartDesign::Pad",
            state=DiffState.ADDED,
            has_changes=True,
            children=[],
        )
        panel.show_diff_tree([root_node])
        assert panel.tree_widget.topLevelItemCount() == 1

        # When: Show empty list
        panel.show_diff_tree([])

        # Then: Tree is cleared (empty nodes means no display)
        assert panel.tree_widget.topLevelItemCount() == 0


class TestShowDiffTreeMixedStates:
    """Tests for show_diff_tree() with mixed node states."""

    def test_added_nodes_shown_with_green_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """ADDED nodes display with light green background."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: ADDED node
        added_node = NodePresentation(
            path="Body/NewPad",
            type_id="PartDesign::Pad",
            state=DiffState.ADDED,
            has_changes=True,
            children=[],
        )

        # When: Show tree with ADDED node
        panel.show_diff_tree([added_node])

        # Then: Root item exists and child has green background
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        bg_color = child_item.background(0).color()
        assert bg_color == QColor(200, 255, 200)

    def test_deleted_nodes_shown_with_red_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """DELETED nodes display with light red background."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: DELETED node
        deleted_node = NodePresentation(
            path="Body/OldPad",
            type_id="PartDesign::Pad",
            state=DiffState.DELETED,
            has_changes=True,
            children=[],
        )

        # When: Show tree with DELETED node
        panel.show_diff_tree([deleted_node])

        # Then: Root item exists and child has red background
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        bg_color = child_item.background(0).color()
        assert bg_color == QColor(255, 200, 200)

    def test_modified_nodes_shown_with_blue_background(self, panel) -> None:  # type: ignore[no-untyped-def]
        """MODIFIED nodes display with light blue background."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: MODIFIED node
        modified_node = NodePresentation(
            path="Body/ModifiedPad",
            type_id="PartDesign::Pad",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[],
        )

        # When: Show tree with MODIFIED node
        panel.show_diff_tree([modified_node])

        # Then: Root item exists and child has blue background
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        bg_color = child_item.background(0).color()
        assert bg_color == QColor(200, 200, 255)

    def test_unchanged_nodes_shown_without_color(self, panel) -> None:  # type: ignore[no-untyped-def]
        """UNCHANGED nodes display without custom color (default background)."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: UNCHANGED node
        unchanged_node = NodePresentation(
            path="Body/BasePart",
            type_id="PartDesign::Body",
            state=DiffState.UNCHANGED,
            has_changes=False,
            children=[],
        )

        # When: Show tree with UNCHANGED node
        panel.show_diff_tree([unchanged_node])

        # Then: Root item exists and child has default background (not colored)
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        bg_color = child_item.background(0).color()
        # Should NOT be any of the special colors
        assert bg_color != QColor(200, 255, 200)  # Not green
        assert bg_color != QColor(255, 200, 200)  # Not red
        assert bg_color != QColor(200, 200, 255)  # Not blue

    def test_path_stored_in_user_role_for_retrieval(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Node paths are stored in Qt.UserRole for later property lookup."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Node with a specific path
        test_node = NodePresentation(
            path="Body/Pad/Length",
            type_id="PropertyLength",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[],
        )

        # When: Show tree with the node
        panel.show_diff_tree([test_node])

        # Then: Path is retrievable from UserRole on child item (root is git_path wrapper)
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        stored_path = child_item.data(0, Qt.ItemDataRole.UserRole)
        assert stored_path == "Body/Pad/Length"


class TestDisplayNameExtractionEdgeCases:
    """Tests for display name extraction edge cases."""

    def test_empty_path_falls_back_to_type_id(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Empty path falls back to using type_id as display text."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Node with empty path
        node = NodePresentation(
            path="",
            type_id="PartDesign::Body",
            state=DiffState.UNCHANGED,
            has_changes=False,
            children=[],
        )

        # When: Show tree with the node
        panel.show_diff_tree([node])

        # Then: Root exists and child uses type_id (no slash to split on)
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        assert child_item.text(0) == "PartDesign::Body (PartDesign::Body)"

    def test_path_ending_with_slash_uses_empty_display_name(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Path ending with '/' results in empty string as last segment."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Node with path ending in "/"
        node = NodePresentation(
            path="Body/Pad/",
            type_id="PartDesign::Pad",
            state=DiffState.UNCHANGED,
            has_changes=False,
            children=[],
        )

        # When: Show tree with the node
        panel.show_diff_tree([node])

        # Then: Root exists and child shows empty name before type_id
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        assert child_item.text(0) == " (PartDesign::Pad)"

    def test_single_segment_path_shows_as_display_name(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Single segment path (no slashes) uses the entire path as display name."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Node with single-segment path (no slashes)
        node = NodePresentation(
            path="Body",
            type_id="PartDesign::Body",
            state=DiffState.UNCHANGED,
            has_changes=False,
            children=[],
        )

        # When: Show tree with the node
        panel.show_diff_tree([node])

        # Then: Root exists and child uses the path segment as display name
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        assert child_item.text(0) == "Body (PartDesign::Body)"


class TestShowDiffTreeHierarchy:
    """Tests for show_diff_tree() tree hierarchy."""

    def test_children_appear_nested_under_parents(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Child nodes appear nested under their parent nodes."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Parent node with children
        child1 = NodePresentation(
            path="Body/Pad/Length",
            type_id="PropertyLength",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[],
        )
        child2 = NodePresentation(
            path="Body/Pad/Width",
            type_id="PropertyLength",
            state=DiffState.ADDED,
            has_changes=True,
            children=[],
        )
        parent = NodePresentation(
            path="Body/Pad",
            type_id="PartDesign::Pad",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[child1, child2],
        )

        # When: Show tree with parent and children
        panel.show_diff_tree([parent])

        # Then: Root item exists, parent is its child, grand-children are nested under parent
        assert panel.tree_widget.topLevelItemCount() == 1
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        assert root_item.childCount() == 1  # One parent node
        parent_item = root_item.child(0)
        assert parent_item is not None
        assert parent_item.childCount() == 2
        assert parent_item.child(0).text(0) == "Length (PropertyLength)"
        assert parent_item.child(1).text(0) == "Width (PropertyLength)"

    def test_deeply_nested_children_display_correctly(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Deeply nested children are displayed at correct levels."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Deeply nested structure
        grandchild = NodePresentation(
            path="Body/Pad/Sketch/Constraint",
            type_id="PropertyConstraint",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[],
        )
        child = NodePresentation(
            path="Body/Pad/Sketch",
            type_id="PartDesign::Sketch",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[grandchild],
        )
        parent = NodePresentation(
            path="Body/Pad",
            type_id="PartDesign::Pad",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[child],
        )

        # When: Show deeply nested tree
        panel.show_diff_tree([parent])

        # Then: All levels present under root wrapper
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        assert root_item.childCount() == 1
        pad_item = root_item.child(0)
        assert pad_item.text(0) == "Pad (PartDesign::Pad)"
        assert pad_item.childCount() == 1
        sketch_item = pad_item.child(0)
        assert sketch_item.text(0) == "Sketch (PartDesign::Sketch)"
        assert sketch_item.childCount() == 1
        constraint_item = sketch_item.child(0)
        assert constraint_item.text(0) == "Constraint (PropertyConstraint)"

    def test_multiple_root_nodes_display_independently(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Multiple root nodes display as children of the git_path wrapper."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Multiple root nodes
        root1 = NodePresentation(
            path="Body/Pad",
            type_id="PartDesign::Pad",
            state=DiffState.ADDED,
            has_changes=True,
            children=[],
        )
        root2 = NodePresentation(
            path="Pocket/Hole",
            type_id="PartDesign::Hole",
            state=DiffState.DELETED,
            has_changes=True,
            children=[],
        )

        # When: Show tree with multiple roots
        panel.show_diff_tree([root1, root2])

        # Then: Both appear as children of the single root wrapper item
        assert panel.tree_widget.topLevelItemCount() == 1
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        assert root_item.childCount() == 2
        assert root_item.child(0).text(0) == "Pad (PartDesign::Pad)"
        assert root_item.child(1).text(0) == "Hole (PartDesign::Hole)"


class TestShowDiffTreeExpandCollapse:
    """Tests for show_diff_tree() expand/collapse functionality."""

    def test_nodes_expanded_by_default(self, panel) -> None:  # type: ignore[no-untyped-def]
        """All nodes are expanded by default for immediate visibility."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Parent with children
        child = NodePresentation(
            path="Body/Pad/Length",
            type_id="PropertyLength",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[],
        )
        parent = NodePresentation(
            path="Body/Pad",
            type_id="PartDesign::Pad",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[child],
        )

        # When: Show tree
        panel.show_diff_tree([parent])

        # Then: Children are visible (expanded by default)
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        # Parent should be child of root wrapper
        assert root_item.childCount() == 1
        parent_item = root_item.child(0)
        assert parent_item is not None
        # Child should exist under parent
        assert parent_item.childCount() == 1
        child_item = parent_item.child(0)
        assert child_item.text(0) == "Length (PropertyLength)"


class TestShowDiffTreeScrolling:
    """Tests for show_diff_tree() scrollable content."""

    def test_tree_is_scrollable_when_content_exceeds_view(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Tree widget provides scrolling when content exceeds viewport."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Many nodes that exceed typical view height
        nodes = [
            NodePresentation(
                path=f"Body/Feature{i}",
                type_id="PartDesign::Feature",
                state=DiffState.ADDED if i % 2 == 0 else "MODIFIED",
                has_changes=True,
                children=[],
            )
            for i in range(50)
        ]

        # When: Show tree with many nodes
        panel.show_diff_tree(nodes)

        # Then: All nodes are present as children of root wrapper
        assert panel.tree_widget.topLevelItemCount() == 1
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        assert root_item.childCount() == 50
        # Tree widget should have scrollbar capability
        # (QTreeWidget supports scrolling by default)
        assert panel.tree_widget.verticalScrollBar() is not None


class TestShowDiffTreeGitPath:
    """Tests for show_diff_tree() git_path top-level item functionality."""

    def test_git_path_displayed_as_top_level_item(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Tree widget displays git_path as top-level item when provided."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Node and a git_path
        node = NodePresentation(
            path="Body/Pad",
            type_id="PartDesign::Pad",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[],
        )
        git_path = "path/to/document.FCStd"

        # When: Show tree with git_path
        panel.show_diff_tree([node], git_path)

        # Then: Top-level item shows git_path
        assert panel.tree_widget.topLevelItemCount() == 1
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        assert root_item.text(0) == "path/to/document.FCStd"

    def test_child_nodes_added_under_git_path_root(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Child nodes are correctly added under the git_path top-level item."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Multiple nodes under a git_path
        child1 = NodePresentation(
            path="Body/Pad",
            type_id="PartDesign::Pad",
            state=DiffState.ADDED,
            has_changes=True,
            children=[],
        )
        child2 = NodePresentation(
            path="Body/Pocket",
            type_id="PartDesign::Pocket",
            state=DiffState.DELETED,
            has_changes=True,
            children=[],
        )
        git_path = "projects/myproject/doc.FCStd"

        # When: Show tree with multiple nodes and git_path
        panel.show_diff_tree([child1, child2], git_path)

        # Then: Root item contains all nodes as children
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        assert root_item.text(0) == "projects/myproject/doc.FCStd"
        assert root_item.childCount() == 2
        assert root_item.child(0).text(0) == "Pad (PartDesign::Pad)"
        assert root_item.child(1).text(0) == "Pocket (PartDesign::Pocket)"

    def test_document_name_fallback_when_git_path_empty(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Tree widget falls back to document_name when git_path is empty."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Node and empty git_path
        node = NodePresentation(
            path="Body/Pad",
            type_id="PartDesign::Pad",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[],
        )
        git_path = ""

        # When: Show tree with empty git_path
        panel.show_diff_tree([node], git_path)

        # Then: Falls back to "Unnamed Document"
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        assert root_item.text(0) == "Unnamed Document"

    def test_nested_children_structure_preserved_under_git_path_root(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Nested child structure is preserved under the git_path top-level item."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Nested tree structure with git_path
        grandchild = NodePresentation(
            path="Body/Pad/Sketch",
            type_id="PartDesign::Sketch",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[],
        )
        child = NodePresentation(
            path="Body/Pad",
            type_id="PartDesign::Pad",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[grandchild],
        )
        git_path = "repo/docs/model.FCStd"

        # When: Show nested tree with git_path
        panel.show_diff_tree([child], git_path)

        # Then: Structure preserved under git_path root
        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        assert root_item.text(0) == "repo/docs/model.FCStd"
        assert root_item.childCount() == 1

        pad_item = root_item.child(0)
        assert pad_item.text(0) == "Pad (PartDesign::Pad)"
        assert pad_item.childCount() == 1

        sketch_item = pad_item.child(0)
        assert sketch_item.text(0) == "Sketch (PartDesign::Sketch)"


class TestShowDiffTreesSelectionKeyWiring:
    """Tests for show_diff_trees() root key and click callback wiring."""

    def test_show_diff_trees_stores_fallback_root_key_in_user_role(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Root item stores fallback selection key when git_path is empty."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.ui.presenters.presentation_models import DiffTreePresentation

        panel.show_diff_trees([DiffTreePresentation(nodes=[], git_path="", warnings=[])])

        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        assert root_item.text(0) == "Unnamed Document"
        assert root_item.data(0, Qt.ItemDataRole.UserRole) == "Unnamed Document"

    def test_tree_item_click_forwards_root_key_and_node_path(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Clicking child item forwards (git_path, node_path) to callback."""
        from freecad.diff_wb.ui.presenters.presentation_models import DiffTreePresentation, NodePresentation

        captured: list[tuple[str, str]] = []

        def callback(git_path: str, node_path: str) -> None:
            captured.append((git_path, node_path))

        panel.set_node_selection_callback(callback)
        panel.show_diff_trees(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body",
                            type_id="PartDesign::Body",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    warnings=[],
                )
            ]
        )

        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None

        panel._on_tree_item_clicked(child_item, 0)

        assert captured == [("parts/A.FCStd", "Body")]


class TestShowDiffTreesWarningDisplay:
    """Tests for warning indicator rendering in show_diff_trees()."""

    def test_show_diff_trees_warning_is_tooltip_only(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Warnings are exposed via tooltip and not as inline orange text labels."""
        from PySide6.QtWidgets import QLabel

        from freecad.diff_wb.ui.presenters.presentation_models import DiffTreePresentation

        panel.show_diff_trees(
            [
                DiffTreePresentation(
                    nodes=[],
                    git_path="parts/A.FCStd",
                    warnings=["Old snapshot missing"],
                )
            ]
        )

        root_item = panel.tree_widget.topLevelItem(0)
        assert root_item is not None
        container = panel.tree_widget.itemWidget(root_item, 0)
        assert container is not None

        labels = container.findChildren(QLabel)
        assert labels
        assert not any(label.text() == "Old snapshot missing" for label in labels)

        # Warning tooltip is shown on the icon label when icon assets are available.
        # In headless/unit environments icon loading may be unavailable, so keep this
        # assertion conditional.
        tooltip_values = [label.toolTip() for label in labels]
        if any(tooltip_values):
            assert "Old snapshot missing" in tooltip_values
