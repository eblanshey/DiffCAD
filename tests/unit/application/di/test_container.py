"""File responsibility: Tests for dependency injection container.

These tests verify that the DI container correctly wires all application
layer dependencies together, including git repository detection components.
"""

from freecad.diff_wb.application.actions.get_commits import GetCommitsAction
from freecad.diff_wb.application.di.container import (
    ApplicationContainer,
    create_application_container,
)
from freecad.diff_wb.domain.freecad_ports import FreeCadContext
from freecad.diff_wb.domain.git.git_service import GitService
from freecad.diff_wb.infrastructure.git.git_port_adapter import GitPortAdapter


class TestApplicationContainer:
    """Tests for the ApplicationContainer dataclass."""

    def test_container_creates_all_actions(self) -> None:
        """All actions are instantiated by the container."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore

        # Execute
        container = create_application_container(ctx)

        # Verify
        assert container.take_snapshot_action is not None
        assert container.compare_snapshots_action is not None
        assert container.list_snapshots_action is not None
        assert container.open_all_documents_in_repository_action is not None

    def test_container_wires_dependencies_correctly(self) -> None:
        """Actions have correct dependencies injected."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore

        # Execute
        container = create_application_container(ctx)

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

    def test_container_returns_application_container_instance(self) -> None:
        """Container returns an ApplicationContainer instance."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore

        # Execute
        container = create_application_container(ctx)

        # Verify
        assert isinstance(container, ApplicationContainer)


class TestGitRepositoryDetectionWiring:
    """Tests for git repository detection component wiring in the container."""

    def test_container_creates_git_port_adapter(self) -> None:
        """Container creates a GitPortAdapter instance."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore

        # Execute
        container = create_application_container(ctx)

        # Verify
        assert isinstance(container.git_port, GitPortAdapter)

    def test_container_creates_git_service(self) -> None:
        """Container creates a GitService instance."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        # Execute
        container = create_application_container(ctx)

        # Verify
        assert isinstance(container.git_service, GitService)

    def test_container_creates_find_active_git_repository_action(self) -> None:
        """Container creates a FindActiveGitRepositoryAction instance."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        # Execute
        container = create_application_container(ctx)

        # Verify
        assert container.find_active_git_repository_action is not None
        assert hasattr(container.find_active_git_repository_action, "_freecad_port")
        assert hasattr(container.find_active_git_repository_action, "_git_service")

    def test_git_service_injected_with_git_port(self) -> None:
        """GitService receives the GitPort instance."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        # Execute
        container = create_application_container(ctx)

        # Verify - check that git_service has _git_port attribute
        assert hasattr(container.git_service, "_git_port")
        assert container.git_service._git_port is container.git_port

    def test_find_active_git_repository_action_injected_with_dependencies(self) -> None:
        """FindActiveGitRepositoryAction receives correct dependencies."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        # Execute
        container = create_application_container(ctx)

        # Verify
        action = container.find_active_git_repository_action
        assert action._freecad_port is container._freecad_port
        assert action._git_service is container.git_service

    def test_all_components_are_wired_together(self) -> None:
        """All git-related components are properly wired together."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        # Execute
        container = create_application_container(ctx)

        # Verify the complete wiring chain:
        # GitPortAdapter -> GitService -> FindActiveGitRepositoryAction
        # Check that git_port has the required method (Protocol check without isinstance)
        assert hasattr(container.git_port, "find_top_level_git_path")
        assert container.git_service._git_port is container.git_port
        assert container.find_active_git_repository_action._git_service is container.git_service
        assert container.find_active_git_repository_action._freecad_port is container._freecad_port


class TestGetCommitsActionWiring:
    """Tests for GetCommitsAction wiring in the container."""

    def test_container_has_get_commits_action_attribute(self) -> None:
        """Container has get_commits_action attribute."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        # Execute
        container = create_application_container(ctx)

        # Verify
        assert hasattr(container, "get_commits_action")
        assert container.get_commits_action is not None

    def test_get_commits_action_is_properly_initialized_with_git_service(self) -> None:
        """GetCommitsAction is properly initialized with git_service."""
        # Setup
        ctx = FreeCadContext(app=None)  # type: ignore
        # Execute
        container = create_application_container(ctx)

        # Verify
        action = container.get_commits_action
        assert isinstance(action, GetCommitsAction)
        assert hasattr(action, "_git_service")
        assert action._git_service is container.git_service

    def test_get_commits_action_can_retrieve_commits_through_container(self) -> None:
        """GetCommitsAction can retrieve commits through the container."""
        # Setup - configure fake git port via git service's port
        ctx = FreeCadContext(app=None)  # type: ignore
        # Execute
        container = create_application_container(ctx)

        # Verify - call execute with a valid repo to verify action is wired correctly
        # The fake git port returns empty commits for any path
        from freecad.diff_wb.domain.git.models import GitRepository

        repo = GitRepository(name="test_project", absolute_path="/tmp/test_project")
        result = container.get_commits_action.execute(repo=repo)

        # Verify the action executed and returned success (empty list from fake)
        assert result is not None
        assert result.is_success is True
        assert result.data == []
