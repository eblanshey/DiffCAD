# File responsibility: Selects the Qt binding for FreeCAD runtime and tests.
"""Qt wrapper boundary for runtime and test environments."""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from PySide6 import QtCore as QtCore, QtGui as QtGui, QtWidgets as QtWidgets
else:
    try:
        # Prefer FreeCAD's bundled PySide.
        from PySide import QtCore as QtCore, QtGui as QtGui, QtWidgets as QtWidgets
    except ImportError:
        # Unit tests run without FreeCAD, so FreeCAD's PySide wrapper modules are unavailable.
        # Fall back to the dev dependency while keeping production code on one Qt import boundary.
        from PySide6 import QtCore as QtCore, QtGui as QtGui, QtWidgets as QtWidgets


__all__ = ["QtCore", "QtGui", "QtWidgets"]
