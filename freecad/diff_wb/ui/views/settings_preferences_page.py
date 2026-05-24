# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Preferences page UI for editing diff settings and saving/loading via application actions.
"""Diff settings preferences page for FreeCAD preferences dialog."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...application.actions.get_diff_settings import GetDiffSettingsAction
from ...application.actions.save_diff_settings import SaveDiffSettingsAction
from ...domain.config import EXCLUDED_PROPERTIES, EXCLUDED_PROPERTIES_BY_TYPE, EXCLUDED_TYPES, FLOAT_PRECISION
from ...domain.settings.persistence_state import (
    ByTypeSettingState,
    ListSettingState,
    SettingsPersistenceState,
)
from ...domain.settings.text_codec import (
    parse_by_type_lines,
    parse_list_lines,
    serialize_by_type_lines,
    serialize_list_lines,
)
from ...utils import Log, translate


@dataclass(frozen=True)
class _ListControls:
    default_radio: QRadioButton
    custom_radio: QRadioButton
    text_edit: QTextEdit


class DiffSettingsPreferencesPage:
    """Preferences page for Diff Workbench settings."""

    _default_get_settings_action: GetDiffSettingsAction | None = None
    _default_save_settings_action: SaveDiffSettingsAction | None = None

    @classmethod
    def configure_actions(
        cls,
        get_settings_action: GetDiffSettingsAction,
        save_settings_action: SaveDiffSettingsAction,
    ) -> None:
        """Set default actions used by FreeCAD no-arg page construction."""
        cls._default_get_settings_action = get_settings_action
        cls._default_save_settings_action = save_settings_action

    def __init__(
        self,
        get_settings_action: GetDiffSettingsAction | None = None,
        save_settings_action: SaveDiffSettingsAction | None = None,
    ) -> None:
        resolved_get_settings_action = get_settings_action or self.__class__._default_get_settings_action
        resolved_save_settings_action = save_settings_action or self.__class__._default_save_settings_action
        if resolved_get_settings_action is None or resolved_save_settings_action is None:
            raise RuntimeError("DiffSettingsPreferencesPage actions are not configured")
        self._get_settings_action: GetDiffSettingsAction = resolved_get_settings_action
        self._save_settings_action: SaveDiffSettingsAction = resolved_save_settings_action

        self._loaded_state: SettingsPersistenceState | None = None
        self._is_loading = False

        self.form = QWidget()
        self.form.setWindowTitle(translate("ProjectHistory", "General"))
        root_layout = QVBoxLayout(self.form)

        info_text = QLabel(
            translate(
                "ProjectHistory",
                "Settings apply only during tree comparisons. Saved tree snapshots are unaffected by these settings.",
            ),
            self.form,
        )
        info_text.setWordWrap(True)
        root_layout.addWidget(info_text)

        self._excluded_types_controls = self._build_list_group(
            "excluded_types",
            translate("ProjectHistory", "One TypeId per line."),
        )
        root_layout.addWidget(
            self._wrap_group(
                translate("ProjectHistory", "Excluded object types"),
                self._excluded_types_controls,
            )
        )

        self._excluded_properties_controls = self._build_list_group(
            "excluded_properties",
            translate("ProjectHistory", "One property name per line."),
        )
        root_layout.addWidget(
            self._wrap_group(
                translate("ProjectHistory", "Excluded properties"),
                self._excluded_properties_controls,
            )
        )

        self._excluded_by_type_controls = self._build_list_group(
            "excluded_properties_by_type",
            translate("ProjectHistory", "One line per mapping: TypeId -> Property"),
        )
        root_layout.addWidget(
            self._wrap_group(
                translate("ProjectHistory", "Type-specific excluded properties"),
                self._excluded_by_type_controls,
            )
        )

        self._float_precision_spin = QSpinBox(self.form)
        self._float_precision_spin.setRange(0, 12)
        self._float_precision_spin.setSingleStep(1)
        precision_layout = QFormLayout()
        precision_layout.addRow(translate("ProjectHistory", "Float precision"), self._float_precision_spin)
        precision_group = QGroupBox(translate("ProjectHistory", "Numeric comparison"), self.form)
        precision_group.setLayout(precision_layout)
        root_layout.addWidget(precision_group)
        root_layout.addStretch(1)

        self._excluded_types_default_radio = self._excluded_types_controls.default_radio
        self._excluded_types_custom_radio = self._excluded_types_controls.custom_radio
        self._excluded_types_text_edit = self._excluded_types_controls.text_edit

        self._excluded_properties_default_radio = self._excluded_properties_controls.default_radio
        self._excluded_properties_custom_radio = self._excluded_properties_controls.custom_radio
        self._excluded_properties_text_edit = self._excluded_properties_controls.text_edit

        self._excluded_by_type_default_radio = self._excluded_by_type_controls.default_radio
        self._excluded_by_type_custom_radio = self._excluded_by_type_controls.custom_radio
        self._excluded_by_type_text_edit = self._excluded_by_type_controls.text_edit

        self._bind_signals()

    def loadSettings(self) -> None:  # noqa: N802
        """Load persisted settings into preferences controls."""
        result = self._get_settings_action.execute()
        if not result.is_success or not isinstance(result.data, SettingsPersistenceState):
            Log.error(result.message or "Failed to load diff settings state")
            state = self._empty_state()
        else:
            state = result.data
        self._loaded_state = state

        self._is_loading = True
        self._apply_list_state(self._excluded_types_controls, state.excluded_types)
        self._apply_list_state(self._excluded_properties_controls, state.excluded_properties)
        self._apply_by_type_state(self._excluded_by_type_controls, state.excluded_properties_by_type)
        self._float_precision_spin.setValue(state.float_precision)
        self._is_loading = False
        self._sync_visibility()

    def saveSettings(self) -> None:  # noqa: N802
        """Collect control values and persist through application action."""
        loaded = self._loaded_state or self._empty_state()
        state_to_save = SettingsPersistenceState(
            excluded_types=self._collect_list_state(
                controls=self._excluded_types_controls,
                current_state=loaded.excluded_types,
            ),
            excluded_properties=self._collect_list_state(
                controls=self._excluded_properties_controls,
                current_state=loaded.excluded_properties,
            ),
            excluded_properties_by_type=self._collect_by_type_state(
                controls=self._excluded_by_type_controls,
                current_state=loaded.excluded_properties_by_type,
            ),
            float_precision=self._float_precision_spin.value(),
        )
        result = self._save_settings_action.execute(state_to_save)
        if not result.is_success:
            Log.error(result.message or "Failed to save diff settings state")
            return
        self._loaded_state = state_to_save

    def _bind_signals(self) -> None:
        self._excluded_types_controls.custom_radio.toggled.connect(
            lambda checked: self._on_custom_toggled("excluded_types", checked)
        )
        self._excluded_properties_controls.custom_radio.toggled.connect(
            lambda checked: self._on_custom_toggled("excluded_properties", checked)
        )
        self._excluded_by_type_controls.custom_radio.toggled.connect(
            lambda checked: self._on_custom_toggled("excluded_properties_by_type", checked)
        )

        self._excluded_types_controls.default_radio.toggled.connect(lambda _checked: self._sync_visibility())
        self._excluded_properties_controls.default_radio.toggled.connect(lambda _checked: self._sync_visibility())
        self._excluded_by_type_controls.default_radio.toggled.connect(lambda _checked: self._sync_visibility())

    def _sync_visibility(self) -> None:
        self._excluded_types_controls.text_edit.setVisible(self._excluded_types_controls.custom_radio.isChecked())
        self._excluded_properties_controls.text_edit.setVisible(
            self._excluded_properties_controls.custom_radio.isChecked()
        )
        self._excluded_by_type_controls.text_edit.setVisible(self._excluded_by_type_controls.custom_radio.isChecked())

    def _on_custom_toggled(self, setting_name: str, checked: bool) -> None:
        if self._is_loading or not checked:
            self._sync_visibility()
            return
        self._maybe_prefill_from_defaults(setting_name)
        self._sync_visibility()

    def _maybe_prefill_from_defaults(self, setting_name: str) -> None:
        if self._loaded_state is None:
            return

        if setting_name == "excluded_types":
            self._maybe_prefill_list(
                controls=self._excluded_types_controls,
                current_state=self._loaded_state.excluded_types,
                defaults=EXCLUDED_TYPES,
            )
            return
        if setting_name == "excluded_properties":
            self._maybe_prefill_list(
                controls=self._excluded_properties_controls,
                current_state=self._loaded_state.excluded_properties,
                defaults=EXCLUDED_PROPERTIES,
            )
            return
        self._maybe_prefill_by_type(
            controls=self._excluded_by_type_controls,
            current_state=self._loaded_state.excluded_properties_by_type,
            defaults=EXCLUDED_PROPERTIES_BY_TYPE,
        )

    def _maybe_prefill_list(
        self,
        *,
        controls: _ListControls,
        current_state: ListSettingState,
        defaults: list[str],
    ) -> None:
        if current_state.custom_initialized:
            return
        if parse_list_lines(controls.text_edit.toPlainText()):
            return
        controls.text_edit.setPlainText(serialize_list_lines(defaults))

    def _maybe_prefill_by_type(
        self,
        *,
        controls: _ListControls,
        current_state: ByTypeSettingState,
        defaults: dict[str, list[str]],
    ) -> None:
        if current_state.custom_initialized:
            return
        if parse_by_type_lines(controls.text_edit.toPlainText()):
            return
        controls.text_edit.setPlainText(serialize_by_type_lines(defaults))

    def _build_list_group(self, textarea_name: str, helper_text: str) -> _ListControls:
        default_radio = QRadioButton(translate("ProjectHistory", "Use default exclusion list"), self.form)
        custom_radio = QRadioButton(translate("ProjectHistory", "Use custom exclusion list"), self.form)

        text_edit = QTextEdit(self.form)
        text_edit.setObjectName(textarea_name)
        text_edit.setPlaceholderText(helper_text)
        return _ListControls(default_radio=default_radio, custom_radio=custom_radio, text_edit=text_edit)

    def _wrap_group(self, title: str, controls: _ListControls) -> QGroupBox:
        group = QGroupBox(title, self.form)
        group_layout = QVBoxLayout(group)

        radios_layout = QHBoxLayout()
        radios_layout.addWidget(controls.default_radio)
        radios_layout.addWidget(controls.custom_radio)

        group_layout.addLayout(radios_layout)
        group_layout.addWidget(controls.text_edit)
        return group

    def _apply_list_state(self, controls: _ListControls, state: ListSettingState) -> None:
        controls.default_radio.setChecked(state.use_default)
        controls.custom_radio.setChecked(not state.use_default)
        controls.text_edit.setPlainText(serialize_list_lines(state.custom_values))

    def _apply_by_type_state(self, controls: _ListControls, state: ByTypeSettingState) -> None:
        controls.default_radio.setChecked(state.use_default)
        controls.custom_radio.setChecked(not state.use_default)
        controls.text_edit.setPlainText(serialize_by_type_lines(state.custom_values))

    def _collect_list_state(
        self,
        *,
        controls: _ListControls,
        current_state: ListSettingState,
    ) -> ListSettingState:
        use_default = controls.default_radio.isChecked()
        custom_values = parse_list_lines(controls.text_edit.toPlainText())
        custom_initialized = current_state.custom_initialized or not use_default
        return ListSettingState(
            use_default=use_default,
            custom_values=custom_values,
            custom_initialized=custom_initialized,
        )

    def _collect_by_type_state(
        self,
        *,
        controls: _ListControls,
        current_state: ByTypeSettingState,
    ) -> ByTypeSettingState:
        use_default = controls.default_radio.isChecked()
        custom_values = parse_by_type_lines(controls.text_edit.toPlainText())
        custom_initialized = current_state.custom_initialized or not use_default
        return ByTypeSettingState(
            use_default=use_default,
            custom_values=custom_values,
            custom_initialized=custom_initialized,
        )

    def _empty_state(self) -> SettingsPersistenceState:
        return SettingsPersistenceState(
            excluded_types=ListSettingState(use_default=True, custom_values=[], custom_initialized=False),
            excluded_properties=ListSettingState(use_default=True, custom_values=[], custom_initialized=False),
            excluded_properties_by_type=ByTypeSettingState(
                use_default=True,
                custom_values={},
                custom_initialized=False,
            ),
            float_precision=FLOAT_PRECISION,
        )


__all__ = ["DiffSettingsPreferencesPage"]
