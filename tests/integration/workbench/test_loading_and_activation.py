# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Integration tests for workbench loading and toolbox behavior."""

from __future__ import annotations


class TestWorkbenchLoading:
    """Tests for workbench loading and module structure."""

    def test_workbench_loads_without_errors(self, freecad_app) -> None:  # type: ignore[no-untyped-def]
        """Test workbench module loads without console errors and has required attributes.

        Verifies:
        - Module importability
        - No Console.PrintError during load
        - Required attributes present (Gui, getMainWindow)
        - HistoryWorkbench class exists when GUI available
        - Required attributes on HistoryWorkbench class
        """
        errors = []
        original_print_error = freecad_app.Console.PrintError

        def tracked_print_error(text: str) -> None:
            errors.append(text)
            original_print_error(text)

        freecad_app.Console.PrintError = tracked_print_error

        try:
            import freecad.history_wb.entrypoints.workbench as wb_module

            assert wb_module is not None
            assert hasattr(wb_module, "Gui")
            assert hasattr(wb_module, "getMainWindow")

            # Check if full GUI is available
            if wb_module.Gui is not None and wb_module.getMainWindow is not None:
                from freecad.history_wb.entrypoints.workbench import HistoryWorkbench

                assert HistoryWorkbench is not None
                assert hasattr(HistoryWorkbench, "MenuText")
                assert hasattr(HistoryWorkbench, "ToolTip")
                assert hasattr(HistoryWorkbench, "Icon")
                assert hasattr(HistoryWorkbench, "toolbar_commands")

                # Verify specific attribute values
                assert HistoryWorkbench.MenuText == "History"
                assert HistoryWorkbench.ToolTip == "Track project iterations and history"
                assert HistoryWorkbench.toolbar_commands == [
                    "DiffOpenDiffWindow",
                    "DiffRefreshRepository",
                    "DiffRecomputeActiveDocument",
                    "DiffRecomputeAllOpenDocuments",
                    "DiffOpenAllDocumentsInRepository",
                    "DiffInitializeGitRepository",
                    "DiffCloseDiffWindows",
                    "DiffCommit",
                ]
        finally:
            freecad_app.Console.PrintError = original_print_error

        if errors:
            import pytest

            pytest.fail(f"Console errors detected during module load: {len(errors)}\n" + "\n".join(errors))
