# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GitCommit frozen dataclass contracts.
"""Unit tests for the GitCommit model."""

import dataclasses
from datetime import datetime

import pytest
from freecad.history_wb.domain.git import GitCommit


@pytest.fixture
def sample_commit() -> GitCommit:
    return GitCommit(
        id="abc123def456",
        message="Add new feature\n\nThis implements the new feature.",
        author="John Doe <john@example.com>",
        timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
    )


class TestGitCommit:
    """Tests for GitCommit construction and frozen behavior."""

    def test_creation_stores_all_fields(self, sample_commit: GitCommit) -> None:
        assert sample_commit.id == "abc123def456"
        assert sample_commit.message == "Add new feature\n\nThis implements the new feature."
        assert sample_commit.author == "John Doe <john@example.com>"
        assert sample_commit.timestamp == datetime.fromisoformat("2024-01-15T10:30:00+00:00")

    def test_frozen_prevents_modification(self, sample_commit: GitCommit) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            sample_commit.id = "new_id"  # type: ignore[misc]

    def test_equality_and_hash(self) -> None:
        c1 = GitCommit(id="same", message="msg", author="Auth", timestamp=datetime.fromisoformat("2024-01-01T00:00:00"))
        c2 = GitCommit(id="same", message="msg", author="Auth", timestamp=datetime.fromisoformat("2024-01-01T00:00:00"))
        c3 = GitCommit(id="diff", message="msg", author="Auth", timestamp=datetime.fromisoformat("2024-01-01T00:00:00"))

        assert c1 == c2
        assert hash(c1) == hash(c2)
        assert c1 != c3
        # Usable in sets and dicts
        assert len({c1, c2}) == 1
        assert {c1: "a", c3: "b"}[c3] == "b"
