# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for CreateDocumentDiffsAction orchestration with split state/issues model.

from dataclasses import dataclass
from datetime import datetime
from unittest.mock import patch

from freecad.history_wb.application.actions.create_document_diffs import CreateDocumentDiffsAction
from freecad.history_wb.application.actions.result_models import (
    CreateDocumentDiffsRequest,
    DiffIssues,
    DocumentDiffMode,
    GeneralDiffIssue,
    Result,
    SnapshotIssue,
    SnapshotLoadResult,
    SnapshotLoadStatus,
)
from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.domain.git.models import DirtyFile, DirtyFileStatus, GitRepository
from freecad.history_wb.domain.snapshots.models import Snapshot


def _snapshot(git_path: str, suffix: str = "") -> Snapshot:
    return Snapshot(
        snapshot_id=f"id-{git_path}-{suffix}",
        document_name=git_path.split("/")[-1],
        timestamp=datetime.now(),
        objects=[],
        occurrences=[],
        git_path=git_path,
    )


class _FakeCommitSnapshotAction:
    def __init__(self, mapping: dict[tuple[str | None, str], SnapshotLoadResult]) -> None:
        self._mapping = mapping

    def execute(self, repo: GitRepository, commit: str | None, fcstd_git_path: str) -> Result:  # noqa: ARG002
        return Result.success(self._mapping[(commit, fcstd_git_path)])


class _FakeDiffAction:
    @dataclass
    class _Diff:
        new_snapshot: Snapshot
        has_changes: bool

    def __init__(self, changed_paths: set[str], fail_paths: set[str] | None = None) -> None:
        self._changed_paths = changed_paths
        self._fail_paths = fail_paths or set()

    def execute(self, old: Snapshot | None, new: Snapshot) -> Result:  # noqa: ARG002
        if new.git_path in self._fail_paths:
            return Result.failure("simulated diff failure")
        return Result.success(self._Diff(new_snapshot=new, has_changes=new.git_path in self._changed_paths))


class _FakeWorkingSnapshotAction:
    def __init__(self, snapshots_by_doc: dict[str, Snapshot]) -> None:
        self._snapshots_by_doc = snapshots_by_doc
        self.calls: list[str] = []

    def execute(self, repo: GitRepository, document: object) -> Result:  # noqa: ARG002
        self.calls.append(document.name)
        return Result.success(self._snapshots_by_doc[document.name])


class _FakeGitService:
    def __init__(
        self,
        committed: dict[str, list[str]] | None = None,
        staged: list[str] | None = None,
        dirty: list[DirtyFile] | None = None,
    ) -> None:
        self._committed = committed or {}
        self._staged = staged or []
        self._dirty = dirty or []

    def get_committed_files(self, repo: GitRepository, commit: str) -> list[str]:  # noqa: ARG002
        return self._committed.get(commit, [])

    def get_staged_files(self, repo: GitRepository) -> list[str]:  # noqa: ARG002
        return self._staged

    def get_dirty_files(self, repo: GitRepository) -> list[DirtyFile]:  # noqa: ARG002
        return self._dirty


@dataclass
class _Doc:
    name: str
    FileName: str


def _build_action(
    *,
    snapshot_mapping: dict[tuple[str | None, str], SnapshotLoadResult],
    changed_paths: set[str] | None = None,
    committed_paths: dict[str, list[str]] | None = None,
    staged_paths: list[str] | None = None,
    dirty_files: list[DirtyFile] | None = None,
    working_snapshots: dict[str, Snapshot] | None = None,
    fail_diff_paths: set[str] | None = None,
) -> CreateDocumentDiffsAction:
    return CreateDocumentDiffsAction(
        create_working_snapshot_action=_FakeWorkingSnapshotAction(working_snapshots or {}),
        create_commit_snapshot_action=_FakeCommitSnapshotAction(snapshot_mapping),
        create_diff_action=_FakeDiffAction(changed_paths or set(), fail_paths=fail_diff_paths),
        git_service=_FakeGitService(
            committed_paths,
            staged_paths,
            dirty_files or [],
        ),
    )


