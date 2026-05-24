"""File responsibility: Dependency injection container for application layer.

This module wires actions and domain services together.
It's the composition root for the application layer (backend).
UI layer components are composed separately in the composer module.

NO UI knowledge: no presenters, no views, no UIState.
"""

from dataclasses import dataclass

from ...domain.diff.engine import DiffEngine
from ...domain.freecad_ports import AppPort, FreeCadContext, FreeCadPort
from ...domain.git.git_service import GitService
from ...domain.git.ports import GitPort
from ...domain.settings import SettingsRepository
from ...domain.snapshots.gui_extractor import SnapshotExtractor
from ...infrastructure.freecad.freecad_file_manager import FreeCadFileManagerAdapter
from ...infrastructure.freecad.freecad_visual_diff_creator import FreeCADVisualDiffCreator
from ...infrastructure.freecad.ports import get_app_port, get_port
from ...infrastructure.freecad.settings_repo import FreeCADSettingsRepository
from ...infrastructure.git.git_port_adapter import GitPortAdapter
from ...infrastructure.persistence.snapshot_yaml_deserializer import SnapshotYamlDeserializer
from ..actions.can_write_global_git_identity import CanWriteGlobalGitIdentityAction
from ..actions.commit_staging import CommitStagingAction
from ..actions.create_diff import CreateDiffAction
from ..actions.create_document_diffs import CreateDocumentDiffsAction
from ..actions.create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
from ..actions.create_document_snapshot_working import CreateDocumentSnapshotForWorkingTreeAction
from ..actions.find_active_git_repository import FindActiveGitRepositoryAction
from ..actions.get_commits import GetCommitsAction
from ..actions.get_committed_file_paths import GetCommittedFilePathsAction
from ..actions.get_diff_settings import GetDiffSettingsAction
from ..actions.get_dirty_documents import GetDirtyDocumentsAction
from ..actions.get_git_identity import GetGitIdentityAction
from ..actions.get_git_repository_init_candidates import GetGitRepositoryInitCandidatesAction
from ..actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from ..actions.get_staged_file_paths import GetStagedFilePathsAction
from ..actions.initialize_git_repository import InitializeGitRepositoryAction
from ..actions.open_all_documents_in_repository import OpenAllDocumentsInRepositoryAction
from ..actions.open_visual_diff import OpenVisualDiffAction
from ..actions.recompute_all_open_documents import RecomputeAllOpenDocumentsAction
from ..actions.save_diff_settings import SaveDiffSettingsAction
from ..actions.save_git_identity import SaveGitIdentityAction
from ..actions.stage_documents import StageDocumentsAction


__all__ = [
    "ApplicationContainer",
    "create_application_container",
]


@dataclass
class ApplicationContainer:
    """Holds all wired application layer dependencies ONLY.

    This container is created at workbench Initialize() time,
    BEFORE any GUI components exist. It contains only:
    - Actions (application layer - API endpoint handlers)
    - Domain services
    - Ports/Repositories

    NO UI knowledge: no presenters, no views, no UIState.
    """

    # Ports (infrastructure adapters)
    _freecad_port: FreeCadPort
    _app_port: AppPort

    # Actions (application layer - pure orchestration, no UI)
    get_open_eligible_docs_action: GetOpenEligibleDocumentsAction
    create_working_snapshot_action: CreateDocumentSnapshotForWorkingTreeAction
    create_commit_snapshot_action: CreateDocumentSnapshotForCommitAction
    create_diff_action: CreateDiffAction
    create_document_diffs_action: CreateDocumentDiffsAction
    stage_documents_action: StageDocumentsAction
    get_dirty_documents_action: GetDirtyDocumentsAction
    get_staged_file_paths_action: GetStagedFilePathsAction
    get_committed_file_paths_action: GetCommittedFilePathsAction
    commit_staging_action: CommitStagingAction
    get_git_identity_action: GetGitIdentityAction
    save_git_identity_action: SaveGitIdentityAction
    can_write_global_git_identity_action: CanWriteGlobalGitIdentityAction
    get_diff_settings_action: GetDiffSettingsAction
    save_diff_settings_action: SaveDiffSettingsAction
    open_visual_feature_diff_action: OpenVisualDiffAction

    # Settings repository for runtime precision and user preferences
    settings_repo: SettingsRepository

    # Git components (domain layer)
    git_port: GitPort
    git_service: GitService
    find_active_git_repository_action: FindActiveGitRepositoryAction
    get_git_repository_init_candidates_action: GetGitRepositoryInitCandidatesAction
    initialize_git_repository_action: InitializeGitRepositoryAction
    get_commits_action: GetCommitsAction
    open_all_documents_in_repository_action: OpenAllDocumentsInRepositoryAction
    recompute_all_open_documents_action: RecomputeAllOpenDocumentsAction
    # NO ui_state - that's frontend state, not application state

    def log(self, message: str) -> None:
        """Log a message to the FreeCAD console.

        Helper method for entry points to log messages without
        knowing about port infrastructure.

        Args:
            message: The message to log
        """
        self._freecad_port.message(message)

    def translate(self, context: str, text: str) -> str:
        """Translate text using FreeCAD's translation system.

        Helper method for entry points to translate text without
        knowing about port infrastructure.

        Args:
            context: The translation context (e.g., "Workbench", "Log")
            text: The text to translate

        Returns:
            The translated text
        """
        return self._app_port.translate(context, text)


