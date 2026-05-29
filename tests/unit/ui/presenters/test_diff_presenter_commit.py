"""File responsibility: Unit tests for DiffPresenter commit selection via application action."""

from datetime import datetime
from unittest.mock import MagicMock

from freecad.history_wb.application.actions.create_document_diffs import CreateDocumentDiffsAction
from freecad.history_wb.application.actions.get_committed_file_paths import GetCommittedFilePathsAction
from freecad.history_wb.application.actions.get_dirty_documents import GetDirtyDocumentsAction
from freecad.history_wb.application.actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from freecad.history_wb.application.actions.get_staged_file_paths import GetStagedFilePathsAction
from freecad.history_wb.application.actions.open_visual_diff import (
    OpenVisualDiffAction,
    OpenVisualDiffRequest,
    VisualDiffRequestType,
)
from freecad.history_wb.application.actions.restore_documents import RestoreDocumentsAction
from freecad.history_wb.application.actions.result_models import (
    CreateDocumentDiffsRequest,
    DocumentDiffMode,
    DocumentDiffResult,
    DocumentDiffStatus,
    Result,
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
        get_dirty_documents_action=MagicMock(spec=GetDirtyDocumentsAction),
        get_staged_file_paths_action=MagicMock(spec=GetStagedFilePathsAction),
        get_committed_file_paths_action=MagicMock(spec=GetCommittedFilePathsAction),
        open_visual_feature_diff_action=MagicMock(spec=OpenVisualDiffAction),
        restore_documents_action=MagicMock(spec=RestoreDocumentsAction),
    )
    return view, presenter, create_document_diffs_action


class TestDiffPresenterCommitSelection:
    def test_commit_selection_calls_document_diffs_action(self) -> None:
        view, presenter, create_document_diffs_action = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        create_document_diffs_action.execute.return_value = Result.success([])

        presenter._on_commit_selected("abc123")

        create_document_diffs_action.execute.assert_called_once_with(
            CreateDocumentDiffsRequest(mode=DocumentDiffMode.COMMIT, repo=repo, commit_hash="abc123")
        )

    def test_staging_selection_calls_document_diffs_action(self) -> None:
        view, presenter, create_document_diffs_action = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        create_document_diffs_action.execute.return_value = Result.success([])

        presenter._on_staging_selected()

        create_document_diffs_action.execute.assert_called_once_with(
            CreateDocumentDiffsRequest(mode=DocumentDiffMode.STAGING, repo=repo)
        )

    def test_working_tree_selection_calls_document_diffs_action(self) -> None:
        from tests.fakes.fake_freecad_port import DocumentLike

        view, presenter, create_document_diffs_action = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        doc = MagicMock(spec=DocumentLike)
        presenter._get_eligible_docs.execute.return_value = Result.success([doc])
        presenter._get_dirty_documents.execute.return_value = Result.success([])
        create_document_diffs_action.execute.return_value = Result.success([])

        presenter._on_working_tree_selected()

        create_document_diffs_action.execute.assert_called_once_with(
            CreateDocumentDiffsRequest(mode=DocumentDiffMode.WORKING_TREE, repo=repo, documents=[doc])
        )

    def test_commit_selection_renders_new_document_state_without_indicator(self) -> None:
        view, presenter, create_document_diffs_action = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        create_document_diffs_action.execute.return_value = Result.success(
            [DocumentDiffResult(git_path="doc.FCStd", status=DocumentDiffStatus.NEW_FILE)]
        )

        presenter._on_commit_selected("abc123")

        show_trees_call = next((c for c in view.get_calls() if c["method"] == "show_doc_diffs"), None)
        assert show_trees_call is not None
        presentations = show_trees_call["diff_trees"]
        assert len(presentations) == 1
        assert presentations[0].git_path == "doc.FCStd"
        assert presentations[0].nodes == []
        assert presentations[0].document_state == DiffState.ADDED
        assert presentations[0].indicators == []

    def test_commit_selection_renders_deleted_document_state_without_indicator(self) -> None:
        view, presenter, create_document_diffs_action = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        create_document_diffs_action.execute.return_value = Result.success(
            [DocumentDiffResult(git_path="doc.FCStd", status=DocumentDiffStatus.DELETED_FILE)]
        )

        presenter._on_commit_selected("abc123")

        show_trees_call = next((c for c in view.get_calls() if c["method"] == "show_doc_diffs"), None)
        assert show_trees_call is not None
        presentations = show_trees_call["diff_trees"]
        assert len(presentations) == 1
        assert presentations[0].document_state == DiffState.DELETED
        assert presentations[0].indicators == []

    def test_commit_selection_old_snapshot_missing_keeps_indicator_and_unchanged_document_state(self) -> None:
        view, presenter, create_document_diffs_action = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        create_document_diffs_action.execute.return_value = Result.success(
            [DocumentDiffResult(git_path="doc.FCStd", status=DocumentDiffStatus.OLD_SNAPSHOT_MISSING)]
        )

        presenter._on_commit_selected("abc123")

        show_trees_call = next((c for c in view.get_calls() if c["method"] == "show_doc_diffs"), None)
        assert show_trees_call is not None
        presentations = show_trees_call["diff_trees"]
        assert len(presentations) == 1
        assert presentations[0].document_state == DiffState.UNCHANGED
        assert len(presentations[0].indicators) == 1

    def test_summary_uses_document_status_counts(self) -> None:
        view, presenter, _ = _make_presenter()
        presenter.present_diffs(
            diff_results=[],
            dirty_paths=set(),
            document_statuses={
                "mod.FCStd": DocumentDiffStatus.MODIFIED,
                "del.FCStd": DocumentDiffStatus.DELETED_FILE,
                "add.FCStd": DocumentDiffStatus.NEW_FILE,
                "same.FCStd": DocumentDiffStatus.UNCHANGED,
            },
        )

        summary_call = next((c for c in view.get_calls() if c["method"] == "show_summary"), None)
        assert summary_call is not None
        assert summary_call["modified_docs"] == 1
        assert summary_call["deleted_docs"] == 1
        assert summary_call["added_docs"] == 1


