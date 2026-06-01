"""File responsibility: Unit tests for DiffPresenter integration with document diff action results."""

from datetime import datetime
from unittest.mock import MagicMock

from freecad.history_wb.application.actions.create_document_diffs import CreateDocumentDiffsAction
from freecad.history_wb.application.actions.get_committed_file_paths import GetCommittedFilePathsAction
from freecad.history_wb.application.actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from freecad.history_wb.application.actions.get_staged_file_paths import GetStagedFilePathsAction
from freecad.history_wb.application.actions.open_document import OpenDocumentAction
from freecad.history_wb.application.actions.open_visual_diff import (
    OpenVisualDiffAction,
    OpenVisualDiffRequest,
    VisualDiffRequestType,
)
from freecad.history_wb.application.actions.restore_documents import RestoreDocumentsAction
from freecad.history_wb.application.actions.result_models import (
    CreateDocumentDiffsRequest,
    DiffIssues,
    DocumentDiffMode,
    DocumentDiffResult,
    GeneralDiffIssue,
    Result,
    SnapshotIssue,
)
from freecad.history_wb.application.actions.stage_documents import StageDocumentsAction
from freecad.history_wb.application.actions.unstage_documents import UnstageDocumentsAction
from freecad.history_wb.domain.diff.models import DiffResult, DiffState
from freecad.history_wb.domain.git.models import GitRepository
from freecad.history_wb.domain.snapshots.models import Snapshot
from freecad.history_wb.ui.presenters.diff_presenter import DiffPresenter
from freecad.history_wb.ui.state import UIState
from freecad.history_wb.ui.views.models import HistorySelection
from tests.fakes.fake_diff_view import FakeDiffView


def _make_presenter() -> tuple[FakeDiffView, DiffPresenter, MagicMock]:
    view = FakeDiffView()
    ui_state = UIState(git_repository=None)
    create_document_diffs_action = MagicMock(spec=CreateDocumentDiffsAction)
    presenter = DiffPresenter(
        view=view,
        ui_state=ui_state,
        get_eligible_docs_action=MagicMock(spec=GetOpenEligibleDocumentsAction),
        create_document_diffs_action=create_document_diffs_action,
        stage_documents_action=MagicMock(spec=StageDocumentsAction),
        unstage_documents_action=MagicMock(spec=UnstageDocumentsAction),
        get_staged_file_paths_action=MagicMock(spec=GetStagedFilePathsAction),
        get_committed_file_paths_action=MagicMock(spec=GetCommittedFilePathsAction),
        open_visual_feature_diff_action=MagicMock(spec=OpenVisualDiffAction),
        open_document_action=MagicMock(spec=OpenDocumentAction),
        restore_documents_action=MagicMock(spec=RestoreDocumentsAction),
    )
    return view, presenter, create_document_diffs_action


