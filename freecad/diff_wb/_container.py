# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: Container helper module for entry point tests.
"""Container helper module for testable entry points.

This module provides a way to inject a container instance into entry point modules
for testing without requiring FreeCAD to be running. It allows tests to use
the same _container variable that commands.py and workbench.py expect.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from .application.di.container import ApplicationContainer
else:
    # At runtime, avoid circular imports - use Any placeholder
    ApplicationContainer = Any  # type: ignore[var-annotated]


# Module-level variable for entry point compatibility.
# This mirrors the _container from init_gui.py but can be set by tests.
# IMPORTANT: _container is ALWAYS set by init_gui.py BEFORE any entry point modules
# (workbench.py, commands.py) are imported. This ensures _container is never None
# during normal FreeCAD operation. Tests set it via set_container() before importing
# entry points. Initialized to None for module loading, but guaranteed to be set
# before any entry point code executes.
_container: ApplicationContainer | None = None


def set_container(container: ApplicationContainer) -> None:
    """Set the container for entry points.

    This is used by tests to inject a container instance into the
    entry point modules without running init_gui.py.

    Args:
        container: The ApplicationContainer instance to use
    """
    global _container
    _container = container


def get_container() -> ApplicationContainer | None:
    """Get the current container.

    Returns:
        The currently set container (always available after init_gui.py runs)
    """
    return _container


def clear_container() -> None:
    """Clear the container for testing.

    This resets _container to None for a clean test state.
    """
    global _container
    _container = None
