# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for CreateDocumentDiffsAction orchestration and status classification.
"""Unit tests for CreateDocumentDiffsAction."""

from dataclasses import dataclass
from datetime import datetime

from freecad.history_wb.application.actions.create_document_diffs import CreateDocumentDiffsAction
from freecad.history_wb.application.actions.result_models import (
    CreateDocumentDiffsRequest,
    DocumentDiffMode,
    DocumentDiffStatus,
    Result,
    SnapshotLoadResult,
    SnapshotLoadStatus,
)
from freecad.history_wb.domain.git.models import GitRepository
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
        load = self._mapping[(commit, fcstd_git_path)]
        return Result.success(load)


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


class _FakeCommittedPathsAction:
    def __init__(self, mapping: dict[str, list[str]]) -> None:
        self._mapping = mapping
        self.calls: list[str] = []

    def execute(self, repo: GitRepository, commit: str) -> Result:  # noqa: ARG002
        self.calls.append(commit)
        return Result.success(self._mapping.get(commit, []))


class _FakeStagedPathsAction:
    def __init__(self, paths: list[str]) -> None:
        self._paths = paths

    def execute(self, repo: GitRepository) -> Result:  # noqa: ARG002
        return Result.success(self._paths)


class _FakeWorkingSnapshotAction:
    def __init__(self, snapshots_by_doc: dict[str, Snapshot]) -> None:
        self._snapshots_by_doc = snapshots_by_doc

    def execute(self, repo: GitRepository, document: object) -> Result:  # noqa: ARG002
        return Result.success(self._snapshots_by_doc[document.name])


@dataclass
class _Doc:
    name: str


def _build_action(
    *,
    snapshot_mapping: dict[tuple[str | None, str], SnapshotLoadResult],
    changed_paths: set[str] | None = None,
    committed_paths: dict[str, list[str]] | None = None,
    staged_paths: list[str] | None = None,
    working_snapshots: dict[str, Snapshot] | None = None,
    fail_diff_paths: set[str] | None = None,
) -> CreateDocumentDiffsAction:
    committed_paths_action = _FakeCommittedPathsAction(committed_paths or {})
    return CreateDocumentDiffsAction(
        create_working_snapshot_action=_FakeWorkingSnapshotAction(working_snapshots or {}),
        create_commit_snapshot_action=_FakeCommitSnapshotAction(snapshot_mapping),
        create_diff_action=_FakeDiffAction(changed_paths or set(), fail_paths=fail_diff_paths),
        get_staged_file_paths_action=_FakeStagedPathsAction(staged_paths or []),
        get_committed_file_paths_action=committed_paths_action,
    )