class TestDiffPresenterStageSingleDocument:
    def test_stage_click_clears_property_panel(self) -> None:
        view, presenter, _ = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo

        snapshot = Snapshot(
            snapshot_id="s1",
            document_name="doc.FCStd",
            timestamp=datetime.now(),
            git_path="doc.FCStd",
        )
        presenter._diff_results_by_path["doc.FCStd"] = DiffResult(
            old_snapshot=snapshot,
            new_snapshot=snapshot,
        )
        presenter._stage_documents.execute.return_value = Result.success(None)

        presenter.on_add_button_clicked("doc.FCStd")

        assert any(call["method"] == "clear_property_diff" for call in view.get_calls())


class TestVisualDiffClickHandling:
    def test_visual_diff_click_builds_working_tree_request(self) -> None:
        view, presenter, _ = _make_presenter()
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
        assert request.old_commit is None
        assert request.new_commit is None

    def test_visual_diff_click_builds_commit_request(self) -> None:
        view, presenter, _ = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        presenter._current_history_selection = HistorySelection(item_kind="COMMIT", commit_hash="abc123")

        snapshot = Snapshot(
            snapshot_id="s1",
            document_name="doc.FCStd",
            timestamp=datetime.now(),
            git_path="doc.FCStd",
        )
        presenter._diff_results_by_path["doc.FCStd"] = DiffResult(old_snapshot=snapshot, new_snapshot=snapshot)

        presenter.on_visual_diff_clicked("doc.FCStd", "Body/Pad")

        request = presenter._open_visual_feature_diff.execute.call_args.args[0]
        assert request.type is VisualDiffRequestType.COMMIT
        assert request.old_commit == "abc123~1"
        assert request.new_commit == "abc123"


class TestRemoveFromReviewed:
    def test_per_file_remove_calls_action_clears_property_and_refreshes_staging(self) -> None:
        view, presenter, create_document_diffs_action = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        presenter._unstage_documents.execute.return_value = Result.success(True)
        create_document_diffs_action.execute.return_value = Result.success([])

        presenter.on_remove_from_reviewed_button_clicked("doc.FCStd")

        presenter._unstage_documents.execute.assert_called_once_with(repo, ["doc.FCStd"])
        assert any(call["method"] == "clear_property_diff" for call in view.get_calls())
        create_document_diffs_action.execute.assert_called_with(
            CreateDocumentDiffsRequest(mode=DocumentDiffMode.STAGING, repo=repo)
        )

    def test_remove_all_refreshes_working_tree_when_working_tree_selected(self) -> None:
        view, presenter, _ = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        presenter._unstage_documents.execute.return_value = Result.success(True)
        view.set_current_history_selection(HistorySelection(item_kind="WORKING_TREE", commit_hash=None))

        presenter._on_working_tree_selected = MagicMock()
        presenter.on_remove_all_from_reviewed_clicked()

        presenter._unstage_documents.execute.assert_called_once_with(repo, None)
        presenter._on_working_tree_selected.assert_called_once()

    def test_staging_selection_shows_remove_all_summary_button(self) -> None:
        view, presenter, create_document_diffs_action = _make_presenter()
        repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
        presenter._ui_state.git_repository = repo
        create_document_diffs_action.execute.return_value = Result.success([])

        presenter._current_history_selection = HistorySelection(item_kind="STAGING", commit_hash=None)
        presenter.present_diffs([], set(), {"doc.FCStd": DocumentDiffStatus.NEW_FILE})

        assert any(
            call["method"] == "set_remove_all_button_visible" and call["visible"] is True for call in view.get_calls()
        )
