# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the GitService class using fake GitPort
# implementations. These tests verify that GitService correctly creates
# GitRepository objects from paths and handles edge cases properly.
"""Unit tests for the GitService class."""

import dataclasses
import os

from freecad.diff_wb.domain.git import GitRepository, GitService
from tests.unit.domain.git.test_git_port import FakeGitPort


class TestGitServiceInitialization:
    """Tests for GitService initialization and dependency injection."""

    def test_initialization_with_git_port(self):
        """Test that GitService can be initialized with a GitPort."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        assert service is not None

    def test_git_port_is_stored(self):
        """Test that the GitPort is stored in the service."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        assert service._git_port == fake_port


class TestGitServiceGetRepository:
    """Tests for GitService.get_repository() method."""

    def test_get_repository_returns_none_for_nonexistent_repo(self):
        """Test that get_repository returns None when path is not in a git repo."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        result = service.get_repository("/some/random/path")

        assert result is None

    def test_get_repository_returns_repository_when_path_is_git_root(self):
        """Test that get_repository returns GitRepository when path IS the git root."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project")

        assert result is not None
        assert isinstance(result, GitRepository)
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_returns_repository_for_subdirectory(self):
        """Test that get_repository returns GitRepository when path is a subdirectory."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project/src")

        assert result is not None
        assert isinstance(result, GitRepository)
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_returns_repository_for_nested_subdirectory(self):
        """Test that get_repository works with deeply nested paths."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project/src/module/submodule")

        assert result is not None
        assert isinstance(result, GitRepository)
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_returns_repository_for_file_in_repo(self):
        """Test that get_repository works for files within the repo."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project/src/main.py")

        assert result is not None
        assert isinstance(result, GitRepository)
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_handles_trailing_slash(self):
        """Test that get_repository handles trailing slashes correctly."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project/")

        assert result is not None
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_with_multiple_repos(self):
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

    def test_get_repository_with_empty_path(self):
        """Test handling of empty path."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        result = service.get_repository("")

        assert result is None

    def test_get_repository_with_root_directory(self):
        """Test handling of root directory."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        result = service.get_repository("/")

        assert result is None

    def test_get_repository_with_single_character_path(self):
        """Test handling of single character path."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        result = service.get_repository("a")

        assert result is None

    def test_get_repository_with_special_characters_in_name(self):
        """Test handling of repository names with special characters."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my-project_v2.0")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my-project_v2.0/src/file-name.py")

        assert result is not None
        assert result.name == "my-project_v2.0"
        assert result.absolute_path == "/home/user/my-project_v2.0"

    def test_get_repository_with_relative_path(self):
        """Test handling of relative paths (should return None)."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("src/main.py")

        # Relative paths won't match absolute git roots
        assert result is None


class TestGitServiceGetRepositoryIntegration:
    """Integration tests for GitService with realistic scenarios."""

    def test_workflow_detect_active_repository(self):
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

    def test_workflow_no_repository_for_unsaved_document(self):
        """Test workflow when document is not in a git repo."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        # Simulate checking an unsaved or temporary document
        doc_path = "/tmp/unsaved_file.FCStd"
        repo = service.get_repository(doc_path)

        assert repo is None

    def test_get_repository_returns_frozen_dataclass(self):
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

    def test_get_repository_uses_os_path_basename(self):
        """Test that service correctly extracts name using os.path.basename."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/test-repo")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/test-repo")

        # Verify the name matches what os.path.basename would return
        expected_name = os.path.basename("/home/user/test-repo")
        assert result is not None
        assert result.name == expected_name

    def test_get_repository_preserves_absolute_path(self):
        """Test that service preserves the absolute path as-is."""
        fake_port = FakeGitPort()
        test_path = "/absolute/path/to/repository"
        fake_port.add_git_repo(test_path)
        service = GitService(git_port=fake_port)

        result = service.get_repository(test_path + "/subdir")

        assert result is not None
        assert result.absolute_path == test_path
