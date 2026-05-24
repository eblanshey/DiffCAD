# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Fake logger implementation that captures log messages for testing
# verification without relying on FreeCAD Console or standard logging.
"""Fake logger implementation for testing."""

from freecad.history_wb.utils import Logger


class FakeLogger(Logger):
    """Logger that captures messages for testing.

    This fake logger stores all log messages in memory, allowing tests
    to verify that logging occurred correctly without side effects.

    Attributes:
        _messages: Internal list of (level, message) tuples
    """

    def __init__(self) -> None:
        """Initialize an empty message capture list."""
        self._messages: list[tuple[str, str]] = []

    def info(self, message: str) -> None:
        """Capture an info-level message."""
        self._messages.append(("info", message))

    def warning(self, message: str) -> None:
        """Capture a warning-level message."""
        self._messages.append(("warning", message))

    def error(self, message: str) -> None:
        """Capture an error-level message."""
        self._messages.append(("error", message))

    @property
    def messages(self) -> list[tuple[str, str]]:
        """Get a copy of all captured messages."""
        return self._messages.copy()

    def clear(self) -> None:
        """Clear all captured messages."""
        self._messages.clear()

    def get_messages_by_level(self, level: str) -> list[str]:
        """Get all messages at a specific log level.

        Args:
            level: The log level to filter by ("info", "warning", "error")

        Returns:
            List of messages at the specified level
        """
        return [msg for lvl, msg in self._messages if lvl == level]


__all__ = ["FakeLogger"]
