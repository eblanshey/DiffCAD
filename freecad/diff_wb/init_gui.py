# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: This module is the entrypoint for FreeCAD when loading the Diff Workbench.
It initializes the runtime context, wires dependency injection, creates infrastructure
adapters, and registers the workbench, commands, and translation paths.

This module is also the composition root - it creates the single instance of the
ApplicationContainer and exposes it via _container module for use by entry points.
"""

"""FreeCAD Diff Workbench GUI initialization."""

try:
    import FreeCADGui as Gui
except Exception:  # pylint: disable=broad-exception-caught
    Gui = None

if Gui is not None:
    from ._container import set_container
    from .application.di.container import create_application_container
    from .domain.snapshots import InMemorySnapshotRepository
    from .freecad_version_check import check_python_and_freecad_version
    from .infrastructure.freecad.ports import get_freecad_runtime_context
    from .resources import TRANSLATIONSPATH

    # Initialize FreeCAD language support
    Gui.addLanguagePath(TRANSLATIONSPATH)
    Gui.updateLocale()

    # Check Python and FreeCAD version compatibility
    check_python_and_freecad_version()

    # Create runtime context for dependency injection (composition root)
    ctx = get_freecad_runtime_context()

    # Create infrastructure adapters
    snapshot_repo = InMemorySnapshotRepository()

    # Create application layer container (wires all dependencies)
    container = create_application_container(
        ctx=ctx,
        snapshot_repo=snapshot_repo,
        diff_view=None,  # Phase 8: Will be DiffPanelView() when UI exists
    )

    # Set container BEFORE importing entry points so they can safely use it
    # This is critical because workbench.py and commands.py evaluate _container.translate()
    # at module load time when defining class attributes
    set_container(container)

    # NOW import entry points (they can safely access _container)
    from .entrypoints.commands import register_commands
    from .entrypoints.workbench import DiffWorkbench

    # Register commands with wired actions and presenters
    register_commands(container)

    # Register workbench
    Gui.addWorkbench(DiffWorkbench())
