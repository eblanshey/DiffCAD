"""File responsibility: Dependency injection container for application and UI layers.

This module wires actions, presenters, and views together.
It's the composition root for the application layer.
"""

from dataclasses import dataclass

from ...domain.diff.engine import DiffEngine
from ...domain.logging import Logger
from ...domain.snapshots.extractor import SnapshotExtractor
from ...domain.snapshots.repository import InMemorySnapshotRepository
from ...infrastructure.freecad.logger import FreeCADLogger
from ...infrastructure.freecad.ports import AppPort, FreeCadContext, FreeCadPort, get_app_port, get_port
from ...infrastructure.freecad.settings_repo import FreeCADSettingsRepository
from ...ui.presenters.diff_presenter import DiffPresenter
from ...ui.presenters.snapshot_presenter import SnapshotPresenter
from ...ui.protocols.diff_view import DiffView
from ...ui.protocols.snapshot_view import SnapshotView
from ..actions.commands.compare_snapshots import CompareSnapshotsAction
from ..actions.commands.take_snapshot import TakeSnapshotAction
from ..actions.queries.list_snapshots import ListSnapshotsAction


class NullSnapshotView(SnapshotView):
    """Null object implementation of SnapshotView for use when no view is available.

    This follows the Null Object pattern to avoid passing None to SnapshotPresenter,
    which violates the type contract. All methods are no-ops.
    """

    def show_success(self, message: str, snapshot_id: str) -> None:
        """Do nothing - null object pattern."""
        pass

    def show_error(self, message: str) -> None:
        """Do nothing - null object pattern."""
        pass

    def show_loading(self, message: str = "Creating snapshot...") -> None:
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
    settings_repo: FreeCADSettingsRepository | None = None,
) -> ApplicationContainer:
    """Wire all application layer dependencies.

    Args:
        ctx: FreeCAD runtime context
        snapshot_repo: Snapshot repository (created in init_gui.py)
        diff_view: Optional view for diff display (Phase 8)
        settings_repo: Optional settings repository (uses FreeCADSettingsRepository if None)

    Returns:
        ApplicationContainer with all wired components
    """
    # Get infrastructure adapters
    freecad_port = get_port(ctx)
    app_port = get_app_port(ctx)
    logger: Logger = FreeCADLogger(freecad_port)

    # Use provided settings_repo or create default
    if settings_repo is None:
        settings_repo = FreeCADSettingsRepository(ctx)

    # Create domain services
    extractor = SnapshotExtractor(logger=logger)
    diff_engine = DiffEngine(settings_repo=settings_repo)

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
        logger=logger,
    )

    list_snapshots_action = ListSnapshotsAction(snapshot_repo=snapshot_repo)

    # Create presenters (UI layer - interface adapters)
    # Note: For Phase 7, may use fake/None views until Phase 8
    snapshot_presenter = SnapshotPresenter(view=NullSnapshotView())
    diff_presenter = DiffPresenter(view=diff_view) if diff_view else None

    return ApplicationContainer(
        _freecad_port=freecad_port,
        _app_port=app_port,
        take_snapshot_action=take_snapshot_action,
        compare_snapshots_action=compare_snapshots_action,
        list_snapshots_action=list_snapshots_action,
        snapshot_presenter=snapshot_presenter,
        diff_presenter=diff_presenter,
    )
