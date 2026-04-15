"""File responsibility: Tests for dependency injection container.

These tests verify that the DI container correctly wires all application
layer dependencies together, including git repository detection components.
"""

import pytest

from freecad.diff_wb.application.di.container import (
    ApplicationContainer,
    create_application_container,
)
from freecad.diff_wb.domain.freecad_ports import FreeCadContext
from freecad.diff_wb.domain.git.git_service import GitService
from freecad.diff_wb.domain.snapshots.repository import InMemorySnapshotRepository
from freecad.diff_wb.infrastructure.git.git_port_adapter import GitPortAdapter
from freecad.diff_wb.ui.presenters.application_state import ApplicationState
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
        except RuntimeError as e:
            pytest.fail(f"load_snapshots() raised RuntimeError: {e}")

        # Verify empty repository shows 0 snapshots
        assert len(fake_view.get_shown_snapshots()) == 0


class TestGitRepositoryDetectionWiring:
    """Tests for git repository detection component wiring in the container."""

    def test_container_creates_git_port_adapter(self) -> None:
        """Container creates a GitPortAdapter instance."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        # Execute
        container = create_application_container(ctx, snapshot_repo)

        # Verify
        assert isinstance(container.git_port, GitPortAdapter)

    def test_container_creates_git_service(self) -> None:
        """Container creates a GitService instance."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        # Execute
        container = create_application_container(ctx, snapshot_repo)

        # Verify
        assert isinstance(container.git_service, GitService)

    def test_container_creates_find_active_git_repository_action(self) -> None:
        """Container creates a FindActiveGitRepositoryAction instance."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        # Execute
        container = create_application_container(ctx, snapshot_repo)

        # Verify
        assert container.find_active_git_repository_action is not None
        assert hasattr(container.find_active_git_repository_action, "_freecad_port")
        assert hasattr(container.find_active_git_repository_action, "_git_service")

    def test_container_creates_application_state(self) -> None:
        """Container creates an ApplicationState instance."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        # Execute
        container = create_application_container(ctx, snapshot_repo)

        # Verify
        assert isinstance(container.application_state, ApplicationState)

    def test_application_state_initialized_with_none_git_repository(self) -> None:
        """ApplicationState is initialized with git_repository=None."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        # Execute
        container = create_application_container(ctx, snapshot_repo)

        # Verify
        assert container.application_state.git_repository is None

    def test_git_service_injected_with_git_port(self) -> None:
        """GitService receives the GitPort instance."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        # Execute
        container = create_application_container(ctx, snapshot_repo)

        # Verify - check that git_service has _git_port attribute
        assert hasattr(container.git_service, "_git_port")
        assert container.git_service._git_port is container.git_port

    def test_find_active_git_repository_action_injected_with_dependencies(self) -> None:
        """FindActiveGitRepositoryAction receives correct dependencies."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        # Execute
        container = create_application_container(ctx, snapshot_repo)

        # Verify
        action = container.find_active_git_repository_action
        assert action._freecad_port is container._freecad_port
        assert action._git_service is container.git_service

    def test_all_components_are_wired_together(self) -> None:
        """All git-related components are properly wired together."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        snapshot_repo = InMemorySnapshotRepository()

        # Execute
        container = create_application_container(ctx, snapshot_repo)

        # Verify the complete wiring chain:
        # GitPortAdapter -> GitService -> FindActiveGitRepositoryAction
        # Check that git_port has the required method (Protocol check without isinstance)
        assert hasattr(container.git_port, "find_top_level_git_path")
        assert container.git_service._git_port is container.git_port
        assert container.find_active_git_repository_action._git_service is container.git_service
        assert container.find_active_git_repository_action._freecad_port is container._freecad_port

        # Verify ApplicationState is created but not yet wired to any presenter
        # (Presenter wiring happens in Phase 1.9 during UI integration)
        assert isinstance(container.application_state, ApplicationState)
