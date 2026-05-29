# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for creating snapshot from git commit or index.
"""Application action for creating snapshot from a git commit or index."""

from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ...domain.git.paths import to_git_path
from ...domain.snapshots import get_snapshot_yaml_path_for_document
from ...domain.snapshots.serializer import SnapshotDeserializer
from ...utils import Log
from .result_models import Result, SnapshotLoadResult, SnapshotLoadStatus


__all__ = ["CreateDocumentSnapshotForCommitAction"]


class CreateDocumentSnapshotForCommitAction:
    """Create a snapshot from a document at a specific git commit or from the index.

    This extracts the YAML snapshot file from git (either from the index or a specific
    commit) and deserializes it to create a Snapshot object.
    """

    def __init__(self, git_service: GitService, snapshot_deserializer: SnapshotDeserializer) -> None:
        """Initialize with GitService.

        Args:
            git_service: GitService for git operations.
            snapshot_deserializer: Snapshot deserializer port implementation.
        """
        self._git_service = git_service
        self._snapshot_deserializer = snapshot_deserializer

    def execute(self, repo: GitRepository, commit: str | None, fcstd_git_path: str) -> Result:
        """Create a snapshot from a git commit or index.

        When `commit` is None, retrieves the YAML snapshot from the git index.
        When `commit` is specified, retrieves from that commit.

        The `fcstd_git_path` is the path to the FCStd file (e.g., "path/to/mydoc.FCStd").
        This action computes the corresponding YAML snapshot path internally.

        Args:
            repo: GitRepository containing the document.
            commit: Git commit reference or None for index.
            fcstd_git_path: Relative path of the FCStd file within the repository.

        Returns:
            Result containing SnapshotLoadResult with status describing outcome.

            Status mapping:
            - FOUND: FCStd exists and snapshot YAML is valid.
            - DOCUMENT_MISSING: FCStd path does not exist in selected commit/index.
              This is returned even when stale snapshot YAML still exists.
            - SNAPSHOT_MISSING: FCStd exists, but corresponding snapshot YAML is missing.
            - INVALID_SNAPSHOT: Snapshot YAML exists but fails deserialization.
        """
        # Compute the YAML snapshot path from the FCStd git_path
        fcstd_git_path = to_git_path(fcstd_git_path)
        yaml_git_path = to_git_path(str(get_snapshot_yaml_path_for_document(fcstd_git_path)))

        document_exists = self._git_service.file_exists(repo, commit, fcstd_git_path)
        if not document_exists:
            Log.debug(f"Document missing for {fcstd_git_path} (status={SnapshotLoadStatus.DOCUMENT_MISSING.name})")
            return Result.success(SnapshotLoadResult(snapshot=None, status=SnapshotLoadStatus.DOCUMENT_MISSING))

        # Get file contents from git
        yaml_contents = self._git_service.get_file_contents(repo, commit, yaml_git_path)

        if yaml_contents is None:
            Log.debug(f"No snapshot found for {yaml_git_path} (status={SnapshotLoadStatus.SNAPSHOT_MISSING.name})")
            return Result.success(SnapshotLoadResult(snapshot=None, status=SnapshotLoadStatus.SNAPSHOT_MISSING))

        try:
            snapshot = self._snapshot_deserializer.from_yaml(yaml_contents)
            snapshot = snapshot.with_identity(fcstd_git_path)
            return Result.success(SnapshotLoadResult(snapshot=snapshot, status=SnapshotLoadStatus.FOUND))
        except (ValueError, TypeError, KeyError) as e:
            Log.exception(f"Failed to deserialize snapshot for {yaml_git_path}: {e}")
            return Result.success(SnapshotLoadResult(snapshot=None, status=SnapshotLoadStatus.INVALID_SNAPSHOT))
