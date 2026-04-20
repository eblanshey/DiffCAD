"""Tests for Phase 3: UI Composer.

These tests verify that the UI Composer correctly creates and wires all UI components.

Following TDD: these tests were written BEFORE implementation.
"""

from unittest.mock import MagicMock, patch

import pytest

from freecad.diff_wb.application.di.container import ApplicationContainer
from freecad.diff_wb.ui.composer import compose_and_register_ui
from freecad.diff_wb.ui.registry import ui_registry
from freecad.diff_wb.ui.state import UIState


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset UI registry before each test to ensure clean state."""
    ui_registry.clear()
    yield
    ui_registry.clear()


class TestComposeAndRegisterUiReturnsView:
    """Test that compose_and_register_ui returns a DiffPanelView."""

    def test_compose_returns_diff_panel_view_instance(self) -> None:
        """compose_and_register_ui should return a DiffPanelView instance."""
        from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView

        # Create mock container with all required attributes
        mock_container = MagicMock(spec=ApplicationContainer)
        mock_container.list_snapshots_action = MagicMock()
        mock_container.get_open_eligible_docs_action = MagicMock()
        mock_container.create_working_snapshot_action = MagicMock()
        mock_container.create_commit_snapshot_action = MagicMock()
        mock_container.create_diff_action = MagicMock()
        mock_container.stage_documents_action = MagicMock()
        mock_container.get_dirty_documents_action = MagicMock()
        mock_container.get_staged_file_paths_action = MagicMock()
        mock_container.get_committed_file_paths_action = MagicMock()
        mock_container.find_active_git_repository_action = MagicMock()
        mock_container.get_commits_action = MagicMock()

        # Mock the DiffPanelView to avoid PySide6 dependency in unit tests
        with patch("freecad.diff_wb.ui.composer.DiffPanelView") as MockView:
            mock_view = MagicMock(spec=DiffPanelView)
            mock_view.tree_widget = MagicMock()  # Need this for signal connection
            MockView.return_value = mock_view

            result = compose_and_register_ui(mock_container)

            assert result is mock_view
            assert isinstance(result, MagicMock)


class TestComposeCreatesUiState:
    """Test that compose_and_register_ui creates a UIState instance."""

    def test_compose_creates_ui_state(self) -> None:
        """compose_and_register_ui should create a UIState instance."""
        # Create mock container with all required attributes
        mock_container = MagicMock(spec=ApplicationContainer)
        mock_container.list_snapshots_action = MagicMock()
        mock_container.get_open_eligible_docs_action = MagicMock()
        mock_container.create_working_snapshot_action = MagicMock()
        mock_container.create_commit_snapshot_action = MagicMock()
        mock_container.create_diff_action = MagicMock()
        mock_container.stage_documents_action = MagicMock()
        mock_container.get_dirty_documents_action = MagicMock()
        mock_container.get_staged_file_paths_action = MagicMock()
        mock_container.get_committed_file_paths_action = MagicMock()
        mock_container.find_active_git_repository_action = MagicMock()
        mock_container.get_commits_action = MagicMock()

        with (
            patch("freecad.diff_wb.ui.composer.DiffPanelView"),
            patch("freecad.diff_wb.ui.composer.UIState") as MockUIState,
        ):
            mock_ui_state = MagicMock(spec=UIState)
            MockUIState.return_value = mock_ui_state

            compose_and_register_ui(mock_container)

            # Verify UIState was created with git_repository=None
            MockUIState.assert_called_once_with(git_repository=None)


class TestComposerRegistersSnapshotPresenter:
    """Test that snapshot presenter is registered after composition."""

    def _create_mock_container(self):
        """Helper to create a mock container with all required attributes."""
        mock_container = MagicMock(spec=ApplicationContainer)
        mock_container.list_snapshots_action = MagicMock()
        mock_container.get_open_eligible_docs_action = MagicMock()
        mock_container.create_working_snapshot_action = MagicMock()
        mock_container.create_commit_snapshot_action = MagicMock()
        mock_container.create_diff_action = MagicMock()
        mock_container.stage_documents_action = MagicMock()
        mock_container.get_dirty_documents_action = MagicMock()
        mock_container.get_staged_file_paths_action = MagicMock()
        mock_container.get_committed_file_paths_action = MagicMock()
        mock_container.get_committed_file_paths_action = MagicMock()
        mock_container.find_active_git_repository_action = MagicMock()
        mock_container.get_commits_action = MagicMock()
        return mock_container

    def test_snapshot_presenter_is_registered(self) -> None:
        """After composition, ui_registry.snapshot_presenter should be set."""
        mock_container = self._create_mock_container()

        with patch("freecad.diff_wb.ui.composer.DiffPanelView"), patch("freecad.diff_wb.ui.composer.SnapshotPresenter"):
            compose_and_register_ui(mock_container)

            # Verify snapshot presenter is registered (not None and not raising error)
            assert ui_registry._snapshot_presenter is not None

    def test_snapshot_presenter_receives_correct_dependencies(self) -> None:
        """SnapshotPresenter should receive view and list_snapshots_action."""
        mock_container = self._create_mock_container()
        mock_list_action = MagicMock()
        mock_container.list_snapshots_action = mock_list_action

        with (
            patch("freecad.diff_wb.ui.composer.DiffPanelView") as MockView,
            patch("freecad.diff_wb.ui.composer.SnapshotPresenter") as MockPresenter,
        ):
            mock_view = MagicMock()
            MockView.return_value = mock_view

            compose_and_register_ui(mock_container)

            # Verify SnapshotPresenter was called with correct arguments
            MockPresenter.assert_called_once()
            call_args = MockPresenter.call_args
            assert call_args.kwargs["view"] is mock_view
            assert call_args.kwargs["list_snapshots_action"] is mock_list_action


class TestComposerRegistersDiffPresenter:
    """Test that diff presenter is registered after composition."""

    def _create_mock_container(self):
        """Helper to create a mock container with all required attributes."""
        mock_container = MagicMock(spec=ApplicationContainer)
        mock_container.list_snapshots_action = MagicMock()
        mock_container.get_open_eligible_docs_action = MagicMock()
        mock_container.create_working_snapshot_action = MagicMock()
        mock_container.create_commit_snapshot_action = MagicMock()
        mock_container.create_diff_action = MagicMock()
        mock_container.stage_documents_action = MagicMock()
        mock_container.get_dirty_documents_action = MagicMock()
        mock_container.get_staged_file_paths_action = MagicMock()
        mock_container.get_committed_file_paths_action = MagicMock()
        mock_container.find_active_git_repository_action = MagicMock()
        mock_container.get_commits_action = MagicMock()
        return mock_container

    def test_diff_presenter_is_registered(self) -> None:
        """After composition, ui_registry.diff_presenter should be set."""
        mock_container = self._create_mock_container()

        with patch("freecad.diff_wb.ui.composer.DiffPanelView"), patch("freecad.diff_wb.ui.composer.DiffPresenter"):
            compose_and_register_ui(mock_container)

            # Verify diff presenter is registered
            assert ui_registry._diff_presenter is not None

    def test_diff_presenter_receives_ui_state(self) -> None:
        """DiffPresenter should receive ui_state reference."""
        mock_container = self._create_mock_container()

        with (
            patch("freecad.diff_wb.ui.composer.DiffPanelView"),
            patch("freecad.diff_wb.ui.composer.UIState") as MockUIState,
            patch("freecad.diff_wb.ui.composer.DiffPresenter") as MockPresenter,
        ):
            mock_ui_state = MagicMock(spec=UIState)
            MockUIState.return_value = mock_ui_state

            compose_and_register_ui(mock_container)

            # Verify DiffPresenter received ui_state
            MockPresenter.assert_called_once()
            assert MockPresenter.call_args.kwargs["ui_state"] is mock_ui_state

    def test_diff_presenter_receives_all_required_actions(self) -> None:
        """DiffPresenter should receive all required action dependencies."""
        mock_container = self._create_mock_container()

        with (
            patch("freecad.diff_wb.ui.composer.DiffPanelView"),
            patch("freecad.diff_wb.ui.composer.DiffPresenter") as MockPresenter,
        ):
            compose_and_register_ui(mock_container)

            call_args = MockPresenter.call_args
            assert "get_eligible_docs_action" in call_args.kwargs
            assert "create_working_snapshot_action" in call_args.kwargs
            assert "create_commit_snapshot_action" in call_args.kwargs
            assert "create_diff_action" in call_args.kwargs
            assert "stage_documents_action" in call_args.kwargs
            assert "get_dirty_documents_action" in call_args.kwargs
            assert "get_staged_file_paths_action" in call_args.kwargs
            assert "get_committed_file_paths_action" in call_args.kwargs


class TestComposerConnectsTreeWidgetCallback:
    """Test that tree widget signal is connected to diff_presenter.on_node_selected."""

    def _create_mock_container(self):
        """Helper to create a mock container with all required attributes."""
        mock_container = MagicMock(spec=ApplicationContainer)
        mock_container.list_snapshots_action = MagicMock()
        mock_container.get_open_eligible_docs_action = MagicMock()
        mock_container.create_working_snapshot_action = MagicMock()
        mock_container.create_commit_snapshot_action = MagicMock()
        mock_container.create_diff_action = MagicMock()
        mock_container.stage_documents_action = MagicMock()
        mock_container.get_dirty_documents_action = MagicMock()
        mock_container.get_staged_file_paths_action = MagicMock()
        mock_container.get_committed_file_paths_action = MagicMock()
        mock_container.find_active_git_repository_action = MagicMock()
        mock_container.get_commits_action = MagicMock()
        return mock_container

    def test_set_node_selection_callback_is_called(self) -> None:
        """set_node_selection_callback should be called with presenter's on_node_selected method."""
        mock_container = self._create_mock_container()

        with (
            patch("freecad.diff_wb.ui.composer.DiffPanelView") as MockView,
            patch("freecad.diff_wb.ui.composer.DiffPresenter") as MockPresenter,
        ):
            mock_view = MagicMock()
            MockView.return_value = mock_view
            mock_presenter = MagicMock()
            MockPresenter.return_value = mock_presenter

            compose_and_register_ui(mock_container)

            # Verify set_node_selection_callback was called with on_node_selected
            mock_view.set_node_selection_callback.assert_called_once_with(mock_presenter.on_node_selected)

    def test_callback_invokes_on_node_selected_with_git_path_and_node_path(self) -> None:
        """Callback should invoke on_node_selected with both git_path and node_path."""

        mock_container = self._create_mock_container()

        with (
            patch("freecad.diff_wb.ui.composer.DiffPanelView") as MockView,
            patch("freecad.diff_wb.ui.composer.DiffPresenter") as MockPresenter,
        ):
            mock_view = MagicMock()
            MockView.return_value = mock_view
            mock_presenter = MagicMock()
            MockPresenter.return_value = mock_presenter

            compose_and_register_ui(mock_container)

            # Get the callback that was registered
            callback = mock_view.set_node_selection_callback.call_args[0][0]

            # Simulate calling the callback directly with both parameters
            callback("test_git_path", "test_node_path")

            # Verify on_node_selected was called with both arguments
            mock_presenter.on_node_selected.assert_called_once_with("test_git_path", "test_node_path")