def test_commit_mode_covers_new_file_old_missing_invalid_and_diff_states() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    paths = ["new.FCStd", "old-missing.FCStd", "old-invalid.FCStd", "modified.FCStd", "same.FCStd"]
    snapshot_mapping = {
        ("c1", "new.FCStd"): SnapshotLoadResult(_snapshot("new.FCStd", "new"), SnapshotLoadStatus.FOUND),
        ("c1^", "new.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.DOCUMENT_MISSING),
        ("c1", "old-missing.FCStd"): SnapshotLoadResult(
            _snapshot("old-missing.FCStd", "new"), SnapshotLoadStatus.FOUND
        ),
        ("c1^", "old-missing.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.SNAPSHOT_MISSING),
        ("c1", "old-invalid.FCStd"): SnapshotLoadResult(
            _snapshot("old-invalid.FCStd", "new"), SnapshotLoadStatus.FOUND
        ),
        ("c1^", "old-invalid.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.INVALID_SNAPSHOT),
        ("c1", "modified.FCStd"): SnapshotLoadResult(_snapshot("modified.FCStd", "new"), SnapshotLoadStatus.FOUND),
        ("c1^", "modified.FCStd"): SnapshotLoadResult(_snapshot("modified.FCStd", "old"), SnapshotLoadStatus.FOUND),
        ("c1", "same.FCStd"): SnapshotLoadResult(_snapshot("same.FCStd", "new"), SnapshotLoadStatus.FOUND),
        ("c1^", "same.FCStd"): SnapshotLoadResult(_snapshot("same.FCStd", "old"), SnapshotLoadStatus.FOUND),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        changed_paths={"new.FCStd", "modified.FCStd"},
        committed_paths={"c1": paths},
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="c1"))

    by_path = {item.git_path: item for item in result.data}
    assert by_path["new.FCStd"].status == DocumentDiffStatus.NEW_FILE
    assert by_path["new.FCStd"].snapshot_diff is not None
    assert by_path["old-missing.FCStd"].status == DocumentDiffStatus.OLD_SNAPSHOT_MISSING
    assert by_path["old-missing.FCStd"].snapshot_diff is not None
    assert by_path["old-invalid.FCStd"].status == DocumentDiffStatus.INVALID_SNAPSHOT
    assert by_path["old-invalid.FCStd"].snapshot_diff is not None
    assert by_path["modified.FCStd"].status == DocumentDiffStatus.MODIFIED
    assert by_path["modified.FCStd"].snapshot_diff is not None
    assert by_path["same.FCStd"].status == DocumentDiffStatus.UNCHANGED


def test_commit_mode_when_commit_snapshot_missing_or_invalid_returns_document_status_only() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        ("c1", "missing.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.SNAPSHOT_MISSING),
        ("c1^", "missing.FCStd"): SnapshotLoadResult(_snapshot("missing.FCStd", "old"), SnapshotLoadStatus.FOUND),
        ("c1", "invalid.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.INVALID_SNAPSHOT),
        ("c1^", "invalid.FCStd"): SnapshotLoadResult(_snapshot("invalid.FCStd", "old"), SnapshotLoadStatus.FOUND),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        committed_paths={"c1": ["missing.FCStd", "invalid.FCStd"]},
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="c1"))
    by_path = {item.git_path: item for item in result.data}
    assert by_path["missing.FCStd"].status == DocumentDiffStatus.SNAPSHOT_MISSING
    assert by_path["missing.FCStd"].snapshot_diff is None
    assert by_path["invalid.FCStd"].status == DocumentDiffStatus.INVALID_SNAPSHOT
    assert by_path["invalid.FCStd"].snapshot_diff is None


def test_staging_mode_covers_index_missing_head_missing_and_head_snapshot_missing() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    staged_paths = ["index-missing.FCStd", "head-missing.FCStd", "head-snapshot-missing.FCStd"]
    snapshot_mapping = {
        (None, "index-missing.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.SNAPSHOT_MISSING),
        ("HEAD", "index-missing.FCStd"): SnapshotLoadResult(
            _snapshot("index-missing.FCStd", "head"), SnapshotLoadStatus.FOUND
        ),
        (None, "head-missing.FCStd"): SnapshotLoadResult(
            _snapshot("head-missing.FCStd", "index"), SnapshotLoadStatus.FOUND
        ),
        ("HEAD", "head-missing.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.DOCUMENT_MISSING),
        (None, "head-snapshot-missing.FCStd"): SnapshotLoadResult(
            _snapshot("head-snapshot-missing.FCStd", "index"), SnapshotLoadStatus.FOUND
        ),
        ("HEAD", "head-snapshot-missing.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.SNAPSHOT_MISSING),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping, staged_paths=staged_paths, changed_paths={"head-missing.FCStd"}
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.STAGING, repo=repo))
    by_path = {item.git_path: item for item in result.data}

    assert by_path["index-missing.FCStd"].status == DocumentDiffStatus.SNAPSHOT_MISSING
    assert by_path["head-missing.FCStd"].status == DocumentDiffStatus.NEW_FILE
    assert by_path["head-missing.FCStd"].snapshot_diff is not None
    assert by_path["head-snapshot-missing.FCStd"].status == DocumentDiffStatus.OLD_SNAPSHOT_MISSING
    assert by_path["head-snapshot-missing.FCStd"].snapshot_diff is not None


def test_working_tree_mode_covers_new_file_and_old_snapshot_missing() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    docs = [_Doc(name="new"), _Doc(name="missing")]
    working_snapshots = {
        "new": _snapshot("new.FCStd", "working"),
        "missing": _snapshot("missing.FCStd", "working"),
    }
    snapshot_mapping = {
        (None, "new.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.DOCUMENT_MISSING),
        (None, "missing.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.SNAPSHOT_MISSING),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping, working_snapshots=working_snapshots, changed_paths={"new.FCStd"}
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, documents=docs))
    by_path = {item.git_path: item for item in result.data}

    assert by_path["new.FCStd"].status == DocumentDiffStatus.NEW_FILE
    assert by_path["new.FCStd"].snapshot_diff is not None
    assert by_path["missing.FCStd"].status == DocumentDiffStatus.OLD_SNAPSHOT_MISSING
    assert by_path["missing.FCStd"].snapshot_diff is not None


def test_staging_mode_sets_modified_and_unchanged_from_diff_result() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    staged_paths = ["modified.FCStd", "same.FCStd"]
    snapshot_mapping = {
        (None, "modified.FCStd"): SnapshotLoadResult(_snapshot("modified.FCStd", "index"), SnapshotLoadStatus.FOUND),
        ("HEAD", "modified.FCStd"): SnapshotLoadResult(_snapshot("modified.FCStd", "head"), SnapshotLoadStatus.FOUND),
        (None, "same.FCStd"): SnapshotLoadResult(_snapshot("same.FCStd", "index"), SnapshotLoadStatus.FOUND),
        ("HEAD", "same.FCStd"): SnapshotLoadResult(_snapshot("same.FCStd", "head"), SnapshotLoadStatus.FOUND),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        staged_paths=staged_paths,
        changed_paths={"modified.FCStd"},
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.STAGING, repo=repo))
    by_path = {item.git_path: item for item in result.data}

    assert by_path["modified.FCStd"].status == DocumentDiffStatus.MODIFIED
    assert by_path["modified.FCStd"].snapshot_diff is not None
    assert by_path["same.FCStd"].status == DocumentDiffStatus.UNCHANGED
    assert by_path["same.FCStd"].snapshot_diff is not None


def test_working_tree_mode_sets_modified_and_unchanged_from_diff_result() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    docs = [_Doc(name="modified"), _Doc(name="same")]
    working_snapshots = {
        "modified": _snapshot("modified.FCStd", "working"),
        "same": _snapshot("same.FCStd", "working"),
    }
    snapshot_mapping = {
        (None, "modified.FCStd"): SnapshotLoadResult(_snapshot("modified.FCStd", "index"), SnapshotLoadStatus.FOUND),
        (None, "same.FCStd"): SnapshotLoadResult(_snapshot("same.FCStd", "index"), SnapshotLoadStatus.FOUND),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        working_snapshots=working_snapshots,
        changed_paths={"modified.FCStd"},
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, documents=docs))
    by_path = {item.git_path: item for item in result.data}

    assert by_path["modified.FCStd"].status == DocumentDiffStatus.MODIFIED
    assert by_path["modified.FCStd"].snapshot_diff is not None
    assert by_path["same.FCStd"].status == DocumentDiffStatus.UNCHANGED
    assert by_path["same.FCStd"].snapshot_diff is not None


def test_commit_mode_new_file_keeps_status_when_diff_fails() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        ("c1", "new.FCStd"): SnapshotLoadResult(_snapshot("new.FCStd", "new"), SnapshotLoadStatus.FOUND),
        ("c1^", "new.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.DOCUMENT_MISSING),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        committed_paths={"c1": ["new.FCStd"]},
        fail_diff_paths={"new.FCStd"},
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="c1"))
    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0].git_path == "new.FCStd"
    assert result.data[0].status == DocumentDiffStatus.NEW_FILE
    assert result.data[0].snapshot_diff is None


def test_commit_mode_scopes_to_selected_commit_paths_only() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        ("c1", "selected.FCStd"): SnapshotLoadResult(_snapshot("selected.FCStd", "new"), SnapshotLoadStatus.FOUND),
        ("c1^", "selected.FCStd"): SnapshotLoadResult(_snapshot("selected.FCStd", "old"), SnapshotLoadStatus.FOUND),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        committed_paths={"c1": ["selected.FCStd"], "c1^": ["unrelated.FCStd"]},
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="c1"))

    assert result.data is not None
    assert [item.git_path for item in result.data] == ["selected.FCStd"]


