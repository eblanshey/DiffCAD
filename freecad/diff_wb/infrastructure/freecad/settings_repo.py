# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the FreeCADSettingsRepository that implements
# the SettingsRepository protocol using FreeCAD's Parameter system. It uses hard-coded
# defaults from config.py as fallback values when no persisted settings exist.
"""FreeCAD settings repository implementation."""

from __future__ import annotations

from ...config import EXCLUDED_PROPERTIES, EXCLUDED_TYPES
from ...domain.settings.models import Settings
from .ports import FreeCadContext


class FreeCADSettingsRepository:
    """Settings repository implementation using FreeCAD's Parameter system.

    This class adapts FreeCAD's Parameter API to the SettingsRepository
    interface, allowing domain code to work with settings through the port abstraction.
    Uses hard-coded defaults from config.py when no persisted settings exist.
    """

    def __init__(self, ctx: FreeCadContext) -> None:
        self._ctx = ctx
        self._group_path = "User parameter:BaseApp/Preferences/Mod/DiffWorkbench"

    def _get_group(self) -> object:
        return self._ctx.app.ParamGet(self._group_path)

    def get_excluded_types(self) -> list[str]:
        """Get list of type IDs to exclude from diff computation.

        Returns:
            List of FreeCAD type IDs to exclude (e.g., ["App::Origin"]).
            Returns default from config.py if no persisted value exists.
        """
        group = self._get_group()
        raw = group.GetString("ExcludedTypes", "")  # type: ignore[attr-defined]
        if not raw:
            return EXCLUDED_TYPES
        return [item.strip() for item in raw.split(",") if item.strip()]

    def get_excluded_properties(self) -> list[str]:
        """Get list of property names to exclude from comparison.

        Returns:
            List of property names to exclude (e.g., ["TimeStamp", "Label2"]).
            Returns default from config.py if no persisted value exists.
        """
        group = self._get_group()
        raw = group.GetString("ExcludedProperties", "")  # type: ignore[attr-defined]
        if not raw:
            return EXCLUDED_PROPERTIES
        return [item.strip() for item in raw.split(",") if item.strip()]

    def get_settings(self) -> Settings:
        """Get all settings as a Settings object.

        Returns:
            Settings object with excluded types and properties from FreeCAD preferences,
            or defaults from config.py if no persisted values exist.
        """
        return Settings(
            excluded_types=self.get_excluded_types(),
            excluded_properties=self.get_excluded_properties(),
        )
