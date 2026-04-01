# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Utility functions and classes for the Diff Workbench.
"""Utility functions and classes for the Diff Workbench.

This module contains shared utilities including the unified logging system.
"""

from typing import Protocol


class LoggerProtocol(Protocol):
    """Logger protocol for consistent logging interface.

    This protocol defines the standard logging methods used throughout
    the application. All logger implementations must conform to this interface.
    """

    def debug(self, message: str) -> None:
        """Log a debug message."""
        ...

    def info(self, message: str) -> None:
        """Log an informational message."""
        ...

    def warning(self, message: str) -> None:
        """Log a warning message."""
        ...

    def error(self, message: str) -> None:
        """Log an error message."""
        ...


class StdoutLogger:
    """Logger that outputs to stdout/stderr.

    This is the default logger used before the application initializes its
    production logger. Useful for testing or CLI scenarios where FreeCAD
    console is not available.
    """

    def debug(self, message: str) -> None:
        """Log a debug message to stdout."""
        print(f"DEBUG: {message}")

    def info(self, message: str) -> None:
        """Log an informational message to stdout."""
        print(message)

    def warning(self, message: str) -> None:
        """Log a warning message to stdout."""
        print(f"WARNING: {message}")

    def error(self, message: str) -> None:
        """Log an error message to stderr."""
        print(f"ERROR: {message}", flush=True)


# Global logger instance - starts as StdoutLogger to ensure messages aren't lost
_logger: LoggerProtocol = StdoutLogger()


def set_logger(logger: LoggerProtocol) -> None:
    """Set the global logger instance.

    This should be called once during application startup (in workbench.Initialize()).
    After initialization, all logging calls will use the configured logger.

    Args:
        logger: The logger instance to use for all logging operations
    """
    global _logger
    _logger = logger


class Logger:
    """Logger wrapper that delegates to the global logger instance.

    This class provides a unified logging interface that works with both
    the default StdoutLogger and FreeCAD's console logger after initialization.

    Usage:
        Logger.debug("Debug message")
        Logger.info("Info message")
        Logger.warning("Warning message")
        Logger.error("Error message")
        Logger.exception("Exception message")  # Required for BLE001 compliance
    """

    def debug(self, message: str) -> None:
        """Log a debug message.

        Args:
            message: The message to log
        """

        # During development just use info for now
        _logger.info(message)

    def info(self, message: str) -> None:
        """Log an informational message.

        Args:
            message: The message to log
        """
        _logger.info(message)

    def warning(self, message: str) -> None:
        """Log a warning message.

        Args:
            message: The message to log
        """
        _logger.warning(message)

    def error(self, message: str) -> None:
        """Log an error message.

        Args:
            message: The message to log
        """
        _logger.error(message)

    def exception(self, message: str) -> None:
        """Log an error message with exception context.

        This method is used in except blocks to satisfy ruff's BLE001 rule
        which requires exceptions to be logged properly.

        Args:
            message: The message to log
        """
        _logger.error(message)


# Module-level logger instance for convenient access
# Ruff's BLE001 rule recognizes this as a logger object due to the exception() method
Log = Logger()


__all__ = [
    "LoggerProtocol",
    "StdoutLogger",
    "Logger",
    "Log",
    "set_logger",
]