def test_commit_mode_git_changed_no_parametric_diff_sets_general_issue() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        ("c1", "a.FCStd"): SnapshotLoadResult(_snapshot("a.FCStd", "new"), SnapshotLoadStatus.FOUND),
        ("c1^", "a.FCStd"): SnapshotLoadResult(_snapshot("a.FCStd", "old"), SnapshotLoadStatus.FOUND),
    }
    action = _build_action(snapshot_mapping=snapshot_mapping, committed_paths={"c1": ["a.FCStd"]})

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="c1"))

    doc = result.data[0]
    assert doc.document_state == DiffState.MODIFIED
    assert doc.issues.general == [GeneralDiffIssue.GIT_CHANGED_NO_PARAMETRIC_DIFF]
    assert doc.snapshot_diff is not None


def test_added_file_with_new_snapshot_missing_returns_added_plus_issue() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        ("c1", "a.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.SNAPSHOT_MISSING),
        ("c1^", "a.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.DOCUMENT_MISSING),
    }
    action = _build_action(snapshot_mapping=snapshot_mapping, committed_paths={"c1": ["a.FCStd"]})

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="c1"))

    doc = result.data[0]
    assert doc.document_state == DiffState.ADDED
    assert doc.issues.new_snapshot == SnapshotIssue.MISSING


def test_deleted_file_with_old_snapshot_missing_returns_deleted_plus_issue() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        ("c1", "a.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.DOCUMENT_MISSING),
        ("c1^", "a.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.SNAPSHOT_MISSING),
    }
    action = _build_action(snapshot_mapping=snapshot_mapping, committed_paths={"c1": ["a.FCStd"]})

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="c1"))

    doc = result.data[0]
    assert doc.document_state == DiffState.DELETED
    assert doc.issues.old_snapshot == SnapshotIssue.MISSING


def test_both_snapshot_missing_surfaces_both_side_issues() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        ("c1", "a.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.SNAPSHOT_MISSING),
        ("c1^", "a.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.SNAPSHOT_MISSING),
    }
    action = _build_action(snapshot_mapping=snapshot_mapping, committed_paths={"c1": ["a.FCStd"]})

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="c1"))

    doc = result.data[0]
    assert doc.document_state == DiffState.MODIFIED
    assert doc.issues.old_snapshot == SnapshotIssue.MISSING
    assert doc.issues.new_snapshot == SnapshotIssue.MISSING


def test_working_tree_dirty_not_open_returns_missing_new_snapshot_issue() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    action = _build_action(
        snapshot_mapping={},
        dirty_files=[DirtyFile(git_path="closed.FCStd", status=DirtyFileStatus.MODIFIED)],
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, eligible_docs=[]))

    doc = result.data[0]
    assert doc.git_path == "closed.FCStd"
    assert doc.document_state == DiffState.MODIFIED
    assert doc.issues == DiffIssues(new_snapshot=SnapshotIssue.MISSING)


def test_existing_git_changed_with_parametric_changes_returns_modified_without_file_changed_only_issue() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        ("c1", "a.FCStd"): SnapshotLoadResult(_snapshot("a.FCStd", "new"), SnapshotLoadStatus.FOUND),
        ("c1^", "a.FCStd"): SnapshotLoadResult(_snapshot("a.FCStd", "old"), SnapshotLoadStatus.FOUND),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        committed_paths={"c1": ["a.FCStd"]},
        changed_paths={"a.FCStd"},
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="c1"))

    doc = result.data[0]
    assert doc.document_state == DiffState.MODIFIED
    assert GeneralDiffIssue.GIT_CHANGED_NO_PARAMETRIC_DIFF not in doc.issues.general


