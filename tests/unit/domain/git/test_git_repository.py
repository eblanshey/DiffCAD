# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the GitRepository model including creation,
# property access, immutability verification, and string representation.
"""Unit tests for the GitRepository model."""

import dataclasses

from freecad.diff_wb.domain.git import GitRepository


class TestGitRepository:
    """Tests for the GitRepository dataclass."""

    def test_creation_with_valid_values(self):
        """Test GitRepository creation with valid name and absolute_path."""
        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")

        assert repo.name == "my_project"
        assert repo.absolute_path == "/home/user/my_project"

    def test_creation_with_root_directory_name(self):
        """Test GitRepository creation with a root-level directory name."""
        repo = GitRepository(name="project", absolute_path="/var/www/project")

        assert repo.name == "project"
        assert repo.absolute_path == "/var/www/project"

    def test_creation_with_nested_path(self):
        """Test GitRepository creation with a deeply nested path."""
        repo = GitRepository(name="deep_project", absolute_path="/home/user/documents/work/projects/deep_project")

        assert repo.name == "deep_project"
        assert repo.absolute_path == "/home/user/documents/work/projects/deep_project"

    def test_creation_with_special_characters_in_name(self):
        """Test GitRepository creation with special characters in name."""
        repo = GitRepository(name="my-project_v2.0", absolute_path="/home/user/my-project_v2.0")

        assert repo.name == "my-project_v2.0"
        assert repo.absolute_path == "/home/user/my-project_v2.0"

    def test_frozen_dataclass_immutability(self):
        """Test that GitRepository is frozen (immutable)."""
        repo = GitRepository(name="test_project", absolute_path="/path/to/test_project")

        # Attempting to modify should raise an error
        try:
            repo.name = "new_name"  # type: ignore[assignment]
            raise AssertionError("Expected FrozenInstanceError")
        except dataclasses.FrozenInstanceError:
            pass  # Expected behavior

    def test_hash_functionality(self):
        """Test that GitRepository instances are hashable."""
        repo1 = GitRepository(name="project1", absolute_path="/path/to/project1")
        repo2 = GitRepository(name="project2", absolute_path="/path/to/project2")

        # Should be able to use in sets and as dict keys
        repo_set = {repo1, repo2}
        assert len(repo_set) == 2

        repo_dict = {repo1: "value1"}
        assert repo_dict[repo1] == "value1"

    def test_equality_same_values(self):
        """Test equality of GitRepository instances with same values."""
        repo1 = GitRepository(name="my_project", absolute_path="/home/user/my_project")
        repo2 = GitRepository(name="my_project", absolute_path="/home/user/my_project")

        assert repo1 == repo2
        assert hash(repo1) == hash(repo2)

    def test_inequality_different_names(self):
        """Test inequality when names differ."""
        repo1 = GitRepository(name="project_a", absolute_path="/home/user/project")
        repo2 = GitRepository(name="project_b", absolute_path="/home/user/project")

        assert repo1 != repo2

    def test_inequality_different_paths(self):
        """Test inequality when paths differ."""
        repo1 = GitRepository(name="project", absolute_path="/home/user/project")
        repo2 = GitRepository(name="project", absolute_path="/var/www/project")

        assert repo1 != repo2

    def test_string_representation(self):
        """Test the string representation of GitRepository."""
        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")

        expected = "my_project (/home/user/my_project)"
        assert str(repo) == expected

    def test_string_representation_with_complex_path(self):
        """Test string representation with complex path."""
        repo = GitRepository(name="complex-project", absolute_path="/home/user/documents/work/complex-project")

        expected = "complex-project (/home/user/documents/work/complex-project)"
        assert str(repo) == expected

    def test_repr_output(self):
        """Test that repr output contains key information."""
        repo = GitRepository(name="test_repo", absolute_path="/path/to/test_repo")

        repr_str = repr(repo)
        assert "test_repo" in repr_str
        assert "/path/to/test_repo" in repr_str

    def test_with_empty_name(self):
        """Test GitRepository creation with empty name (edge case)."""
        repo = GitRepository(name="", absolute_path="/some/path")

        assert repo.name == ""
        assert repo.absolute_path == "/some/path"

    def test_with_root_path(self):
        """Test GitRepository with root-like path."""
        repo = GitRepository(name="root_project", absolute_path="/root_project")

        assert repo.name == "root_project"
        assert repo.absolute_path == "/root_project"
