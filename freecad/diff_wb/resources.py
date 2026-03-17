# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Provides utilities for locating package resources
# including icons, UI files, and translation files.
"""Resource path management for the Diff Workbench."""

from __future__ import annotations

from pathlib import Path


def get_resource_path() -> Path:
    """Get the path to the resources directory."""
    return Path(__file__).parent / "resources"


def get_icon_path(icon_name: str) -> Path:
    """Get the full path to an icon file.

    Args:
        icon_name: The name of the icon file (e.g., "Logo.svg")

    Returns:
        Path to the icon file
    """
    return get_resource_path() / "icons" / icon_name


# Path for icons (used in entrypoints)
ICONPATH = str(get_resource_path() / "icons")


def get_ui_path(ui_name: str) -> Path:
    """Get the full path to a UI file.

    Args:
        ui_name: The name of the UI file (e.g., "diff_panel.ui")

    Returns:
        Path to the UI file
    """
    return get_resource_path() / "ui" / ui_name


def get_translation_path() -> Path:
    """Get the path to the translations directory."""
    return get_resource_path() / "translations"


# Path for FreeCAD's translation system (used in init_gui.py)
TRANSLATIONSPATH = str(get_translation_path())
