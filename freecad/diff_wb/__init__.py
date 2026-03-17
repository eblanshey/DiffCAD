# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: Core package initialization for Diff Workbench,
# providing version information and serving as the main entry point
# for the FreeCAD workbench.
"""Diff Workbench - A FreeCAD workbench for comparing document snapshots."""

from .version import __version__


__all__ = ["__version__"]
