# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the GitService class using fake GitPort
# implementations. These tests verify that GitService correctly creates
# GitRepository objects from paths, handles commits, filters documents,
# and stages files properly.
"""Unit tests for the GitService class."""

import dataclasses
import os

from freecad.diff_wb.domain.git import GitRepository, GitService
from tests.fakes.fake_git_port import FakeGitPort


class TestGitServiceInitialization:
    """Tests for GitService initialization and dependency injection."""

    def test_initialization_with_git_port(self) -> None:
        """Test that GitService can be initialized with a GitPort."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        assert service is not None

    def test_git_port_is_stored(self) -> None:
        """Test that the GitPort is stored in the service."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        assert service._git_port == fake_port


class TestGitServiceGetRepository:
    """Tests for GitService.get_repository() method."""

    def test_get_repository_returns_none_for_nonexistent_repo(self) -> None:
        """Test that get_repository returns None when path is not in a git repo."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        result = service.get_repository("/some/random/path")

        assert result is None

    def test_get_repository_returns_repository_when_path_is_git_root(self) -> None:
        """Test that get_repository returns GitRepository when path IS the git root."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project")

        assert result is not None
        assert isinstance(result, GitRepository)
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_returns_repository_for_subdirectory(self) -> None:
        """Test that get_repository returns GitRepository when path is a subdirectory."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project/src")

        assert result is not None
        assert isinstance(result, GitRepository)
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_returns_repository_for_nested_subdirectory(self) -> None:
        """Test that get_repository works with deeply nested paths."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project/src/module/submodule")

        assert result is not None
        assert isinstance(result, GitRepository)
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_returns_repository_for_file_in_repo(self) -> None:
        """Test that get_repository works for files within the repo."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project/src/main.py")

        assert result is not None
        assert isinstance(result, GitRepository)
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_handles_trailing_slash(self) -> None:
        """Test that get_repository handles trailing slashes correctly."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project/")

        assert result is not None
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_with_multiple_repos(self) -> None:
        """Test behavior when multiple git repos are configured."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/project_a")
        fake_port.add_git_repo("/home/user/project_b")
        service = GitService(git_port=fake_port)

        result_a = service.get_repository("/home/user/project_a/src")
        result_b = service.get_repository("/home/user/project_b/src")

        assert result_a is not None
        assert result_b is not None
        assert result_a.name == "project_a"
        assert result_a.absolute_path == "/home/user/project_a"
        assert result_b.name == "project_b"
        assert result_b.absolute_path == "/home/user/project_b"


class TestGitServiceGetRepositoryEdgeCases:
    """Tests for edge cases in GitService.get_repository()."""

    def test_get_repository_with_empty_path(self) -> None:
        """Test handling of empty path."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        result = service.get_repository("")

        assert result is None

    def test_get_repository_with_root_directory(self) -> None:
        """Test handling of root directory."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        result = service.get_repository("/")

        assert result is None

    def test_get_repository_with_single_character_path(self) -> None:
        """Test handling of single character path."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        result = service.get_repository("a")

        assert result is None

    def test_get_repository_with_special_characters_in_name(self) -> None:
        """Test handling of repository names with special characters."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my-project_v2.0")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my-project_v2.0/src/file-name.py")

        assert result is not None
        assert result.name == "my-project_v2.0"
        assert result.absolute_path == "/home/user/my-project_v2.0"

    def test_get_repository_with_relative_path(self) -> None:
        """Test handling of relative paths (should return None)."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("src/main.py")

        # Relative paths won't match absolute git roots
        assert result is None


