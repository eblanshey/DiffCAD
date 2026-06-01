# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for StageDocumentsAction staging snapshots and deleted documents.
"""Unit tests for StageDocumentsAction."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from freecad.history_wb.application.actions.stage_documents import StageDocumentsAction
from freecad.history_wb.domain.freecad_ports import FreeCadPort
from freecad.history_wb.domain.git.git_service import GitService
from freecad.history_wb.domain.git.models import GitRepository
from freecad.history_wb.domain.snapshots.models import Snapshot


def _snapshot(git_path: str) -> Snapshot:
    return Snapshot(
        snapshot_id="test-uuid",
        document_name=Path(git_path).name,
        timestamp=None,  # type: ignore[arg-type]
        objects=[],
        occurrences=[],
        git_path=git_path,
    )


def _build_action() -> tuple[StageDocumentsAction, MagicMock, MagicMock, GitRepository]:
    git_service = MagicMock(spec=GitService)
    freecad_port = MagicMock(spec=FreeCadPort)
    freecad_port.get_all_open_documents.return_value = []
    git_service.get_eligible_docs.return_value = []
    action = StageDocumentsAction(git_service=git_service, freecad_port=freecad_port)
    repo = GitRepository(name="test_repo", absolute_path="/home/user/dir/test_repo")
    return action, git_service, freecad_port, repo


class TestStageDocumentsAction:
    def test_empty_snapshots_and_deleted_paths_returns_success(self) -> None:
        action, git_service, _, repo = _build_action()

        result = action.execute(repo, [], deleted_paths=[])

        assert result.is_success is True
        assert result.data is True
        git_service.stage_files.assert_not_called()

    def test_matching_open_doc_always_calls_save_document(self) -> None:
        action, git_service, freecad_port, repo = _build_action()
        git_service.stage_files.return_value = True

        mock_doc = MagicMock()
        mock_doc.FileName = "/home/user/dir/test_repo/path/to/mydoc.FCStd"
        freecad_port.get_all_open_documents.return_value = [mock_doc]
        git_service.get_eligible_docs.return_value = [mock_doc]

        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer"),
            patch("pathlib.Path.mkdir"),
        ):
            result = action.execute(repo, [_snapshot("path/to/mydoc.FCStd")], deleted_paths=[])

        assert result.is_success is True
        freecad_port.save_document.assert_called_once_with(mock_doc)
        freecad_port.save_document_if_modified.assert_not_called()

    def test_save_failure_returns_failure_result(self) -> None:
        action, git_service, freecad_port, repo = _build_action()

        mock_doc = MagicMock()
        mock_doc.FileName = "/home/user/dir/test_repo/mydoc.FCStd"
        freecad_port.get_all_open_documents.return_value = [mock_doc]
        git_service.get_eligible_docs.return_value = [mock_doc]
        freecad_port.save_document.side_effect = Exception("save failed")

        result = action.execute(repo, [_snapshot("mydoc.FCStd")], deleted_paths=[])

        assert result.is_success is False
        assert "Failed to save document before staging" in (result.message or "")
        git_service.stage_files.assert_not_called()

    def test_deleted_path_stages_fcstd_and_tracked_yaml(self) -> None:
        action, git_service, _, repo = _build_action()
        git_service.file_exists.return_value = True
        git_service.stage_files.return_value = True

        with patch("pathlib.Path.unlink") as unlink_mock:
            result = action.execute(repo, [], deleted_paths=["parts/deleted.FCStd"])

        assert result.is_success is True
        git_service.stage_files.assert_called_once_with(
            repo,
            ["parts/deleted.FCStd", "parts/.snapshots/deleted.yaml"],
        )
        unlink_mock.assert_called_once()

    def test_deleted_path_deletes_yaml_from_disk(self) -> None:
        action, git_service, _, repo = _build_action()
        git_service.file_exists.return_value = False
        git_service.stage_files.return_value = True

        with patch("pathlib.Path.unlink") as unlink_mock:
            result = action.execute(repo, [], deleted_paths=["deleted.FCStd"])

        assert result.is_success is True
        unlink_mock.assert_called_once_with(missing_ok=True)

    def test_deleted_yaml_unlink_failure_returns_failure_and_skips_git_stage(self) -> None:
        action, git_service, _, repo = _build_action()
        with patch("pathlib.Path.unlink", side_effect=OSError("permission denied")):
            result = action.execute(repo, [], deleted_paths=["deleted.FCStd"])

        assert result.is_success is False
        assert "Failed to delete snapshot YAML" in (result.message or "")
        git_service.stage_files.assert_not_called()

    def test_deleted_path_skips_untracked_yaml_staging(self) -> None:
        action, git_service, _, repo = _build_action()
        git_service.file_exists.return_value = False
        git_service.stage_files.return_value = True

        with patch("pathlib.Path.unlink"):
            result = action.execute(repo, [], deleted_paths=["parts/deleted.FCStd"])

        assert result.is_success is True
        git_service.stage_files.assert_called_once_with(repo, ["parts/deleted.FCStd"])

    def test_deleted_path_with_open_doc_logs_warning_and_does_not_save(self) -> None:
        action, git_service, freecad_port, repo = _build_action()
        git_service.file_exists.return_value = False
        git_service.stage_files.return_value = True

        mock_doc = MagicMock()
        mock_doc.FileName = "/home/user/dir/test_repo/deleted.FCStd"
        freecad_port.get_all_open_documents.return_value = [mock_doc]
        git_service.get_eligible_docs.return_value = [mock_doc]

        with (
            patch("pathlib.Path.unlink"),
            patch("freecad.history_wb.application.actions.stage_documents.Log.warning") as warning_mock,
        ):
            result = action.execute(repo, [], deleted_paths=["deleted.FCStd"])

        assert result.is_success is True
        warning_mock.assert_called_once()
        freecad_port.save_document.assert_not_called()

    def test_snapshots_and_deleted_paths_stage_in_one_call(self) -> None:
        action, git_service, _, repo = _build_action()
        git_service.file_exists.return_value = True
        git_service.stage_files.return_value = True

        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer"),
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.unlink"),
        ):
            result = action.execute(repo, [_snapshot("a.FCStd")], deleted_paths=["b.FCStd"])

        assert result.is_success is True
        git_service.stage_files.assert_called_once_with(
            repo,
            ["a.FCStd", ".snapshots/a.yaml", "b.FCStd", ".snapshots/b.yaml"],
        )

    def test_snapshot_and_deleted_overlap_returns_failure_before_side_effects(self) -> None:
        action, git_service, freecad_port, repo = _build_action()

        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer") as serializer_mock,
            patch("pathlib.Path.unlink") as unlink_mock,
        ):
            result = action.execute(repo, [_snapshot("same.FCStd")], deleted_paths=["same.FCStd"])

        assert result.is_success is False
        assert "both present and deleted" in (result.message or "")
        freecad_port.save_document.assert_not_called()
        serializer_mock.to_yaml.assert_not_called()
        unlink_mock.assert_not_called()
        git_service.stage_files.assert_not_called()

    def test_duplicate_paths_deduped_preserving_order(self) -> None:
        action, git_service, _, repo = _build_action()
        git_service.file_exists.return_value = False
        git_service.stage_files.return_value = True

        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer"),
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.unlink"),
        ):
            result = action.execute(
                repo,
                [_snapshot("same.FCStd"), _snapshot("same.FCStd")],
                deleted_paths=[],
            )

        assert result.is_success is True
        git_service.stage_files.assert_called_once_with(repo, ["same.FCStd", ".snapshots/same.yaml"])

    def test_creates_snapshot_yaml_with_expected_path(self) -> None:
        action, _, _, repo = _build_action()
        snapshot = _snapshot("path/to/mydoc.FCStd")

        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer") as serializer_mock,
            patch("pathlib.Path.mkdir"),
        ):
            result = action.execute(repo, [snapshot], deleted_paths=[])

        assert result.is_success is True
        serializer_mock.to_yaml.assert_called_once_with(snapshot, Path("/home/user/dir/test_repo/path/to/.snapshots/mydoc.yaml"))

    def test_stages_both_fcstd_and_yaml_for_snapshot(self) -> None:
        action, git_service, _, repo = _build_action()
        git_service.stage_files.return_value = True

        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer"),
            patch("pathlib.Path.mkdir"),
        ):
            result = action.execute(repo, [_snapshot("path/to/mydoc.FCStd")], deleted_paths=[])

        assert result.is_success is True
        git_service.stage_files.assert_called_once_with(repo, ["path/to/mydoc.FCStd", "path/to/.snapshots/mydoc.yaml"])

    def test_multiple_snapshots_stage_all_paths(self) -> None:
        action, git_service, _, repo = _build_action()
        git_service.stage_files.return_value = True

        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer"),
            patch("pathlib.Path.mkdir"),
        ):
            result = action.execute(repo, [_snapshot("doc1.FCStd"), _snapshot("subdir/doc2.FCStd")], deleted_paths=[])

        assert result.is_success is True
        git_service.stage_files.assert_called_once_with(
            repo,
            ["doc1.FCStd", ".snapshots/doc1.yaml", "subdir/doc2.FCStd", "subdir/.snapshots/doc2.yaml"],
        )

    def test_yaml_serialize_failure_returns_failure_and_skips_stage(self) -> None:
        action, git_service, _, repo = _build_action()

        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer") as serializer_mock,
            patch("pathlib.Path.mkdir"),
        ):
            serializer_mock.to_yaml.side_effect = Exception("Serialization failed")
            result = action.execute(repo, [_snapshot("mydoc.FCStd")], deleted_paths=[])

        assert result.is_success is False
        assert "Failed to persist snapshot" in (result.message or "")
        git_service.stage_files.assert_not_called()

    def test_directory_creation_failure_returns_failure_and_skips_stage(self) -> None:
        action, git_service, _, repo = _build_action()

        with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
            result = action.execute(repo, [_snapshot("mydoc.FCStd")], deleted_paths=[])

        assert result.is_success is False
        assert "Failed to create snapshot directory" in (result.message or "")
        git_service.stage_files.assert_not_called()

    def test_git_stage_failure_returns_failure(self) -> None:
        action, git_service, _, repo = _build_action()
        git_service.stage_files.return_value = False

        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer"),
            patch("pathlib.Path.mkdir"),
        ):
            result = action.execute(repo, [_snapshot("mydoc.FCStd")], deleted_paths=[])

        assert result.is_success is False
        assert result.message == "Failed to stage one or more files"

    def test_snapshot_without_git_path_is_skipped(self) -> None:
        action, git_service, _, repo = _build_action()
        git_service.stage_files.return_value = True

        with (
            patch("freecad.history_wb.application.actions.stage_documents.SnapshotYamlSerializer"),
            patch("pathlib.Path.mkdir"),
        ):
            result = action.execute(repo, [_snapshot("")], deleted_paths=[])

        assert result.is_success is True
        git_service.stage_files.assert_not_called()
