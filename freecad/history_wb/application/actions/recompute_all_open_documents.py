# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Recompute every open FreeCAD document through application action.
"""Application action for recomputing all open FreeCAD documents."""

from __future__ import annotations

from ...domain.freecad_ports import FreeCadPort
from ...utils import Log
from .result_models import Result


class RecomputeAllOpenDocumentsAction:
    """Recompute all currently open documents in FreeCAD."""

    def __init__(self, freecad_port: FreeCadPort) -> None:
        self._freecad_port = freecad_port

    def execute(self) -> Result:
        """Recompute every open document and return recomputed file names."""
        open_documents = self._freecad_port.get_all_open_documents()

        recomputed_documents: list[str] = []
        for document in open_documents:
            document.recompute()
            recomputed_documents.append(document.FileName)

        Log.info(f"Recomputed {len(recomputed_documents)} open documents")
        return Result.success(recomputed_documents)


__all__ = ["RecomputeAllOpenDocumentsAction"]