def test_existing_git_unchanged_with_parametric_changes_returns_modified_without_file_changed_only_issue() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    docs = [_Doc(name="a", FileName="/repo/a.FCStd")]
    snapshot_mapping = {(None, "a.FCStd"): SnapshotLoadResult(_snapshot("a.FCStd", "old"), SnapshotLoadStatus.FOUND)}
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        working_snapshots={"a": _snapshot("a.FCStd", "new")},
        dirty_files=[DirtyFile(git_path="a.FCStd", status=DirtyFileStatus.MODIFIED)],
        changed_paths={"a.FCStd"},
    )

    result = action.execute(
        CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, eligible_docs=docs)
    )

    doc = result.data[0]
    assert doc.document_state == DiffState.MODIFIED
    assert GeneralDiffIssue.GIT_CHANGED_NO_PARAMETRIC_DIFF not in doc.issues.general


def test_both_documents_missing_returns_unchanged_without_snapshot_issues() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        ("c1", "ghost.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.DOCUMENT_MISSING),
        ("c1^", "ghost.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.DOCUMENT_MISSING),
    }
    action = _build_action(snapshot_mapping=snapshot_mapping, committed_paths={"c1": ["ghost.FCStd"]})

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="c1"))

    doc = result.data[0]
    assert doc.document_state == DiffState.UNCHANGED
    assert doc.issues.old_snapshot is None
    assert doc.issues.new_snapshot is None
    assert doc.issues.general == []


def test_working_tree_includes_clean_open_eligible_docs() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    docs = [_Doc(name="a", FileName="/repo/a.FCStd")]
    snapshot_mapping = {
        (None, "a.FCStd"): SnapshotLoadResult(_snapshot("a.FCStd", "old"), SnapshotLoadStatus.FOUND)
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        working_snapshots={"a": _snapshot("a.FCStd", "new")},
    )

    result = action.execute(
        CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, eligible_docs=docs)
    )

    assert len(result.data) == 1
    assert result.data[0].git_path == "a.FCStd"
    assert result.data[0].document_state == DiffState.UNCHANGED
    assert result.data[0].snapshot_diff is not None


def test_diff_computation_failure_on_git_modified_keeps_state_and_sets_general_issue() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        ("c1", "a.FCStd"): SnapshotLoadResult(_snapshot("a.FCStd", "new"), SnapshotLoadStatus.FOUND),
        ("c1^", "a.FCStd"): SnapshotLoadResult(_snapshot("a.FCStd", "old"), SnapshotLoadStatus.FOUND),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        committed_paths={"c1": ["a.FCStd"]},
        fail_diff_paths={"a.FCStd"},
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="c1"))

    doc = result.data[0]
    assert doc.document_state == DiffState.MODIFIED
    assert doc.issues.general == [GeneralDiffIssue.DIFF_COMPUTATION_FAILED]


def test_diff_computation_failure_on_in_memory_only_keeps_modified_and_sets_general_issue() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    docs = [_Doc(name="a", FileName="/repo/a.FCStd")]
    snapshot_mapping = {
        (None, "a.FCStd"): SnapshotLoadResult(_snapshot("a.FCStd", "old"), SnapshotLoadStatus.FOUND),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        working_snapshots={"a": _snapshot("a.FCStd", "new")},
        dirty_files=[DirtyFile(git_path="a.FCStd", status=DirtyFileStatus.MODIFIED)],
        fail_diff_paths={"a.FCStd"},
    )

    result = action.execute(
        CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, eligible_docs=docs)
    )

    doc = result.data[0]
    assert doc.document_state == DiffState.MODIFIED
    assert doc.issues.general == [GeneralDiffIssue.DIFF_COMPUTATION_FAILED]


def test_old_invalid_and_new_missing_issues_both_surface() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        ("c1", "a.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.SNAPSHOT_MISSING),
        ("c1^", "a.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.INVALID_SNAPSHOT),
    }
    action = _build_action(snapshot_mapping=snapshot_mapping, committed_paths={"c1": ["a.FCStd"]})

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="c1"))

    doc = result.data[0]
    assert doc.issues.old_snapshot == SnapshotIssue.INVALID
    assert doc.issues.new_snapshot == SnapshotIssue.MISSING


