"""File responsibility: Unit tests for CommitStagingAction."""

from freecad.history_wb.application.actions.commit_staging import CommitStagingAction
from freecad.history_wb.domain.git.git_service import GitService
from freecad.history_wb.domain.git.models import GitRepository

from tests.fakes import FakeGitPort


def _build_action(git_port: FakeGitPort) -> CommitStagingAction:
    """Build a CommitStagingAction with a GitService backed by the given FakeGitPort.

    Args:
        git_port: The fake git port to use for git operations.

    Returns:
        A fully wired CommitStagingAction instance.
    """
    return CommitStagingAction(git_service=GitService(git_port=git_port))


class TestCommitStagingAction:
    """Test suite for CommitStagingAction."""

    def test_execute_success_commits(self) -> None:
        """Happy path: commits staged changes, returns success."""
        # Arrange
        git_port = FakeGitPort()
        git_port.add_git_repo("/home/user/project")
        action = _build_action(git_port)
        repo = GitRepository(name="project", absolute_path="/home/user/project")

        # Act
        result = action.execute(repo, message="Add new feature")

        # Assert
        assert result.is_success is True
        assert result.data is True
        assert result.message is None

    def test_execute_failure_returns_error(self) -> None:
        """Error: commit fails, returns failure result."""
        # Arrange
        git_port = FakeGitPort(fail_commit=True)
        git_port.add_git_repo("/home/user/project")
        action = _build_action(git_port)
        repo = GitRepository(name="project", absolute_path="/home/user/project")

        # Act
        result = action.execute(repo, message="Add new feature")

        # Assert
        assert result.is_success is False
        assert result.data is None
        assert result.message == "Git commit failed"

    def test_execute_passes_correct_repo_path(self) -> None:
        """Verifies git_service.commit is called with correct repo path."""
        # Arrange
        git_port = FakeGitPort()
        git_port.add_git_repo("/home/user/my_repo")
        action = _build_action(git_port)
        repo = GitRepository(name="my_repo", absolute_path="/home/user/my_repo")

        # Act
        action.execute(repo, message="Fix bug")

        # Assert
        assert git_port._last_commit_call is not None
        git_root, message = git_port._last_commit_call
        assert git_root == "/home/user/my_repo"
        assert message == "Fix bug"

    def test_execute_multiple_commits(self) -> None:
        """Tests creating multiple commits sequentially with different messages."""
        # Arrange
        git_port = FakeGitPort()
        git_port.add_git_repo("/home/user/project")
        action = _build_action(git_port)
        repo = GitRepository(name="project", absolute_path="/home/user/project")

        # Act
        result1 = action.execute(repo, message="First commit")
        result2 = action.execute(repo, message="Second commit")

        # Assert
        assert result1.is_success is True
        assert result2.is_success is True
        # Verify both commits were recorded with their respective messages
        assert git_port._last_commit_call is not None
        assert git_port._last_commit_call[0] == "/home/user/project"
        assert git_port._last_commit_call[1] == "Second commit"

    def test_execute_empty_message_succeeds(self) -> None:
        """Empty message is passed through (validation is in command layer)."""
        # Arrange
        git_port = FakeGitPort()
        git_port.add_git_repo("/home/user/project")
        action = _build_action(git_port)
        repo = GitRepository(name="project", absolute_path="/home/user/project")

        # Act
        result = action.execute(repo, message="")

        # Assert
        assert result.is_success is True
        # The empty message was passed through to git_port
        assert git_port._last_commit_call is not None
        assert git_port._last_commit_call[1] == ""
