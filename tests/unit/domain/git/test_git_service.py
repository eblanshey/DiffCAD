# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GitService public behavior using FakeGitPort.
"""Unit tests for the GitService class."""

import pytest
from freecad.history_wb.domain.git import GitRepository, GitService

from tests.fakes import FakeGitPort, MockDocument


class TestGetRepository:
    """Tests for GitService.get_repository() path detection."""

    @pytest.mark.parametrize(
        ("query_path", "expected"),
        [
            # Root match
            ("/home/user/project", "/home/user/project"),
            # Subdirectory
            ("/home/user/project/src", "/home/user/project"),
            # Deeply nested
            ("/home/user/project/src/module/submodule", "/home/user/project"),
            # File path
            ("/home/user/project/src/main.py", "/home/user/project"),
            # Trailing slash
            ("/home/user/project/", "/home/user/project"),
        ],
    )
    def test_finds_repository_for_paths_within_repo(self, query_path: str, expected: str) -> None:
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/project")
        service = GitService(git_port=fake_port)

        result = service.get_repository(query_path)

        assert result is not None
        assert result.name == "project"
        assert result.absolute_path == expected

    def test_repository_name_handles_windows_path(self) -> None:
        fake_port = FakeGitPort()
        fake_port.add_git_repo("C:\\Users\\me\\project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("C:\\Users\\me\\project")

        assert result is not None
        assert result.name == "project"

    @pytest.mark.parametrize(
        "query_path",
        [
            "/some/random/path",
            "",
            "/",
            "a",
            "src/main.py",  # relative path won't match absolute git roots
        ],
    )
    def test_returns_none_for_paths_outside_repo(self, query_path: str) -> None:
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/project")
        service = GitService(git_port=fake_port)

        result = service.get_repository(query_path)

        assert result is None


class TestGetCommits:
    """Tests for GitService.get_commits() paging and ordering."""

    def test_returns_commits_desc_with_limit_and_skip(self) -> None:
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/repo")
        for i in range(5):
            fake_port.add_commit(
                root_path="/repo",
                commit_id=f"commit{i}",
                message=f"Commit {i}",
                author="Author",
                timestamp=f"2024-01-{i + 1:02d}T00:00:00Z",
            )
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        # Default limit=20 returns all 5, newest first
        all_commits = service.get_commits(repo=repo)
        assert len(all_commits) == 5
        assert all_commits[0].id == "commit4"
        assert all_commits[-1].id == "commit0"

        # Limit truncates from newest
        limited = service.get_commits(repo=repo, limit=2)
        assert len(limited) == 2
        assert limited[0].id == "commit4"
        assert limited[1].id == "commit3"

        # Skip pagination
        skipped = service.get_commits(repo=repo, limit=2, skip=2)
        assert len(skipped) == 2
        assert skipped[0].id == "commit2"
        assert skipped[1].id == "commit1"

    def test_returns_empty_list_for_unknown_repo(self) -> None:
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="nonexistent", absolute_path="/nonexistent")

        result = service.get_commits(repo=repo)

        assert result == []


class TestGetEligibleDocs:
    """Tests for GitService.get_eligible_docs() filtering."""

    def test_filters_documents_to_repo_boundary(self) -> None:
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/project")
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="project", absolute_path="/home/user/project")

        documents = [
            MockDocument("/home/user/project/doc1.FCStd"),
            MockDocument("/home/user/outside/outside.FCStd"),
            MockDocument("/home/user/project/src/doc2.FCStd"),
            MockDocument("/home/user/neither/neither.FCStd"),
        ]

        result = service.get_eligible_docs(repo=repo, documents=documents)

        assert len(result) == 2
        assert result[0].FileName == "/home/user/project/doc1.FCStd"
        assert result[1].FileName == "/home/user/project/src/doc2.FCStd"

    def test_returns_empty_for_no_documents(self) -> None:
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/repo")
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.get_eligible_docs(repo=repo, documents=[])

        assert result == []


class TestStageFiles:
    """Tests for GitService.stage_files() delegation."""

    def test_returns_true_on_success(self) -> None:
        fake_port = FakeGitPort(fail_stage=False)
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.stage_files(repo=repo, paths=["file.FCStd"])

        assert result is True

    def test_returns_false_on_failure(self) -> None:
        fake_port = FakeGitPort(fail_stage=True)
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.stage_files(repo=repo, paths=["file.FCStd"])

        assert result is False

    def test_returns_true_for_empty_paths(self) -> None:
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.stage_files(repo=repo, paths=[])

        assert result is True


