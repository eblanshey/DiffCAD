# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Ultra-thin GUI initialization module that only sets up translation
support, performs version checks, provides runtime context, and registers the HistoryWorkbench
class with FreeCAD. No container creation, no command registration, no global state manipulation."""

try:
    import FreeCADGui as Gui  # type: ignore[name-defined]
except ImportError as e:
    from .utils import Log

    Log.exception(f"Failed to import FreeCADGui: {e}")
    Gui = None  # type: ignore[assignment]

if Gui is not None:
    from .entrypoints.workbench import HistoryWorkbench
    from .freecad_version_check import check_python_and_freecad_version
    from .resources import ICONPATH, TRANSLATIONSPATH

    # Register icon search path so preference group icons like
    # "preferences-diff.svg" are discoverable by FreeCAD.
    Gui.addIconPath(ICONPATH)

    # Initialize FreeCAD language support
    Gui.addLanguagePath(TRANSLATIONSPATH)
    Gui.updateLocale()

    # Check Python and FreeCAD version compatibility
    check_python_and_freecad_version()

    # Register workbench (container creation happens in workbench.Initialize())
    Gui.addWorkbench(HistoryWorkbench())
