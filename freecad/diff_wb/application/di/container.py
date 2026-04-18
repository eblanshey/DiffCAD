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
from ...domain.snapshots.gui_extractor import SnapshotExtractor
from ...domain.snapshots.repository import InMemorySnapshotRepository
from ...infrastructure.freecad.ports import get_app_port, get_port
from ...infrastructure.freecad.settings_repo import FreeCADSettingsRepository
from ...infrastructure.git.git_port_adapter import GitPortAdapter
from ..actions.commands.compare_snapshots import CompareSnapshotsAction
from ..actions.commands.take_snapshot import TakeSnapshotAction
from ..actions.create_diff import CreateDiffAction
from ..actions.create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
from ..actions.create_document_snapshot_working import CreateDocumentSnapshotForWorkingTreeAction
from ..actions.find_active_git_repository import FindActiveGitRepositoryAction
from ..actions.get_commits import GetCommitsAction
from ..actions.get_dirty_documents import GetDirtyDocumentsAction
from ..actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from ..actions.queries.list_snapshots import ListSnapshotsAction
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
    take_snapshot_action: TakeSnapshotAction
    compare_snapshots_action: CompareSnapshotsAction
    list_snapshots_action: ListSnapshotsAction
    get_open_eligible_docs_action: GetOpenEligibleDocumentsAction
    create_working_snapshot_action: CreateDocumentSnapshotForWorkingTreeAction
    create_commit_snapshot_action: CreateDocumentSnapshotForCommitAction
    create_diff_action: CreateDiffAction
    stage_documents_action: StageDocumentsAction
    get_dirty_documents_action: GetDirtyDocumentsAction

    # Git components (domain layer)
    git_port: GitPort
    git_service: GitService
    find_active_git_repository_action: FindActiveGitRepositoryAction
    get_commits_action: GetCommitsAction
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
    snapshot_repo = InMemorySnapshotRepository()
    settings_repo = FreeCADSettingsRepository(ctx)

    # Create domain services
    extractor = SnapshotExtractor()
    diff_engine = DiffEngine(settings_repo=settings_repo)

    # Create git detection components
    git_port = GitPortAdapter()
    git_service = GitService(git_port=git_port)

    # Create actions (application layer - pure orchestration)
    take_snapshot_action = TakeSnapshotAction(
        freecad_port=freecad_port,
        extractor=extractor,
        snapshot_repo=snapshot_repo,
    )

    compare_snapshots_action = CompareSnapshotsAction(
        snapshot_repo=snapshot_repo,
        diff_engine=diff_engine,
        settings_repo=settings_repo,
    )

    list_snapshots_action = ListSnapshotsAction(snapshot_repo=snapshot_repo)

    find_active_git_repository_action = FindActiveGitRepositoryAction(
        freecad_port=freecad_port,
        git_service=git_service,
    )

    get_commits_action = GetCommitsAction(git_service=git_service)

    # Create new actions for working tree diff
    get_open_eligible_docs_action = GetOpenEligibleDocumentsAction(
        freecad_port=freecad_port,
        git_service=git_service,
    )
    create_working_snapshot_action = CreateDocumentSnapshotForWorkingTreeAction(
        git_service=git_service,
        extractor=extractor,
    )
    create_commit_snapshot_action = CreateDocumentSnapshotForCommitAction(git_service=git_service)
    create_diff_action = CreateDiffAction(diff_engine=diff_engine)
    stage_documents_action = StageDocumentsAction(git_service=git_service)
    get_dirty_documents_action = GetDirtyDocumentsAction(git_service=git_service)

    return ApplicationContainer(
        _freecad_port=freecad_port,
        _app_port=app_port,
        take_snapshot_action=take_snapshot_action,
        compare_snapshots_action=compare_snapshots_action,
        list_snapshots_action=list_snapshots_action,
        get_open_eligible_docs_action=get_open_eligible_docs_action,
        create_working_snapshot_action=create_working_snapshot_action,
        create_commit_snapshot_action=create_commit_snapshot_action,
        create_diff_action=create_diff_action,
        stage_documents_action=stage_documents_action,
        get_dirty_documents_action=get_dirty_documents_action,
        git_port=git_port,
        git_service=git_service,
        find_active_git_repository_action=find_active_git_repository_action,
        get_commits_action=get_commits_action,
    )