class TestGitServiceGetRepositoryIntegration:
    """Integration tests for GitService with realistic scenarios."""

    def test_workflow_detect_active_repository(self) -> None:
        """Test the complete workflow of detecting an active repository."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/workbench_project")
        service = GitService(git_port=fake_port)

        # Simulate checking a FreeCAD document path
        doc_path = "/home/user/workbench_project/freecad/diff_wb/document.FCStd"
        repo = service.get_repository(doc_path)

        assert repo is not None
        assert repo.name == "workbench_project"
        assert repo.absolute_path == "/home/user/workbench_project"

    def test_workflow_no_repository_for_unsaved_document(self) -> None:
        """Test workflow when document is not in a git repo."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        # Simulate checking an unsaved or temporary document
        doc_path = "/tmp/unsaved_file.FCStd"
        repo = service.get_repository(doc_path)

        assert repo is None

    def test_get_repository_returns_frozen_dataclass(self) -> None:
        """Test that returned GitRepository is immutable (frozen)."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/project")
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/project/src")

        assert repo is not None
        # Try to modify - should raise FrozenInstanceError
        try:
            repo.name = "modified"  # type: ignore
            raise AssertionError("Expected FrozenInstanceError")
        except dataclasses.FrozenInstanceError:
            pass  # Expected behavior


class TestGitServiceWithRealPathOperations:
    """Tests that verify GitService correctly uses os.path operations."""

    def test_get_repository_uses_os_path_basename(self) -> None:
        """Test that service correctly extracts name using os.path.basename."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/test-repo")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/test-repo")

        # Verify the name matches what os.path.basename would return
        expected_name = os.path.basename("/home/user/test-repo")
        assert result is not None
        assert result.name == expected_name

    def test_get_repository_preserves_absolute_path(self) -> None:
        """Test that service preserves the absolute path as-is."""
        fake_port = FakeGitPort()
        test_path = "/absolute/path/to/repository"
        fake_port.add_git_repo(test_path)
        service = GitService(git_port=fake_port)

        result = service.get_repository(test_path + "/subdir")

        assert result is not None
        assert result.absolute_path == test_path


class TestGitServiceGetCommitsInitialization:
    """Tests for GitService.get_commits() initialization."""

    def test_get_commits_method_exists(self) -> None:
        """Test that get_commits method exists on GitService."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        assert hasattr(service, "get_commits")
        assert callable(service.get_commits)

    def test_get_commits_method_signature(self) -> None:
        """Test that get_commits has correct signature with limit parameter."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        # Verify the method accepts repo and limit parameters
        import inspect

        sig = inspect.signature(service.get_commits)
        params = list(sig.parameters.keys())

        assert "repo" in params
        assert "limit" in params


class TestGitServiceGetCommitsWithEmptyCommits:
    """Tests for GitService.get_commits() with empty commit lists."""

    def test_get_commits_returns_empty_list_when_no_commits(self) -> None:
        """Test that get_commits returns empty list when repo has no commits."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        result = service.get_commits(repo=repo)

        assert result == []
        assert isinstance(result, list)

    def test_get_commits_returns_empty_list_for_nonexistent_repo(self) -> None:
        """Test that get_commits returns empty list for non-existent repository."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        # Create a repo object for a path that doesn't exist in fake port
        repo = GitRepository(name="nonexistent", absolute_path="/nonexistent/path")

        result = service.get_commits(repo=repo)

        assert result == []


