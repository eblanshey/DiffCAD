# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for UIState (formerly ApplicationState).
# These tests verify that the UIState dataclass correctly manages
# the git repository state, including default values, setting values, and
# modifying the git_repository after creation.
"""Unit tests for UIState."""

from freecad.diff_wb.domain.git.models import GitRepository
from freecad.diff_wb.ui.state import UIState


class TestUIState:
    """Tests for UIState dataclass."""

    def test_create_with_default_values(self) -> None:
        """Creating state with no arguments sets git_repository to None."""
        # Act
        state = UIState()

        # Assert
        assert state.git_repository is None

    def test_create_with_git_repository(self) -> None:
        """Creating state with a git repository stores it correctly."""
        # Arrange
        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")

        # Act
        state = UIState(git_repository=repo)

        # Assert
        assert state.git_repository is not None
        assert state.git_repository.name == "test_project"
        assert state.git_repository.absolute_path == "/home/user/test_project"

    def test_modify_git_repository_after_creation(self) -> None:
        """git_repository can be modified after state creation."""
        # Arrange
        state = UIState()
        new_repo = GitRepository(name="new_project", absolute_path="/home/user/new_project")

        # Act
        state.git_repository = new_repo

        # Assert
        assert state.git_repository is not None
        assert state.git_repository.name == "new_project"
        assert state.git_repository.absolute_path == "/home/user/new_project"

    def test_set_git_repository_to_none(self) -> None:
        """git_repository can be set to None after being set."""
        # Arrange
        repo = GitRepository(name="temp_project", absolute_path="/tmp/temp_project")
        state = UIState(git_repository=repo)

        # Act
        state.git_repository = None

        # Assert
        assert state.git_repository is None

    def test_git_repository_is_mutable(self) -> None:
        """The git_repository field is mutable (unlike GitRepository itself)."""
        # Arrange
        state = UIState()
        repo1 = GitRepository(name="first", absolute_path="/path/first")
        repo2 = GitRepository(name="second", absolute_path="/path/second")

        # Act
        state.git_repository = repo1
        first_value = state.git_repository
        state.git_repository = repo2

        # Assert
        assert first_value is repo1
        assert state.git_repository is repo2

    def test_can_store_different_repositories_successively(self) -> None:
        """State can hold different repositories over time."""
        # Arrange
        state = UIState()
        repos = [GitRepository(name=f"project_{i}", absolute_path=f"/projects/project_{i}") for i in range(3)]

        # Act & Assert - set and verify each repository
        for expected_repo in repos:
            state.git_repository = expected_repo
            assert state.git_repository is not None
            assert state.git_repository.name == expected_repo.name
            assert state.git_repository.absolute_path == expected_repo.absolute_path

    def test_preserves_repository_properties(self) -> None:
        """Repository properties are preserved when stored in state."""
        # Arrange
        repo = GitRepository(name="my_awesome_project", absolute_path="/home/dev/my_awesome_project")

        # Act
        state = UIState(git_repository=repo)

        # Assert
        assert state.git_repository is not None
        assert state.git_repository.name == "my_awesome_project"
        assert state.git_repository.absolute_path == "/home/dev/my_awesome_project"