def test_staging_mode_new_file_keeps_status_when_diff_fails() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        (None, "new.FCStd"): SnapshotLoadResult(_snapshot("new.FCStd", "index"), SnapshotLoadStatus.FOUND),
        ("HEAD", "new.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.DOCUMENT_MISSING),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        staged_paths=["new.FCStd"],
        fail_diff_paths={"new.FCStd"},
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.STAGING, repo=repo))
    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0].git_path == "new.FCStd"
    assert result.data[0].status == DocumentDiffStatus.NEW_FILE
    assert result.data[0].snapshot_diff is None


def test_working_tree_mode_new_file_keeps_status_when_diff_fails() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    docs = [_Doc(name="new")]
    working_snapshots = {"new": _snapshot("new.FCStd", "working")}
    snapshot_mapping = {(None, "new.FCStd"): SnapshotLoadResult(None, SnapshotLoadStatus.DOCUMENT_MISSING)}
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        working_snapshots=working_snapshots,
        fail_diff_paths={"new.FCStd"},
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, documents=docs))
    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0].git_path == "new.FCStd"
    assert result.data[0].status == DocumentDiffStatus.NEW_FILE
    assert result.data[0].snapshot_diff is None


def test_commit_mode_returns_diff_computation_failed_when_existing_file_diff_fails() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        ("c1", "broken.FCStd"): SnapshotLoadResult(_snapshot("broken.FCStd", "new"), SnapshotLoadStatus.FOUND),
        ("c1^", "broken.FCStd"): SnapshotLoadResult(_snapshot("broken.FCStd", "old"), SnapshotLoadStatus.FOUND),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        committed_paths={"c1": ["broken.FCStd"]},
        fail_diff_paths={"broken.FCStd"},
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="c1"))

    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0].git_path == "broken.FCStd"
    assert result.data[0].status == DocumentDiffStatus.DIFF_COMPUTATION_FAILED
    assert result.data[0].snapshot_diff is None


