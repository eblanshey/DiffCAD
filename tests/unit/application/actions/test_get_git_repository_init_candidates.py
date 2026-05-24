# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for git repository initialization candidate discovery.
"""Unit tests for GetGitRepositoryInitCandidatesAction."""

from unittest.mock import MagicMock

from freecad.history_wb.application.actions.get_git_repository_init_candidates import (
    GetGitRepositoryInitCandidatesAction,
)
from freecad.history_wb.domain.git.git_service import GitService

from tests.fakes.fake_freecad_port import FakeFreeCadPort
from tests.fakes.fake_git_port import FakeGitPort


def _doc(path: str) -> MagicMock:
    doc = MagicMock()
    doc.FileName = path
    return doc


class TestGetGitRepositoryInitCandidatesAction:
    """Tests for candidate discovery from open documents."""

    def test_returns_unique_parent_directories_for_saved_open_documents(self) -> None:
        fake_freecad = FakeFreeCadPort(
            open_documents=[
                _doc("/home/user/project/a.FCStd"),
                _doc("/home/user/project/b.FCStd"),
                _doc("/home/user/other/c.FCStd"),
            ]
        )
        action = GetGitRepositoryInitCandidatesAction(
            freecad_port=fake_freecad,
            git_service=GitService(FakeGitPort()),
        )

        result = action.execute()

        assert result.is_success is True
        assert [candidate.path for candidate in result.data] == [
            "/home/user/other",
            "/home/user/project",
        ]
        assert [candidate.is_available for candidate in result.data] == [True, True]

    def test_skips_unsaved_documents(self) -> None:
        fake_freecad = FakeFreeCadPort(open_documents=[_doc(""), _doc("/home/user/project/a.FCStd")])
        action = GetGitRepositoryInitCandidatesAction(
            freecad_port=fake_freecad,
            git_service=GitService(FakeGitPort()),
        )

        result = action.execute()

        assert result.is_success is True
        assert [candidate.path for candidate in result.data] == ["/home/user/project"]

    def test_disables_directories_inside_git_repository_with_reason(self) -> None:
        fake_git = FakeGitPort()
        fake_git.add_git_repo("/home/user/repo")

        fake_freecad = FakeFreeCadPort(
            open_documents=[
                _doc("/home/user/repo/model.FCStd"),
                _doc("/home/user/repo/sub/assembly.FCStd"),
                _doc("/home/user/plain/model.FCStd"),
            ]
        )
        action = GetGitRepositoryInitCandidatesAction(
            freecad_port=fake_freecad,
            git_service=GitService(fake_git),
        )

        result = action.execute()

        assert result.is_success is True
        assert [
            (candidate.path, candidate.is_available, candidate.existing_repository_path) for candidate in result.data
        ] == [
            ("/home/user/plain", True, None),
            ("/home/user/repo", False, "/home/user/repo"),
            ("/home/user/repo/sub", False, "/home/user/repo"),
        ]

    def test_fails_when_no_saved_documents_are_open(self) -> None:
        fake_freecad = FakeFreeCadPort(open_documents=[_doc(""), _doc("")])
        action = GetGitRepositoryInitCandidatesAction(
            freecad_port=fake_freecad,
            git_service=GitService(FakeGitPort()),
        )

        result = action.execute()

        assert result.is_success is False
        assert result.message == "No saved open documents found"

    def test_fails_when_no_documents_are_open(self) -> None:
        action = GetGitRepositoryInitCandidatesAction(
            freecad_port=FakeFreeCadPort(open_documents=[]),
            git_service=GitService(FakeGitPort()),
        )

        result = action.execute()

        assert result.is_success is False
        assert result.message == "No documents are open"
