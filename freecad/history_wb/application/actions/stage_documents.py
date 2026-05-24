# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for staging documents to git.
# This module provides the StageDocumentsAction which persists snapshot YAML files
# and stages both the original FCStd files and their corresponding YAML snapshots
# to the git repository using git add.
"""Application action for staging documents to git."""

from pathlib import Path

from ...domain.freecad_ports import DocumentLike, FreeCadPort
from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ...domain.git.paths import relative_git_path, to_git_path
from ...domain.snapshots import get_snapshot_yaml_path_for_document
from ...domain.snapshots.models import Snapshot
from ...infrastructure.persistence.snapshot_yaml import SnapshotYamlSerializer
from ...utils import Log
from .result_models import Result


__all__ = ["StageDocumentsAction"]


class StageDocumentsAction:
    """Stage documents to git by persisting snapshots and running git add."""

    def __init__(self, git_service: GitService, freecad_port: FreeCadPort) -> None:
        self._git_service = git_service
        self._freecad_port = freecad_port

    def _get_open_docs_by_git_path(self, repo: GitRepository) -> dict[str, DocumentLike]:
        """Return eligible open FreeCAD documents keyed by repository git path."""
        all_open_docs = self._freecad_port.get_all_open_documents()
        eligible_docs = self._git_service.get_eligible_docs(repo, list(all_open_docs))

        docs_by_git_path: dict[str, DocumentLike] = {}
        for doc in eligible_docs:
            doc_path = getattr(doc, "FileName", "")
            if not doc_path:
                continue
            git_path = relative_git_path(doc_path, repo.absolute_path)
            docs_by_git_path[git_path] = doc
        return docs_by_git_path

    def _save_open_doc_if_modified(self, doc: DocumentLike, git_path: str) -> Result | None:
        try:
            saved = self._freecad_port.save_document_if_modified(doc)
            if saved:
                Log.info(f"Saved modified open document before staging: {git_path}")
        except Exception as e:  # noqa: BLE001
            # Broad catch required: FreeCAD save adapters and tests can raise arbitrary exceptions.
            Log.exception(f"Failed to save open document before staging {git_path}: {e}")
            return Result.failure(f"Failed to save document before staging: {e}")
        return None

    def execute(self, repo: GitRepository, snapshots: list[Snapshot]) -> Result:
        """Stage documents by persisting snapshots and adding to git.

        For each snapshot:
        1. Determine the full file path (repo.absolute_path + git_path)
        2. Determine the snapshot directory using get_snapshot_directory
        3. Persist snapshot YAML to snapshot_dir/snapshot_name.yaml
        4. Collect both the FCStd path and YAML path for staging

        Args:
            repo: GitRepository containing the documents.
            snapshots: List of Snapshots to stage.

        Returns:
            Result containing True on success, or failure message on error.
        """
        if not snapshots:
            return Result.success(True)

        all_paths_to_stage: list[str] = []
        docs_by_git_path = self._get_open_docs_by_git_path(repo)

        for snapshot in snapshots:
            git_path = snapshot.git_path
            if not git_path:
                Log.warning(f"Snapshot has no git_path, cannot stage: {snapshot.document_name}")
                continue
            git_path = to_git_path(git_path)

            matching_doc = docs_by_git_path.get(git_path)
            if matching_doc is not None:
                save_result = self._save_open_doc_if_modified(matching_doc, git_path)
                if save_result is not None:
                    return save_result

            # Get the yaml path (relative to git_path) and make it absolute
            yaml_path_relative = get_snapshot_yaml_path_for_document(git_path)
            yaml_path = Path(repo.absolute_path) / yaml_path_relative

            # Create snapshot directory if it doesn't exist (use parent of yaml path)
            snapshot_dir = yaml_path.parent
            try:
                snapshot_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                Log.exception(f"Failed to create snapshot directory {snapshot_dir}: {e}")
                return Result.failure(f"Failed to create snapshot directory: {e}")

            # Persist snapshot to YAML
            try:
                SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
                Log.info(f"Persisted snapshot to {yaml_path}")
            except Exception as e:  # noqa: BLE001
                # Broad catch required: serialization backends may raise non-IO domain exceptions.
                Log.exception(f"Failed to persist snapshot for {git_path}: {e}")
                return Result.failure(f"Failed to persist snapshot: {e}")

            # Collect paths to stage (relative to git root)
            all_paths_to_stage.append(git_path)  # The FCStd file
            # Convert yaml_path to relative from repo root
            yaml_relative = relative_git_path(str(yaml_path), repo.absolute_path)
            all_paths_to_stage.append(yaml_relative)

        # Stage all files
        if all_paths_to_stage:
            success = self._git_service.stage_files(repo, all_paths_to_stage)
            if not success:
                return Result.failure("Failed to stage one or more files")
            Log.info(f"Staged {len(all_paths_to_stage)} files")

        return Result.success(True)
