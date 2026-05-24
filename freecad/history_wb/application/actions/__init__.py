"""Module responsibility: Action use cases."""

from .can_write_global_git_identity import CanWriteGlobalGitIdentityAction
from .commit_staging import CommitStagingAction
from .create_diff import CreateDiffAction
from .create_document_diffs import CreateDocumentDiffsAction
from .create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
from .create_document_snapshot_working import CreateDocumentSnapshotForWorkingTreeAction
from .find_active_git_repository import FindActiveGitRepositoryAction
from .get_commits import GetCommitsAction
from .get_diff_settings import GetDiffSettingsAction
from .get_git_identity import GetGitIdentityAction
from .get_git_repository_init_candidates import GetGitRepositoryInitCandidatesAction
from .get_open_eligible_documents import GetOpenEligibleDocumentsAction
from .initialize_git_repository import InitializeGitRepositoryAction
from .open_all_documents_in_repository import OpenAllDocumentsInRepositoryAction
from .open_visual_diff import OpenVisualDiffAction
from .recompute_all_open_documents import RecomputeAllOpenDocumentsAction
from .result_models import (
    CompareResult,
    CreateDocumentDiffsRequest,
    DocumentDiffMode,
    DocumentDiffResult,
    DocumentDiffStatus,
    Result,
    SnapshotResult,
    SnapshotSummary,
)
from .save_diff_settings import SaveDiffSettingsAction
from .save_git_identity import SaveGitIdentityAction


__all__ = [
    # Commands
    "CommitStagingAction",
    "CanWriteGlobalGitIdentityAction",
    # Actions
    "FindActiveGitRepositoryAction",
    "GetCommitsAction",
    "GetDiffSettingsAction",
    "GetGitIdentityAction",
    "GetOpenEligibleDocumentsAction",
    "GetGitRepositoryInitCandidatesAction",
    "InitializeGitRepositoryAction",
    "OpenAllDocumentsInRepositoryAction",
    "OpenVisualDiffAction",
    "RecomputeAllOpenDocumentsAction",
    "SaveDiffSettingsAction",
    "SaveGitIdentityAction",
    "CreateDocumentSnapshotForWorkingTreeAction",
    "CreateDocumentSnapshotForCommitAction",
    "CreateDiffAction",
    "CreateDocumentDiffsAction",
    # Result models
    "Result",
    "SnapshotResult",
    "CompareResult",
    "SnapshotSummary",
    "CreateDocumentDiffsRequest",
    "DocumentDiffMode",
    "DocumentDiffStatus",
    "DocumentDiffResult",
]
