# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for FreeCadPortAdapter modified-save behavior.
"""Unit tests for FreeCadPortAdapter.save_document_if_modified."""

from unittest.mock import MagicMock, PropertyMock

from freecad.history_wb.domain.freecad_ports import FreeCadContext
from freecad.history_wb.infrastructure.freecad.ports import FreeCadPortAdapter


class TestFreeCadPortAdapterSaveIfModified:
    def test_modified_gui_document_saves_and_returns_true(self) -> None:
        doc = MagicMock()
        doc.Name = "Doc"

        gui_doc = MagicMock()
        type(gui_doc).Modified = PropertyMock(return_value=True)

        gui = MagicMock()
        gui.getDocument.return_value = gui_doc

        ctx = FreeCadContext(app=MagicMock(), gui=gui)  # type: ignore[arg-type]
        adapter = FreeCadPortAdapter(ctx)

        result = adapter.save_document_if_modified(doc)

        assert result is True
        doc.save.assert_called_once_with()

    def test_unmodified_gui_document_does_not_save_and_returns_false(self) -> None:
        doc = MagicMock()
        doc.Name = "Doc"

        gui_doc = MagicMock()
        type(gui_doc).Modified = PropertyMock(return_value=False)

        gui = MagicMock()
        gui.getDocument.return_value = gui_doc

        ctx = FreeCadContext(app=MagicMock(), gui=gui)  # type: ignore[arg-type]
        adapter = FreeCadPortAdapter(ctx)

        result = adapter.save_document_if_modified(doc)

        assert result is False
        doc.save.assert_not_called()

    def test_missing_gui_document_does_not_save_and_returns_false(self) -> None:
        doc = MagicMock()
        doc.Name = "Doc"

        gui = MagicMock()
        gui.getDocument.return_value = None

        ctx = FreeCadContext(app=MagicMock(), gui=gui)  # type: ignore[arg-type]
        adapter = FreeCadPortAdapter(ctx)

        result = adapter.save_document_if_modified(doc)

        assert result is False
        doc.save.assert_not_called()