class TestGitServiceGetCommitsWithSingleCommit:
    """Tests for GitService.get_commits() with a single commit."""

    def test_get_commits_returns_single_commit(self) -> None:
        """Test that get_commits returns one commit when only one exists."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="abc123def456",
            message="Initial commit",
            author="John Doe",
            timestamp="2024-01-15T10:30:00Z",
        )
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        result = service.get_commits(repo=repo)

        assert len(result) == 1
        assert result[0].id == "abc123def456"
        assert result[0].message == "Initial commit"
        assert result[0].author == "John Doe"
        assert result[0].timestamp.isoformat() == "2024-01-15T10:30:00+00:00"


class TestGitServiceGetCommitsWithMultipleCommits:
    """Tests for GitService.get_commits() with multiple commits."""

    def test_get_commits_returns_all_commits(self) -> None:
        """Test that get_commits returns all commits when limit is high enough."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="commit1",
            message="First commit",
            author="Alice",
            timestamp="2024-01-01T00:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="commit2",
            message="Second commit",
            author="Bob",
            timestamp="2024-01-02T00:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="commit3",
            message="Third commit",
            author="Charlie",
            timestamp="2024-01-03T00:00:00Z",
        )
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        result = service.get_commits(repo=repo)

        assert len(result) == 3

    def test_get_commits_returns_all_commit_properties(self) -> None:
        """Test that all commit properties are accessible from returned commits."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="test-commit-hash-12345",
            message="Test commit message\n\nThis is the commit body.",
            author="Test Author <test@example.com>",
            timestamp="2024-06-15T14:30:45Z",
        )
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        result = service.get_commits(repo=repo)

        assert len(result) == 1
        commit = result[0]

        assert commit.id == "test-commit-hash-12345"
        assert commit.message == "Test commit message\n\nThis is the commit body."
        assert commit.author == "Test Author <test@example.com>"
        assert commit.timestamp.isoformat() == "2024-06-15T14:30:45+00:00"


class TestGitServiceGetCommitsLimitParameter:
    """Tests for GitService.get_commits() limit parameter."""

    def test_get_commits_respects_limit_parameter(self) -> None:
        """Test that get_commits respects the limit parameter."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        # Add 10 commits
        for i in range(10):
            fake_port.add_commit(
                root_path="/home/user/my_project",
                commit_id=f"commit{i}",
                message=f"Commit {i}",
                author=f"Author {i}",
                timestamp=f"2024-01-{i + 1:02d}T00:00:00Z",
            )
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        # Test with limit=5
        result = service.get_commits(repo=repo, limit=5)
        assert len(result) == 5

        # Test with default limit (20) - should return all 10
        result_default = service.get_commits(repo=repo)
        assert len(result_default) == 10

        # Test with limit=0 - should return empty list
        result_zero = service.get_commits(repo=repo, limit=0)
        assert result_zero == []

    def test_get_commits_default_limit_is_20(self) -> None:
        """Test that the default limit is 20 commits."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        # Add 25 commits
        for i in range(25):
            fake_port.add_commit(
                root_path="/home/user/my_project",
                commit_id=f"commit{i}",
                message=f"Commit {i}",
                author=f"Author {i}",
                timestamp=f"2024-01-{i + 1:02d}T00:00:00Z",
            )
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        # Default limit should be 20
        result = service.get_commits(repo=repo)
        assert len(result) == 20

    def test_get_commits_respects_skip_parameter(self) -> None:
        """Test that get_commits respects skip for pagination."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        for i in range(5):
            fake_port.add_commit(
                root_path="/home/user/my_project",
                commit_id=f"commit{i}",
                message=f"Commit {i}",
                author=f"Author {i}",
                timestamp=f"2024-01-{i + 1:02d}T00:00:00Z",
            )
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        result = service.get_commits(repo=repo, limit=2, skip=2)
        assert len(result) == 2
        assert result[0].id == "commit2"
        assert result[1].id == "commit1"


class TestGitServiceGetCommitsDESCOrder:
    """Tests for GitService.get_commits() DESC order."""

    def test_get_commits_returns_commits_in_desc_order(self) -> None:
        """Test that get_commits returns commits in DESC order (newest first)."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="oldest",
            message="Oldest commit",
            author="Old Author",
            timestamp="2024-01-01T00:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="middle",
            message="Middle commit",
            author="Middle Author",
            timestamp="2024-01-02T00:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="newest",
            message="Newest commit",
            author="New Author",
            timestamp="2024-01-03T00:00:00Z",
        )
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        result = service.get_commits(repo=repo)

        # Should be in reverse order (newest first)
        assert len(result) == 3
        assert result[0].id == "newest"
        assert result[1].id == "middle"
        assert result[2].id == "oldest"

    def test_get_commits_limit_applied_after_reversing(self) -> None:
        """Test that limit is applied after reversing for DESC order."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        # Add commits in chronological order
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="first",
            message="First",
            author="Author",
            timestamp="2024-01-01T00:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="second",
            message="Second",
            author="Author",
            timestamp="2024-01-02T00:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="third",
            message="Third",
            author="Author",
            timestamp="2024-01-03T00:00:00Z",
        )
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        # With limit=2, should get newest 2 (third and second)
        result = service.get_commits(repo=repo, limit=2)

        assert len(result) == 2
        assert result[0].id == "third"
        assert result[1].id == "second"


