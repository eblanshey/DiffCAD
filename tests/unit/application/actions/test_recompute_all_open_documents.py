# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for recomputing all open FreeCAD documents action.
"""Unit tests for RecomputeAllOpenDocumentsAction."""

from __future__ import annotations

from typing import cast

from freecad.history_wb.application.actions.recompute_all_open_documents import (
    RecomputeAllOpenDocumentsAction,
)
from freecad.history_wb.domain.freecad_ports import DocumentLike, DocumentObjectLike

from tests.fakes.fake_freecad_port import FakeFreeCadPort


class _RecomputableDocument:
    """Simple document test double tracking recompute calls."""

    def __init__(self, file_name: str) -> None:
        self.FileName = file_name
        self.Objects: list[DocumentObjectLike] = []
        self.recompute_call_count = 0

    def recompute(self) -> None:
        self.recompute_call_count += 1

    def getObject(self, name: str) -> DocumentObjectLike | None:  # noqa: N802
        return None

    def save(self) -> None:
        return None


class TestRecomputeAllOpenDocumentsAction:
    """Tests for RecomputeAllOpenDocumentsAction."""

    def test_execute_recomputes_every_open_document(self) -> None:
        """Action calls recompute once for every open document."""
        first_doc = _RecomputableDocument("/home/user/dir/first.FCStd")
        second_doc = _RecomputableDocument("/home/user/dir/second.FCStd")
        fake_port = FakeFreeCadPort(
            open_documents=[
                cast(DocumentLike, first_doc),
                cast(DocumentLike, second_doc),
            ]
        )

        action = RecomputeAllOpenDocumentsAction(fake_port)

        result = action.execute()

        assert result.is_success is True
        assert result.data == ["/home/user/dir/first.FCStd", "/home/user/dir/second.FCStd"]
        assert first_doc.recompute_call_count == 1
        assert second_doc.recompute_call_count == 1

    def test_execute_succeeds_with_no_open_documents(self) -> None:
        """Action returns success with empty data when no docs are open."""
        fake_port = FakeFreeCadPort(open_documents=[])
        action = RecomputeAllOpenDocumentsAction(fake_port)

        result = action.execute()

        assert result.is_success is True
        assert result.data == []
