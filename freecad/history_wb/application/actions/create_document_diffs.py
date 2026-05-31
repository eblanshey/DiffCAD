# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action orchestrating document-level diff results by mode.
"""Application action for document-level diff orchestration."""

from datetime import datetime

from ...domain.diff.models import DiffState
from ...domain.freecad_ports import DocumentLike
from ...domain.git.git_service import GitService
from ...domain.git.models import DirtyFile, DirtyFileStatus, GitRepository
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
    ) -> None:
        self._create_working_snapshot = create_working_snapshot_action
        self._create_commit_snapshot = create_commit_snapshot_action
        self._create_diff = create_diff_action
        self._git_service = git_service

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
        """Compute diffs for every open eligible document and every dirty git path.

        Candidate set is union of dirty git paths and open eligible document paths.
        This ensures clean-but-open documents appear for baseline comparison, and
        dirty-but-closed documents appear with a status-only indicator.
        """
        dirty_files = self._git_service.get_dirty_files(request.repo)
        dirty_by_path: dict[str, DirtyFile] = {item.git_path: item for item in dirty_files}
        eligible_docs = request.eligible_docs or []
        docs_by_path = self._documents_by_git_path(request.repo, eligible_docs)
        # Union ensures both dirty-closed and clean-open paths are candidates.
        candidate_paths = set(dirty_by_path) | set(docs_by_path)

        # No dirty files and no open docs means nothing to display.
        if not candidate_paths:
            return []

        results: list[DocumentDiffResult] = []
        for git_path in sorted(candidate_paths):
            dirty_item = dirty_by_path.get(git_path)
            document = docs_by_path.get(git_path)

            # Deleted path takes priority over open document to preserve git deletion intent.
            if dirty_item is not None and dirty_item.status == DirtyFileStatus.DELETED:
                results.append(self._result_for_deleted_path(request.repo, git_path, document))
                continue

            # Open document always gets working snapshot, even when git-clean.
            if document is not None:
                open_doc_result = self._result_for_open_document(
                    repo=request.repo,
                    git_path=git_path,
                    document=document,
                    git_changed=git_path in dirty_by_path,
                )
                if open_doc_result is not None:
                    results.append(open_doc_result)
                continue

            # Dirty path not open (non-deleted) -> status-only result.
            if dirty_item is None:
                raise RuntimeError(f"Candidate path {git_path} has no dirty item and no document")
            results.append(self._result_for_dirty_path_not_open(git_path, dirty_item))

        return results

    def _result_for_deleted_path(
        self,
        repo: GitRepository,
        git_path: str,
        document: DocumentLike | None,
    ) -> DocumentDiffResult:
        """Build deleted-path result with optional tree diff from old snapshot."""
        # Open doc exists for deleted path: warn and never snapshot working side.
        if document is not None:
            Log.warning(f"Deleted path {git_path} has an open document. Git deletion wins; skipping snapshot.")
        # Load old snapshot from index to build deleted-vs-empty tree diff.
        old_load = self._load_snapshot(repo, None, git_path)

        # New side explicitly missing: file no longer exists.
        new_load = SnapshotLoadResult(
            snapshot=None,
            status=SnapshotLoadStatus.DOCUMENT_MISSING,
        )
        issues = self._issues_for_loads(old_load, new_load)
        old_snap, new_snap = self._snapshots_for_diff(DiffState.DELETED, old_load, new_load)

        if old_snap is not None and new_snap is not None:
            diff = self._create_diff.execute(old_snap, new_snap)
            snapshot_diff = diff.data if diff.is_success and diff.data else None
            # Diff engine succeeded but produced no payload: treat as computation failure.
            if diff.is_success and diff.data is None:
                issues.general.append(GeneralDiffIssue.DIFF_COMPUTATION_FAILED)
        else:
            # Old snapshot missing: cannot build tree diff, still return DELETED state.
            snapshot_diff = None
        return DocumentDiffResult(
            git_path=git_path,
            document_state=DiffState.DELETED,
            issues=issues,
            snapshot_diff=snapshot_diff,
        )

    def _result_for_open_document(
        self,
        repo: GitRepository,
        git_path: str,
        document: DocumentLike,
        git_changed: bool,
    ) -> DocumentDiffResult | None:
        """Build result for open document path by creating working snapshot."""
        working = self._create_working_snapshot.execute(repo, document)
        # Snapshot extraction failed -- skip this document path.
        if not working.is_success or working.data is None:
            Log.warning(f"Failed to create working snapshot: {working.message}")
            return None

        working_snapshot = working.data
        old_load = self._load_snapshot(repo, None, working_snapshot.git_path)
        working_load = SnapshotLoadResult(
            snapshot=working_snapshot,
            status=SnapshotLoadStatus.FOUND,
        )

        return self._build_document_diff_result(
            git_path,
            new_load=working_load,
            old_load=old_load,
            git_changed=git_changed,
            mode="working-tree",
        )

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
        dirty_item: DirtyFile,
    ) -> DocumentDiffResult:
        """Return status-only result when a git-dirty path has no open document."""
        # DELETED must be handled by dedicated path that loads old snapshot.
        if dirty_item.status == DirtyFileStatus.DELETED:
            raise RuntimeError(f"Deleted path {git_path} should be handled by main loop, not this helper")
        # Map git status to document state: added -> ADDED, modified -> MODIFIED.
        state = DiffState.ADDED if dirty_item.status == DirtyFileStatus.ADDED else DiffState.MODIFIED
        return DocumentDiffResult(
            git_path=git_path,
            document_state=state,
            issues=DiffIssues(new_snapshot=SnapshotIssue.MISSING),
        )

    def _compute_for_paths(
        self,
        repo: GitRepository,
        git_paths: set[str],
        new_ref: str | None,
        old_ref: str | None,
    ) -> list[DocumentDiffResult]:
        """Compute diffs for paths at historical refs (commit/staging modes).

        Every path in set considered changed by definition -- committed files,
        staged files, or explicitly requested historical paths.
        """
        results: list[DocumentDiffResult] = []
        for git_path in git_paths:
            new_load = self._load_snapshot(repo, new_ref, git_path)
            old_load = self._load_snapshot(repo, old_ref, git_path)
            results.append(
                self._build_document_diff_result(
                    git_path,
                    new_load=new_load,
                    old_load=old_load,
                    git_changed=True,
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
    ) -> tuple[Snapshot | None, Snapshot | None]:
        """Select snapshots for diff according to document state.

        Returns (None, None) when no valid diff can be computed:
        - ADDED with missing new snapshot
        - DELETED with missing old snapshot
        - MODIFIED/UNCHANGED with missing new snapshot

        ADDED: empty old vs real new.
        DELETED: real old vs empty new.
        MODIFIED/UNCHANGED: real old vs real new. But if the old snapshot is
        missing (first-time snapshot, no baseline), synthesize an empty old
        snapshot so the diff can run. The result is a full-tree "added" diff,
        which is correct for a document with no prior snapshot history.
        """
        if document_state == DiffState.ADDED:
            new_snapshot = new_load.snapshot
            # Cannot diff added file without new snapshot.
            if new_snapshot is None:
                return None, None
            return self._empty_snapshot_for(new_snapshot), new_snapshot
        if document_state == DiffState.DELETED:
            old_snapshot = old_load.snapshot
            # Cannot diff deleted file without old snapshot.
            if old_snapshot is None:
                return None, None
            return old_snapshot, self._empty_snapshot_for(old_snapshot)

        new_snapshot = new_load.snapshot
        # MODIFIED/UNCHANGED cannot diff without new side.
        if new_snapshot is None:
            return None, None

        old_snapshot = old_load.snapshot
        # Missing old baseline: synthesize empty old for full-tree added diff.
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
        git_changed: bool,
        mode: str,
    ) -> DocumentDiffResult:
        """Build one document-level result from state, issues, and optional diff.

        Determines document state from snapshot load results, collects issues,
        selects snapshots for comparison, then computes tree diff if possible.
        """
        document_state = self._document_state_for_loads(old_load, new_load, git_changed)
        issues = self._issues_for_loads(old_load, new_load)

        # Both sides missing: document absent both refs, issues-only result.
        if not self._document_exists(old_load) and not self._document_exists(new_load):
            return DocumentDiffResult(git_path=git_path, document_state=document_state, issues=issues)

        old_snapshot, new_snapshot = self._snapshots_for_diff(document_state, old_load, new_load)

        # Snapshot selection failed (e.g. deleted with missing old snapshot).
        if old_snapshot is None or new_snapshot is None:
            return DocumentDiffResult(git_path=git_path, document_state=document_state, issues=issues)
        return self._compute_diff_result(
            git_path=git_path,
            old_snapshot=old_snapshot,
            new_snapshot=new_snapshot,
            document_state=document_state,
            issues=issues,
            git_file_changed=git_changed,
            mode=mode,
        )