def test_working_tree_missing_old_snapshot_still_computes_diff() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    docs = [_Doc(name="a", FileName="/repo/a.FCStd")]
    snapshot_mapping = {
        (None, "a.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.SNAPSHOT_MISSING),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        working_snapshots={"a": _snapshot("a.FCStd", "new")},
        dirty_files=[DirtyFile(git_path="a.FCStd", status=DirtyFileStatus.MODIFIED)],
        changed_paths={"a.FCStd"},
    )

    result = action.execute(
        CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, eligible_docs=docs)
    )

    assert len(result.data) == 1
    assert result.data[0].snapshot_diff is not None
    assert result.data[0].document_state == DiffState.MODIFIED


def test_working_tree_invalid_old_snapshot_still_computes_diff() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    docs = [_Doc(name="a", FileName="/repo/a.FCStd")]
    snapshot_mapping = {
        (None, "a.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.INVALID_SNAPSHOT),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        working_snapshots={"a": _snapshot("a.FCStd", "new")},
    )

    result = action.execute(
        CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, eligible_docs=docs)
    )

    assert len(result.data) == 1
    assert result.data[0].snapshot_diff is not None
    assert result.data[0].issues.old_snapshot == SnapshotIssue.INVALID


def test_working_tree_dirty_closed_added_path_returns_added_with_missing_new_issue() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    action = _build_action(
        snapshot_mapping={},
        dirty_files=[DirtyFile(git_path="new.FCStd", status=DirtyFileStatus.ADDED)],
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, eligible_docs=[]))

    doc = result.data[0]
    assert doc.git_path == "new.FCStd"
    assert doc.document_state == DiffState.ADDED
    assert doc.issues == DiffIssues(new_snapshot=SnapshotIssue.MISSING)


def test_working_tree_dirty_deleted_path_returns_deleted_with_tree_diff_when_old_snapshot_exists() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        (None, "gone.FCStd"): SnapshotLoadResult(_snapshot("gone.FCStd", "old"), SnapshotLoadStatus.FOUND)
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        dirty_files=[DirtyFile(git_path="gone.FCStd", status=DirtyFileStatus.DELETED)],
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, eligible_docs=[]))

    doc = result.data[0]
    assert doc.document_state == DiffState.DELETED
    assert doc.snapshot_diff is not None


def test_working_tree_dirty_deleted_path_with_missing_old_snapshot_returns_deleted_without_tree_diff() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        (None, "gone.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.SNAPSHOT_MISSING)
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        dirty_files=[DirtyFile(git_path="gone.FCStd", status=DirtyFileStatus.DELETED)],
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, eligible_docs=[]))

    doc = result.data[0]
    assert doc.document_state == DiffState.DELETED
    assert doc.snapshot_diff is None
    assert doc.issues.old_snapshot == SnapshotIssue.MISSING


def test_working_tree_deleted_path_with_open_doc_logs_warning_and_skips_working_snapshot() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    docs = [_Doc(name="a", FileName="/repo/a.FCStd")]
    snapshot_mapping = {
        (None, "a.FCStd"): SnapshotLoadResult(_snapshot("a.FCStd", "old"), SnapshotLoadStatus.FOUND)
    }
    working_action = _FakeWorkingSnapshotAction({})
    action = CreateDocumentDiffsAction(
        create_working_snapshot_action=working_action,
        create_commit_snapshot_action=_FakeCommitSnapshotAction(snapshot_mapping),
        create_diff_action=_FakeDiffAction(set()),
        git_service=_FakeGitService(
            dirty=[DirtyFile(git_path="a.FCStd", status=DirtyFileStatus.DELETED)]
        ),
    )

    with patch("freecad.history_wb.application.actions.create_document_diffs.Log.warning") as warning_mock:
        result = action.execute(
            CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, eligible_docs=docs)
        )

    assert warning_mock.call_count == 1
    assert working_action.calls == []
    assert result.data[0].document_state == DiffState.DELETED
