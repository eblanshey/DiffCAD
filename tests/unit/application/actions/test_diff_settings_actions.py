# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for diff settings application actions delegation behavior.
"""Tests for GetDiffSettingsAction and SaveDiffSettingsAction."""

from __future__ import annotations

from freecad.history_wb.application.actions.get_diff_settings import GetDiffSettingsAction
from freecad.history_wb.application.actions.save_diff_settings import SaveDiffSettingsAction
from freecad.history_wb.domain.settings.persistence_state import (
    ByTypeSettingState,
    ListSettingState,
    SettingsPersistenceState,
)


def _make_state() -> SettingsPersistenceState:
    return SettingsPersistenceState(
        excluded_types=ListSettingState(use_default=False, custom_values=["App::Part"], custom_initialized=True),
        excluded_properties=ListSettingState(
            use_default=False,
            custom_values=["Label2", "TimeStamp"],
            custom_initialized=True,
        ),
        excluded_properties_by_type=ByTypeSettingState(
            use_default=False,
            custom_values={"App::Part": ["Label"]},
            custom_initialized=True,
        ),
        float_precision=6,
    )


class _FakeSettingsPersistenceRepository:
    def __init__(self, state: SettingsPersistenceState) -> None:
        self._state = state
        self.saved_state: SettingsPersistenceState | None = None

    def get_persistence_state(self) -> SettingsPersistenceState:
        return self._state

    def save_persistence_state(self, state: SettingsPersistenceState) -> None:
        self.saved_state = state


def test_get_diff_settings_action_execute_delegates_and_returns_persistence_state() -> None:
    expected_state = _make_state()
    repo = _FakeSettingsPersistenceRepository(state=expected_state)
    action = GetDiffSettingsAction(settings_repo=repo)

    result = action.execute()

    assert result.is_success is True
    assert result.data == expected_state


def test_save_diff_settings_action_execute_delegates_save_with_exact_state() -> None:
    state = _make_state()
    repo = _FakeSettingsPersistenceRepository(state=state)
    action = SaveDiffSettingsAction(settings_repo=repo)

    result = action.execute(state)

    assert result.is_success is True
    assert repo.saved_state is state
