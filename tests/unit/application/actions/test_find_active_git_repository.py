# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for FindActiveGitRepositoryAction orchestration and result contracts.
"""Unit tests for FindActiveGitRepositoryAction."""

from unittest.mock import MagicMock

from freecad.history_wb.application.actions.find_active_git_repository import (
    FindActiveGitRepositoryAction,
)
from freecad.history_wb.domain.git.git_service import GitService
from freecad.history_wb.domain.git.models import GitRepository

from tests.fakes.fake_freecad_port import FakeFreeCadPort
from tests.fakes.fake_git_port import FakeGitPort


class TestFindActiveGitRepositoryAction:
    """Tests for FindActiveGitRepositoryAction execute behavior."""

    def test_execute_returns_repository_when_document_in_git_repo(self) -> None:
        fake_freecad = FakeFreeCadPort()
        fake_git = FakeGitPort()
        fake_git.add_git_repo("/home/user/project")

        mock_doc = MagicMock()
        mock_doc.FileName = "/home/user/project/src/file.FCStd"
        fake_freecad._open_documents = [mock_doc]

        service = GitService(fake_git)
        action = FindActiveGitRepositoryAction(fake_freecad, service)

        result = action.execute()

        assert result.is_success is True
        assert isinstance(result.data, GitRepository)
        assert result.data.name == "project"
        assert result.data.absolute_path == "/home/user/project"

    def test_execute_fails_when_no_documents_open(self) -> None:
        fake_freecad = FakeFreeCadPort(open_documents=[])
        service = GitService(FakeGitPort())
        action = FindActiveGitRepositoryAction(fake_freecad, service)

        result = action.execute()

        assert result.is_success is False
        assert result.data is None
        assert result.message == "No documents are open"

    def test_execute_fails_when_document_not_in_git_repo(self) -> None:
        fake_freecad = FakeFreeCadPort()
        mock_doc = MagicMock()
        mock_doc.FileName = "/tmp/unsaved.FCStd"
        fake_freecad._open_documents = [mock_doc]

        service = GitService(FakeGitPort())
        action = FindActiveGitRepositoryAction(fake_freecad, service)

        result = action.execute()

        assert result.is_success is False
        assert result.message == "No git repository found for open documents"

    def test_execute_skips_unsaved_documents(self) -> None:
        fake_freecad = FakeFreeCadPort()
        fake_git = FakeGitPort()
        fake_git.add_git_repo("/home/user/saved")

        unsaved = MagicMock()
        unsaved.FileName = ""
        saved = MagicMock()
        saved.FileName = "/home/user/saved/file.FCStd"
        fake_freecad._open_documents = [unsaved, saved]

        service = GitService(fake_git)
        action = FindActiveGitRepositoryAction(fake_freecad, service)

        result = action.execute()

        assert result.is_success is True
        assert result.data.name == "saved"

    def test_execute_fails_when_all_documents_unsaved(self) -> None:
        fake_freecad = FakeFreeCadPort()
        doc1 = MagicMock()
        doc1.FileName = ""
        doc2 = MagicMock()
        doc2.FileName = ""
        fake_freecad._open_documents = [doc1, doc2]

        service = GitService(FakeGitPort())
        action = FindActiveGitRepositoryAction(fake_freecad, service)

        result = action.execute()

        assert result.is_success is False
        assert result.message == "No git repository found for open documents"
