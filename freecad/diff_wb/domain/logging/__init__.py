# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: This module defines the Logger Protocol interface used
# by domain services. Implementations are provided by infrastructure layer.
"""Domain layer logging interfaces."""

from .logger import Logger


__all__ = ["Logger"]
