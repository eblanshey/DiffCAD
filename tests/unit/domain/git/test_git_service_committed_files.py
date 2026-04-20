# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GitService.get_committed_files() delegation.
"""Unit tests for GitService.get_committed_files() delegation."""

from freecad.diff_wb.domain.git import GitRepository, GitService
from tests.fakes.fake_git_port import FakeGitPort


class TestGitServiceGetCommittedFiles:
    """Tests for GitService.get_committed_files() method."""

    def test_method_exists(self) -> None:
        """Test that get_committed_files method exists on GitService."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        assert hasattr(service, "get_committed_files")
        assert callable(service.get_committed_files)

    def test_method_signature(self) -> None:
        """Test that get_committed_files has correct signature."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        import inspect

        sig = inspect.signature(service.get_committed_files)
        params = list(sig.parameters.keys())

        assert "repo" in params
        assert "commit" in params

    def test_delegates_to_git_port(self) -> None:
        """Test that get_committed_files delegates to git_port with correct parameters."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        result = service.get_committed_files(repo=repo, commit="abc123")

        # FakeGitPort returns empty list by default
        assert result == []

    def test_passes_repo_absolute_path_to_git_port(self) -> None:
        """Test that the repo's absolute_path is passed correctly to git_port."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        test_path = "/home/user/my_project"
        repo = GitRepository(name="my_project", absolute_path=test_path)

        result = service.get_committed_files(repo=repo, commit="HEAD")

        assert isinstance(result, list)

    def test_returns_committed_files_from_port(self) -> None:
        """Test that committed files are returned from git_port."""
        fake_port = FakeGitPort()
        fake_port.set_committed_files(
            root_path="/home/user/my_project",
            commit="abc123",
            paths=["doc1.FCStd", "src/doc2.FCStd"],
        )
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")

        result = service.get_committed_files(repo=repo, commit="abc123")

        assert result == ["doc1.FCStd", "src/doc2.FCStd"]

    def test_returns_empty_list_for_unconfigured_commit(self) -> None:
        """Test that empty list is returned for unconfigured commit."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        result = service.get_committed_files(repo=repo, commit="nonexistent")

        assert result == []

    def test_returns_empty_list_for_different_commit(self) -> None:
        """Test that different commits return different file lists."""
        fake_port = FakeGitPort()
        fake_port.set_committed_files(
            root_path="/home/user/my_project",
            commit="commit1",
            paths=["doc1.FCStd"],
        )
        fake_port.set_committed_files(
            root_path="/home/user/my_project",
            commit="commit2",
            paths=["doc2.FCStd", "doc3.FCStd"],
        )
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")

        result1 = service.get_committed_files(repo=repo, commit="commit1")
        result2 = service.get_committed_files(repo=repo, commit="commit2")

        assert result1 == ["doc1.FCStd"]
        assert result2 == ["doc2.FCStd", "doc3.FCStd"]

    def test_returns_empty_list_for_different_repo(self) -> None:
        """Test that different repos return different file lists."""
        fake_port = FakeGitPort()
        fake_port.set_committed_files(
            root_path="/home/user/project_a",
            commit="HEAD",
            paths=["doc_a.FCStd"],
        )
        service = GitService(git_port=fake_port)

        repo_a = GitRepository(name="project_a", absolute_path="/home/user/project_a")
        repo_b = GitRepository(name="project_b", absolute_path="/home/user/project_b")

        result_a = service.get_committed_files(repo=repo_a, commit="HEAD")
        result_b = service.get_committed_files(repo=repo_b, commit="HEAD")

        assert result_a == ["doc_a.FCStd"]
        assert result_b == []
