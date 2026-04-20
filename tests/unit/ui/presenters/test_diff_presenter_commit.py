"""File responsibility: Unit tests for DiffPresenter commit selection orchestration.

Tests for _on_commit_selected() and _compute_commit_diffs() methods.
"""

import datetime
from unittest.mock import MagicMock

from freecad.diff_wb.application.actions.create_diff import CreateDiffAction
from freecad.diff_wb.application.actions.create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
from freecad.diff_wb.application.actions.create_document_snapshot_working import (
    CreateDocumentSnapshotForWorkingTreeAction,
)
from freecad.diff_wb.application.actions.get_committed_file_paths import GetCommittedFilePathsAction
from freecad.diff_wb.application.actions.get_dirty_documents import GetDirtyDocumentsAction
from freecad.diff_wb.application.actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from freecad.diff_wb.application.actions.get_staged_file_paths import GetStagedFilePathsAction
from freecad.diff_wb.application.actions.stage_documents import StageDocumentsAction
from freecad.diff_wb.domain.diff.models import DiffHierarchy, DiffResult
from freecad.diff_wb.domain.git.models import GitRepository
from freecad.diff_wb.domain.snapshots import Snapshot
from freecad.diff_wb.ui.presenters.diff_presenter import DiffPresenter
from freecad.diff_wb.ui.state import UIState
from tests.fakes.fake_diff_view import FakeDiffView


def _create_test_presenter(
    get_committed_file_paths_action: MagicMock | None = None,
) -> tuple[FakeDiffView, DiffPresenter, MagicMock]:
    """Helper to create a DiffPresenter with mock dependencies.

    Args:
        get_committed_file_paths_action: Optional mock for GetCommittedFilePathsAction.

    Returns:
        Tuple of (FakeDiffView, DiffPresenter, get_committed_file_paths_action mock).
    """
    view = FakeDiffView()
    ui_state = UIState(git_repository=None)

    # Create mock actions
    get_eligible_docs_action = MagicMock(spec=GetOpenEligibleDocumentsAction)
    create_working_snapshot_action = MagicMock(spec=CreateDocumentSnapshotForWorkingTreeAction)
    create_commit_snapshot_action = MagicMock(spec=CreateDocumentSnapshotForCommitAction)
    create_diff_action = MagicMock(spec=CreateDiffAction)
    stage_documents_action = MagicMock(spec=StageDocumentsAction)
    get_dirty_documents_action = MagicMock(spec=GetDirtyDocumentsAction)
    get_staged_file_paths_action = MagicMock(spec=GetStagedFilePathsAction)

    if get_committed_file_paths_action is None:
        get_committed_file_paths_action = MagicMock(spec=GetCommittedFilePathsAction)

    presenter = DiffPresenter(
        view=view,
        ui_state=ui_state,
        get_eligible_docs_action=get_eligible_docs_action,
        create_working_snapshot_action=create_working_snapshot_action,
        create_commit_snapshot_action=create_commit_snapshot_action,
        create_diff_action=create_diff_action,
        stage_documents_action=stage_documents_action,
        get_dirty_documents_action=get_dirty_documents_action,
        get_staged_file_paths_action=get_staged_file_paths_action,
        get_committed_file_paths_action=get_committed_file_paths_action,
    )
    return view, presenter, get_committed_file_paths_action


def _make_result(is_success: bool, data=None, message: str | None = None) -> MagicMock:
    """Create a mock Result object.

    Args:
        is_success: Whether the result is successful.
        data: The data to return.
        message: Error message for failures.

    Returns:
        A MagicMock configured as a Result.
    """
    result = MagicMock()
    result.is_success = is_success
    result.data = data
    result.message = message
    return result


def _make_snapshot(
    snapshot_id: str,
    document_name: str,
    git_path: str | None = None,
) -> Snapshot:
    """Create a test Snapshot.

    Args:
        snapshot_id: Unique ID for the snapshot.
        document_name: Name of the document.
        git_path: Git path of the file.

    Returns:
        A Snapshot instance.
    """
    return Snapshot(
        snapshot_id=snapshot_id,
        document_name=document_name,
        timestamp=datetime.datetime.now(),
        git_path=git_path,
    )


