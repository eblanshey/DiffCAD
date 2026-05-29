# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Integration smoke test for DiffPanelView instantiation and public methods."""

from __future__ import annotations


class TestDiffPanelView:
    """Smoke test for DiffPanelView instantiation and public interface."""

    def test_diff_panel_smoke(self) -> None:
        """Verify DiffPanelView instantiates and exposes required public methods."""
        from freecad.history_wb.qt import QtWidgets

        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])

        from freecad.history_wb.ui import DiffPanelView

        panel = DiffPanelView()
        assert panel is not None

        # Public protocol methods must be callable
        assert callable(panel.show_doc_diff)
        assert callable(panel.show_summary)

        # Methods execute without errors
        panel.show_doc_diff([])
        panel.show_summary(0, 0, 0)
