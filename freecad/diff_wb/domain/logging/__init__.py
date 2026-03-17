# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: This module defines the Logger Protocol interface used
# by domain services. Implementations can use FreeCAD Console or standard logging.
"""Domain layer logging interfaces."""

from .logger import FreeCADLogger, Logger


__all__ = ["Logger", "FreeCADLogger"]
