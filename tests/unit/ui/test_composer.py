# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Verify UI composer wiring, registration, and constructed dependencies.

from unittest.mock import MagicMock, patch

import pytest
from freecad.history_wb.application.di.container import ApplicationContainer
from freecad.history_wb.ui.composer import compose_and_register_ui
from freecad.history_wb.ui.registry import ui_registry
from freecad.history_wb.ui.state import UIState


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset UI registry before each test to ensure clean state."""
    ui_registry.clear()
    yield
    ui_registry.clear()


def _mock_container() -> MagicMock:
    """Create a mock container with all required action attributes."""
    mock = MagicMock(spec=ApplicationContainer)
    mock.get_open_eligible_docs_action = MagicMock()
    mock.create_working_snapshot_action = MagicMock()
    mock.create_commit_snapshot_action = MagicMock()
    mock.create_diff_action = MagicMock()
    mock.create_document_diffs_action = MagicMock()
    mock.stage_documents_action = MagicMock()
    mock.get_dirty_documents_action = MagicMock()
    mock.open_visual_feature_diff_action = MagicMock()
    mock.get_staged_file_paths_action = MagicMock()
    mock.get_committed_file_paths_action = MagicMock()
    mock.find_active_git_repository_action = MagicMock()
    mock.get_commits_action = MagicMock()
    mock.settings_repo = MagicMock()
    return mock


def test_compose_creates_and_registers_ui_components() -> None:
    """compose_and_register_ui returns view, creates UIState(git_repository=None), registers both presenters, calls on_workbench_activated."""  # noqa: E501
    mock_container = _mock_container()

    with (
        patch("freecad.history_wb.ui.composer.DiffPanelView") as MockView,
        patch("freecad.history_wb.ui.composer.UIState") as MockUIState,
        patch("freecad.history_wb.ui.composer.DiffPresenter") as MockDiffPresenter,
        patch("freecad.history_wb.ui.composer.GitRepositoryPresenter") as MockGitPresenter,
    ):
        mock_view = MagicMock()
        MockView.return_value = mock_view

        mock_ui_state = MagicMock(spec=UIState)
        MockUIState.return_value = mock_ui_state

        mock_diff_presenter = MagicMock()
        MockDiffPresenter.return_value = mock_diff_presenter

        mock_git_presenter = MagicMock()
        MockGitPresenter.return_value = mock_git_presenter

        result = compose_and_register_ui(mock_container)

        # Returns the view
        assert result is mock_view

        # Creates UIState with git_repository=None
        MockUIState.assert_called_once_with(git_repository=None)

        # Both presenters created and registered
        assert MockDiffPresenter.call_count == 1
        assert MockGitPresenter.call_count == 1

        # GitRepositoryPresenter.on_workbench_activated called
        mock_git_presenter.on_workbench_activated.assert_called_once()


def test_compose_wires_action_dependencies_and_callbacks() -> None:
    """Action dependencies and set_node_selection_callback are wired correctly."""
    mock_container = _mock_container()

    with (
        patch("freecad.history_wb.ui.composer.DiffPanelView") as MockView,
        patch("freecad.history_wb.ui.composer.UIState"),
        patch("freecad.history_wb.ui.composer.DiffPresenter") as MockDiffPresenter,
        patch("freecad.history_wb.ui.composer.GitRepositoryPresenter") as MockGitPresenter,
    ):
        mock_view = MagicMock()
        MockView.return_value = mock_view

        mock_diff_presenter = MagicMock()
        MockDiffPresenter.return_value = mock_diff_presenter

        mock_git_presenter = MagicMock()
        MockGitPresenter.return_value = mock_git_presenter

        compose_and_register_ui(mock_container)

        # DiffPresenter receives correct actions from container
        diff_kwargs = MockDiffPresenter.call_args.kwargs
        assert diff_kwargs["get_eligible_docs_action"] is mock_container.get_open_eligible_docs_action
        assert diff_kwargs["create_document_diffs_action"] is mock_container.create_document_diffs_action
        assert diff_kwargs["stage_documents_action"] is mock_container.stage_documents_action
        assert diff_kwargs["get_dirty_documents_action"] is mock_container.get_dirty_documents_action
        assert diff_kwargs["open_visual_feature_diff_action"] is mock_container.open_visual_feature_diff_action

        # GitRepositoryPresenter receives correct actions from container
        git_kwargs = MockGitPresenter.call_args.kwargs
        assert git_kwargs["find_git_repo_action"] is mock_container.find_active_git_repository_action
        assert git_kwargs["get_commits_action"] is mock_container.get_commits_action

        # set_node_selection_callback wired to presenter
        mock_view.set_node_selection_callback.assert_called_once_with(mock_diff_presenter.on_node_selected)
        mock_view.set_visual_diff_callback.assert_called_once_with(mock_diff_presenter.on_visual_diff_clicked)
