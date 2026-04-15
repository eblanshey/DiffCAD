"""File responsibility: Dependency injection container for application and UI layers.

This module wires actions, presenters, and views together.
It's the composition root for the application layer.
"""

from dataclasses import dataclass
from typing import Any

from ...domain.diff.engine import DiffEngine
from ...domain.freecad_ports import AppPort, FreeCadContext, FreeCadPort
from ...domain.git.git_service import GitService
from ...domain.git.ports import GitPort
from ...domain.snapshots.gui_extractor import SnapshotExtractor
from ...domain.snapshots.repository import InMemorySnapshotRepository
from ...infrastructure.freecad.ports import get_app_port, get_port
from ...infrastructure.freecad.settings_repo import FreeCADSettingsRepository
from ...infrastructure.git.git_port_adapter import GitPortAdapter
from ...ui.presenters.application_state import ApplicationState
from ...ui.presenters.diff_presenter import DiffPresenter
from ...ui.presenters.snapshot_presenter import SnapshotPresenter
from ...ui.protocols.diff_view import DiffView
from ...ui.protocols.snapshot_view import SnapshotView
from ..actions.commands.compare_snapshots import CompareSnapshotsAction
from ..actions.commands.take_snapshot import TakeSnapshotAction
from ..actions.find_active_git_repository import FindActiveGitRepositoryAction
from ..actions.queries.list_snapshots import ListSnapshotsAction


class NullSnapshotView(SnapshotView):
    """Null object implementation of SnapshotView for use when no view is available.

    This follows the Null Object pattern to avoid passing None to SnapshotPresenter,
    which violates the type contract. All methods are no-ops.
    """

    def show_success(self, snapshot_name: str) -> None:
        """Do nothing - null object pattern."""
        pass

    def show_error(self, error_message: str) -> None:
        """Do nothing - null object pattern."""
        pass

    def show_loading(self, message: str | None = None) -> None:
        """Do nothing - null object pattern."""
        pass

    def show_snapshots(self, snapshots: list[Any]) -> None:
        """Do nothing - null object pattern."""
        pass


__all__ = [
    "ApplicationContainer",
    "create_application_container",
]


@dataclass
class ApplicationContainer:
    """Holds all wired application layer components.

    The container also stores port instances and provides helper methods
    for entry points to use without knowing about the port infrastructure.
    """

    # Ports (infrastructure adapters)
    _freecad_port: FreeCadPort
    _app_port: AppPort

    # Actions (application layer)
    take_snapshot_action: TakeSnapshotAction
    compare_snapshots_action: CompareSnapshotsAction
    list_snapshots_action: ListSnapshotsAction

    # Presenters (UI layer)
    snapshot_presenter: SnapshotPresenter
    diff_presenter: DiffPresenter | None

    # Git repository detection components
    git_port: GitPort
    git_service: GitService
    find_active_git_repository_action: FindActiveGitRepositoryAction
    application_state: ApplicationState

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


def create_application_container(
    ctx: FreeCadContext,
    snapshot_repo: InMemorySnapshotRepository,
    diff_view: DiffView | None = None,
    snapshot_view: SnapshotView | None = None,
    settings_repo: FreeCADSettingsRepository | None = None,
) -> ApplicationContainer:
    """Wire all application layer dependencies.

    Args:
        ctx: FreeCAD runtime context
        snapshot_repo: Snapshot repository (created in init_gui.py)
        diff_view: Optional view for diff display
        snapshot_view: Optional view for snapshot display
        settings_repo: Optional settings repository (uses FreeCADSettingsRepository if None)

    Returns:
        ApplicationContainer with all wired components
    """
    # Get infrastructure adapters
    freecad_port = get_port(ctx)
    app_port = get_app_port(ctx)

    # Use provided settings_repo or create default
    if settings_repo is None:
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

    # Create presenters (UI layer - interface adapters)
    snapshot_presenter = SnapshotPresenter(
        view=snapshot_view or NullSnapshotView(),
        list_snapshots_action=list_snapshots_action,
    )
    diff_presenter = DiffPresenter(view=diff_view) if diff_view else None

    # Create application state (UI state holder)
    application_state = ApplicationState(git_repository=None)

    return ApplicationContainer(
        _freecad_port=freecad_port,
        _app_port=app_port,
        take_snapshot_action=take_snapshot_action,
        compare_snapshots_action=compare_snapshots_action,
        list_snapshots_action=list_snapshots_action,
        snapshot_presenter=snapshot_presenter,
        diff_presenter=diff_presenter,
        git_port=git_port,
        git_service=git_service,
        find_active_git_repository_action=find_active_git_repository_action,
        application_state=application_state,
    )