def test_staging_mode_returns_diff_computation_failed_when_existing_file_diff_fails() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    snapshot_mapping = {
        (None, "broken.FCStd"): SnapshotLoadResult(_snapshot("broken.FCStd", "index"), SnapshotLoadStatus.FOUND),
        ("HEAD", "broken.FCStd"): SnapshotLoadResult(_snapshot("broken.FCStd", "head"), SnapshotLoadStatus.FOUND),
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        staged_paths=["broken.FCStd"],
        fail_diff_paths={"broken.FCStd"},
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.STAGING, repo=repo))

    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0].git_path == "broken.FCStd"
    assert result.data[0].status == DocumentDiffStatus.DIFF_COMPUTATION_FAILED
    assert result.data[0].snapshot_diff is None


def test_working_tree_mode_returns_diff_computation_failed_when_existing_file_diff_fails() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    docs = [_Doc(name="broken")]
    working_snapshots = {"broken": _snapshot("broken.FCStd", "working")}
    snapshot_mapping = {
        (None, "broken.FCStd"): SnapshotLoadResult(_snapshot("broken.FCStd", "index"), SnapshotLoadStatus.FOUND)
    }
    action = _build_action(
        snapshot_mapping=snapshot_mapping,
        working_snapshots=working_snapshots,
        fail_diff_paths={"broken.FCStd"},
    )

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, documents=docs))

    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0].git_path == "broken.FCStd"
    assert result.data[0].status == DocumentDiffStatus.DIFF_COMPUTATION_FAILED
    assert result.data[0].snapshot_diff is None


def test_execute_sorts_results_by_git_path_for_deterministic_order() -> None:
    repo = GitRepository(name="r", absolute_path="/repo")
    staged_paths = ["z.FCStd", "a.FCStd"]
    snapshot_mapping = {
        (None, "z.FCStd"): SnapshotLoadResult(_snapshot("z.FCStd", "index"), SnapshotLoadStatus.FOUND),
        ("HEAD", "z.FCStd"): SnapshotLoadResult(_snapshot("z.FCStd", "head"), SnapshotLoadStatus.FOUND),
        (None, "a.FCStd"): SnapshotLoadResult(_snapshot("a.FCStd", "index"), SnapshotLoadStatus.FOUND),
        ("HEAD", "a.FCStd"): SnapshotLoadResult(_snapshot("a.FCStd", "head"), SnapshotLoadStatus.FOUND),
    }
    action = _build_action(snapshot_mapping=snapshot_mapping, staged_paths=staged_paths)

    result = action.execute(CreateDocumentDiffsRequest(mode=DocumentDiffMode.STAGING, repo=repo))

    assert [item.git_path for item in result.data] == ["a.FCStd", "z.FCStd"]