def create_application_container(ctx: FreeCadContext) -> ApplicationContainer:
    """Wire ONLY application layer dependencies.

    No UI components are created here - this runs before GUI exists.
    UIState is created by the composer later when GUI is available.

    Args:
        ctx: FreeCAD runtime context

    Returns:
        ApplicationContainer with only application layer wired components
    """
    # Get infrastructure adapters
    freecad_port = get_port(ctx)
    app_port = get_app_port(ctx)

    # Create domain components
    settings_repo = FreeCADSettingsRepository(ctx)

    # Create domain services
    extractor = SnapshotExtractor(gui=ctx.gui)
    diff_engine = DiffEngine(settings_repo=settings_repo)

    # Create git detection components
    git_port = GitPortAdapter()
    git_service = GitService(git_port=git_port)

    find_active_git_repository_action = FindActiveGitRepositoryAction(
        freecad_port=freecad_port,
        git_service=git_service,
    )
    get_git_repository_init_candidates_action = GetGitRepositoryInitCandidatesAction(
        freecad_port=freecad_port,
        git_service=git_service,
    )
    initialize_git_repository_action = InitializeGitRepositoryAction(git_service=git_service)

    get_commits_action = GetCommitsAction(git_service=git_service)
    open_all_documents_in_repository_action = OpenAllDocumentsInRepositoryAction(
        freecad_port=freecad_port,
    )
    recompute_all_open_documents_action = RecomputeAllOpenDocumentsAction(
        freecad_port=freecad_port,
    )

    # Create new actions for working tree diff
    get_open_eligible_docs_action = GetOpenEligibleDocumentsAction(
        freecad_port=freecad_port,
        git_service=git_service,
    )
    create_working_snapshot_action = CreateDocumentSnapshotForWorkingTreeAction(
        git_service=git_service,
        extractor=extractor,
    )
    create_commit_snapshot_action = CreateDocumentSnapshotForCommitAction(
        git_service=git_service,
        snapshot_deserializer=SnapshotYamlDeserializer(),
    )
    create_diff_action = CreateDiffAction(diff_engine=diff_engine)
    stage_documents_action = StageDocumentsAction(git_service=git_service, freecad_port=freecad_port)
    get_dirty_documents_action = GetDirtyDocumentsAction(git_service=git_service)
    get_staged_file_paths_action = GetStagedFilePathsAction(git_service=git_service)
    get_committed_file_paths_action = GetCommittedFilePathsAction(git_service=git_service)
    create_document_diffs_action = CreateDocumentDiffsAction(
        create_working_snapshot_action=create_working_snapshot_action,
        create_commit_snapshot_action=create_commit_snapshot_action,
        create_diff_action=create_diff_action,
        get_staged_file_paths_action=get_staged_file_paths_action,
        get_committed_file_paths_action=get_committed_file_paths_action,
    )
    commit_staging_action = CommitStagingAction(git_service=git_service)
    get_git_identity_action = GetGitIdentityAction(git_service=git_service)
    save_git_identity_action = SaveGitIdentityAction(git_service=git_service)
    can_write_global_git_identity_action = CanWriteGlobalGitIdentityAction(git_service=git_service)
    get_diff_settings_action = GetDiffSettingsAction(settings_repo=settings_repo)
    save_diff_settings_action = SaveDiffSettingsAction(settings_repo=settings_repo)
    file_manager = FreeCadFileManagerAdapter(git_service=git_service)
    open_visual_feature_diff_action = OpenVisualDiffAction(
        git_service=git_service,
        visual_diff=FreeCADVisualDiffCreator(ctx),
        file_manager=file_manager,
    )

    return ApplicationContainer(
        _freecad_port=freecad_port,
        _app_port=app_port,
        get_open_eligible_docs_action=get_open_eligible_docs_action,
        create_working_snapshot_action=create_working_snapshot_action,
        create_commit_snapshot_action=create_commit_snapshot_action,
        create_diff_action=create_diff_action,
        create_document_diffs_action=create_document_diffs_action,
        stage_documents_action=stage_documents_action,
        get_dirty_documents_action=get_dirty_documents_action,
        get_staged_file_paths_action=get_staged_file_paths_action,
        get_committed_file_paths_action=get_committed_file_paths_action,
        commit_staging_action=commit_staging_action,
        get_git_identity_action=get_git_identity_action,
        save_git_identity_action=save_git_identity_action,
        can_write_global_git_identity_action=can_write_global_git_identity_action,
        get_diff_settings_action=get_diff_settings_action,
        save_diff_settings_action=save_diff_settings_action,
        open_visual_feature_diff_action=open_visual_feature_diff_action,
        settings_repo=settings_repo,
        git_port=git_port,
        git_service=git_service,
        find_active_git_repository_action=find_active_git_repository_action,
        get_git_repository_init_candidates_action=get_git_repository_init_candidates_action,
        initialize_git_repository_action=initialize_git_repository_action,
        get_commits_action=get_commits_action,
        open_all_documents_in_repository_action=open_all_documents_in_repository_action,
        recompute_all_open_documents_action=recompute_all_open_documents_action,
    )
