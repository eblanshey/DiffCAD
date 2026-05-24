# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for creating snapshot from working tree document.
# This module provides the CreateDocumentSnapshotForWorkingTreeAction which creates
# a Snapshot domain model from a FreeCAD document that is currently open and within
# the git repository.
"""Application action for creating snapshot from working tree document."""

from ...domain.freecad_ports import DocumentLike
from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ...domain.git.paths import relative_git_path
from ...domain.snapshots.gui_extractor import SnapshotExtractor
from ...utils import Log
from .result_models import Result


__all__ = ["CreateDocumentSnapshotForWorkingTreeAction"]


class CreateDocumentSnapshotForWorkingTreeAction:
    """Create a snapshot for a document in the working tree."""

    def __init__(
        self,
        git_service: GitService,
        extractor: SnapshotExtractor,
    ) -> None:
        self._git_service = git_service
        self._extractor = extractor

    def execute(self, repo: GitRepository, document: DocumentLike) -> Result:
        """Execute the action to create a snapshot for a working tree document.

        Args:
            repo: GitRepository containing the document.
            document: DocumentLike instance representing the FreeCAD document.

        Returns:
            Result containing Snapshot on success, or failure message.
        """
        doc_path = getattr(document, "FileName", "")
        if not doc_path:
            Log.warning("Document has no file path (unsaved)")
            return Result.failure("Document has no file path (unsaved)")

        eligible_docs = self._git_service.get_eligible_docs(repo, [document])
        if not eligible_docs:
            Log.warning(f"Document {doc_path} is not in the git repository")
            return Result.failure("Document is not in the git repository")

        git_path = relative_git_path(doc_path, repo.absolute_path)
        try:
            snapshot = self._extractor.extract_tree(document, git_path=git_path)
        except Exception as e:  # noqa: BLE001
            # Broad catch required: extractor port intentionally shields arbitrary FreeCAD/runtime failures.
            Log.exception(f"Failed to extract snapshot for {git_path}: {e}")
            return Result.failure(f"Failed to extract snapshot: {e}")

        Log.info(f"Created working tree snapshot for {git_path}")
        return Result.success(snapshot)
