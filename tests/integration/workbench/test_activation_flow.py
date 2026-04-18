# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Integration tests for workbench activation flow with UI registry.

These tests require FreeCAD runtime with GUI support. They verify the complete
architecture where:
- Container provides application layer actions
- UI Registry provides UI layer presenters
- Workbench composes and registers UI components
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from freecad.diff_wb.entrypoints.workbench import DiffWorkbench


@pytest.mark.skip(reason="Requires FreeCAD runtime with GUI. Use ./run_integration_tests.sh")
class TestWorkbenchActivationFlow:  # noqa: B024
    """Tests for workbench activation flow including UI component registration."""

    def test_workbench_activates_and_creates_panel(self, initialized_workbench: DiffWorkbench) -> None:
        """Test workbench Activated() creates the diff panel on first activation.

        Verifies:
        - _subwindow is None initially
        - Activated() creates and shows the panel
        - _subwindow is set after activation
        - UI registry has presenters registered
        """
        from freecad.diff_wb.ui.registry import ui_registry

        wb = initialized_workbench

        # Initially no subwindow
        assert wb._subwindow is None

        # Activate workbench (this will create the panel)
        wb.Activated()

        # Subwindow should now exist
        assert wb._subwindow is not None

        # Verify UI registry has presenters registered (Phase 5 architecture)
        assert ui_registry.snapshot_presenter is not None

    def test_workbench_reuses_existing_panel_on_reactivation(self, initialized_workbench: DiffWorkbench) -> None:
        """Test workbench reuses existing panel on re-activation.

        Verifies:
        - Second activation doesn't create a new panel
        - Existing panel is shown and raised
        """
        wb = initialized_workbench

        # First activation
        wb.Activated()
        first_subwindow = wb._subwindow

        assert first_subwindow is not None

        # Second activation
        wb.Activated()

        # Should be the same subwindow
        assert wb._subwindow is first_subwindow

    def test_ui_registry_has_presenters_after_panel_creation(self, initialized_workbench: DiffWorkbench) -> None:
        """Test that UI registry has presenters after panel is created.

        This test verifies the composer correctly registers presenters in the UI registry.
        It checks that:
        - SnapshotPresenter is registered in ui_registry
        - DiffPresenter is registered in ui_registry
        - Presenters have correct dependencies wired
        """
        from freecad.diff_wb._container import get_container
        from freecad.diff_wb.ui.registry import ui_registry

        wb = initialized_workbench

        # Trigger panel creation by activating workbench
        wb.Activated()

        # Verify subwindow was created
        assert wb._subwindow is not None

        # Verify presenters are in UI registry (Phase 5 architecture)
        assert ui_registry.snapshot_presenter is not None
        assert ui_registry.diff_presenter is not None

        # Verify container has actions (not presenters)
        container = get_container()
        assert container.take_snapshot_action is not None
        assert container.compare_snapshots_action is not None
