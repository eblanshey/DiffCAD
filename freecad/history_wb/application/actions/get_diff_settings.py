# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for reading persisted diff settings state.
"""Application action for retrieving diff settings persistence state."""

from __future__ import annotations

from ...domain.settings import SettingsPersistenceRepository
from ...domain.settings.persistence_state import SettingsPersistenceState
from ...utils import Log
from .result_models import Result


class GetDiffSettingsAction:
    """Read diff settings persistence state from repository."""

    def __init__(self, settings_repo: SettingsPersistenceRepository) -> None:
        self._settings_repo = settings_repo

    def execute(self) -> Result:
        """Return persisted state used by preferences page."""
        try:
            state: SettingsPersistenceState = self._settings_repo.get_persistence_state()
            return Result.success(state)
        except Exception as exc:  # noqa: BLE001
            message = f"Failed to load diff settings: {exc}"
            Log.exception(message)
            return Result.failure(message)


__all__ = ["GetDiffSettingsAction"]