class TestComposerInitializesGitRepositoryPresenter:
    """Test that git repository presenter is initialized."""

    def _create_mock_container(self):
        """Helper to create a mock container with all required attributes."""
        mock_container = MagicMock(spec=ApplicationContainer)
        mock_container.list_snapshots_action = MagicMock()
        mock_container.get_open_eligible_docs_action = MagicMock()
        mock_container.create_working_snapshot_action = MagicMock()
        mock_container.create_commit_snapshot_action = MagicMock()
        mock_container.create_diff_action = MagicMock()
        mock_container.stage_documents_action = MagicMock()
        mock_container.get_dirty_documents_action = MagicMock()
        mock_container.get_staged_file_paths_action = MagicMock()
        mock_container.get_committed_file_paths_action = MagicMock()
        mock_container.find_active_git_repository_action = MagicMock()
        mock_container.get_commits_action = MagicMock()
        return mock_container

    def test_git_repository_presenter_is_created(self) -> None:
        """GitRepositoryPresenter should be instantiated during composition."""
        mock_container = self._create_mock_container()

        with (
            patch("freecad.diff_wb.ui.composer.DiffPanelView"),
            patch("freecad.diff_wb.ui.composer.GitRepositoryPresenter") as MockPresenter,
        ):
            compose_and_register_ui(mock_container)

            # Verify GitRepositoryPresenter was created
            MockPresenter.assert_called_once()

    def test_git_repository_presenter_receives_ui_state(self) -> None:
        """GitRepositoryPresenter should receive ui_state reference."""
        mock_container = self._create_mock_container()

        with (
            patch("freecad.diff_wb.ui.composer.DiffPanelView"),
            patch("freecad.diff_wb.ui.composer.UIState") as MockUIState,
            patch("freecad.diff_wb.ui.composer.GitRepositoryPresenter") as MockPresenter,
        ):
            mock_ui_state = MagicMock(spec=UIState)
            MockUIState.return_value = mock_ui_state

            compose_and_register_ui(mock_container)

            # Verify GitRepositoryPresenter received ui_state
            MockPresenter.assert_called_once()
            assert MockPresenter.call_args.kwargs["ui_state"] is mock_ui_state

    def test_git_repository_presenter_receives_required_actions(self) -> None:
        """GitRepositoryPresenter should receive find_git_repo_action and get_commits_action."""
        mock_container = self._create_mock_container()

        with (
            patch("freecad.diff_wb.ui.composer.DiffPanelView"),
            patch("freecad.diff_wb.ui.composer.GitRepositoryPresenter") as MockPresenter,
        ):
            compose_and_register_ui(mock_container)

            call_args = MockPresenter.call_args
            assert "find_git_repo_action" in call_args.kwargs
            assert "get_commits_action" in call_args.kwargs

    def test_git_repository_presenter_on_workbench_activated_is_called(self) -> None:
        """GitRepositoryPresenter.on_workbench_activated() should be called after creation."""
        mock_container = self._create_mock_container()

        with (
            patch("freecad.diff_wb.ui.composer.DiffPanelView"),
            patch("freecad.diff_wb.ui.composer.GitRepositoryPresenter") as MockPresenter,
        ):
            mock_presenter_instance = MagicMock()
            MockPresenter.return_value = mock_presenter_instance

            compose_and_register_ui(mock_container)

            # Verify on_workbench_activated was called after construction
            mock_presenter_instance.on_workbench_activated.assert_called_once()


