# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for getting eligible open documents.
# This module provides the GetOpenEligibleDocumentsAction which retrieves all
# open FreeCAD documents and filters them to those within the git repository.
"""Application action for getting eligible open documents."""

from ...domain.freecad_ports import FreeCadPort
from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from .result_models import Result


__all__ = ["GetOpenEligibleDocumentsAction"]


class GetOpenEligibleDocumentsAction:
    """Get all open documents that are within the git repository.

    Returns an empty list (not a failure) when no documents are eligible,
    either because no documents are open or all documents are outside the
    git repository.
    """

    def __init__(
        self,
        freecad_port: FreeCadPort,
        git_service: GitService,
    ) -> None:
        self._freecad_port = freecad_port
        self._git_service = git_service

    def execute(self, repo: GitRepository) -> Result:
        """Execute the action to get eligible open documents.

        Args:
            repo: GitRepository to filter documents against.

        Returns:
            Result containing list of DocumentLike on success.
        """
        all_docs = self._freecad_port.get_all_open_documents()
        eligible = self._git_service.get_eligible_docs(repo, list(all_docs))
        return Result.success(eligible)
