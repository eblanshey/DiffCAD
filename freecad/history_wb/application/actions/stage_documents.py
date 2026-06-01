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

    def _save_open_doc(self, doc: DocumentLike, git_path: str) -> Result | None:
        """Unconditionally save an open document before staging.

        Staging requires FCStd on disk match snapshot being persisted.
        """
        try:
            self._freecad_port.save_document(doc)
            Log.info(f"Saved open document before staging: {git_path}")
        except Exception as e:  # noqa: BLE001
            # Broad catch required: FreeCAD save adapters and tests can raise arbitrary exceptions.
            Log.exception(f"Failed to save open document before staging {git_path}: {e}")
            return Result.failure(f"Failed to save document before staging: {e}")
        return None

    def _validate_no_conflicts(self, snapshots: list[Snapshot], deleted_paths: list[str]) -> Result | None:
        """Reject inputs where same path appears in snapshot and deleted lists."""
        snapshot_git_paths = {to_git_path(snapshot.git_path) for snapshot in snapshots if snapshot.git_path}
        deleted_git_paths = {to_git_path(path) for path in deleted_paths}
        conflicting_paths = snapshot_git_paths & deleted_git_paths
        if not conflicting_paths:
            return None
        conflicts = ", ".join(sorted(conflicting_paths))
        Log.warning(f"Cannot stage paths as both present and deleted: {conflicts}")
        return Result.failure(f"Cannot stage paths as both present and deleted: {conflicts}")

    def _collect_snapshot_and_yaml_paths(
        self,
        repo: GitRepository,
        snapshots: list[Snapshot],
        docs_by_git_path: dict[str, DocumentLike],
        all_paths_to_stage: list[str],
    ) -> Result | None:
        """Persist snapshot YAML files and collect FCStd/YAML stage paths."""

        # Persist snapshots and collect paths.
        for snapshot in snapshots:
            raw_git_path = snapshot.git_path
            if not raw_git_path:
                Log.warning(f"Snapshot has no git_path, cannot stage: {snapshot.document_name}")
                continue
            git_path = to_git_path(raw_git_path)

            # Save open document unconditionally before writing YAML.
            matching_doc = docs_by_git_path.get(git_path)
            if matching_doc is not None:
                save_result = self._save_open_doc(matching_doc, git_path)
                if save_result is not None:
                    return save_result

            # Build absolute YAML path and ensure directory exists.
            yaml_path_relative = get_snapshot_yaml_path_for_document(git_path)
            yaml_path = Path(repo.absolute_path) / yaml_path_relative
            snapshot_dir = yaml_path.parent
            try:
                snapshot_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                Log.exception(f"Failed to create snapshot directory {snapshot_dir}: {e}")
                return Result.failure(f"Failed to create snapshot directory: {e}")

            # Write snapshot YAML.
            try:
                SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
                Log.info(f"Persisted snapshot to {yaml_path}")
            except Exception as e:  # noqa: BLE001
                # Broad catch required: serialization backends may raise non-IO domain exceptions.
                Log.exception(f"Failed to persist snapshot for {git_path}: {e}")
                return Result.failure(f"Failed to persist snapshot: {e}")

            all_paths_to_stage.append(git_path)
            all_paths_to_stage.append(relative_git_path(str(yaml_path), repo.absolute_path))
        return None

    def _collect_deleted_paths(
        self,
        repo: GitRepository,
        deleted_paths: list[str],
        docs_by_git_path: dict[str, DocumentLike],
        all_paths_to_stage: list[str],
    ) -> Result | None:
        """Collect FCStd/YAML deletion stage paths and clean YAML files from disk."""

        # Stage deletions.
        for deleted_path in deleted_paths:
            git_path = to_git_path(deleted_path)

            # Open doc for a deleted path -- do not save (would resurrect file).
            if docs_by_git_path.get(git_path) is not None:
                Log.warning(f"Deleted path {git_path} has an open document. Not saving; git deletion takes priority.")

            # Compute YAML path for cleanup.
            yaml_git_path = str(get_snapshot_yaml_path_for_document(git_path))
            yaml_abs_path = Path(repo.absolute_path) / yaml_git_path

            # Remove YAML from disk if it still exists.
            try:
                yaml_abs_path.unlink(missing_ok=True)
            except OSError as e:
                Log.exception(f"Failed to delete snapshot YAML for {git_path}: {e}")
                return Result.failure(f"Failed to delete snapshot YAML: {e}")

            # Always stage the FCStd deletion.
            all_paths_to_stage.append(git_path)

            # Stage YAML deletion only if it was tracked.
            # Staging an untracked missing path causes git add to fail with a
            # pathspec error, so guard with an index existence check.
            if self._git_service.file_exists(repo, None, yaml_git_path):
                all_paths_to_stage.append(yaml_git_path)
        return None

    def execute(self, repo: GitRepository, snapshots: list[Snapshot], deleted_paths: list[str]) -> Result:
        """Stage documents by persisting snapshots and adding to git.

        For each snapshot:
        1. Determine the full file path (repo.absolute_path + git_path)
        2. Determine the snapshot directory using get_snapshot_directory
        3. Persist snapshot YAML to snapshot_dir/snapshot_name.yaml
        4. Collect both the FCStd path and YAML path for staging

        Args:
            repo: GitRepository containing the documents.
            snapshots: List of Snapshots to stage.
            deleted_paths: Git paths of deleted FCStd files to stage.

        Returns:
            Result containing True on success, or failure message on error.
        """
        conflict_result = self._validate_no_conflicts(snapshots, deleted_paths)
        if conflict_result is not None:
            return conflict_result

        # Both empty -- nothing to stage.
        if not snapshots and not deleted_paths:
            return Result.success(True)

        all_paths_to_stage: list[str] = []
        docs_by_git_path = self._get_open_docs_by_git_path(repo)

        snapshot_collect_result = self._collect_snapshot_and_yaml_paths(
            repo, snapshots, docs_by_git_path, all_paths_to_stage
        )
        if snapshot_collect_result is not None:
            return snapshot_collect_result

        deleted_collect_result = self._collect_deleted_paths(repo, deleted_paths, docs_by_git_path, all_paths_to_stage)
        if deleted_collect_result is not None:
            return deleted_collect_result

        # Deduplicate while preserving first-seen order. A plain set would make
        # ordering nondeterministic, which makes logs and tests harder to reason about.
        deduped_paths_to_stage = list(dict.fromkeys(all_paths_to_stage))

        # Stage all collected paths.
        if deduped_paths_to_stage:
            success = self._git_service.stage_files(repo, deduped_paths_to_stage)
            if not success:
                return Result.failure("Failed to stage one or more files")
            Log.info(f"Staged {len(deduped_paths_to_stage)} files")

        return Result.success(True)
