# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Defines AppPort Protocol for translation operations and provides FreeCAD adapter implementation.
"""App port interface for translation functionality.

This module defines the AppPort Protocol for translation operations,
allowing for test doubles in unit tests.
"""

from __future__ import annotations

from typing import Protocol

from .context import FreeCadContext, get_runtime_context


class AppPort(Protocol):
    """Interface for application-level operations.

    This Protocol defines operations like translation that are provided
    by the FreeCAD application, allowing for test doubles.
    """

    def translate(self, context: str, text: str) -> str:
        """Translate the given text in the provided translation context."""
        ...


class AppPortAdapter:
    """Runtime adapter implementing AppPort using FreeCAD's translation API."""

    def __init__(self, ctx: FreeCadContext) -> None:
        self._ctx = ctx

    def translate(self, context: str, text: str) -> str:
        return self._ctx.app.translate(context, text)


def get_app_port(ctx: FreeCadContext | None = None) -> AppPort:
    """Get an AppPort instance.

    If no context is provided, creates a runtime context.
    """
    if ctx is None:
        ctx = get_runtime_context()
    return AppPortAdapter(ctx)
