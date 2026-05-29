# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for restore_documents action orchestration and restore scopes.
"""Unit tests for RestoreDocumentsAction."""

from unittest.mock import patch

from freecad.history_wb.application.actions.restore_documents import (
    RestoreDocumentsAction,
    RestoreDocumentsRequest,
    RestoreScope,
    RestoreSource,
)
from freecad.history_wb.domain.git import GitRepository, GitService
from tests.fakes import FakeFreeCadPort, FakeGitPort, MockDocument


def test_all_fcstd_scope_uses_union_of_source_and_current_saved_paths() -> None:
    fake_git_port = FakeGitPort()
    fake_git_port.set_all_fcstd_paths("/repo", "abc123", ["a.FCStd"])
    fake_git_port.set_current_saved_fcstd_paths("/repo", ["b.FCStd"])
    service = GitService(git_port=fake_git_port)
    action = RestoreDocumentsAction(git_service=service, freecad_port=FakeFreeCadPort())
    repo = GitRepository(name="repo", absolute_path="/repo")

    result = action.execute(
        RestoreDocumentsRequest(
            repo=repo,
            source=RestoreSource.COMMIT,
            scope=RestoreScope.ALL_FCSTD,
            commit_hash="abc123",
        )
    )

    assert result.is_success is True
    assert fake_git_port.get_last_restore_call() == ("/repo", "abc123", ["a.FCStd", "b.FCStd"])


def test_single_restore_closes_project_docs_reopens_and_restores_active_doc() -> None:
    active_doc = MockDocument("/repo/a.FCStd", name="DocA")
    other_project_doc = MockDocument("/repo/b.FCStd", name="DocB")
    outside_doc = MockDocument("/outside/x.FCStd", name="Outside")
    freecad_port = FakeFreeCadPort(
        active_document=active_doc, open_documents=[active_doc, other_project_doc, outside_doc]
    )

    fake_git_port = FakeGitPort()
    fake_git_port.set_file_contents("abc123", "a.FCStd", "exists")
    service = GitService(git_port=fake_git_port)
    action = RestoreDocumentsAction(git_service=service, freecad_port=freecad_port)
    repo = GitRepository(name="repo", absolute_path="/repo")

    with patch("os.path.exists", return_value=True):
        result = action.execute(
            RestoreDocumentsRequest(
                repo=repo,
                source=RestoreSource.COMMIT,
                scope=RestoreScope.SINGLE_PATH,
                commit_hash="abc123",
                paths=["a.FCStd"],
            )
        )

    assert result.is_success is True
    assert freecad_port.closed_document_names == ["DocA", "DocB"]
    assert freecad_port.opened_document_paths == ["/repo/a.FCStd", "/repo/b.FCStd"]
    assert freecad_port.active_document_names == ["DocA"]


def test_reopens_documents_even_when_restore_fails() -> None:
    doc = MockDocument("/repo/a.FCStd", name="DocA")
    freecad_port = FakeFreeCadPort(active_document=doc, open_documents=[doc])

    fake_git_port = FakeGitPort()
    fake_git_port.set_file_contents(None, "a.FCStd", "exists")
    fake_git_port.restore_paths_from_ref = lambda git_root, commit, paths: False  # type: ignore[method-assign]

    service = GitService(git_port=fake_git_port)
    action = RestoreDocumentsAction(git_service=service, freecad_port=freecad_port)
    repo = GitRepository(name="repo", absolute_path="/repo")

    with patch("os.path.exists", return_value=True):
        result = action.execute(
            RestoreDocumentsRequest(
                repo=repo,
                source=RestoreSource.INDEX,
                scope=RestoreScope.SINGLE_PATH,
                paths=["a.FCStd"],
            )
        )

    assert result.is_success is False
    assert freecad_port.closed_document_names == ["DocA"]
    assert freecad_port.opened_document_paths == ["/repo/a.FCStd"]