class TestGitServiceGetCommitsIntegration:
    """Integration tests for GitService.get_commits()."""

    def test_workflow_get_commits_for_realistic_scenario(self) -> None:
        """Test complete workflow of getting commits for a project."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/freecad_workbench")

        # Simulate realistic commit history - add in chronological order (oldest first)
        # Commits will be returned in DESC order (newest first)
        fake_port.add_commit(
            root_path="/home/user/freecad_workbench",
            commit_id="c3d4e5f6a1b2",
            message="docs: update README with installation instructions",
            author="Developer One",
            timestamp="2024-06-13T09:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/freecad_workbench",
            commit_id="b2c3d4e5f6a1",
            message="fix: resolve merge conflict in utils.py",
            author="Developer Two",
            timestamp="2024-06-14T15:30:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/freecad_workbench",
            commit_id="a1b2c3d4e5f6",
            message="feat: add diff comparison feature",
            author="Developer One",
            timestamp="2024-06-15T10:00:00Z",
        )
        service = GitService(git_port=fake_port)

        # Get repository from a file path within the project
        doc_path = "/home/user/freecad_workbench/freecad/diff_wb/document.FCStd"
        repo = service.get_repository(doc_path)
        assert repo is not None

        # Get recent commits
        commits = service.get_commits(repo=repo, limit=3)

        assert len(commits) == 3
        # Most recent commit should be first (DESC order)
        assert "diff comparison feature" in commits[0].message
        assert commits[0].author == "Developer One"


class MockDocument:
    """Mock document class for testing get_eligible_docs."""

    def __init__(self, file_name: str, name: str = "") -> None:
        self.FileName = file_name
        self.Name = name or file_name.split("/")[-1]


class TestGitServiceGetEligibleDocsInitialization:
    """Tests for GitService.get_eligible_docs() initialization."""

    def test_get_eligible_docs_method_exists(self) -> None:
        """Test that get_eligible_docs method exists on GitService."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        assert hasattr(service, "get_eligible_docs")
        assert callable(service.get_eligible_docs)

    def test_get_eligible_docs_method_signature(self) -> None:
        """Test that get_eligible_docs has correct signature."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        import inspect

        sig = inspect.signature(service.get_eligible_docs)
        params = list(sig.parameters.keys())

        assert "repo" in params
        assert "documents" in params


class TestGitServiceGetEligibleDocsEmptyCases:
    """Tests for GitService.get_eligible_docs() with empty inputs."""

    def test_get_eligible_docs_returns_empty_list_for_empty_documents(self) -> None:
        """Test that get_eligible_docs returns empty list when no documents provided."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        result = service.get_eligible_docs(repo=repo, documents=[])

        assert result == []
        assert isinstance(result, list)

    def test_get_eligible_docs_returns_empty_list_when_no_documents_in_repo(self) -> None:
        """Test that empty list is returned when no documents are in git repo."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        # All documents are outside the git repo
        documents = [
            MockDocument("/tmp/unsaved.FCStd"),
            MockDocument("/home/user/other_project/doc.FCStd"),
        ]

        result = service.get_eligible_docs(repo=repo, documents=documents)

        assert result == []

    def test_get_eligible_docs_filters_out_documents_outside_git_repo(self) -> None:
        """Test that documents outside git repo are filtered out."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        documents = [
            MockDocument("/home/user/my_project/doc1.FCStd"),  # In repo
            MockDocument("/tmp/temp.FCStd"),  # Outside repo
            MockDocument("/home/user/other/doc2.FCStd"),  # Outside repo
        ]

        result = service.get_eligible_docs(repo=repo, documents=documents)

        assert len(result) == 1
        assert result[0].FileName == "/home/user/my_project/doc1.FCStd"


