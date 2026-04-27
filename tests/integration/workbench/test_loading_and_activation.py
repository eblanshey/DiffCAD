# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Integration tests for workbench loading and module structure."""

from __future__ import annotations

import inspect

import pytest


class TestWorkbenchLoading:
    """Tests for workbench loading and module structure."""

    def test_workbench_loads_without_errors(self, freecad_app) -> None:  # type: ignore[no-untyped-def]
        """Test workbench module loads without console errors and has required attributes.

        Verifies:
        - Module importability
        - No Console.PrintError during load
        - Required attributes present (Gui, getMainWindow)
        - DiffWorkbench class exists when GUI available
        - Required attributes on DiffWorkbench class
        """
        errors = []
        original_print_error = freecad_app.Console.PrintError

        def tracked_print_error(text: str) -> None:
            errors.append(text)
            original_print_error(text)

        freecad_app.Console.PrintError = tracked_print_error

        try:
            import freecad.diff_wb.entrypoints.workbench as wb_module

            assert wb_module is not None
            assert hasattr(wb_module, "Gui")
            assert hasattr(wb_module, "getMainWindow")

            # Check if full GUI is available
            if wb_module.Gui is not None and wb_module.getMainWindow is not None:
                from freecad.diff_wb.entrypoints.workbench import DiffWorkbench

                assert DiffWorkbench is not None
                assert hasattr(DiffWorkbench, "MenuText")
                assert hasattr(DiffWorkbench, "ToolTip")
                assert hasattr(DiffWorkbench, "Icon")
                assert hasattr(DiffWorkbench, "toolbox")

                # Verify specific attribute values
                assert DiffWorkbench.MenuText == "Diff"
                assert DiffWorkbench.ToolTip == "Compare document snapshots"
                assert DiffWorkbench.toolbox == [
                    "DiffTakeSnapshot",
                    "DiffCompare",
                    "DiffSwapColumns",
                    "DiffCommit",
                    "DiffOpenAllDocumentsInRepository",
                ]
        finally:
            freecad_app.Console.PrintError = original_print_error

        if errors:
            pytest.fail(f"Console errors detected during module load: {len(errors)}\n" + "\n".join(errors))

    def test_workbench_has_required_methods_and_attributes(self, freecad_app) -> None:  # type: ignore[no-untyped-def]
        """Test workbench module defines required methods and attributes.

        Tests the workbench class definition without requiring Gui.Workbench to exist.
        Verifies:
        - Module has Gui and getMainWindow imports
        - If DiffWorkbench class is available (GUI available), check its attributes
        - If not available (headless), check that source code contains expected definitions
        """
        import freecad.diff_wb.entrypoints.workbench as wb_module

        # Gui and getMainWindow may be None in headless mode - that's OK
        assert hasattr(wb_module, "Gui")
        assert hasattr(wb_module, "getMainWindow")

        # Check if DiffWorkbench class is available
        if wb_module.Gui is not None and hasattr(wb_module.Gui, "Workbench"):
            from freecad.diff_wb.entrypoints.workbench import DiffWorkbench

            # Class is available - check instance attributes
            wb = DiffWorkbench()
            assert hasattr(wb, "Initialize")
            assert hasattr(wb, "Activated")
            assert hasattr(wb, "Deactivated")
            assert hasattr(wb, "GetClassName")
            assert wb.MenuText == "Diff"
            assert wb.ToolTip == "Compare document snapshots"
            assert wb.toolbox == [
                "DiffTakeSnapshot",
                "DiffCompare",
                "DiffSwapColumns",
                "DiffCommit",
                "DiffOpenAllDocumentsInRepository",
            ]
        else:
            # Class not available (headless/Xvfb mode) - check source code instead
            source = inspect.getsource(wb_module)
            assert "MenuText" in source
            assert "ToolTip" in source
            assert "toolbox" in source
            assert "Initialize" in source
            assert "Activated" in source
            assert "Deactivated" in source
            assert "DiffWorkbench" in source
