# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Integration tests for DiffPanelView component.

These tests verify that the DiffPanelView can be instantiated and provides
the required UI components and protocol methods for displaying diff information.
"""

from __future__ import annotations

import pytest


class TestDiffPanelView:
    """Tests for DiffPanelView instantiation and interface compliance."""

    @pytest.fixture(scope="module")
    def panel(self) -> object:
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

        assert DiffPanelView is not None, "DiffPanelView not available (PySide6 not installed?)"
        return DiffPanelView()

    def test_diff_panel_instantiates(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test DiffPanelView can be created without errors."""
        assert panel is not None

    def test_diff_panel_has_ui_components(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test DiffPanelView has required UI widgets.

        Verifies presence of:
        - tree_widget: QTreeWidget for displaying diff tree
        - properties_tree: QTreeWidget for property details (replaces QTableWidget)
        - snapshot_list: QListWidget for snapshot selection
        """
        assert hasattr(panel, "tree_widget"), "Missing tree_widget"
        assert hasattr(panel, "properties_tree"), "Missing properties_tree"
        assert hasattr(panel, "snapshot_list"), "Missing snapshot_list"

    def test_diff_panel_implements_protocols(self, panel) -> None:  # type: ignore[no-untyped-def]
        """Test DiffPanelView implements required protocol methods.

        Verifies presence of:
        - SnapshotView methods: show_success, show_error, show_loading
        - DiffView methods: show_diff_tree, show_summary
        """
        # SnapshotView protocol methods
        assert hasattr(panel, "show_success")
        assert hasattr(panel, "show_error")
        assert hasattr(panel, "show_loading")

        # DiffView protocol methods
        assert hasattr(panel, "show_diff_tree")
        assert hasattr(panel, "show_summary")

        # Verify they're callable
        assert callable(panel.show_success)
        assert callable(panel.show_error)
        assert callable(panel.show_loading)
        assert callable(panel.show_diff_tree)
        assert callable(panel.show_summary)

        # Test that methods can be called without errors (they're stubs in Phase 8)
        panel.show_success("test_snapshot")
        panel.show_error("test error")
        panel.show_loading("loading...")
        panel.show_diff_tree([])
        panel.show_summary(0, 0, 0)
