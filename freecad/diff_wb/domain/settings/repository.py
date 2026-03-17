# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Defines the SettingsRepository Protocol for
# retrieving configuration settings used during diff computation.
"""Settings repository interface (port)."""

from typing import Protocol


class SettingsRepository(Protocol):
    """Interface for settings access.

    Implementations can use FreeCAD Preferences, in-memory storage, or any other backend.
    """

    def get_excluded_types(self) -> list[str]:
        """Get list of type IDs to exclude from diff computation.

        Returns:
            List of FreeCAD type IDs to exclude (e.g., ["App::Origin"])
        """
        ...

    def get_excluded_properties(self) -> list[str]:
        """Get list of property names to exclude from comparison.

        Returns:
            List of property names to exclude (e.g., ["TimeStamp", "Label2"])
        """
        ...
