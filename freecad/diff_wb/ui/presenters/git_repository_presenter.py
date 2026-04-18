# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Presents git repository information and manages commit loading in the UI.
"""Git repository presenter for UI layer."""

from freecad.diff_wb.application.actions.find_active_git_repository import (
    FindActiveGitRepositoryAction,
)
from freecad.diff_wb.application.actions.get_commits import GetCommitsAction
from freecad.diff_wb.domain.git.models import GitRepository
from freecad.diff_wb.ui.state import UIState
from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView
from freecad.diff_wb.utils import Log


class GitRepositoryPresenter:
    """Handles git repository detection and UI display.

    This presenter is responsible for:
    1. Detecting the active git repository when the workbench is activated
    2. Updating the UI state with the detected repository
    3. Displaying the repository information in the view
    4. Loading and displaying commits for the repository

    Attributes:
        _view: The DiffPanelView instance for displaying repository info.
        _find_git_repo_action: The action for finding the active git repository.
        _get_commits_action: The action for getting git commits.
        _ui_state: The UI state holder for storing repository.
    """

    def __init__(
        self,
        view: DiffPanelView,
        find_git_repo_action: FindActiveGitRepositoryAction,
        get_commits_action: GetCommitsAction,
        ui_state: UIState,
    ) -> None:
        """Initialize the presenter with required dependencies.

        Args:
            view: The DiffPanelView instance for displaying repository info.
            find_git_repo_action: The action for finding the active git repository.
            get_commits_action: The action for getting git commits.
            ui_state: The UI state holder for storing repository.
        """
        self._view = view
        self._find_git_repo_action = find_git_repo_action
        self._get_commits_action = get_commits_action
        self._ui_state = ui_state
        self._view.set_refresh_callback(self.on_refresh_clicked)

    def on_workbench_activated(self) -> None:
        """Detect and display git repository when workbench activates.

        This method is called when the workbench is activated to detect
        the current git repository and display it in the UI.
        """
        self._detect_git_repository()

    def on_refresh_clicked(self) -> None:
        """Re-detect and display git repository when refresh is clicked."""
        self._detect_git_repository()

    def _detect_git_repository(self) -> None:
        """Detect git repository and update UI and application state.

        This protected method encapsulates the common logic for git repository
        detection used by both workbench activation and refresh button clicks.
        """
        result = self._find_git_repo_action.execute()

        if result.is_success:
            repo = result.data
            self._ui_state.git_repository = repo
            self._view.show_repository(repo)

            # After detecting repository, load commits
            if repo is not None:
                self._load_commits(repo)
        else:
            self._ui_state.git_repository = None
            self._view.show_repository(None)
            Log.warning(f"Git detection failed: {result.message}")

    def _load_commits(self, repo: GitRepository) -> None:
        """Load and display commits for the repository.

        Args:
            repo: The GitRepository to load commits from.
        """
        result = self._get_commits_action.execute(repo)

        if result.is_success:
            commits = result.data
            # Clear diff displays before reloading commits to prevent stale data
            # from previous selections remaining visible
            self._view.show_diff_trees([])
            self._view.show_properties([])
            self._view.show_commits(commits)
        else:
            # Clear diff displays even on failure
            self._view.show_diff_trees([])
            self._view.show_properties([])
            # Show empty list on failure
            self._view.show_commits([])
            Log.warning(f"Failed to load commits: {result.message}")
