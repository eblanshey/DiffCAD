# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: FreeCAD-specific adapters implementing
# application ports and runtime context for FreeCAD integration.
"""FreeCAD infrastructure adapters."""

from .freecad_file_manager import FreeCadFileManagerAdapter
from .freecad_visual_diff_creator import FreeCADVisualDiffCreator
from .logger import FreeCADLogger
from .ports import (
    FreeCadContext,
    FreeCadPort,
    get_freecad_runtime_context,
    get_port,
)
from .settings_repo import FreeCADSettingsRepository


__all__ = [
    "FreeCADLogger",
    "FreeCadContext",
    "FreeCadPort",
    "get_port",
    "get_freecad_runtime_context",
    "FreeCADSettingsRepository",
    "FreeCADVisualDiffCreator",
    "FreeCadFileManagerAdapter",
]