def _make_diff_result(
    old_snapshot: Snapshot | None,
    new_snapshot: Snapshot,
    added_count: int = 0,
    deleted_count: int = 0,
    modified_count: int = 0,
) -> DiffResult:
    """Create a test DiffResult.

    Args:
        old_snapshot: Old snapshot or None.
        new_snapshot: New snapshot.
        added_count: Number of added nodes.
        deleted_count: Number of deleted nodes.
        modified_count: Number of modified nodes.

    Returns:
        A DiffResult instance.
    """
    return DiffResult(
        old_snapshot=old_snapshot,
        new_snapshot=new_snapshot,
        hierarchy=DiffHierarchy(),
        added_count=added_count,
        deleted_count=deleted_count,
        modified_count=modified_count,
    )


class TestDiffPresenterOnCommitSelected:
    """Tests for DiffPresenter._on_commit_selected() orchestration."""

    def test_on_commit_selected_calls_get_committed_file_paths_for_commit(self) -> None:
        """_on_commit_selected() calls GetCommittedFilePathsAction for the commit."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        mock_get_paths_result = _make_result(is_success=True, data=["doc.FCStd"])
        mock_get_paths.execute.return_value = mock_get_paths_result

        # Setup snapshot and diff mocks
        new_snapshot = _make_snapshot("s1", "doc.FCStd", git_path="doc.FCStd")
        mock_snap_result = _make_result(is_success=True, data=new_snapshot)
        presenter._create_commit_snapshot.execute.return_value = mock_snap_result

        mock_diff_result = _make_diff_result(old_snapshot=None, new_snapshot=new_snapshot)
        mock_diff_exec_result = _make_result(is_success=True, data=mock_diff_result)
        presenter._create_diff.execute.return_value = mock_diff_exec_result

        # Act
        presenter._on_commit_selected("abc123")

        # Assert
        presenter._get_committed_file_paths.execute.assert_any_call(mock_repo, "abc123")

    def test_on_commit_selected_calls_get_committed_file_paths_for_parent(self) -> None:
        """_on_commit_selected() calls GetCommittedFilePathsAction for the parent commit."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        mock_get_paths_result = _make_result(is_success=True, data=["doc.FCStd"])
        mock_get_paths.execute.return_value = mock_get_paths_result

        # Setup snapshot and diff mocks
        new_snapshot = _make_snapshot("s1", "doc.FCStd", git_path="doc.FCStd")
        mock_snap_result = _make_result(is_success=True, data=new_snapshot)
        presenter._create_commit_snapshot.execute.return_value = mock_snap_result

        mock_diff_result = _make_diff_result(old_snapshot=None, new_snapshot=new_snapshot)
        mock_diff_exec_result = _make_result(is_success=True, data=mock_diff_result)
        presenter._create_diff.execute.return_value = mock_diff_exec_result

        # Act
        presenter._on_commit_selected("abc123")

        # Assert
        presenter._get_committed_file_paths.execute.assert_any_call(mock_repo, "abc123^")

    def test_on_commit_selected_unions_commit_and_parent_paths(self) -> None:
        """_on_commit_selected() unions commit paths and parent paths."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Commit has doc1.FCStd, parent has doc2.FCStd
        mock_get_paths.execute.side_effect = [
            _make_result(is_success=True, data=["doc1.FCStd"]),  # commit
            _make_result(is_success=True, data=["doc2.FCStd"]),  # parent
        ]

        # Setup snapshot and diff mocks for both paths
        new_snapshot1 = _make_snapshot("s1", "doc1.FCStd", git_path="doc1.FCStd")
        new_snapshot2 = _make_snapshot("s2", "doc2.FCStd", git_path="doc2.FCStd")

        call_count = [0]

        def snapshot_side_effect(repo, ref, path):
            call_count[0] += 1
            snap = new_snapshot1 if path == "doc1.FCStd" else new_snapshot2
            return _make_result(is_success=True, data=snap)

        presenter._create_commit_snapshot.execute.side_effect = snapshot_side_effect

        def diff_side_effect(old, new):
            return _make_result(is_success=True, data=_make_diff_result(old_snapshot=old, new_snapshot=new))

        presenter._create_diff.execute.side_effect = diff_side_effect

        # Act
        presenter._on_commit_selected("abc123")

        # Assert - both paths should be processed
        assert presenter._create_commit_snapshot.execute.call_count == 4  # 2 paths x 2 refs each

    def test_on_commit_selected_both_snapshots_exist_diff_created(self) -> None:
        """When both commit and parent snapshots exist, diff is created."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        mock_get_paths_result = _make_result(is_success=True, data=["doc.FCStd"])
        mock_get_paths.execute.return_value = mock_get_paths_result

        commit_snap = _make_snapshot("s1", "doc.FCStd", git_path="doc.FCStd")
        parent_snap = _make_snapshot("s2", "doc.FCStd", git_path="doc.FCStd")

        call_count = [0]

        def snapshot_side_effect(repo, ref, path):
            call_count[0] += 1
            if call_count[0] % 2 == 1:  # commit snapshot (odd calls)
                return _make_result(is_success=True, data=commit_snap)
            return _make_result(is_success=True, data=parent_snap)  # parent snapshot (even calls)

        presenter._create_commit_snapshot.execute.side_effect = snapshot_side_effect

        captured_args = []

        def diff_side_effect(old, new):
            captured_args.append((old, new))
            return _make_result(
                is_success=True,
                data=_make_diff_result(old_snapshot=old, new_snapshot=new),
            )

        presenter._create_diff.execute.side_effect = diff_side_effect

        # Act
        presenter._on_commit_selected("abc123")

        # Assert - diff should be created with both snapshots
        # _create_diff.execute(parent_snapshot, commit_snapshot) → old=parent_snap, new=commit_snap
        assert len(captured_args) == 1
        old_snap, new_snap = captured_args[0]
        assert old_snap is parent_snap
        assert new_snap is commit_snap

    def test_on_commit_selected_commit_exists_parent_none_diff_with_none_old(self) -> None:
        """Commit snapshot exists but parent is None → diff with old_snapshot=None."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        mock_get_paths_result = _make_result(is_success=True, data=["doc.FCStd"])
        mock_get_paths.execute.return_value = mock_get_paths_result

        commit_snap = _make_snapshot("s1", "doc.FCStd", git_path="doc.FCStd")

        def snapshot_side_effect(repo, ref, path):
            if ref == "abc123":  # commit ref
                return _make_result(is_success=True, data=commit_snap)
            return _make_result(is_success=True, data=None)  # parent ref fails

        presenter._create_commit_snapshot.execute.side_effect = snapshot_side_effect

        captured_args = []

        def diff_side_effect(old, new):
            captured_args.append((old, new))
            return _make_result(
                is_success=True,
                data=_make_diff_result(old_snapshot=old, new_snapshot=new),
            )

        presenter._create_diff.execute.side_effect = diff_side_effect

        # Act
        presenter._on_commit_selected("abc123")

        # Assert - diff created with None as old_snapshot
        assert len(captured_args) == 1
        old_snap, new_snap = captured_args[0]
        assert old_snap is None
        assert new_snap is commit_snap

    def test_on_commit_selected_parent_exists_commit_none_skip(self) -> None:
        """Parent snapshot exists but commit is None → skip (no data to compare)."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        mock_get_paths_result = _make_result(is_success=True, data=["doc.FCStd"])
        mock_get_paths.execute.return_value = mock_get_paths_result

        parent_snap = _make_snapshot("s2", "doc.FCStd", git_path="doc.FCStd")

        def snapshot_side_effect(repo, ref, path):
            if ref == "abc123":  # commit ref
                return _make_result(is_success=True, data=None)  # no commit snapshot
            return _make_result(is_success=True, data=parent_snap)  # parent exists

        presenter._create_commit_snapshot.execute.side_effect = snapshot_side_effect

        # Act
        presenter._on_commit_selected("abc123")

        # Assert - no diff created
        presenter._create_diff.execute.assert_not_called()

    def test_on_commit_selected_both_none_skip(self) -> None:
        """Both commit and parent snapshots are None → skip."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        mock_get_paths_result = _make_result(is_success=True, data=["doc.FCStd"])
        mock_get_paths.execute.return_value = mock_get_paths_result

        # Both return None
        presenter._create_commit_snapshot.execute.return_value = _make_result(is_success=True, data=None)

        # Act
        presenter._on_commit_selected("abc123")

        # Assert - no diff created
        presenter._create_diff.execute.assert_not_called()

    def test_on_commit_selected_parent_snapshot_missing_tracked_as_missing(self) -> None:
        """Parent snapshot missing → diff created + path tracked in missing_snapshot_paths."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        mock_get_paths_result = _make_result(is_success=True, data=["doc.FCStd"])
        mock_get_paths.execute.return_value = mock_get_paths_result

        commit_snap = _make_snapshot("s1", "doc.FCStd", git_path="doc.FCStd")

        def snapshot_side_effect(repo, ref, path):
            if ref == "abc123":  # commit ref
                return _make_result(is_success=True, data=commit_snap)
            return _make_result(is_success=True, data=None)  # parent fails (YAML extraction, etc.)

        presenter._create_commit_snapshot.execute.side_effect = snapshot_side_effect

        presenter._create_diff.execute.return_value = _make_result(
            is_success=True,
            data=_make_diff_result(old_snapshot=None, new_snapshot=commit_snap),
        )

        # Act
        presenter._on_commit_selected("abc123")

        # Assert - present_diffs should be called with missing paths
        calls = fake_view.get_calls()
        present_diffs_call = next((c for c in calls if c["method"] == "show_diff_trees"), None)
        assert present_diffs_call is not None
        presentations = present_diffs_call["diff_trees"]
        # Should have 1 diff tree + 1 warning item for missing snapshot
        assert len(presentations) == 2
        # Find the warning item
        warning_items = [p for p in presentations if p.warnings]
        assert len(warning_items) == 1
        assert warning_items[0].git_path == "doc.FCStd"

    def test_on_commit_selected_no_git_repository_early_return(self) -> None:
        """Returns early with no diff computation when no git repository is set."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        # No git repository set (ui_state.git_repository is None by default)

        # Act
        presenter._on_commit_selected("abc123")

        # Assert - no actions should have been called
        mock_get_paths.execute.assert_not_called()
        presenter._create_commit_snapshot.execute.assert_not_called()
        presenter._create_diff.execute.assert_not_called()

    def test_on_commit_selected_root_commit_parent_ref_fails_gracefully(self) -> None:
        """Root commit: parent ref fails gracefully, uses None for parent snapshot."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Commit has files, parent (root commit ^) has no files
        mock_get_paths.execute.side_effect = [
            _make_result(is_success=True, data=["doc.FCStd"]),  # commit has file
            _make_result(is_success=True, data=[]),  # parent (root) has no files
        ]

        commit_snap = _make_snapshot("s1", "doc.FCStd", git_path="doc.FCStd")

        def snapshot_side_effect(repo, ref, path):
            if ref == "abc123^":  # parent ref for root commit
                return _make_result(is_success=True, data=None)
            return _make_result(is_success=True, data=commit_snap)

        presenter._create_commit_snapshot.execute.side_effect = snapshot_side_effect

        captured_args = []

        def diff_side_effect(old, new):
            captured_args.append((old, new))
            return _make_result(
                is_success=True,
                data=_make_diff_result(old_snapshot=old, new_snapshot=new),
            )

        presenter._create_diff.execute.side_effect = diff_side_effect

        # Act
        presenter._on_commit_selected("abc123")

        # Assert - diff created with None as old_snapshot (root commit behavior)
        assert len(captured_args) == 1
        old_snap, new_snap = captured_args[0]
        assert old_snap is None
        assert new_snap is commit_snap

    def test_on_commit_selected_stores_results_in_diff_results_by_path(self) -> None:
        """_on_commit_selected() stores diff results in _diff_results_by_path."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        mock_get_paths_result = _make_result(is_success=True, data=["doc.FCStd"])
        mock_get_paths.execute.return_value = mock_get_paths_result

        commit_snap = _make_snapshot("s1", "doc.FCStd", git_path="doc.FCStd")

        def snapshot_side_effect(repo, ref, path):
            return (
                _make_result(is_success=True, data=commit_snap)
                if ref == "abc123"
                else _make_result(is_success=True, data=None)
            )

        presenter._create_commit_snapshot.execute.side_effect = snapshot_side_effect

        mock_diff_result = _make_diff_result(old_snapshot=None, new_snapshot=commit_snap)
        presenter._create_diff.execute.return_value = _make_result(is_success=True, data=mock_diff_result)

        # Act
        presenter._on_commit_selected("abc123")

        # Assert
        assert "doc.FCStd" in presenter._diff_results_by_path
        assert presenter._diff_results_by_path["doc.FCStd"] is mock_diff_result

    def test_on_commit_selected_no_changes_logs_info(self) -> None:
        """When no FCStd files changed, logs info and shows empty diff trees."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Both commit and parent have no FCStd files
        mock_get_paths.execute.side_effect = [
            _make_result(is_success=True, data=[]),
            _make_result(is_success=True, data=[]),
        ]

        # Act
        presenter._on_commit_selected("abc123")

        # Assert - show_diff_trees called with empty list
        calls = fake_view.get_calls()
        show_trees_call = next((c for c in calls if c["method"] == "show_diff_trees"), None)
        assert show_trees_call is not None
        assert show_trees_call["diff_trees"] == []


