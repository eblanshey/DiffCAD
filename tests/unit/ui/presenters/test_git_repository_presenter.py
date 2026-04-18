# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GitRepositoryPresenter.
# These tests verify that the presenter correctly orchestrates git repository
# detection and updates both the application state and the view.
"""Unit tests for GitRepositoryPresenter."""

from unittest.mock import MagicMock

import pytest

from freecad.diff_wb.domain.git.models import GitCommit, GitRepository
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
def mock_get_commits_action():
    """Create a mock GetCommitsAction."""
    return MagicMock()


@pytest.fixture
def mock_ui_state():
    """Create a mock UIState."""
    return MagicMock()


@pytest.fixture
def presenter(mock_view, mock_find_action, mock_get_commits_action, mock_ui_state):
    """Create a GitRepositoryPresenter instance with mocked dependencies."""
    return GitRepositoryPresenter(
        view=mock_view,
        find_git_repo_action=mock_find_action,
        get_commits_action=mock_get_commits_action,
        ui_state=mock_ui_state,
    )


class TestGitRepositoryPresenter:
    """Tests for GitRepositoryPresenter."""

    def test_on_workbench_activated_with_successful_detection(
        self,
        presenter,
        mock_view,
        mock_find_action,
        mock_ui_state,
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
        mock_ui_state.git_repository = repo
        mock_view.show_repository.assert_called_once_with(repo)

    def test_on_workbench_activated_with_failed_detection(
        self,
        presenter,
        mock_view,
        mock_find_action,
        mock_ui_state,
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
        mock_ui_state.git_repository = None
        mock_view.show_repository.assert_called_once_with(None)

    def test_on_workbench_activated_with_none_repository(
        self,
        presenter,
        mock_view,
        mock_find_action,
        mock_ui_state,
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
        mock_ui_state.git_repository = None
        mock_view.show_repository.assert_called_once_with(None)

    def test_presenter_initialization_stores_dependencies(
        self,
        mock_view,
        mock_find_action,
        mock_get_commits_action,
        mock_ui_state,
    ):
        """Presenter stores all dependencies correctly on initialization."""
        # Act
        presenter = GitRepositoryPresenter(
            view=mock_view,
            find_git_repo_action=mock_find_action,
            get_commits_action=mock_get_commits_action,
            ui_state=mock_ui_state,
        )

        # Assert
        assert presenter._view is mock_view
        assert presenter._find_git_repo_action is mock_find_action
        assert presenter._get_commits_action is mock_get_commits_action
        assert presenter._ui_state is mock_ui_state

    def test_on_refresh_clicked_with_successful_detection(
        self,
        presenter,
        mock_view,
        mock_find_action,
        mock_ui_state,
    ):
        """on_refresh_clicked() updates state and view when detection succeeds."""
        # Arrange
        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.data = repo
        mock_find_action.execute.return_value = mock_result

        # Act
        presenter.on_refresh_clicked()

        # Assert
        mock_find_action.execute.assert_called_once()
        mock_ui_state.git_repository = repo
        mock_view.show_repository.assert_called_once_with(repo)

    def test_on_refresh_clicked_with_failed_detection(
        self,
        presenter,
        mock_view,
        mock_find_action,
        mock_ui_state,
    ):
        """on_refresh_clicked() sets state to None and shows no repo message on failure."""
        # Arrange
        mock_result = MagicMock()
        mock_result.is_success = False
        mock_result.message = "No active document"
        mock_find_action.execute.return_value = mock_result

        # Act
        presenter.on_refresh_clicked()

        # Assert
        mock_find_action.execute.assert_called_once()
        mock_ui_state.git_repository = None
        mock_view.show_repository.assert_called_once_with(None)

    def test_on_refresh_clicked_with_none_repository(
        self,
        presenter,
        mock_view,
        mock_find_action,
        mock_ui_state,
    ):
        """on_refresh_clicked() handles case where action returns None repository."""
        # Arrange
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.data = None  # Action succeeded but found no repo
        mock_find_action.execute.return_value = mock_result

        # Act
        presenter.on_refresh_clicked()

        # Assert
        mock_find_action.execute.assert_called_once()
        mock_ui_state.git_repository = None
        mock_view.show_repository.assert_called_once_with(None)

    def test_presenter_initialization_registers_refresh_callback(
        self,
        mock_view,
        mock_find_action,
        mock_get_commits_action,
        mock_ui_state,
    ):
        """Presenter registers its on_refresh_clicked method as the refresh callback on initialization."""
        # Act
        presenter = GitRepositoryPresenter(
            view=mock_view,
            find_git_repo_action=mock_find_action,
            get_commits_action=mock_get_commits_action,
            ui_state=mock_ui_state,
        )

        # Assert
        mock_view.set_refresh_callback.assert_called_once_with(presenter.on_refresh_clicked)


class TestCommitLoading:
    """Tests for GitRepositoryPresenter commit loading functionality."""

    def test_load_commits_calls_show_commits_on_success(
        self,
        presenter,
        mock_view,
        mock_get_commits_action,
    ):
        """_load_commits() calls show_commits with commits on success."""
        # Arrange
        commits = [
            GitCommit(
                id="a1b2c3d4e5f67890",
                message="Test commit",
                author="Test Author",
                timestamp="2024-01-15T10:30:00+00:00",
            ),
        ]
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.data = commits
        mock_get_commits_action.execute.return_value = mock_result

        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")

        # Act
        presenter._load_commits(repo)

        # Assert
        mock_get_commits_action.execute.assert_called_once_with(repo)
        mock_view.show_commits.assert_called_once_with(commits)

    def test_load_commits_shows_empty_list_on_failure(
        self,
        presenter,
        mock_view,
        mock_get_commits_action,
    ):
        """_load_commits() shows empty list when action fails."""
        # Arrange
        mock_result = MagicMock()
        mock_result.is_success = False
        mock_result.message = "Git error"
        mock_get_commits_action.execute.return_value = mock_result

        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")

        # Act
        presenter._load_commits(repo)

        # Assert
        mock_view.show_commits.assert_called_once_with([])

    def test_detect_git_repository_loads_commits_on_success(
        self,
        presenter,
        mock_view,
        mock_find_action,
        mock_get_commits_action,
        mock_ui_state,
    ):
        """_detect_git_repository() loads commits after detecting repository."""
        # Arrange
        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")

        # Mock find action to return repo
        mock_find_result = MagicMock()
        mock_find_result.is_success = True
        mock_find_result.data = repo
        mock_find_action.execute.return_value = mock_find_result

        # Mock get commits action to return commits
        commits = [GitCommit(id="a1b2c3d", message="Test", author="Test", timestamp="2024-01-15T10:30:00+00:00")]
        mock_commit_result = MagicMock()
        mock_commit_result.is_success = True
        mock_commit_result.data = commits
        mock_get_commits_action.execute.return_value = mock_commit_result

        # Act
        presenter._detect_git_repository()

        # Assert
        mock_get_commits_action.execute.assert_called_once_with(repo)
        mock_view.show_commits.assert_called_once()
