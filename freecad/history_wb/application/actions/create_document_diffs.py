# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action orchestrating document-level diff statuses by mode.
"""Application action for document-level diff orchestration."""

from datetime import datetime

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
    """Compute document-level diffs for commit/staging/working-tree modes.

    Document status mapping used by orchestration:
    - NEW_FILE:
      new side has FCStd + snapshot; old side FCStd is missing.
      Diff tree is computed as empty-old -> new snapshot.
    - DELETED_FILE:
      old side has snapshot; new side FCStd is missing.
      Diff tree is computed as old snapshot -> empty-new.
    - OLD_SNAPSHOT_MISSING:
      old side FCStd exists but old snapshot YAML is missing.
      Status-only result, no document-row added/deleted highlight.
    - SNAPSHOT_MISSING:
      selected/new side FCStd exists but selected/new snapshot YAML is missing,
      or selected/new side has no usable comparison data.
    - INVALID_SNAPSHOT:
      selected side or old side snapshot YAML exists but is invalid.
    - MODIFIED / UNCHANGED:
      both sides have valid snapshots and diff computes successfully.
    - DIFF_COMPUTATION_FAILED:
      both sides available for normal diff, but diff engine failed.
      (new/deleted statuses are preserved on diff failure for those cases.)
    """

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

    def _empty_snapshot_for(self, source: Snapshot) -> Snapshot:
        """Build empty snapshot matching source identity for add/delete diffing."""
        return Snapshot(
            snapshot_id=f"empty-{source.snapshot_id}",
            document_name=source.document_name,
            timestamp=source.timestamp if source.timestamp is not None else datetime.now(),
            objects=[],
            occurrences=[],
            git_path=source.git_path,
        )

    def _compute_status_only_result(self, git_path: str, status: DocumentDiffStatus) -> DocumentDiffResult:
        """Create status-only document result without diff tree."""
        return DocumentDiffResult(git_path=git_path, status=status)

    def _compute_diff_result(
        self,
        *,
        git_path: str,
        old_snapshot: Snapshot,
        new_snapshot: Snapshot,
        status_on_diff_failure: DocumentDiffStatus,
        mode: str,
    ) -> DocumentDiffResult:
        """Compute tree diff and map success/failure to document result.

        Diff-result mapping:
        - NEW_FILE: return NEW_FILE with added-node tree diff.
        - DELETED_FILE: return DELETED_FILE with deleted-node tree diff.
        - DIFF_COMPUTATION_FAILED: used for normal old->new comparisons only.

        Failure mapping:
        - new/deleted document comparisons preserve NEW_FILE/DELETED_FILE even
          when diff computation fails, so document-level state is not lost.
        - regular comparisons map failures to DIFF_COMPUTATION_FAILED.
        """
        diff = self._create_diff.execute(old_snapshot, new_snapshot)
        if not diff.is_success or diff.data is None:
            Log.warning(f"Failed to compute {mode} diff for {git_path}: {diff.message}")
            return DocumentDiffResult(git_path=git_path, status=status_on_diff_failure)

        if status_on_diff_failure in (DocumentDiffStatus.NEW_FILE, DocumentDiffStatus.DELETED_FILE):
            return DocumentDiffResult(git_path=git_path, status=status_on_diff_failure, snapshot_diff=diff.data)

        status = DocumentDiffStatus.MODIFIED if diff.data.has_changes else DocumentDiffStatus.UNCHANGED
        return DocumentDiffResult(git_path=git_path, status=status, snapshot_diff=diff.data)

    def _result_for_missing_new_snapshot(
        self,
        *,
        git_path: str,
        new_load: SnapshotLoadResult,
        old_load: SnapshotLoadResult,
        mode: str,
    ) -> DocumentDiffResult | None:
        """Handle outcomes when selected/new side snapshot missing or document deleted."""
        status = new_load.status

        if status == SnapshotLoadStatus.FOUND:
            return None
        if status == SnapshotLoadStatus.SNAPSHOT_MISSING:
            return self._compute_status_only_result(git_path, DocumentDiffStatus.SNAPSHOT_MISSING)
        if status == SnapshotLoadStatus.INVALID_SNAPSHOT:
            return self._compute_status_only_result(git_path, DocumentDiffStatus.INVALID_SNAPSHOT)
        if status != SnapshotLoadStatus.DOCUMENT_MISSING:
            Log.warning(f"Unhandled new snapshot load status for {git_path}: {status.name}")
            return self._compute_status_only_result(git_path, DocumentDiffStatus.INVALID_SNAPSHOT)

        # Handle DOCUMENT_MISSING status
        if old_load.snapshot is not None:
            empty_new_snapshot = self._empty_snapshot_for(old_load.snapshot)
            return self._compute_diff_result(
                git_path=git_path,
                old_snapshot=old_load.snapshot,
                new_snapshot=empty_new_snapshot,
                status_on_diff_failure=DocumentDiffStatus.DELETED_FILE,
                mode=f"deleted-file {mode}",
            )
        if old_load.status == SnapshotLoadStatus.SNAPSHOT_MISSING:
            return self._compute_status_only_result(git_path, DocumentDiffStatus.OLD_SNAPSHOT_MISSING)
        if old_load.status == SnapshotLoadStatus.INVALID_SNAPSHOT:
            return self._compute_status_only_result(git_path, DocumentDiffStatus.INVALID_SNAPSHOT)
        return self._compute_status_only_result(git_path, DocumentDiffStatus.SNAPSHOT_MISSING)

    def _build_document_diff_result(
        self,
        git_path: str,
        new_load: SnapshotLoadResult,
        old_load: SnapshotLoadResult,
        mode: str,
    ) -> DocumentDiffResult:
        """Build one document-level diff result from snapshot load outcomes.

        Case handling:
        - new DOCUMENT_MISSING + old snapshot present -> DELETED_FILE (+ deleted-node tree)
        - new DOCUMENT_MISSING + old SNAPSHOT_MISSING -> OLD_SNAPSHOT_MISSING (status-only)
        - new SNAPSHOT_MISSING -> SNAPSHOT_MISSING (status-only)
        - old DOCUMENT_MISSING + new snapshot present -> NEW_FILE (+ added-node tree)
        - old SNAPSHOT_MISSING -> OLD_SNAPSHOT_MISSING (status-only)
        """
        missing_new_result = self._result_for_missing_new_snapshot(
            git_path=git_path,
            new_load=new_load,
            old_load=old_load,
            mode=mode,
        )
        if missing_new_result is not None:
            return missing_new_result

        new_snapshot = new_load.snapshot
        if new_snapshot is None:
            # Defensive guard for inconsistent loader output: status FOUND but missing snapshot payload.
            return self._compute_status_only_result(git_path, DocumentDiffStatus.INVALID_SNAPSHOT)

        if old_load.snapshot is None:
            old_status = self._classify_missing_old_snapshot(old_load.status)
            if old_status != DocumentDiffStatus.NEW_FILE:
                return self._compute_status_only_result(git_path, old_status)
            empty_old_snapshot = self._empty_snapshot_for(new_snapshot)
            return self._compute_diff_result(
                git_path=git_path,
                old_snapshot=empty_old_snapshot,
                new_snapshot=new_snapshot,
                status_on_diff_failure=DocumentDiffStatus.NEW_FILE,
                mode=f"new-file {mode}",
            )

        return self._compute_diff_result(
            git_path=git_path,
            old_snapshot=old_load.snapshot,
            new_snapshot=new_snapshot,
            status_on_diff_failure=DocumentDiffStatus.DIFF_COMPUTATION_FAILED,
            mode=mode,
        )
