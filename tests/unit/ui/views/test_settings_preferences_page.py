# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for preferences page UI behavior and save/load wiring.
"""Tests for Diff settings preferences page behavior."""

from __future__ import annotations

from dataclasses import replace

from freecad.history_wb.application.actions.result_models import Result
from freecad.history_wb.domain.config import EXCLUDED_TYPES
from freecad.history_wb.domain.settings.persistence_state import (
    ByTypeSettingState,
    ListSettingState,
    SettingsPersistenceState,
)
from freecad.history_wb.qt import QtWidgets
from freecad.history_wb.ui.views.settings_preferences_page import DiffSettingsPreferencesPage


class _FakeGetDiffSettingsAction:
    def __init__(self, state: SettingsPersistenceState) -> None:
        self._state = state

    def execute(self) -> Result:
        return Result.success(self._state)


class _FakeSaveDiffSettingsAction:
    def __init__(self) -> None:
        self.saved_state: SettingsPersistenceState | None = None

    def execute(self, state: SettingsPersistenceState) -> Result:
        self.saved_state = state
        return Result.success(None)


def _make_state() -> SettingsPersistenceState:
    return SettingsPersistenceState(
        excluded_types=ListSettingState(
            use_default=True,
            custom_values=[],
            custom_initialized=False,
        ),
        excluded_properties=ListSettingState(
            use_default=True,
            custom_values=[],
            custom_initialized=False,
        ),
        excluded_properties_by_type=ByTypeSettingState(
            use_default=True,
            custom_values={},
            custom_initialized=False,
        ),
        float_precision=2,
    )


def _ensure_qapplication() -> None:
    app = QtWidgets.QApplication.instance()
    if app is None:
        QtWidgets.QApplication([])


