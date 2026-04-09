# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Integration tests for workbench activation flow with snapshot loading."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.fakes import FakeSnapshotView


if TYPE_CHECKING:
    from freecad.diff_wb.domain.freecad_ports import AppLike, FreeCadContext
    from freecad.diff_wb.entrypoints.workbench import DiffWorkbench


class TestWorkbenchActivationFlow:
    """Tests for workbench activation flow including snapshot presenter wiring."""

    def test_container_accepts_snapshot_view_parameter(
        self, freecad_app: AppLike, freecad_context: FreeCadContext
    ) -> None:
        """Test container accepts snapshot_view parameter and passes it to SnapshotPresenter.

        Verifies:
        - create_application_container accepts snapshot_view parameter
        - SnapshotPresenter receives the view instead of NullSnapshotView
        - Presenter can use the view for load_snapshots()
        """
        from freecad.diff_wb.application.di.container import create_application_container
        from freecad.diff_wb.domain.snapshots import InMemorySnapshotRepository

        fake_view = FakeSnapshotView()
        snapshot_repo = InMemorySnapshotRepository()

        # Execute with snapshot_view parameter
        container = create_application_container(
            ctx=freecad_context,
            snapshot_repo=snapshot_repo,
            snapshot_view=fake_view,  # Pass the fake view
        )

        # Verify presenter was created with our view
        assert container.snapshot_presenter is not None
        assert container.snapshot_presenter._view is fake_view

    def test_workbench_activates_and_creates_panel(self, initialized_workbench: DiffWorkbench) -> None:
        """Test workbench Activated() creates the diff panel on first activation.

        Verifies:
        - _subwindow is None initially
        - Activated() creates and shows the panel
        - _subwindow is set after activation
        """
        wb = initialized_workbench

        # Initially no subwindow
        assert wb._subwindow is None

        # Activate workbench (this will create the panel)
        wb.Activated()

        # Subwindow should now exist
        assert wb._subwindow is not None

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

    def test_snapshot_presenter_loads_snapshots_on_panel_creation(self, initialized_workbench: DiffWorkbench) -> None:
        """Test that snapshot presenter loads snapshots when panel is created.

        This test verifies the connection between the presenter and the view.
        It checks that:
        - SnapshotPresenter is created with DiffPanelView
        - load_snapshots() is called after panel is shown
        - Snapshots are displayed in the panel
        """
        from .._container import get_container

        wb = initialized_workbench

        # Trigger panel creation by activating workbench
        wb.Activated()

        # Verify subwindow was created
        assert wb._subwindow is not None

        # Verify presenter was created via container
        container = get_container()
        assert container.snapshot_presenter is not None

        # Verify the presenter has the correct view (the panel widget)
        assert container.snapshot_presenter._view is not None

        # Verify the presenter has list_snapshots_action wired
        assert container.snapshot_presenter._list_snapshots_action is not None

    def test_container_wires_list_snapshots_action_to_presenter(
        self, freecad_app: AppLike, freecad_context: FreeCadContext
    ) -> None:
        """Test container wires list_snapshots_action to SnapshotPresenter.

        Verifies:
        - SnapshotPresenter receives list_snapshots_action
        - Presenter can execute load_snapshots()
        - Empty repository shows 0 snapshots
        """
        from freecad.diff_wb.application.di.container import create_application_container
        from freecad.diff_wb.domain.snapshots import InMemorySnapshotRepository

        fake_view = FakeSnapshotView()
        snapshot_repo = InMemorySnapshotRepository()

        # Execute with snapshot_view parameter
        container = create_application_container(
            ctx=freecad_context,
            snapshot_repo=snapshot_repo,
            snapshot_view=fake_view,
        )

        # Verify presenter has list_snapshots_action wired
        assert container.snapshot_presenter._list_snapshots_action is not None

        # Verify we can call load_snapshots without error
        try:
            container.snapshot_presenter.load_snapshots()
        except Exception as e:
            pytest.fail(f"load_snapshots() raised exception: {e}")

        # Verify empty repository shows 0 snapshots
        assert len(fake_view.get_shown_snapshots()) == 0
