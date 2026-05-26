"""File responsibility: Unit tests for DiffPresenter commit selection via application action."""

from datetime import datetime
from unittest.mock import MagicMock

from freecad.history_wb.application.actions.create_document_diffs import CreateDocumentDiffsAction
from freecad.history_wb.application.actions.get_dirty_documents import GetDirtyDocumentsAction
from freecad.history_wb.application.actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from freecad.history_wb.application.actions.open_visual_diff import (
    OpenVisualDiffAction,
    OpenVisualDiffRequest,
    VisualDiffRequestType,
)
from freecad.history_wb.application.actions.result_models import (
    CreateDocumentDiffsRequest,
    DocumentDiffMode,
    DocumentDiffResult,
    DocumentDiffStatus,
    Result,
)
from freecad.history_wb.application.actions.stage_documents import StageDocumentsAction
from freecad.history_wb.domain.diff.models import DiffResult
from freecad.history_wb.domain.git.models import GitRepository
from freecad.history_wb.domain.snapshots.models import Snapshot
from freecad.history_wb.ui.presenters.diff_presenter import DiffPresenter
from freecad.history_wb.ui.presenters.presentation_models import NewFileIndicator
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
        get_dirty_documents_action=MagicMock(spec=GetDirtyDocumentsAction),
        open_visual_feature_diff_action=MagicMock(spec=OpenVisualDiffAction),
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

    def test_commit_selection_renders_new_status_indicator_without_tree(self) -> None:
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
        assert isinstance(presentations[0].indicators[0], NewFileIndicator)
        assert presentations[0].indicators[0].tooltip == "New document"


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
