# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module defines the Logger Protocol interface used
# by domain services and provides a FreeCAD Console implementation that falls
# back to standard logging when FreeCAD is not available.
"""Logger protocol and implementations for domain layer."""

from __future__ import annotations

import importlib.util
import logging
from typing import Protocol


class Logger(Protocol):
    """Logger interface for domain layer.

    This Protocol defines the contract for logging operations
    used by domain services. Implementations can use FreeCAD Console or any
    other logging backend.
    """

    def info(self, message: str) -> None:
        """Log an informational message."""
        ...

    def warning(self, message: str) -> None:
        """Log a warning message."""
        ...

    def error(self, message: str) -> None:
        """Log an error message."""
        ...


class FreeCADLogger:
    """FreeCAD Console logger implementation of Logger port.

    Falls back to standard logging if FreeCAD is not available (e.g., in unit tests).
    """

    def __init__(self) -> None:
        """Initialize the logger, checking if FreeCAD is available."""
        self._freecad_available = importlib.util.find_spec("FreeCAD") is not None

    def info(self, message: str) -> None:
        """Log an informational message to FreeCAD Console or standard logging."""
        if self._freecad_available:
            import FreeCAD

            FreeCAD.Console.PrintMessage(f"[INFO] {message}\n")
        else:
            logging.info(message)

    def warning(self, message: str) -> None:
        """Log a warning message to FreeCAD Console or standard logging."""
        if self._freecad_available:
            import FreeCAD

            FreeCAD.Console.PrintWarning(f"[WARNING] {message}\n")
        else:
            logging.warning(message)

    def error(self, message: str) -> None:
        """Log an error message to FreeCAD Console or standard logging."""
        if self._freecad_available:
            import FreeCAD

            FreeCAD.Console.PrintError(f"[ERROR] {message}\n")
        else:
            logging.error(message)
