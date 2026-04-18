# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GetDirtyDocumentsAction using mock dependencies.
# Tests cover returning dirty paths when some documents are dirty, and returning empty
# list when all documents are clean.
"""Unit tests for GetDirtyDocumentsAction."""

from unittest.mock import MagicMock

from freecad.diff_wb.application.actions.get_dirty_documents import GetDirtyDocumentsAction
from freecad.diff_wb.domain.git.models import GitRepository


def test_get_dirty_documents_returns_dirty_paths() -> None:
    """Given documents with some dirty, returns list of dirty git paths."""
    # Setup
    mock_git_service = MagicMock()
    mock_git_service.get_dirty_documents.return_value = ["doc1.FCStd", "doc3.FCStd"]

    action = GetDirtyDocumentsAction(git_service=mock_git_service)
    repo = GitRepository(name="test", absolute_path="/path/to/repo")
    documents = [MagicMock(FileName="/path/to/repo/doc1.FCStd"), MagicMock(FileName="/path/to/repo/doc2.FCStd")]

    # Execute
    result = action.execute(repo, documents)  # type: ignore[arg-type]

    # Assert
    assert result.is_success
    assert result.data == ["doc1.FCStd", "doc3.FCStd"]


def test_get_dirty_documents_empty_list_when_clean() -> None:
    """Given all documents clean, returns empty list."""
    # Setup
    mock_git_service = MagicMock()
    mock_git_service.get_dirty_documents.return_value = []

    action = GetDirtyDocumentsAction(git_service=mock_git_service)
    repo = GitRepository(name="test", absolute_path="/path/to/repo")
    documents = [MagicMock(FileName="/path/to/repo/doc.FCStd")]

    # Execute
    result = action.execute(repo, documents)  # type: ignore[arg-type]

    # Assert
    assert result.is_success
    assert result.data == []
