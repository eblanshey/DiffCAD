# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Discover saved open-document parent directories and mark
# which can be initialized as new git repositories.
"""Application action for git repository initialization candidates."""

from __future__ import annotations

import os

from ...domain.freecad_ports import FreeCadPort
from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepositoryInitCandidate
from ...utils import Log
from .result_models import Result


class GetGitRepositoryInitCandidatesAction:
    """Discover repository initialization candidates from open documents."""

    def __init__(self, freecad_port: FreeCadPort, git_service: GitService) -> None:
        self._freecad_port = freecad_port
        self._git_service = git_service

    def execute(self) -> Result:
        """Return candidate directories derived from saved open documents."""
        documents = self._freecad_port.get_all_open_documents()
        if not documents:
            return Result.failure("No documents are open")

        unique_directories: set[str] = set()

        for document in documents:
            document_path = getattr(document, "FileName", "")
            if not document_path:
                Log.debug("Skipping unsaved document for repository initialization candidates")
                continue

            parent_directory = os.path.abspath(os.path.dirname(document_path))
            unique_directories.add(parent_directory)

        if not unique_directories:
            return Result.failure("No saved open documents found")

        candidates = [self._create_candidate(path) for path in sorted(unique_directories)]
        return Result.success(candidates)

    def _create_candidate(self, path: str) -> GitRepositoryInitCandidate:
        existing_repository = self._git_service.get_repository(path)
        if existing_repository is None:
            return GitRepositoryInitCandidate(path=path, is_available=True)
        return GitRepositoryInitCandidate(
            path=path,
            is_available=False,
            existing_repository_path=existing_repository.absolute_path,
        )
