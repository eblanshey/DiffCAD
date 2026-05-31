# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action orchestrating document-level diff results by mode.
"""Application action for document-level diff orchestration."""

from datetime import datetime

from ...domain.diff.models import DiffState
from ...domain.freecad_ports import DocumentLike, FreeCadPort
from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ...domain.git.paths import relative_git_path
from ...domain.snapshots.models import Snapshot
from ...utils import Log
from .create_diff import CreateDiffAction
from .create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
from .create_document_snapshot_working import CreateDocumentSnapshotForWorkingTreeAction
from .result_models import (
    CreateDocumentDiffsRequest,
    DiffIssues,
    DocumentDiffMode,
    DocumentDiffResult,
    GeneralDiffIssue,
    Result,
    SnapshotIssue,
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
        git_service: GitService,
        freecad_port: FreeCadPort,
    ) -> None:
        self._create_working_snapshot = create_working_snapshot_action
        self._create_commit_snapshot = create_commit_snapshot_action
        self._create_diff = create_diff_action
        self._git_service = git_service
        self._freecad_port = freecad_port

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

        commit_paths = set(self._git_service.get_committed_files(request.repo, commit_hash))
        return self._compute_for_paths(request.repo, commit_paths, commit_hash, f"{commit_hash}^")

    def _compute_staged_diffs(self, request: CreateDocumentDiffsRequest) -> list[DocumentDiffResult]:
        staged_paths = set(self._git_service.get_staged_files(request.repo))
        return self._compute_for_paths(request.repo, staged_paths, None, "HEAD")

    def _compute_working_tree_diffs(self, request: CreateDocumentDiffsRequest) -> list[DocumentDiffResult]:
        """
        Working tree diffs are computed against dirty git path and opened eligible documents. This supports
        scenarios where a user made changes but hasn't saved the document yet.
        To simplify this in the future we can make saving documents a requirement to view diffs.
        """
        eligible_docs = request.eligible_docs or []
        dirty_paths, open_modified_paths = self._working_tree_candidate_paths(request.repo, eligible_docs)

        if request.force_all:
            eligible_paths = set(self._documents_by_git_path(request.repo, eligible_docs).keys())
            diff_candidate_paths = dirty_paths | open_modified_paths | eligible_paths
        else:
            diff_candidate_paths = dirty_paths | open_modified_paths

        if not diff_candidate_paths:
            return []

        eligible_docs_by_path = self._documents_by_git_path(request.repo, eligible_docs)

        results: list[DocumentDiffResult] = []
        for git_path in sorted(diff_candidate_paths):
            document = eligible_docs_by_path.get(git_path)
            if document is None:
                results.append(self._result_for_dirty_path_not_open(git_path, dirty_paths))
                continue

            working = self._create_working_snapshot.execute(request.repo, document)
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
                    git_changed_paths=dirty_paths,
                    open_modified_paths=open_modified_paths,
                    mode="working-tree",
                )
            )

        return results

    def _documents_by_git_path(self, repo: GitRepository, documents: list[DocumentLike]) -> dict[str, DocumentLike]:
        """Build map of open eligible documents keyed by git path."""
        docs_by_path: dict[str, DocumentLike] = {}
        for document in documents:
            doc_path = getattr(document, "FileName", "")
            if not doc_path:
                continue
            try:
                docs_by_path[relative_git_path(doc_path, repo.absolute_path)] = document
            except ValueError:
                continue
        return docs_by_path

    def _result_for_dirty_path_not_open(
        self,
        git_path: str,
        dirty_paths: set[str],
    ) -> DocumentDiffResult:
        """Return status-only result when git dirty path has no open doc."""
        if git_path not in dirty_paths:
            raise RuntimeError(f"Unexpected non-dirty path without open document: {git_path}")
        return DocumentDiffResult(
            git_path=git_path,
            document_state=DiffState.MODIFIED,
            issues=DiffIssues(new_snapshot=SnapshotIssue.MISSING),
        )

    def _working_tree_candidate_paths(
        self,
        repo: GitRepository,
        eligible_docs: list[DocumentLike],
    ) -> tuple[set[str], set[str]]:
        """Return working tree dirty paths and open modified paths."""
        dirty_paths = set(self._git_service.get_dirty_files(repo))
        open_modified_paths: set[str] = set()
        for doc in eligible_docs:
            doc_path = getattr(doc, "FileName", "")
            if not doc_path:
                continue
            if not self._freecad_port.is_document_modified(doc):
                continue
            try:
                open_modified_paths.add(relative_git_path(doc_path, repo.absolute_path))
            except ValueError:
                continue
        return dirty_paths, open_modified_paths

    def _compute_for_paths(
        self,
        repo: GitRepository,
        git_paths: set[str],
        new_ref: str | None,
        old_ref: str | None,
    ) -> list[DocumentDiffResult]:
        results: list[DocumentDiffResult] = []
        for git_path in git_paths:
            new_load = self._load_snapshot(repo, new_ref, git_path)
            old_load = self._load_snapshot(repo, old_ref, git_path)
            results.append(
                self._build_document_diff_result(
                    git_path,
                    new_load=new_load,
                    old_load=old_load,
                    git_changed_paths=git_paths,
                    open_modified_paths=set(),
                    mode="historical",
                )
            )
        return results

    def _load_snapshot(self, repo: GitRepository, commit: str | None, git_path: str) -> SnapshotLoadResult:
        """Load one snapshot result from commit snapshot action."""
        load_result = self._create_commit_snapshot.execute(repo, commit, git_path)
        if not load_result.is_success or load_result.data is None:
            raise RuntimeError(f"Snapshot load failed for {git_path} @ {commit}: {load_result.message}")
        if not isinstance(load_result.data, SnapshotLoadResult):
            raise RuntimeError(f"Unexpected snapshot load payload type for {git_path} @ {commit}")
        return load_result.data

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

    def _document_exists(self, load: SnapshotLoadResult) -> bool:
        """Return whether FCStd exists on selected side."""
        return load.status != SnapshotLoadStatus.DOCUMENT_MISSING

    def _document_state_for_loads(
        self,
        old_load: SnapshotLoadResult,
        new_load: SnapshotLoadResult,
        file_has_changed: bool,
    ) -> DiffState:
        """Compute git-like document state from side existence and git change."""
        old_exists = self._document_exists(old_load)
        new_exists = self._document_exists(new_load)
        if not old_exists and new_exists:
            return DiffState.ADDED
        if old_exists and not new_exists:
            return DiffState.DELETED
        if not old_exists and not new_exists:
            Log.warning("Both old/new document missing while building document diff result")
            return DiffState.UNCHANGED
        return DiffState.MODIFIED if file_has_changed else DiffState.UNCHANGED

    def _snapshot_issue_for_load(self, load: SnapshotLoadResult) -> SnapshotIssue | None:
        """Map one side load status into side issue."""
        if load.status == SnapshotLoadStatus.SNAPSHOT_MISSING:
            return SnapshotIssue.MISSING
        if load.status == SnapshotLoadStatus.INVALID_SNAPSHOT:
            return SnapshotIssue.INVALID
        return None

    def _issues_for_loads(self, old_load: SnapshotLoadResult, new_load: SnapshotLoadResult) -> DiffIssues:
        """Collect side issues from both load results without short-circuit."""
        return DiffIssues(
            old_snapshot=self._snapshot_issue_for_load(old_load),
            new_snapshot=self._snapshot_issue_for_load(new_load),
        )

    def _snapshots_for_diff(
        self,
        document_state: DiffState,
        old_load: SnapshotLoadResult,
        new_load: SnapshotLoadResult,
    ) -> tuple[Snapshot, Snapshot]:
        """Select snapshots for diff according to document state.

        ADDED: empty old vs real new.
        DELETED: real old vs empty new.
        MODIFIED/UNCHANGED: real old vs real new. But if the old snapshot is
        missing (first-time snapshot, no baseline), synthesize an empty old
        snapshot so the diff can run. The result is a full-tree "added" diff,
        which is correct for a document with no prior snapshot history.
        """
        if document_state == DiffState.ADDED:
            new_snapshot = new_load.snapshot
            if new_snapshot is None:
                raise RuntimeError("Missing new snapshot for added file")
            return self._empty_snapshot_for(new_snapshot), new_snapshot
        if document_state == DiffState.DELETED:
            old_snapshot = old_load.snapshot
            if old_snapshot is None:
                raise RuntimeError("Missing old snapshot for deleted file")
            return old_snapshot, self._empty_snapshot_for(old_snapshot)

        new_snapshot = new_load.snapshot
        if new_snapshot is None:
            raise RuntimeError("Missing new snapshot for modified/unchanged file")

        old_snapshot = old_load.snapshot
        if old_snapshot is None:
            old_snapshot = self._empty_snapshot_for(new_snapshot)
        return old_snapshot, new_snapshot

    def _compute_diff_result(
        self,
        git_path: str,
        old_snapshot: Snapshot,
        new_snapshot: Snapshot,
        document_state: DiffState,
        issues: DiffIssues,
        git_file_changed: bool,
        mode: str,
    ) -> DocumentDiffResult:
        """Compute tree diff and finalize result state/issues."""
        diff = self._create_diff.execute(old_snapshot, new_snapshot)
        if not diff.is_success or diff.data is None:
            Log.warning(f"Failed to compute {mode} diff for {git_path}: {diff.message}")
            issues.general.append(GeneralDiffIssue.DIFF_COMPUTATION_FAILED)
            return DocumentDiffResult(git_path=git_path, document_state=document_state, issues=issues)

        if document_state in (DiffState.ADDED, DiffState.DELETED):
            return DocumentDiffResult(
                git_path=git_path,
                document_state=document_state,
                issues=issues,
                snapshot_diff=diff.data,
            )

        if diff.data.has_changes:
            return DocumentDiffResult(
                git_path=git_path,
                document_state=DiffState.MODIFIED,
                issues=issues,
                snapshot_diff=diff.data,
            )

        if git_file_changed:
            issues.general.append(GeneralDiffIssue.GIT_CHANGED_NO_PARAMETRIC_DIFF)
            return DocumentDiffResult(
                git_path=git_path,
                document_state=DiffState.MODIFIED,
                issues=issues,
                snapshot_diff=diff.data,
            )

        return DocumentDiffResult(
            git_path=git_path,
            document_state=DiffState.UNCHANGED,
            issues=issues,
            snapshot_diff=diff.data,
        )

    def _build_document_diff_result(
        self,
        git_path: str,
        new_load: SnapshotLoadResult,
        old_load: SnapshotLoadResult,
        git_changed_paths: set[str],
        open_modified_paths: set[str],
        mode: str,
    ) -> DocumentDiffResult:
        """Build one document-level result from state, issues, and optional diff."""
        git_file_changed = git_path in git_changed_paths
        open_modified = git_path in open_modified_paths
        has_any_change = git_file_changed or open_modified
        document_state = self._document_state_for_loads(old_load, new_load, has_any_change)
        issues = self._issues_for_loads(old_load, new_load)

        if not self._document_exists(old_load) and not self._document_exists(new_load):
            return DocumentDiffResult(git_path=git_path, document_state=document_state, issues=issues)

        if issues.is_diff_blocker_for(document_state):
            return DocumentDiffResult(git_path=git_path, document_state=document_state, issues=issues)

        old_snapshot, new_snapshot = self._snapshots_for_diff(document_state, old_load, new_load)
        return self._compute_diff_result(
            git_path=git_path,
            old_snapshot=old_snapshot,
            new_snapshot=new_snapshot,
            document_state=document_state,
            issues=issues,
            git_file_changed=git_file_changed,
            mode=mode,
        )