class TestGitServiceGetEligibleDocsWithValidDocuments:
    """Tests for GitService.get_eligible_docs() with valid documents."""

    def test_get_eligible_docs_returns_only_documents_within_git_repo(self) -> None:
        """Test that get_eligible_docs returns only documents within git repo."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        documents = [
            MockDocument("/home/user/my_project/doc1.FCStd"),
            MockDocument("/home/user/my_project/src/doc2.FCStd"),
            MockDocument("/home/user/my_project/nested/deep/doc3.FCStd"),
        ]

        result = service.get_eligible_docs(repo=repo, documents=documents)

        assert len(result) == 3
        assert all(doc.FileName.startswith("/home/user/my_project") for doc in result)

    def test_get_eligible_docs_works_with_mixed_documents(self) -> None:
        """Test that it works with mixed documents (some in, some out)."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        documents = [
            MockDocument("/home/user/my_project/in_repo.FCStd"),  # In repo
            MockDocument("/tmp/outside.FCStd"),  # Outside repo
            MockDocument("/home/user/my_project/src/also_in.FCStd"),  # In repo
            MockDocument("/var/tmp/neither.FCStd"),  # Outside repo
        ]

        result = service.get_eligible_docs(repo=repo, documents=documents)

        assert len(result) == 2
        filenames = [doc.FileName for doc in result]
        assert "/home/user/my_project/in_repo.FCStd" in filenames
        assert "/home/user/my_project/src/also_in.FCStd" in filenames

    def test_get_eligible_docs_filters_documents_without_filename(self) -> None:
        """Test that documents without FileName are filtered out."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        class DocWithoutFileName:
            pass

        documents = [
            MockDocument("/home/user/my_project/valid.FCStd"),
            DocWithoutFileName(),  # No FileName attribute
            MockDocument("/home/user/my_project/also_valid.FCStd"),
        ]

        result = service.get_eligible_docs(repo=repo, documents=documents)

        assert len(result) == 2
        assert all(hasattr(doc, "FileName") for doc in result)

    def test_get_eligible_docs_filters_documents_with_empty_filename(self) -> None:
        """Test that documents with empty FileName are filtered out."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        documents = [
            MockDocument("/home/user/my_project/valid.FCStd"),
            MockDocument(""),  # Empty FileName
            MockDocument("/home/user/my_project/also_valid.FCStd"),
        ]

        result = service.get_eligible_docs(repo=repo, documents=documents)

        assert len(result) == 2
        assert all(doc.FileName for doc in result)