class TestDiffPresenterDocumentResults:
    def test_commit_selection_calls_document_diffs_action(self) -> None:
        _, presenter, create_document_diffs_action = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        create_document_diffs_action.execute.return_value = Result.success([])

        presenter._on_commit_selected("abc123")

        create_document_diffs_action.execute.assert_called_once_with(
            CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="abc123")
        )

    def test_indicator_order_old_new_general(self) -> None:
        view, presenter, _ = _make_presenter()
        presenter._current_history_selection = HistorySelection(item_kind="COMMIT", commit_hash="abc")

        presenter.present_diffs(
            [
                DocumentDiffResult(
                    git_path="doc.FCStd",
                    document_state=DiffState.MODIFIED,
                    issues=DiffIssues(
                        old_snapshot=SnapshotIssue.MISSING,
                        new_snapshot=SnapshotIssue.INVALID,
                        general=[GeneralDiffIssue.GIT_CHANGED_NO_PARAMETRIC_DIFF],
                    ),
                )
            ]
        )

        show_trees_call = next((c for c in view.get_calls() if c["method"] == "show_doc_diffs"), None)
        assert show_trees_call is not None
        indicators = show_trees_call["diff_trees"][0].indicators
        assert len(indicators) == 3

    def test_stage_button_rule_uses_state_and_new_side_issue(self) -> None:
        _, presenter, _ = _make_presenter()
        presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        enabled = presenter._compute_stage_button_state(
            DocumentDiffResult(git_path="a.FCStd", document_state=DiffState.MODIFIED, issues=DiffIssues()),
            True,
        )
        blocked = presenter._compute_stage_button_state(
            DocumentDiffResult(
                git_path="a.FCStd",
                document_state=DiffState.MODIFIED,
                issues=DiffIssues(new_snapshot=SnapshotIssue.MISSING),
            ),
            True,
        )
        assert enabled is True
        assert blocked is False

    def test_stage_button_enabled_with_old_side_issue_only(self) -> None:
        _, presenter, _ = _make_presenter()
        presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        enabled = presenter._compute_stage_button_state(
            DocumentDiffResult(
                git_path="a.FCStd",
                document_state=DiffState.MODIFIED,
                issues=DiffIssues(old_snapshot=SnapshotIssue.MISSING),
            ),
            True,
        )

        assert enabled is True

    def test_stage_button_enabled_for_deleted_document(self) -> None:
        _, presenter, _ = _make_presenter()
        presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        enabled = presenter._compute_stage_button_state(
            DocumentDiffResult(git_path="gone.FCStd", document_state=DiffState.DELETED, issues=DiffIssues()),
            True,
        )

        assert enabled is True

    def test_working_tree_uses_open_document_indicator_for_missing_new_snapshot(self) -> None:
        view, presenter, _ = _make_presenter()
        presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        presenter.present_diffs(
            [
                DocumentDiffResult(
                    git_path="doc.FCStd",
                    document_state=DiffState.MODIFIED,
                    issues=DiffIssues(new_snapshot=SnapshotIssue.MISSING),
                )
            ]
        )

        show_trees_call = next((c for c in view.get_calls() if c["method"] == "show_doc_diffs"), None)
        assert show_trees_call is not None
        indicator = show_trees_call["diff_trees"][0].indicators[0]
        assert indicator.__class__.__name__ == "WorkingTreeDocumentClosedIndicator"

    def test_working_tree_deleted_does_not_use_open_document_indicator(self) -> None:
        view, presenter, _ = _make_presenter()
        presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        presenter.present_diffs(
            [
                DocumentDiffResult(
                    git_path="gone.FCStd",
                    document_state=DiffState.DELETED,
                    issues=DiffIssues(old_snapshot=SnapshotIssue.MISSING),
                )
            ]
        )

        show_trees_call = next((c for c in view.get_calls() if c["method"] == "show_doc_diffs"), None)
        assert show_trees_call is not None
        indicators = show_trees_call["diff_trees"][0].indicators
        assert all(ind.__class__.__name__ != "WorkingTreeDocumentClosedIndicator" for ind in indicators)

    def test_commit_selection_does_not_query_changed_path_actions(self) -> None:
        _, presenter, create_document_diffs_action = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        create_document_diffs_action.execute.return_value = Result.success([])

        presenter._on_commit_selected("abc123")

        presenter._get_committed_file_paths.execute.assert_not_called()
        presenter._get_staged_file_paths.execute.assert_not_called()

    def test_present_diffs_filters_out_unchanged_document_without_issues(self) -> None:
        view, presenter, _ = _make_presenter()
        presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        presenter.present_diffs(
            [
                DocumentDiffResult(
                    git_path="doc.FCStd",
                    document_state=DiffState.UNCHANGED,
                    issues=DiffIssues(),
                )
            ]
        )

        show_trees_call = next((c for c in view.get_calls() if c["method"] == "show_doc_diffs"), None)
        assert show_trees_call is not None
        assert show_trees_call["diff_trees"] == []

    def test_present_diffs_shows_deleted_without_snapshot_diff(self) -> None:
        view, presenter, _ = _make_presenter()
        presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        presenter.present_diffs(
            [
                DocumentDiffResult(
                    git_path="gone.FCStd",
                    document_state=DiffState.DELETED,
                    snapshot_diff=None,
                    issues=DiffIssues(),
                )
            ]
        )

        show_trees_call = next((c for c in view.get_calls() if c["method"] == "show_doc_diffs"), None)
        assert show_trees_call is not None
        assert [tree.git_path for tree in show_trees_call["diff_trees"]] == ["gone.FCStd"]

    def test_open_document_click_focuses_history_window_after_refresh(self) -> None:
        _, presenter, _ = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        presenter._open_document.execute.return_value = Result.success("/home/user/dir/repo/doc.FCStd")
        presenter._get_eligible_docs.execute.return_value = Result.failure("no docs")
        focused: list[bool] = []
        presenter.set_focus_history_window_callback(lambda: focused.append(True))

        presenter.on_open_document_for_comparison_clicked("doc.FCStd")

        assert focused == [True]

    def test_add_button_click_removes_staged_row_from_cached_current_files(self) -> None:
        view, presenter, _ = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        snapshot_a = Snapshot(snapshot_id="a", document_name="a.FCStd", timestamp=datetime.now(), git_path="a.FCStd")
        snapshot_b = Snapshot(snapshot_id="b", document_name="b.FCStd", timestamp=datetime.now(), git_path="b.FCStd")
        presenter._diff_results_by_path = {
            "a.FCStd": DiffResult(old_snapshot=snapshot_a, new_snapshot=snapshot_a),
            "b.FCStd": DiffResult(old_snapshot=snapshot_b, new_snapshot=snapshot_b),
        }
        presenter._document_results_by_path = {
            "a.FCStd": DocumentDiffResult(git_path="a.FCStd", document_state=DiffState.MODIFIED, issues=DiffIssues()),
            "b.FCStd": DocumentDiffResult(git_path="b.FCStd", document_state=DiffState.MODIFIED, issues=DiffIssues()),
        }
        presenter._stage_documents.execute.return_value = Result.success(True)

        presenter.on_add_button_clicked("a.FCStd")

        presenter._stage_documents.execute.assert_called_once_with(repo, [snapshot_a], deleted_paths=[])

        assert "a.FCStd" not in presenter._diff_results_by_path
        assert "a.FCStd" not in presenter._document_results_by_path
        show_trees_call = next((c for c in view.get_calls() if c["method"] == "show_doc_diffs"), None)
        assert show_trees_call is not None
        assert [tree.git_path for tree in show_trees_call["diff_trees"]] == ["b.FCStd"]

    def test_deleted_single_mark_reviewed_stages_deleted_path_only(self) -> None:
        _, presenter, _ = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)
        presenter._document_results_by_path = {
            "gone.FCStd": DocumentDiffResult(git_path="gone.FCStd", document_state=DiffState.DELETED, issues=DiffIssues())
        }
        presenter._stage_documents.execute.return_value = Result.success(True)

        presenter.on_add_button_clicked("gone.FCStd")

        presenter._stage_documents.execute.assert_called_once_with(repo, [], deleted_paths=["gone.FCStd"])

    def test_stage_all_sends_snapshots_and_deleted_paths(self) -> None:
        _, presenter, _ = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        snapshot_a = Snapshot(snapshot_id="a", document_name="a.FCStd", timestamp=datetime.now(), git_path="a.FCStd")
        presenter._diff_results_by_path = {
            "a.FCStd": DiffResult(old_snapshot=snapshot_a, new_snapshot=snapshot_a),
        }
        presenter._document_results_by_path = {
            "a.FCStd": DocumentDiffResult(git_path="a.FCStd", document_state=DiffState.MODIFIED, issues=DiffIssues()),
            "gone.FCStd": DocumentDiffResult(git_path="gone.FCStd", document_state=DiffState.DELETED, issues=DiffIssues()),
        }
        presenter._stage_documents.execute.return_value = Result.success(True)

        presenter.on_stage_all_clicked()

        presenter._stage_documents.execute.assert_called_once_with(
            repo,
            [snapshot_a],
            deleted_paths=["gone.FCStd"],
        )

    def test_working_tree_selected_with_no_eligible_docs_still_computes_diffs(self) -> None:
        _, presenter, create_document_diffs_action = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        presenter._get_eligible_docs.execute.return_value = Result.success([])
        create_document_diffs_action.execute.return_value = Result.success([])

        presenter._on_working_tree_selected()

        create_document_diffs_action.execute.assert_called_once_with(
            CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, eligible_docs=[])
        )


class TestVisualDiffClickHandling:
    def test_visual_diff_click_builds_working_tree_request(self) -> None:
        _, presenter, _ = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        snapshot = Snapshot(
            snapshot_id="s1",
            document_name="doc.FCStd",
            timestamp=datetime.now(),
            git_path="doc.FCStd",
        )
        presenter._diff_results_by_path["doc.FCStd"] = DiffResult(old_snapshot=snapshot, new_snapshot=snapshot)

        presenter.on_visual_diff_clicked("doc.FCStd", "Body/Pad")

        presenter._open_visual_feature_diff.execute.assert_called_once()
        request = presenter._open_visual_feature_diff.execute.call_args.args[0]
        assert isinstance(request, OpenVisualDiffRequest)
        assert request.type is VisualDiffRequestType.WORKING