class TestComposerWiresAllDependencies:
    """Test that all presenters receive correct dependencies from container."""

    def _create_mock_container(self):
        """Helper to create a mock container with all required attributes."""
        mock_container = MagicMock(spec=ApplicationContainer)
        mock_container.list_snapshots_action = MagicMock()
        mock_container.get_open_eligible_docs_action = MagicMock()
        mock_container.create_working_snapshot_action = MagicMock()
        mock_container.create_commit_snapshot_action = MagicMock()
        mock_container.create_diff_action = MagicMock()
        mock_container.stage_documents_action = MagicMock()
        mock_container.get_dirty_documents_action = MagicMock()
        mock_container.get_staged_file_paths_action = MagicMock()
        mock_container.get_committed_file_paths_action = MagicMock()
        mock_container.find_active_git_repository_action = MagicMock()
        mock_container.get_commits_action = MagicMock()
        return mock_container

    def test_all_actions_passed_from_container_to_presenters(self) -> None:
        """All container actions should be passed to appropriate presenters."""
        mock_container = self._create_mock_container()

        with (
            patch("freecad.diff_wb.ui.composer.DiffPanelView"),
            patch("freecad.diff_wb.ui.composer.SnapshotPresenter") as MockSnapshotPresenter,
            patch("freecad.diff_wb.ui.composer.DiffPresenter") as MockDiffPresenter,
            patch("freecad.diff_wb.ui.composer.GitRepositoryPresenter") as MockGitPresenter,
        ):
            compose_and_register_ui(mock_container)

            # SnapshotPresenter gets list_snapshots_action
            assert (
                MockSnapshotPresenter.call_args.kwargs["list_snapshots_action"] == mock_container.list_snapshots_action
            )

            # DiffPresenter gets its actions
            assert (
                MockDiffPresenter.call_args.kwargs["get_eligible_docs_action"]
                == mock_container.get_open_eligible_docs_action
            )
            assert (
                MockDiffPresenter.call_args.kwargs["create_working_snapshot_action"]
                == mock_container.create_working_snapshot_action
            )
            assert (
                MockDiffPresenter.call_args.kwargs["create_commit_snapshot_action"]
                == mock_container.create_commit_snapshot_action
            )
            assert MockDiffPresenter.call_args.kwargs["create_diff_action"] == mock_container.create_diff_action
            assert MockDiffPresenter.call_args.kwargs["stage_documents_action"] == mock_container.stage_documents_action
            assert (
                MockDiffPresenter.call_args.kwargs["get_dirty_documents_action"]
                == mock_container.get_dirty_documents_action
            )
            assert (
                MockDiffPresenter.call_args.kwargs["get_staged_file_paths_action"]
                == mock_container.get_staged_file_paths_action
            )
            assert (
                MockDiffPresenter.call_args.kwargs["get_committed_file_paths_action"]
                == mock_container.get_committed_file_paths_action
            )

            # GitRepositoryPresenter gets its actions
            assert (
                MockGitPresenter.call_args.kwargs["find_git_repo_action"]
                == mock_container.find_active_git_repository_action
            )
            assert MockGitPresenter.call_args.kwargs["get_commits_action"] == mock_container.get_commits_action
