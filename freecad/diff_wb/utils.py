# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Utility functions and classes for the Diff Workbench.
"""Utility functions and classes for the Diff Workbench.

This module contains shared utilities including the unified logging system
and translation helper for FreeCAD UI text.
"""

import traceback
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
        _logger.error(f"{message}\n{traceback.format_exc()}")


# Module-level logger instance for convenient access
# Ruff's BLE001 rule recognizes this as a logger object due to the exception() method
Log = Logger()


def format_float(value: float, precision: int) -> str:
    """Format a float value to the given number of decimal places.

    Uses QLocale for locale-aware number formatting, matching FreeCAD's
    property viewer approach (QLocale().toString(value, 'f', decimals)).

    Falls back to Python's built-in formatting when Qt is unavailable
    (e.g., in unit test environments).

    Args:
        value: The float value to format.
        precision: Number of decimal places.

    Returns:
        Formatted string like "1.23" or "-0.01".
    """
    try:
        from PyQt5.QtCore import QLocale  # type: ignore[import-not-found]

        return QLocale().toString(value, "f", precision)  # type: ignore[no-any-return]
    except ImportError:
        # Fall back to Python's built-in formatting when Qt is unavailable
        return f"{value:.{precision}f}"


def float_values_equal(v1: float, v2: float, precision: int) -> bool:
    """Compare two float values after rounding to the given precision.

    Values that look identical at N decimal places are considered equal.
    This replaces math.isclose() for our use case where display precision
    should drive comparison tolerance.

    Args:
        v1: First float value.
        v2: Second float value.
        precision: Number of decimal places to round to.

    Returns:
        True if rounded values are equal.
    """
    return round(v1, precision) == round(v2, precision)


def translate(context: str, text: str) -> str:
    """Translate UI text for FreeCAD workbench.

    This helper calls FreeCAD.Qt.translate() at runtime to get the translated
    string for the given context and text. When FreeCAD or Qt translation
    is unavailable (e.g., in unit test environments), it returns the source
    text unchanged.

    Usage:
        from ..utils import translate
        label = translate("ProjectHistory", "History Panel")

    For strings stored in data structures and translated later, use
    QT_TRANSLATE_NOOP at the definition point instead.

    Args:
        context: The translation context (e.g., "Workbench", "ProjectHistory",
                 or exact command name like "DiffCommit").
        text: The English text to translate.

    Returns:
        Translated text if available, otherwise the original source text.
    """
    try:
        import FreeCAD as App  # pylint: disable=import-error

        return App.Qt.translate(context, text)
    except (ImportError, AttributeError):
        # FreeCAD or Qt not available; return source text
        return text


__all__ = [
    "LoggerProtocol",
    "StdoutLogger",
    "Logger",
    "Log",
    "set_logger",
    "format_float",
    "float_values_equal",
    "translate",
]