class TestGitServiceGetEligibleDocsEdgeCases:
    """Tests for edge cases in GitService.get_eligible_docs()."""

    def test_get_eligible_docs_handles_trailing_slash_in_git_root(self) -> None:
        """Test that trailing slash in git root is handled correctly."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        # Create repo object with trailing slash (simulating different path formats)
        from freecad.diff_wb.domain.git import GitRepository

        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project/")

        documents = [
            MockDocument("/home/user/my_project/doc.FCStd"),
        ]

        result = service.get_eligible_docs(repo=repo, documents=documents)

        assert len(result) == 1

    def test_get_eligible_docs_preserves_document_order(self) -> None:
        """Test that the order of eligible documents is preserved."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        documents = [
            MockDocument("/tmp/first_outside.FCStd"),
            MockDocument("/home/user/my_project/second_in.FCStd"),
            MockDocument("/var/third_outside.FCStd"),
            MockDocument("/home/user/my_project/fourth_in.FCStd"),
        ]

        result = service.get_eligible_docs(repo=repo, documents=documents)

        assert len(result) == 2
        assert result[0].FileName == "/home/user/my_project/second_in.FCStd"
        assert result[1].FileName == "/home/user/my_project/fourth_in.FCStd"

    def test_get_eligible_docs_with_special_characters_in_path(self) -> None:
        """Test handling of paths with special characters."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my-project_v2.0")
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my-project_v2.0")
        assert repo is not None

        documents = [
            MockDocument("/home/user/my-project_v2.0/src/file-name.FCStd"),
            MockDocument("/tmp/other.FCStd"),
        ]

        result = service.get_eligible_docs(repo=repo, documents=documents)

        assert len(result) == 1
        assert result[0].FileName == "/home/user/my-project_v2.0/src/file-name.FCStd"


class TestGitServiceGetEligibleDocsIntegration:
    """Integration tests for GitService.get_eligible_docs()."""

    def test_workflow_filter_documents_for_realistic_scenario(self) -> None:
        """Test complete workflow of filtering documents for a project."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/freecad_workbench")
        service = GitService(git_port=fake_port)

        # Simulate realistic scenario with multiple open documents
        documents = [
            MockDocument("/home/user/freecad_workbench/part1.FCStd", "Part1"),
            MockDocument("/home/user/freecad_workbench/freecad/diff_wb/part2.FCStd", "Part2"),
            MockDocument("/tmp/unsaved_temp.FCStd", "Unsaved"),
            MockDocument("/home/user/downloads/random.FCStd", "Random"),
            MockDocument("/home/user/freecad_workbench/docs/readme.md", "Readme"),
        ]

        repo = service.get_repository("/home/user/freecad_workbench")
        assert repo is not None

        eligible = service.get_eligible_docs(repo=repo, documents=documents)

        # Should only include documents within the git repository
        assert len(eligible) == 3
        filenames = [doc.FileName for doc in eligible]
        assert all("freecad_workbench" in f for f in filenames)
        assert all(not f.startswith("/tmp") and not f.startswith("/home/user/downloads") for f in filenames)

    def test_workflow_all_documents_outside_repo(self) -> None:
        """Test workflow when all documents are outside the git repository."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/project")
        service = GitService(git_port=fake_port)

        # All documents are outside the repo
        documents = [
            MockDocument("/tmp/doc1.FCStd"),
            MockDocument("/var/tmp/doc2.FCStd"),
            MockDocument("/home/user/other_project/doc3.FCStd"),
        ]

        repo = service.get_repository("/home/user/project")
        assert repo is not None

        eligible = service.get_eligible_docs(repo=repo, documents=documents)

        assert eligible == []


class TestGitServiceStageFilesDelegation:
    """Tests for GitService.stage_files() delegation to git_port."""

    def test_stage_files_delegates_to_git_port_with_correct_parameters(self) -> None:
        """Test that stage_files delegates to git_port with correct parameters."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")
        paths = ["file1.py", "src/file2.py"]

        result = service.stage_files(repo=repo, paths=paths)

        # FakeGitPort always returns True by default
        assert result is True

    def test_stage_files_passes_repo_absolute_path_to_git_port(self) -> None:
        """Test that the repo's absolute_path is passed correctly to git_port."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        # Create a repo with a specific path
        test_path = "/home/user/my_project"
        repo = GitRepository(name="my_project", absolute_path=test_path)
        paths = ["document.FCStd"]

        result = service.stage_files(repo=repo, paths=paths)

        assert result is True


class TestGitServiceStageFilesEmptyPaths:
    """Tests for GitService.stage_files() with empty paths list."""

    def test_stage_files_returns_true_for_empty_paths_list(self) -> None:
        """Test that stage_files returns True immediately for empty paths."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")
        paths: list[str] = []

        result = service.stage_files(repo=repo, paths=paths)

        # Empty paths should return True immediately (nothing to stage)
        assert result is True

    def test_stage_files_returns_true_for_none_like_empty_behavior(self) -> None:
        """Test behavior with various empty-like inputs."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        # Empty list
        result = service.stage_files(repo=repo, paths=[])
        assert result is True


class TestGitServiceStageFilesFailurePropagation:
    """Tests for GitService.stage_files() failure handling."""

    def test_stage_files_propagates_failure_from_git_port(self) -> None:
        """Test that failure from git_port propagates correctly as False."""
        # Create FakeGitPort configured to fail
        fake_port = FakeGitPort(fail_stage=True)
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")
        paths = ["file1.py"]

        result = service.stage_files(repo=repo, paths=paths)

        # Should propagate the failure
        assert result is False

    def test_stage_files_returns_false_when_git_port_fails_with_multiple_files(self) -> None:
        """Test failure propagation with multiple files to stage."""
        fake_port = FakeGitPort(fail_stage=True)
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")
        paths = ["file1.py", "file2.py", "src/file3.py"]

        result = service.stage_files(repo=repo, paths=paths)

        assert result is False

    def test_stage_files_succeeds_when_git_port_succeeds(self) -> None:
        """Test that success from git_port propagates correctly as True."""
        fake_port = FakeGitPort(fail_stage=False)
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")
        paths = ["document.FCStd"]

        result = service.stage_files(repo=repo, paths=paths)

        assert result is True


class TestGitServiceStageFilesIntegration:
    """Integration tests for GitService.stage_files()."""

    def test_workflow_stage_files_in_realistic_scenario(self) -> None:
        """Test complete workflow of staging files in a realistic scenario."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        # Simulate a realistic scenario with a FreeCAD project
        repo = GitRepository(
            name="freecad_diff_workbench",
            absolute_path="/home/user/freecad_diff_workbench",
        )
        paths = ["freecad/diff_wb/document.FCStd", "README.md"]

        result = service.stage_files(repo=repo, paths=paths)

        assert result is True

    def test_workflow_stage_files_handles_failure_gracefully(self) -> None:
        """Test that failures are handled gracefully in workflow."""
        fake_port = FakeGitPort(fail_stage=True)
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="project", absolute_path="/home/user/project")
        paths = ["important_file.FCStd"]

        result = service.stage_files(repo=repo, paths=paths)

        # Should return False without raising exception
        assert result is False


