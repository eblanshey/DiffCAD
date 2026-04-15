# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GitRepositoryPresenter.
# These tests verify that the presenter correctly orchestrates git repository
# detection and updates both the application state and the view.
"""Unit tests for GitRepositoryPresenter."""

from unittest.mock import MagicMock

import pytest

from freecad.diff_wb.domain.git.models import GitRepository
from freecad.diff_wb.ui.presenters.git_repository_presenter import GitRepositoryPresenter


@pytest.fixture
def mock_view():
    """Create a mock DiffPanelView."""
    return MagicMock()


@pytest.fixture
def mock_find_action():
    """Create a mock FindActiveGitRepositoryAction."""
    return MagicMock()


@pytest.fixture
def mock_application_state():
    """Create a mock ApplicationState."""
    return MagicMock()


@pytest.fixture
def presenter(mock_view, mock_find_action, mock_application_state):
    """Create a GitRepositoryPresenter instance with mocked dependencies."""
    return GitRepositoryPresenter(
        view=mock_view,
        find_git_repo_action=mock_find_action,
        application_state=mock_application_state,
    )


class TestGitRepositoryPresenter:
    """Tests for GitRepositoryPresenter."""

    def test_on_workbench_activated_with_successful_detection(
        self,
        presenter,
        mock_view,
        mock_find_action,
        mock_application_state,
    ):
        """on_workbench_activated() updates state and view when detection succeeds."""
        # Arrange
        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.data = repo
        mock_find_action.execute.return_value = mock_result

        # Act
        presenter.on_workbench_activated()

        # Assert
        mock_find_action.execute.assert_called_once()
        mock_application_state.git_repository = repo
        mock_view.show_repository.assert_called_once_with(repo)

    def test_on_workbench_activated_with_failed_detection(
        self,
        presenter,
        mock_view,
        mock_find_action,
        mock_application_state,
    ):
        """on_workbench_activated() sets state to None and shows no repo message on failure."""
        # Arrange
        mock_result = MagicMock()
        mock_result.is_success = False
        mock_result.message = "No active document"
        mock_find_action.execute.return_value = mock_result

        # Act
        presenter.on_workbench_activated()

        # Assert
        mock_find_action.execute.assert_called_once()
        mock_application_state.git_repository = None
        mock_view.show_repository.assert_called_once_with(None)

    def test_on_workbench_activated_with_none_repository(
        self,
        presenter,
        mock_view,
        mock_find_action,
        mock_application_state,
    ):
        """on_workbench_activated() handles case where action returns None repository."""
        # Arrange
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.data = None  # Action succeeded but found no repo
        mock_find_action.execute.return_value = mock_result

        # Act
        presenter.on_workbench_activated()

        # Assert
        mock_find_action.execute.assert_called_once()
        mock_application_state.git_repository = None
        mock_view.show_repository.assert_called_once_with(None)

    def test_presenter_initialization_stores_dependencies(
        self,
        mock_view,
        mock_find_action,
        mock_application_state,
    ):
        """Presenter stores all dependencies correctly on initialization."""
        # Act
        presenter = GitRepositoryPresenter(
            view=mock_view,
            find_git_repo_action=mock_find_action,
            application_state=mock_application_state,
        )

        # Assert
        assert presenter._view is mock_view
        assert presenter._find_git_repo_action is mock_find_action
        assert presenter._application_state is mock_application_state