class TestDiffPresenterComputeCommitDiffs:
    """Tests for DiffPresenter._compute_commit_diffs() method."""

    def test_compute_commit_diffs_returns_tuple_of_results_and_missing_paths(self) -> None:
        """_compute_commit_diffs() returns (list[DiffResult], list[str])."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")

        mock_get_paths_result = _make_result(is_success=True, data=["doc.FCStd"])
        mock_get_paths.execute.return_value = mock_get_paths_result

        commit_snap = _make_snapshot("s1", "doc.FCStd", git_path="doc.FCStd")

        def snapshot_side_effect(repo, ref, path):
            return (
                _make_result(is_success=True, data=commit_snap)
                if ref == "abc123"
                else _make_result(is_success=True, data=None)
            )

        presenter._create_commit_snapshot.execute.side_effect = snapshot_side_effect

        mock_diff_result = _make_diff_result(old_snapshot=None, new_snapshot=commit_snap)
        presenter._create_diff.execute.return_value = _make_result(is_success=True, data=mock_diff_result)

        # Act
        results, missing_paths = presenter._compute_commit_diffs(mock_repo, "abc123")

        # Assert
        assert isinstance(results, list)
        assert isinstance(missing_paths, list)
        assert len(results) == 1
        assert len(missing_paths) == 1
        assert missing_paths[0] == "doc.FCStd"

    def test_compute_commit_diffs_handles_failed_get_paths_returns_empty(self) -> None:
        """When GetCommittedFilePathsAction fails, returns empty results."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")

        # Both commit and parent fail
        mock_get_paths.execute.side_effect = [
            _make_result(is_success=False, data=[], message="Git error"),
            _make_result(is_success=False, data=[], message="Git error"),
        ]

        # Act
        results, missing_paths = presenter._compute_commit_diffs(mock_repo, "abc123")

        # Assert
        assert results == []
        assert missing_paths == []

    def test_compute_commit_diffs_handles_failed_snapshot_creation_gracefully(self) -> None:
        """When all snapshot creation fails, both are None → skip entirely."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")

        mock_get_paths_result = _make_result(is_success=True, data=["doc.FCStd"])
        mock_get_paths.execute.return_value = mock_get_paths_result

        # All snapshot creation fails for both commit and parent
        presenter._create_commit_snapshot.execute.return_value = _make_result(
            is_success=False, data=None, message="Extraction failed"
        )

        # Act
        results, missing_paths = presenter._compute_commit_diffs(mock_repo, "abc123")

        # Assert - both snapshots are None, so skip entirely
        assert results == []
        assert missing_paths == []

    def test_compute_commit_diffs_multiple_paths(self) -> None:
        """Computes diffs for multiple paths, no missing paths when both snapshots exist."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")

        mock_get_paths_result = _make_result(is_success=True, data=["doc1.FCStd", "doc2.FCStd"])
        mock_get_paths.execute.return_value = mock_get_paths_result

        snap1 = _make_snapshot("s1", "doc1.FCStd", git_path="doc1.FCStd")
        snap2 = _make_snapshot("s2", "doc2.FCStd", git_path="doc2.FCStd")

        def snapshot_side_effect(repo, ref, path):
            snap = snap1 if path == "doc1.FCStd" else snap2
            return _make_result(is_success=True, data=snap)

        presenter._create_commit_snapshot.execute.side_effect = snapshot_side_effect

        def diff_side_effect(old, new):
            return _make_result(is_success=True, data=_make_diff_result(old_snapshot=old, new_snapshot=new))

        presenter._create_diff.execute.side_effect = diff_side_effect

        # Act
        results, missing_paths = presenter._compute_commit_diffs(mock_repo, "abc123")

        # Assert
        assert len(results) == 2
        assert len(missing_paths) == 0  # both have both snapshots, so no missing

    def test_compute_commit_diffs_only_commit_paths(self) -> None:
        """When only commit has paths (new file), parent has none."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")

        mock_get_paths.execute.side_effect = [
            _make_result(is_success=True, data=["new_file.FCStd"]),  # commit has new file
            _make_result(is_success=True, data=[]),  # parent has nothing
        ]

        new_snap = _make_snapshot("s1", "new_file.FCStd", git_path="new_file.FCStd")

        def snapshot_side_effect(repo, ref, path):
            if ref == "abc123^":
                return _make_result(is_success=True, data=None)
            return _make_result(is_success=True, data=new_snap)

        presenter._create_commit_snapshot.execute.side_effect = snapshot_side_effect

        presenter._create_diff.execute.return_value = _make_result(
            is_success=True,
            data=_make_diff_result(old_snapshot=None, new_snapshot=new_snap),
        )

        # Act
        results, missing_paths = presenter._compute_commit_diffs(mock_repo, "abc123")

        # Assert
        assert len(results) == 1
        assert len(missing_paths) == 1
        assert missing_paths[0] == "new_file.FCStd"

    def test_compute_commit_diffs_union_of_commit_and_parent_paths(self) -> None:
        """Union of commit and parent paths includes files only in parent."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")

        # Commit has doc1, parent has doc2 (deleted file)
        mock_get_paths.execute.side_effect = [
            _make_result(is_success=True, data=["doc1.FCStd"]),
            _make_result(is_success=True, data=["doc2.FCStd"]),
        ]

        snap1 = _make_snapshot("s1", "doc1.FCStd", git_path="doc1.FCStd")
        snap2 = _make_snapshot("s2", "doc2.FCStd", git_path="doc2.FCStd")

        call_count = [0]

        def snapshot_side_effect(repo, ref, path):
            call_count[0] += 1
            if path == "doc1.FCStd":
                if ref == "abc123":
                    return _make_result(is_success=True, data=snap1)
                return _make_result(is_success=True, data=None)
            else:  # doc2.FCStd
                if ref == "abc123":
                    return _make_result(is_success=True, data=None)  # not in commit
                return _make_result(is_success=True, data=snap2)

        presenter._create_commit_snapshot.execute.side_effect = snapshot_side_effect

        def diff_side_effect(old, new):
            return _make_result(is_success=True, data=_make_diff_result(old_snapshot=old, new_snapshot=new))

        presenter._create_diff.execute.side_effect = diff_side_effect

        # Act
        results, missing_paths = presenter._compute_commit_diffs(mock_repo, "abc123")

        # Assert - only doc1 should produce a result (doc2 has no commit snapshot)
        assert len(results) == 1
        assert results[0].new_snapshot is snap1

    def test_compute_commit_diffs_diff_creation_failure_returns_empty(self) -> None:
        """When diff creation fails, path is not in results but IS in missing_paths."""
        fake_view, presenter, mock_get_paths = _create_test_presenter()

        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")

        mock_get_paths_result = _make_result(is_success=True, data=["doc.FCStd"])
        mock_get_paths.execute.return_value = mock_get_paths_result

        commit_snap = _make_snapshot("s1", "doc.FCStd", git_path="doc.FCStd")

        def snapshot_side_effect(repo, ref, path):
            return (
                _make_result(is_success=True, data=commit_snap)
                if ref == "abc123"
                else _make_result(is_success=True, data=None)
            )

        presenter._create_commit_snapshot.execute.side_effect = snapshot_side_effect

        # Diff creation fails
        presenter._create_diff.execute.return_value = _make_result(is_success=False, data=None, message="Diff error")

        # Act
        results, missing_paths = presenter._compute_commit_diffs(mock_repo, "abc123")

        # Assert - path is in missing_paths because parent snapshot is None
        # (regardless of whether diff creation succeeded or not)
        assert results == []
        assert missing_paths == ["doc.FCStd"]
