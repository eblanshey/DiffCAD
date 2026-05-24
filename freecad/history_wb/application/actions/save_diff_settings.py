# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for saving persisted diff settings state.
"""Application action for saving diff settings persistence state."""

from __future__ import annotations

from ...domain.settings import SettingsPersistenceRepository
from ...domain.settings.persistence_state import SettingsPersistenceState
from ...utils import Log
from .result_models import Result


class SaveDiffSettingsAction:
    """Persist diff settings state from preferences page."""

    def __init__(self, settings_repo: SettingsPersistenceRepository) -> None:
        self._settings_repo = settings_repo

    def execute(self, state: SettingsPersistenceState) -> Result:
        """Save preferences page state to repository."""
        try:
            self._settings_repo.save_persistence_state(state)
            return Result.success(None)
        except Exception as exc:  # noqa: BLE001
            message = f"Failed to save diff settings: {exc}"
            Log.exception(message)
            return Result.failure(message)


__all__ = ["SaveDiffSettingsAction"]