class TestCommit:
    """Tests for GitService.commit() delegation."""

    def test_returns_true_and_passes_args_on_success(self) -> None:
        fake_port = FakeGitPort(fail_commit=False)
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/home/user/repo")

        result = service.commit(repo=repo, message="feat: add feature")

        assert result is True
        assert fake_port.get_last_commit_call() == ("/home/user/repo", "feat: add feature")

    def test_returns_false_on_failure(self) -> None:
        fake_port = FakeGitPort(fail_commit=True)
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.commit(repo=repo, message="msg")

        assert result is False


class TestGetStagedFiles:
    """Tests for GitService.get_staged_files() delegation."""

    def test_returns_configured_staged_paths(self) -> None:
        fake_port = FakeGitPort()
        fake_port.set_staged_paths(["doc1.FCStd", "src/doc2.FCStd"])
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.get_staged_files(repo=repo)

        assert result == ["doc1.FCStd", "src/doc2.FCStd"]

    def test_returns_empty_when_nothing_staged(self) -> None:
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.get_staged_files(repo=repo)

        assert result == []


class TestGetFileContents:
    """Tests for GitService.get_file_contents() delegation."""

    def test_returns_content_from_index(self) -> None:
        fake_port = FakeGitPort()
        fake_port.set_file_contents(None, "path/to/file.FCStd", "index content")
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.get_file_contents(repo=repo, commit=None, git_path="path/to/file.FCStd")

        assert result == "index content"

    def test_returns_content_from_commit(self) -> None:
        fake_port = FakeGitPort()
        fake_port.set_file_contents("abc123", "path/to/file.FCStd", "commit content")
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.get_file_contents(repo=repo, commit="abc123", git_path="path/to/file.FCStd")

        assert result == "commit content"

    def test_returns_none_for_missing_file(self) -> None:
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.get_file_contents(repo=repo, commit=None, git_path="missing.FCStd")

        assert result is None


class TestWriteFileFromRef:
    """Tests for GitService.write_file_from_ref() delegation."""

    def test_writes_binary_content_from_index(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        fake_port = FakeGitPort()
        fake_port.set_file_bytes(None, "path/to/file.FCStd", b"\x50\x4b\x03\x04")
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")
        destination = tmp_path / "out.FCStd"

        result = service.write_file_from_ref(
            repo=repo, commit=None, git_path="path/to/file.FCStd", destination=str(destination)
        )

        assert result is True
        assert destination.read_bytes() == b"\x50\x4b\x03\x04"


class TestResolveRef:
    """Tests for GitService.resolve_ref() delegation."""

    def test_returns_resolved_commit_hash(self) -> None:
        fake_port = FakeGitPort()
        fake_port.set_resolved_ref("HEAD~1", "abcdef1234567890abcdef1234567890abcdef12")
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.resolve_ref(repo, "HEAD~1")

        assert result == "abcdef1234567890abcdef1234567890abcdef12"

    def test_returns_none_when_ref_cannot_be_resolved(self) -> None:
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.resolve_ref(repo, "nonexistent-branch")

        assert result is None


class TestInitializeRepository:
    """Tests for GitService.initialize_repository behavior."""

    def test_returns_repository_after_successful_initialization(self) -> None:
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        result = service.initialize_repository("/home/user/project")

        assert result is not None
        assert result.name == "project"
        assert result.absolute_path == "/home/user/project"
        assert fake_port.get_last_init_path() == "/home/user/project"

    def test_returns_none_when_initialization_fails(self) -> None:
        service = GitService(git_port=FakeGitPort(fail_init=True))

        result = service.initialize_repository("/home/user/project")

        assert result is None


class TestGetCommittedFiles:
    """Tests for GitService.get_committed_files() delegation."""

    def test_returns_files_for_configured_commit(self) -> None:
        fake_port = FakeGitPort()
        fake_port.set_committed_files(root_path="/repo", commit="abc123", paths=["doc1.FCStd", "src/doc2.FCStd"])
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.get_committed_files(repo=repo, commit="abc123")

        assert result == ["doc1.FCStd", "src/doc2.FCStd"]

    def test_returns_empty_for_unknown_commit(self) -> None:
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)
        repo = GitRepository(name="repo", absolute_path="/repo")

        result = service.get_committed_files(repo=repo, commit="nonexistent")

        assert result == []


class TestCanWriteGlobalIdentity:
    """Tests for GitService.can_write_global_identity() delegation."""

    @pytest.mark.parametrize("can_write", [True, False])
    def test_returns_configured_global_identity_writability(self, can_write: bool) -> None:
        fake_port = FakeGitPort()
        fake_port.set_can_write_global_identity(can_write)
        service = GitService(git_port=fake_port)

        result = service.can_write_global_identity()

        assert result is can_write
