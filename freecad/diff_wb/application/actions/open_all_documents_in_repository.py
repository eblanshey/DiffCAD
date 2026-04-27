# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Open all FreeCAD documents in a detected repository.
"""Application action for opening all .FCStd documents in a repository."""

from __future__ import annotations

import os

from ...domain.freecad_ports import FreeCadPort
from ...domain.git.models import GitRepository
from ...utils import Log
from .result_models import Result


class OpenAllDocumentsInRepositoryAction:
    """Open every .FCStd file in repository excluding dot-prefixed directories."""

    def __init__(self, freecad_port: FreeCadPort) -> None:
        self._freecad_port = freecad_port

    def execute(self, repo: GitRepository) -> Result:
        """Find and open all .FCStd files under repository path.

        Directory traversal skips directories whose basename starts with a dot.
        """
        opened_paths = list(self._iter_fcstd_paths(repo.absolute_path))

        for document_path in opened_paths:
            self._freecad_port.open_document(document_path)

        Log.info(f"Opened {len(opened_paths)} repository documents from {repo.absolute_path}")
        return Result.success(opened_paths)

    def _iter_fcstd_paths(self, repository_path: str) -> list[str]:
        """Collect all .FCStd paths excluding dot-prefixed directories."""
        fcstd_paths: list[str] = []

        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [directory for directory in dirs if not directory.startswith(".")]
            fcstd_paths.extend(os.path.join(root, filename) for filename in files if filename.endswith(".FCStd"))

        return fcstd_paths


__all__ = ["OpenAllDocumentsInRepositoryAction"]
