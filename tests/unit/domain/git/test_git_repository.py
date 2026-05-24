# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GitRepository frozen dataclass contracts.
"""Unit tests for the GitRepository model."""

import dataclasses

import pytest
from freecad.history_wb.domain.git import GitRepository


@pytest.fixture
def sample_repo() -> GitRepository:
    return GitRepository(name="my_project", absolute_path="/home/user/my_project")


class TestGitRepository:
    """Tests for GitRepository construction and frozen behavior."""

    def test_creation_stores_fields(self, sample_repo: GitRepository) -> None:
        assert sample_repo.name == "my_project"
        assert sample_repo.absolute_path == "/home/user/my_project"

    def test_frozen_prevents_modification(self, sample_repo: GitRepository) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            sample_repo.name = "new_name"  # type: ignore[misc]

    def test_equality_and_hash(self) -> None:
        r1 = GitRepository(name="proj", absolute_path="/path/proj")
        r2 = GitRepository(name="proj", absolute_path="/path/proj")
        r3 = GitRepository(name="other", absolute_path="/path/other")

        assert r1 == r2
        assert hash(r1) == hash(r2)
        assert r1 != r3
        assert len({r1, r2}) == 1
