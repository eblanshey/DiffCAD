"""Module responsibility: Action use cases."""

from .commands import CompareSnapshotsAction, TakeSnapshotAction
from .create_diff import CreateDiffAction
from .create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
from .create_document_snapshot_working import CreateDocumentSnapshotForWorkingTreeAction
from .find_active_git_repository import FindActiveGitRepositoryAction
from .get_commits import GetCommitsAction
from .get_diff_settings import GetDiffSettingsAction
from .get_open_eligible_documents import GetOpenEligibleDocumentsAction
from .open_all_documents_in_repository import OpenAllDocumentsInRepositoryAction
from .queries import ListSnapshotsAction
from .recompute_all_open_documents import RecomputeAllOpenDocumentsAction
from .result_models import CompareResult, Result, SnapshotResult, SnapshotSummary
from .save_diff_settings import SaveDiffSettingsAction


__all__ = [
    # Commands
    "TakeSnapshotAction",
    "CompareSnapshotsAction",
    # Actions
    "FindActiveGitRepositoryAction",
    "GetCommitsAction",
    "GetDiffSettingsAction",
    "GetOpenEligibleDocumentsAction",
    "OpenAllDocumentsInRepositoryAction",
    "RecomputeAllOpenDocumentsAction",
    "SaveDiffSettingsAction",
    "CreateDocumentSnapshotForWorkingTreeAction",
    "CreateDocumentSnapshotForCommitAction",
    "CreateDiffAction",
    # Queries
    "ListSnapshotsAction",
    # Result models
    "Result",
    "SnapshotResult",
    "CompareResult",
    "SnapshotSummary",
]