class TestDiffSettingsPreferencesPage:
    def test_preference_page_loads_current_mode_and_values_into_controls(self) -> None:
        _ensure_qapplication()

        state = SettingsPersistenceState(
            excluded_types=ListSettingState(False, ["App::Part", "App::Link"], True),
            excluded_properties=ListSettingState(True, ["Label2"], True),
            excluded_properties_by_type=ByTypeSettingState(
                False,
                {"App::Part": ["Label"]},
                True,
            ),
            float_precision=5,
        )
        page = DiffSettingsPreferencesPage(
            get_settings_action=_FakeGetDiffSettingsAction(state),
            save_settings_action=_FakeSaveDiffSettingsAction(),
        )

        page.loadSettings()

        assert page._excluded_types_custom_radio.isChecked()
        assert page._excluded_types_text_edit.toPlainText() == "App::Part\nApp::Link"
        assert not page._excluded_types_text_edit.isHidden()

        assert page._excluded_properties_default_radio.isChecked()
        assert page._excluded_properties_text_edit.isHidden()

        assert page._excluded_by_type_custom_radio.isChecked()
        assert page._excluded_by_type_text_edit.toPlainText() == "App::Part -> Label"
        assert page._float_precision_spin.value() == 5

    def test_toggle_default_custom_shows_and_hides_textarea(self) -> None:
        _ensure_qapplication()

        page = DiffSettingsPreferencesPage(
            get_settings_action=_FakeGetDiffSettingsAction(_make_state()),
            save_settings_action=_FakeSaveDiffSettingsAction(),
        )
        page.loadSettings()

        assert page._excluded_types_text_edit.isHidden()

        page._excluded_types_custom_radio.setChecked(True)
        assert not page._excluded_types_text_edit.isHidden()

        page._excluded_types_default_radio.setChecked(True)
        assert page._excluded_types_text_edit.isHidden()

    def test_first_default_to_custom_prefill_happens_only_when_custom_not_initialized(self) -> None:
        _ensure_qapplication()

        uninitialized_state = _make_state()
        page = DiffSettingsPreferencesPage(
            get_settings_action=_FakeGetDiffSettingsAction(uninitialized_state),
            save_settings_action=_FakeSaveDiffSettingsAction(),
        )
        page.loadSettings()
        page._excluded_types_custom_radio.setChecked(True)
        assert page._excluded_types_text_edit.toPlainText() == "\n".join(EXCLUDED_TYPES)

        initialized_state = replace(
            _make_state(),
            excluded_types=ListSettingState(
                use_default=True,
                custom_values=[],
                custom_initialized=True,
            ),
        )
        page_initialized = DiffSettingsPreferencesPage(
            get_settings_action=_FakeGetDiffSettingsAction(initialized_state),
            save_settings_action=_FakeSaveDiffSettingsAction(),
        )
        page_initialized.loadSettings()
        page_initialized._excluded_types_custom_radio.setChecked(True)
        assert page_initialized._excluded_types_text_edit.toPlainText() == ""

    def test_after_save_empty_custom_stays_empty_without_repopulation(self) -> None:
        _ensure_qapplication()

        save_action = _FakeSaveDiffSettingsAction()
        page = DiffSettingsPreferencesPage(
            get_settings_action=_FakeGetDiffSettingsAction(_make_state()),
            save_settings_action=save_action,
        )
        page.loadSettings()

        page._excluded_types_custom_radio.setChecked(True)
        assert page._excluded_types_text_edit.toPlainText() == "\n".join(EXCLUDED_TYPES)

        page._excluded_types_text_edit.setPlainText("")
        page.saveSettings()

        assert save_action.saved_state is not None
        assert save_action.saved_state.excluded_types.custom_values == []
        assert save_action.saved_state.excluded_types.custom_initialized is True

        reopened_state = save_action.saved_state
        reopened_page = DiffSettingsPreferencesPage(
            get_settings_action=_FakeGetDiffSettingsAction(reopened_state),
            save_settings_action=_FakeSaveDiffSettingsAction(),
        )
        reopened_page.loadSettings()
        reopened_page._excluded_types_default_radio.setChecked(True)
        reopened_page._excluded_types_custom_radio.setChecked(True)
        assert reopened_page._excluded_types_text_edit.toPlainText() == ""

    def test_save_triggers_application_action_with_normalized_payload(self) -> None:
        _ensure_qapplication()

        save_action = _FakeSaveDiffSettingsAction()
        page = DiffSettingsPreferencesPage(
            get_settings_action=_FakeGetDiffSettingsAction(_make_state()),
            save_settings_action=save_action,
        )
        page.loadSettings()

        page._excluded_types_custom_radio.setChecked(True)
        page._excluded_types_text_edit.setPlainText("  App::Part  \n\n App::Link ")

        page._excluded_properties_custom_radio.setChecked(True)
        page._excluded_properties_text_edit.setPlainText(" Label2\n\n TimeStamp ")

        page._excluded_by_type_custom_radio.setChecked(True)
        page._excluded_by_type_text_edit.setPlainText(
            " App::Part -> Label \nInvalidLine\n Sketcher::SketchObject -> Geometry\nApp::Part -> Tip"
        )

        page._float_precision_spin.setValue(6)
        page.saveSettings()

        assert save_action.saved_state is not None
        saved = save_action.saved_state

        assert saved.excluded_types.use_default is False
        assert saved.excluded_types.custom_values == ["App::Part", "App::Link"]
        assert saved.excluded_types.custom_initialized is True

        assert saved.excluded_properties.use_default is False
        assert saved.excluded_properties.custom_values == ["Label2", "TimeStamp"]
        assert saved.excluded_properties.custom_initialized is True

        assert saved.excluded_properties_by_type.use_default is False
        assert saved.excluded_properties_by_type.custom_values == {
            "App::Part": ["Label", "Tip"],
            "Sketcher::SketchObject": ["Geometry"],
        }
        assert saved.excluded_properties_by_type.custom_initialized is True
        assert saved.float_precision == 6
