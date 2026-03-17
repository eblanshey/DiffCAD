# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module is the entrypoint for FreeCAD when loading the Diff Workbench.
# It initializes the runtime context, wires dependency injection, creates infrastructure
# adapters, and registers the workbench, commands, and translation paths.
"""FreeCAD Diff Workbench GUI initialization."""

try:
    import FreeCADGui as Gui  # pylint: disable=import-error
except Exception:  # pylint: disable=broad-exception-caught
    Gui = None

if Gui is not None:
    from .domain.logging import FreeCADLogger
    from .domain.snapshots import InMemorySnapshotRepository
    from .domain.snapshots.extractor import SnapshotExtractor
    from .entrypoints.commands import register_commands
    from .entrypoints.workbench import DiffWorkbench
    from .freecad_version_check import check_python_and_freecad_version
    from .infrastructure.freecad.context import get_port, get_runtime_context
    from .infrastructure.freecad.settings_repo import FreeCADSettingsRepository
    from .resources import TRANSLATIONSPATH

    # Initialize FreeCAD language support
    Gui.addLanguagePath(TRANSLATIONSPATH)
    Gui.updateLocale()

    # Check Python and FreeCAD version compatibility
    check_python_and_freecad_version()

    # Create runtime context for dependency injection
    ctx = get_runtime_context()

    # Create infrastructure adapters
    port = get_port(ctx)
    logger = FreeCADLogger()
    settings_repo = FreeCADSettingsRepository(ctx)
    snapshot_repo = InMemorySnapshotRepository()

    # Create domain services with injected dependencies
    extractor = SnapshotExtractor(logger=logger)

    # Register commands and workbench
    register_commands()
    Gui.addWorkbench(DiffWorkbench())
