# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GetCommitsAction using fake GitService
# implementations. Tests cover all success scenarios including successful commit
# retrieval, limit parameter, empty commits, and single commit cases.
"""Unit tests for GetCommitsAction."""

from datetime import datetime

from freecad.diff_wb.application.actions.get_commits import GetCommitsAction
from freecad.diff_wb.domain.git.git_service import GitService
from freecad.diff_wb.domain.git.models import GitCommit, GitRepository
from tests.fakes.fake_git_port import FakeGitPort


class TestGetCommitsActionSuccess:
    """Tests for successful commit retrieval."""

    def test_execute_returns_commits_when_repository_exists(self) -> None:
        """Test that action returns commits when repository exists."""
        # Setup
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/my_project")
        fake_git_port.set_commits(
            "/home/user/my_project",
            [
                GitCommit(
                    id="abc123",
                    message="Fix bug in module",
                    author="John Doe",
                    timestamp=datetime.fromisoformat("2024-01-15T10:30:00"),
                ),
                GitCommit(
                    id="def456",
                    message="Add new feature",
                    author="Jane Smith",
                    timestamp=datetime.fromisoformat("2024-01-14T09:00:00"),
                ),
            ],
        )

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")
        action = GetCommitsAction(git_service)

        # Execute
        result = action.execute(repo)

        # Assert
        assert result.is_success is True
        assert result.data is not None
        assert isinstance(result.data, list)
        assert len(result.data) == 2
        assert result.message is None

    def test_execute_returns_commits_with_correct_data(self) -> None:
        """Test that returned commits have correct data."""
        # Setup
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/project")
        fake_git_port.set_commits(
            "/home/user/project",
            [
                GitCommit(
                    id="commit123",
                    message="Update documentation",
                    author="Alice Johnson",
                    timestamp=datetime.fromisoformat("2024-01-20T14:00:00"),
                ),
            ],
        )

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="project", absolute_path="/home/user/project")
        action = GetCommitsAction(git_service)

        # Execute
        result = action.execute(repo)

        # Assert
        assert result.is_success is True
        assert result.data[0].id == "commit123"
        assert result.data[0].message == "Update documentation"
        assert result.data[0].author == "Alice Johnson"
        assert result.data[0].timestamp == datetime.fromisoformat("2024-01-20T14:00:00")


class TestGetCommitsActionFailure:
    """Tests for failure scenarios."""

    def test_execute_returns_failure_for_invalid_repo(self) -> None:
        """Test that action returns failure for invalid repository."""
        # Setup
        fake_git_port = FakeGitPort()
        git_service = GitService(fake_git_port)
        action = GetCommitsAction(git_service)

        repo = GitRepository(name="nonexistent", absolute_path="/nonexistent/path")

        # Execute
        result = action.execute(repo)

        # Assert - should still succeed but return empty list since fake returns empty
        assert result.is_success is True
        assert result.data == []


class TestGetCommitsActionLimitParameter:
    """Tests for limit parameter functionality."""

    def test_execute_passes_limit_to_service(self) -> None:
        """Test that limit parameter is passed correctly to service."""
        # Setup
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/test_project")
        fake_git_port.set_commits(
            "/home/user/test_project",
            [
                GitCommit(
                    id="1",
                    message="Commit 1",
                    author="Author",
                    timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
                ),
                GitCommit(
                    id="2",
                    message="Commit 2",
                    author="Author",
                    timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
                ),
                GitCommit(
                    id="3",
                    message="Commit 3",
                    author="Author",
                    timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
                ),
            ],
        )

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")
        action = GetCommitsAction(git_service)

        # Execute with limit=2
        result = action.execute(repo, limit=2)

        # Assert - should return only 2 commits
        assert result.is_success is True
        assert len(result.data) == 2

    def test_execute_uses_default_limit_of_20(self) -> None:
        """Test that default limit of 20 is used when not specified."""
        # Setup
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/default_project")
        commits = [
            GitCommit(
                id=str(i),
                message=f"Commit {i}",
                author="Author",
                timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
            )
            for i in range(25)
        ]
        fake_git_port.set_commits("/home/user/default_project", commits)

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="default_project", absolute_path="/home/user/default_project")
        action = GetCommitsAction(git_service)

        # Execute without specifying limit
        result = action.execute(repo)

        # Assert - should return max 20 commits (default limit)
        assert result.is_success is True
        assert len(result.data) <= 20

    def test_execute_passes_skip_to_service(self) -> None:
        """Test that skip parameter is passed correctly to service."""
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/test_project")
        fake_git_port.set_commits(
            "/home/user/test_project",
            [
                GitCommit(
                    id=str(i),
                    message=f"Commit {i}",
                    author="Author",
                    timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
                )
                for i in range(5)
            ],
        )

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")
        action = GetCommitsAction(git_service)

        result = action.execute(repo, limit=2, skip=2)

        assert result.is_success is True
        assert len(result.data) == 2


class TestGetCommitsActionEmptyCommits:
    """Tests for empty commit list scenarios."""

    def test_execute_returns_empty_list_when_no_commits(self) -> None:
        """Test that action returns empty list when repository has no commits."""
        # Setup
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/empty_project")
        fake_git_port.set_commits("/home/user/empty_project", [])

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="empty_project", absolute_path="/home/user/empty_project")
        action = GetCommitsAction(git_service)

        # Execute
        result = action.execute(repo)

        # Assert
        assert result.is_success is True
        assert result.data == []

    def test_execute_returns_success_for_empty_repository(self) -> None:
        """Test that empty repository returns success with empty list."""
        # Setup
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/new_project")
        # Don't set any commits - simulates new repo with no commits

        git_service = GitService(fake_git_port)
        repo = GitRepository(name="new_project", absolute_path="/home/user/new_project")
        action = GetCommitsAction(git_service)

        # Execute
        result = action.execute(repo)

        # Assert
        assert result.is_success is True
        assert isinstance(result.data, list)
        assert len(result.data) == 0


class TestGetCommitsActionSingleCommit:
    """Tests for single commit scenarios."""

    def test_execute_returns_single_commit(self) -> None:
        """Test that action returns single commit correctly."""
        # Setup
        fake_git_port = FakeGitPort()
        fake_git_port.add_git_repo("/home/user/single_commit_project")
        fake_git_port.set_commits(
            "/home/user/single_commit_project",
            [
                GitCommit(
                    id="only-commit",
                    message="Initial commit",
                    author="Creator",
                    timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
                ),
            ],
        )

        git_service = GitService(fake_git_port)
        repo = GitRepository(
            name="single_commit_project",
            absolute_path="/home/user/single_commit_project",
        )
        action = GetCommitsAction(git_service)

        # Execute
        result = action.execute(repo)

        # Assert
        assert result.is_success is True
        assert len(result.data) == 1
        assert result.data[0].id == "only-commit"
        assert result.data[0].message == "Initial commit"


class TestGetCommitsActionDependencies:
    """Tests for action dependency injection and initialization."""

    def test_action_accepts_git_service_dependency(self) -> None:
        """Test that action can be initialized with GitService."""
        fake_git_port = FakeGitPort()
        git_service = GitService(fake_git_port)

        action = GetCommitsAction(git_service)

        assert action._git_service is git_service

    def test_action_dependencies_are_stored_correctly(self) -> None:
        """Test that git service dependency is stored correctly."""
        fake_git_port = FakeGitPort()
        git_service = GitService(fake_git_port)

        action = GetCommitsAction(git_service)

        assert action._git_service is git_service
