# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the FindActiveGitRepositoryAction class
# which is responsible for finding the active git repository from open FreeCAD documents.
# It iterates through all open documents, skipping unsaved ones, and uses GitService
# to find the first document that is in a git repository.
"""Application action for finding active git repository."""

from ...domain.freecad_ports import FreeCadPort
from ...domain.git.git_service import GitService
from ...utils import Log
from .result_models import Result


class FindActiveGitRepositoryAction:
    """Find git repository from open FreeCAD documents.

    This action determines the active git repository by:
    1. Getting all open documents from FreeCAD
    2. Iterating through them, skipping unsaved documents
    3. Using GitService to find the git repository for each saved document
    4. Returning the first repository found

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

        Iterates through all open documents, skipping unsaved ones,
        and returns the first document that is in a git repository.

        Returns:
            Result with GitRepository if found, or failure result with error message.
        """
        # Get all open documents
        docs = self._freecad_port.get_all_open_documents()
        if not docs:
            return Result.failure("No documents are open")

        # Iterate through all documents, skipping unsaved ones
        for doc in docs:
            doc_path = doc.FileName  # FreeCAD documents have FileName property

            # Skip unsaved documents (empty FileName)
            if not doc_path:
                Log.debug("Skipping unsaved document")
                continue

            # Try to find git repository for this document
            repo = self._git_service.get_repository(doc_path)
            if repo is not None:
                Log.info(f"Git repository detected: {repo.name} ({repo.absolute_path})")
                return Result.success(repo)

        return Result.failure("No git repository found for open documents")
