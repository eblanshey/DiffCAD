# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action orchestrating document-level diff statuses by mode.
"""Application action for document-level diff orchestration."""

from ...domain.git.models import GitRepository
from ...domain.snapshots.models import Snapshot
from ...utils import Log
from .create_diff import CreateDiffAction
from .create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
from .create_document_snapshot_working import CreateDocumentSnapshotForWorkingTreeAction
from .get_committed_file_paths import GetCommittedFilePathsAction
from .get_staged_file_paths import GetStagedFilePathsAction
from .result_models import (
    CreateDocumentDiffsRequest,
    DocumentDiffMode,
    DocumentDiffResult,
    DocumentDiffStatus,
    Result,
    SnapshotLoadResult,
    SnapshotLoadStatus,
)


__all__ = ["CreateDocumentDiffsAction"]


class CreateDocumentDiffsAction:
    """Compute document-level diffs for commit/staging/working-tree modes."""

    def __init__(
        self,
        create_working_snapshot_action: CreateDocumentSnapshotForWorkingTreeAction,
        create_commit_snapshot_action: CreateDocumentSnapshotForCommitAction,
        create_diff_action: CreateDiffAction,
        get_staged_file_paths_action: GetStagedFilePathsAction,
        get_committed_file_paths_action: GetCommittedFilePathsAction,
    ) -> None:
        self._create_working_snapshot = create_working_snapshot_action
        self._create_commit_snapshot = create_commit_snapshot_action
        self._create_diff = create_diff_action
        self._get_staged_file_paths = get_staged_file_paths_action
        self._get_committed_file_paths = get_committed_file_paths_action

    def execute(self, request: CreateDocumentDiffsRequest) -> Result:
        """Execute orchestration and return document-level diff results."""
        results: list[DocumentDiffResult]
        if request.mode == DocumentDiffMode.COMMIT:
            results = self._compute_commit_diffs(request)
        elif request.mode == DocumentDiffMode.STAGING:
            results = self._compute_staged_diffs(request)
        else:
            results = self._compute_working_tree_diffs(request)

        results.sort(key=lambda item: item.git_path)
        return Result.success(results)

    def _compute_commit_diffs(self, request: CreateDocumentDiffsRequest) -> list[DocumentDiffResult]:
        commit_hash = request.commit_hash
        if not commit_hash:
            return []

        commit_result = self._get_committed_file_paths.execute(request.repo, commit_hash)
        commit_paths = set(commit_result.data) if commit_result.is_success and commit_result.data else set()

        results: list[DocumentDiffResult] = []
        for git_path in commit_paths:
            commit_load = self._load_snapshot(request.repo, commit_hash, git_path)
            parent_load = self._load_snapshot(request.repo, commit_hash + "^", git_path)
            results.append(
                self._build_document_diff_result(
                    git_path,
                    new_load=commit_load,
                    old_load=parent_load,
                    mode="commit",
                )
            )

        return results

    def _compute_staged_diffs(self, request: CreateDocumentDiffsRequest) -> list[DocumentDiffResult]:
        staged = self._get_staged_file_paths.execute(request.repo)
        staged_paths = staged.data if staged.is_success and staged.data else []

        results: list[DocumentDiffResult] = []
        for git_path in staged_paths:
            index_load = self._load_snapshot(request.repo, None, git_path)
            head_load = self._load_snapshot(request.repo, "HEAD", git_path)
            results.append(
                self._build_document_diff_result(
                    git_path,
                    new_load=index_load,
                    old_load=head_load,
                    mode="staged",
                )
            )

        return results

    def _compute_working_tree_diffs(self, request: CreateDocumentDiffsRequest) -> list[DocumentDiffResult]:
        docs = request.documents or []
        results: list[DocumentDiffResult] = []
        for doc in docs:
            working = self._create_working_snapshot.execute(request.repo, doc)
            if not working.is_success or working.data is None:
                Log.warning(f"Failed to create working snapshot: {working.message}")
                continue

            working_snapshot = working.data
            old_load = self._load_snapshot(request.repo, None, working_snapshot.git_path)
            working_load = SnapshotLoadResult(snapshot=working_snapshot, status=SnapshotLoadStatus.FOUND)
            results.append(
                self._build_document_diff_result(
                    working_snapshot.git_path,
                    new_load=working_load,
                    old_load=old_load,
                    mode="working-tree",
                )
            )

        return results

    def _load_snapshot(self, repo: GitRepository, commit: str | None, git_path: str) -> SnapshotLoadResult:
        load_result = self._create_commit_snapshot.execute(repo, commit, git_path)
        if not load_result.is_success or load_result.data is None:
            return SnapshotLoadResult(snapshot=None, status=SnapshotLoadStatus.INVALID_SNAPSHOT)
        if isinstance(load_result.data, Snapshot):
            return SnapshotLoadResult(snapshot=load_result.data, status=SnapshotLoadStatus.FOUND)
        return load_result.data

    def _classify_missing_old_snapshot(self, status: SnapshotLoadStatus) -> DocumentDiffStatus:
        if status == SnapshotLoadStatus.DOCUMENT_MISSING:
            return DocumentDiffStatus.NEW_FILE
        if status == SnapshotLoadStatus.INVALID_SNAPSHOT:
            return DocumentDiffStatus.INVALID_SNAPSHOT
        return DocumentDiffStatus.OLD_SNAPSHOT_MISSING

    def _status_for_new_snapshot_missing(self, status: SnapshotLoadStatus) -> DocumentDiffStatus | None:
        if status == SnapshotLoadStatus.SNAPSHOT_MISSING:
            return DocumentDiffStatus.SNAPSHOT_MISSING
        if status == SnapshotLoadStatus.INVALID_SNAPSHOT:
            return DocumentDiffStatus.INVALID_SNAPSHOT
        if status == SnapshotLoadStatus.DOCUMENT_MISSING:
            return DocumentDiffStatus.SNAPSHOT_MISSING
        return None

    def _build_document_diff_result(
        self,
        git_path: str,
        new_load: SnapshotLoadResult,
        old_load: SnapshotLoadResult,
        mode: str,
    ) -> DocumentDiffResult:
        new_missing_status = self._status_for_new_snapshot_missing(new_load.status)
        if new_missing_status is not None:
            return DocumentDiffResult(git_path=git_path, status=new_missing_status)

        new_snapshot = new_load.snapshot
        if new_snapshot is None:
            return DocumentDiffResult(git_path=git_path, status=DocumentDiffStatus.INVALID_SNAPSHOT)

        if old_load.snapshot is None:
            old_status = self._classify_missing_old_snapshot(old_load.status)
            diff_result = self._create_diff.execute(None, new_snapshot)
            if not diff_result.is_success or diff_result.data is None:
                Log.warning(f"Failed to compute missing-old {mode} diff for {git_path}: {diff_result.message}")
                return DocumentDiffResult(git_path=git_path, status=old_status)
            return DocumentDiffResult(git_path=git_path, status=old_status, snapshot_diff=diff_result.data)

        diff = self._create_diff.execute(old_load.snapshot, new_snapshot)
        if not diff.is_success or diff.data is None:
            Log.warning(f"Failed to compute {mode} diff for {git_path}: {diff.message}")
            return DocumentDiffResult(git_path=git_path, status=DocumentDiffStatus.DIFF_COMPUTATION_FAILED)

        status = DocumentDiffStatus.MODIFIED if diff.data.has_changes else DocumentDiffStatus.UNCHANGED
        return DocumentDiffResult(git_path=git_path, status=status, snapshot_diff=diff.data)
