# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for staging documents to git.
# This module provides the StageDocumentsAction which persists snapshot YAML files
# and stages both the original FCStd files and their corresponding YAML snapshots
# to the git repository using git add.
"""Application action for staging documents to git."""

import os
from pathlib import Path

from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ...domain.snapshots import get_snapshot_directory_for_document
from ...domain.snapshots.models import Snapshot
from ...infrastructure.persistence.snapshot_yaml import SnapshotYamlSerializer
from ...utils import Log
from .result_models import Result


__all__ = ["StageDocumentsAction"]


class StageDocumentsAction:
    """Stage documents to git by persisting snapshots and running git add."""

    def __init__(self, git_service: GitService) -> None:
        self._git_service = git_service

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

        for snapshot in snapshots:
            git_path = snapshot.git_path
            if not git_path:
                Log.warning(f"Snapshot has no git_path, cannot stage: {snapshot.document_name}")
                continue

            # Compute full path to the FCStd file
            fcstd_path = Path(repo.absolute_path) / git_path

            # Get the snapshot directory using the pure function
            snapshot_dir = get_snapshot_directory_for_document(str(fcstd_path))

            # Create snapshot directory if it doesn't exist
            try:
                snapshot_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                Log.exception(f"Failed to create snapshot directory {snapshot_dir}: {e}")
                return Result.failure(f"Failed to create snapshot directory: {e}")

            # Determine YAML filename (use document name without extension)
            doc_name = os.path.splitext(os.path.basename(git_path))[0]
            yaml_filename = f"{doc_name}.yaml"
            yaml_path = snapshot_dir / yaml_filename

            # Persist snapshot to YAML
            try:
                SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
                Log.info(f"Persisted snapshot to {yaml_path}")
            except Exception as e:
                Log.exception(f"Failed to persist snapshot for {git_path}: {e}")
                return Result.failure(f"Failed to persist snapshot: {e}")

            # Collect paths to stage (relative to git root)
            all_paths_to_stage.append(git_path)  # The FCStd file
            # The YAML path is absolute, convert to relative
            yaml_relative = str(yaml_path)[len(repo.absolute_path) :].lstrip("/")
            all_paths_to_stage.append(yaml_relative)

        # Stage all files
        if all_paths_to_stage:
            success = self._git_service.stage_files(repo, all_paths_to_stage)
            if not success:
                return Result.failure("Failed to stage one or more files")
            Log.info(f"Staged {len(all_paths_to_stage)} files")

        return Result.success(True)
