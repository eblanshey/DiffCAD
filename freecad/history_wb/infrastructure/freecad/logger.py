# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: FreeCAD logger implementation using FreeCadPort.

This module provides a FreeCADLogger class that wraps FreeCadPort to provide
simple info/warning/error methods for domain layer consumption. No FreeCAD
detection logic is needed - FreeCadPort handles all FreeCAD interactions.
"""

from ...domain.freecad_ports import FreeCadPort
from ...utils import Logger


class FreeCADLogger(Logger):
    """FreeCAD Console logger implementation using FreeCadPort.

    This logger wraps FreeCadPort to provide simple info/warning/error methods
    for domain layer consumption. No FreeCAD detection logic needed -
    FreeCadPort handles all FreeCAD interactions.

    Attributes:
        _port: FreeCadPort instance used for logging operations
    """

    def __init__(self, freecad_port: FreeCadPort) -> None:
        """Initialize with FreeCadPort.

        Args:
            freecad_port: FreeCadPort instance for logging
        """
        self._port: FreeCadPort = freecad_port

    def info(self, message: str) -> None:
        """Log an informational message."""
        self._port.message(message)

    def warning(self, message: str) -> None:
        """Log a warning message."""
        self._port.warn(message)

    def error(self, message: str) -> None:
        """Log an error message."""
        self._port.log(message)  # Using log() for errors

    def debug(self, message: str) -> None:
        """Log a debug message."""
        self._port.debug(message)
