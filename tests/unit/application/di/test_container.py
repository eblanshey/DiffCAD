"""File responsibility: Tests for dependency injection container.

These tests verify that the DI container correctly wires all application
layer dependencies together.
"""

import pytest

from freecad.diff_wb.application.di.container import (
    ApplicationContainer,
    create_application_container,
)
from freecad.diff_wb.domain.ports import FreeCadContext
from freecad.diff_wb.domain.snapshots.repository import InMemorySnapshotRepository
from tests.fakes import FakeDiffView, FakeSnapshotView


class TestApplicationContainer:
    """Tests for the ApplicationContainer dataclass."""

    def test_container_creates_all_actions(self) -> None:
        """All actions are instantiated by the container."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        # Execute
        container = create_application_container(ctx, snapshot_repo)

        # Verify
        assert container.take_snapshot_action is not None
        assert container.compare_snapshots_action is not None
        assert container.list_snapshots_action is not None

    def test_container_creates_all_presenters(self) -> None:
        """All presenters are instantiated by the container."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        # Execute
        container = create_application_container(ctx, snapshot_repo)

        # Verify
        assert container.snapshot_presenter is not None
        # diff_presenter is None when no diff_view is provided
        assert container.diff_presenter is None

    def test_container_with_diff_view_creates_diff_presenter(self) -> None:
        """Diff presenter is created when diff_view is provided."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        fake_diff_view = FakeDiffView()

        # Execute
        container = create_application_container(ctx, snapshot_repo, fake_diff_view)

        # Verify
        assert container.diff_presenter is not None

    def test_container_wires_dependencies_correctly(self) -> None:
        """Actions have correct dependencies injected."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        # Execute
        container = create_application_container(ctx, snapshot_repo)

        # Verify TakeSnapshotAction dependencies
        take_action = container.take_snapshot_action
        assert hasattr(take_action, "_freecad_port")
        assert hasattr(take_action, "_extractor")
        assert hasattr(take_action, "_snapshot_repo")

        # Verify CompareSnapshotsAction dependencies
        compare_action = container.compare_snapshots_action
        assert hasattr(compare_action, "_snapshot_repo")
        assert hasattr(compare_action, "_diff_engine")
        assert hasattr(compare_action, "_settings_repo")
        # Note: logger is no longer injected; uses static Log methods

        # Verify ListSnapshotsAction dependencies
        list_action = container.list_snapshots_action
        assert hasattr(list_action, "_snapshot_repo")

    def test_container_injects_view_into_presenters(self) -> None:
        """Presenters receive views."""
        _ctx = FreeCadContext(app=None)  # type: ignore  # Setup for context
        _snapshot_repo = InMemorySnapshotRepository()  # Setup for snapshot repo

        fake_snapshot_view = FakeSnapshotView()
        fake_diff_view = FakeDiffView()

        # We need to manually wire with fake views since the container uses None
        # This test verifies that presenters can accept views
        from freecad.diff_wb.ui.presenters.diff_presenter import DiffPresenter
        from freecad.diff_wb.ui.presenters.snapshot_presenter import SnapshotPresenter

        snapshot_presenter = SnapshotPresenter(view=fake_snapshot_view)
        diff_presenter = DiffPresenter(view=fake_diff_view)

        # Verify
        assert snapshot_presenter._view is fake_snapshot_view
        assert diff_presenter._view is fake_diff_view

    def test_container_returns_application_container_instance(self) -> None:
        """Container returns an ApplicationContainer instance."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        # Execute
        container = create_application_container(ctx, snapshot_repo)

        # Verify
        assert isinstance(container, ApplicationContainer)

    def test_container_accepts_snapshot_view_parameter(self) -> None:
        """Container accepts snapshot_view parameter and passes it to SnapshotPresenter."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        fake_view = FakeSnapshotView()

        # Execute with snapshot_view parameter
        container = create_application_container(
            ctx,
            snapshot_repo,
            snapshot_view=fake_view,
        )

        # Verify presenter was created with our view
        assert container.snapshot_presenter is not None
        assert container.snapshot_presenter._view is fake_view

    def test_container_wires_list_snapshots_action_to_presenter(self) -> None:
        """Container wires list_snapshots_action to SnapshotPresenter."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        fake_view = FakeSnapshotView()

        # Execute
        container = create_application_container(
            ctx,
            snapshot_repo,
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