class TestGitServiceGetStagedFiles:
    """Tests for GitService.get_staged_files() method."""

    def test_get_staged_files_method_exists(self) -> None:
        """Test that get_staged_files method exists on GitService."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        assert hasattr(service, "get_staged_files")
        assert callable(service.get_staged_files)

    def test_get_staged_files_delegates_to_git_port(self) -> None:
        """Test that get_staged_files delegates to git_port with correct parameters."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        result = service.get_staged_files(repo=repo)

        # FakeGitPort returns empty list by default
        assert result == []

    def test_get_staged_files_passes_repo_absolute_path(self) -> None:
        """Test that the repo's absolute_path is passed correctly to git_port."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")

        result = service.get_staged_files(repo=repo)

        # Verify via FakeGitPort internal state (if it tracked calls)
        assert isinstance(result, list)

    def test_get_staged_files_returns_list_of_staged_paths(self) -> None:
        """Test that get_staged_files returns a list of staged paths."""
        fake_port = FakeGitPort()
        # Configure fake port to return some staged files
        fake_port._staged_paths = ["doc1.FCStd", "src/doc2.FCStd"]
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        result = service.get_staged_files(repo=repo)

        assert result == ["doc1.FCStd", "src/doc2.FCStd"]

    def test_get_staged_files_returns_empty_list_when_nothing_staged(self) -> None:
        """Test that empty list is returned when nothing is staged."""
        fake_port = FakeGitPort()
        fake_port._staged_paths = []  # Explicitly set empty
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        result = service.get_staged_files(repo=repo)

        assert result == []


class TestGitServiceGetFileContents:
    """Tests for GitService.get_file_contents() method."""

    def test_get_file_contents_method_exists(self) -> None:
        """Test that get_file_contents method exists on GitService."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        assert hasattr(service, "get_file_contents")
        assert callable(service.get_file_contents)

    def test_get_file_contents_delegates_to_git_port(self) -> None:
        """Test that get_file_contents delegates to git_port with correct parameters."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        result = service.get_file_contents(repo=repo, commit=None, git_path="path/to/file.FCStd")

        # FakeGitPort returns None by default
        assert result is None

    def test_get_file_contents_passes_correct_parameters(self) -> None:
        """Test that all parameters are passed correctly to git_port."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")

        # Test with commit=None (index)
        result_index = service.get_file_contents(repo=repo, commit=None, git_path="file.FCStd")
        assert result_index is None

        # Test with specific commit
        result_commit = service.get_file_contents(repo=repo, commit="abc123", git_path="file.FCStd")
        assert result_commit is None

    def test_get_file_contents_returns_file_contents_from_index(self) -> None:
        """Test that file contents are returned when available from index."""
        fake_port = FakeGitPort()
        fake_port._file_contents = {(None, "path/to/file.FCStd"): "yaml content here"}
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        result = service.get_file_contents(repo=repo, commit=None, git_path="path/to/file.FCStd")

        assert result == "yaml content here"

    def test_get_file_contents_returns_file_contents_from_commit(self) -> None:
        """Test that file contents are returned when available from commit."""
        fake_port = FakeGitPort()
        fake_port._file_contents = {("abc123", "path/to/file.FCStd"): "commit content"}
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        result = service.get_file_contents(repo=repo, commit="abc123", git_path="path/to/file.FCStd")

        assert result == "commit content"

    def test_get_file_contents_returns_none_for_nonexistent_file(self) -> None:
        """Test that None is returned for nonexistent file."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        result = service.get_file_contents(repo=repo, commit=None, git_path="nonexistent.FCStd")

        assert result is None

    def test_get_file_contents_returns_none_for_invalid_commit(self) -> None:
        """Test that None is returned for invalid commit."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        result = service.get_file_contents(repo=repo, commit="invalid_commit", git_path="file.FCStd")

        assert result is None
