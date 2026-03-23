# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module defines the Logger Protocol interface used
# by domain services. Implementations are provided by infrastructure layer
# via dependency injection.
"""Logger protocol for domain layer."""

from typing import Protocol


class Logger(Protocol):
    """Logger interface for domain layer.

    This Protocol defines the contract for logging operations
    used by domain services. Implementations are provided by
    infrastructure layer via dependency injection.
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
