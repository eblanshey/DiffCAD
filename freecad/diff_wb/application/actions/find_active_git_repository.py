# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the FindActiveGitRepositoryAction class
# which is responsible for finding the active git repository from open FreeCAD documents.
# It uses FreeCadPort to get the active document and GitService to find the repository.
"""Application action for finding active git repository."""

from ...domain.freecad_ports import FreeCadPort
from ...domain.git.git_service import GitService
from .result_models import Result


class FindActiveGitRepositoryAction:
    """Find git repository from open FreeCAD documents.

    This action determines the active git repository by:
    1. Getting the active document from FreeCAD
    2. Extracting the document's file path
    3. Using GitService to find the git repository containing that path

    Attributes:
        _freecad_port: The FreeCadPort instance for FreeCAD operations.
        _git_service: The GitService instance for git repository detection.
    """

    def __init__(
        self,
        freecad_port: FreeCadPort,
        git_service: GitService,
    ) -> None:
        """Initialize the action with required dependencies.

        Args:
            freecad_port: Port interface for FreeCAD document operations.
            git_service: Service for git repository detection.
        """
        self._freecad_port = freecad_port
        self._git_service = git_service

    def execute(self) -> Result:
        """Find active git repository from open documents.

        Returns:
            Result with GitRepository if found, or failure result with error message.
        """
        # 1. Get active document from FreeCadPort
        doc = self._freecad_port.get_active_document()
        if doc is None:
            return Result.failure("No active document")

        # 2. Try to get document file path
        try:
            doc_path = doc.FileName  # FreeCAD documents have FileName property
        except AttributeError:
            return Result.failure("Document has no file path (unsaved)")

        if not doc_path:
            return Result.failure("Document is not saved")

        # 3. Use GitService to find repository
        repo = self._git_service.get_repository(doc_path)
        if repo is None:
            return Result.failure("No git repository found for open documents")

        return Result.success(repo)
