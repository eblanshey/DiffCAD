# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module implements the FreeCAD settings persistence model,
# including mode flags, custom values, initialization markers, and float precision
# normalization for Diff Workbench preferences stored via FreeCAD ParamGet.
"""FreeCAD settings repository implementation."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol, cast

from ...domain.config import (
    EXCLUDED_PROPERTIES,
    EXCLUDED_PROPERTIES_BY_TYPE,
    EXCLUDED_TYPES,
    FLOAT_PRECISION,
)
from ...domain.settings.models import Settings
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
from .ports import FreeCadContext


class _ParamGroup(Protocol):
    def GetString(self, key: str, default: str = "") -> str: ...
    def SetString(self, key: str, value: str) -> None: ...
    def GetBool(self, key: str, default: bool = False) -> bool: ...
    def SetBool(self, key: str, value: bool) -> None: ...
    def GetInt(self, key: str, default: int = 0) -> int: ...
    def SetInt(self, key: str, value: int) -> None: ...


MIN_FLOAT_PRECISION = 0
MAX_FLOAT_PRECISION = 12


class FreeCADSettingsRepository:
    """Settings repository implementation using FreeCAD's Parameter system.

    This class adapts FreeCAD's Parameter API to the SettingsRepository
    interface, allowing domain code to work with settings through the port abstraction.
    It stores explicit mode/value/initialized keys per list setting and returns
    config defaults only when mode is set to default.
    """

    KEY_USE_DEFAULT_EXCLUDED_TYPES = "UseDefaultExcludedTypes"
    KEY_CUSTOM_EXCLUDED_TYPES = "CustomExcludedTypes"
    KEY_CUSTOM_EXCLUDED_TYPES_INITIALIZED = "CustomExcludedTypesInitialized"

    KEY_USE_DEFAULT_EXCLUDED_PROPERTIES = "UseDefaultExcludedProperties"
    KEY_CUSTOM_EXCLUDED_PROPERTIES = "CustomExcludedProperties"
    KEY_CUSTOM_EXCLUDED_PROPERTIES_INITIALIZED = "CustomExcludedPropertiesInitialized"

    KEY_USE_DEFAULT_EXCLUDED_PROPERTIES_BY_TYPE = "UseDefaultExcludedPropertiesByType"
    KEY_CUSTOM_EXCLUDED_PROPERTIES_BY_TYPE = "CustomExcludedPropertiesByType"
    KEY_CUSTOM_EXCLUDED_PROPERTIES_BY_TYPE_INITIALIZED = "CustomExcludedPropertiesByTypeInitialized"

    KEY_FLOAT_PRECISION = "FloatPrecision"

    def __init__(self, ctx: FreeCadContext) -> None:
        self._ctx = ctx
        self._group_path = "User parameter:BaseApp/Preferences/Mod/History"
        self._cached_settings: Settings | None = None

    def _get_group(self) -> _ParamGroup:
        return cast(_ParamGroup, self._ctx.app.ParamGet(self._group_path))

    def _get_list_state(
        self,
        *,
        use_default_key: str,
        custom_values_key: str,
        initialized_key: str,
    ) -> ListSettingState:
        group = self._get_group()
        use_default = group.GetBool(use_default_key, True)
        custom_raw = group.GetString(custom_values_key, "")
        initialized = group.GetBool(initialized_key, False)
        return ListSettingState(
            use_default=use_default,
            custom_values=parse_list_lines(custom_raw),
            custom_initialized=initialized,
        )

    def _set_list_state(
        self,
        *,
        use_default_key: str,
        custom_values_key: str,
        initialized_key: str,
        state: ListSettingState,
    ) -> None:
        group = self._get_group()
        group.SetBool(use_default_key, state.use_default)
        group.SetString(custom_values_key, serialize_list_lines(state.custom_values))
        group.SetBool(initialized_key, state.custom_initialized)

    def _get_by_type_state(self) -> ByTypeSettingState:
        group = self._get_group()
        use_default = group.GetBool(self.KEY_USE_DEFAULT_EXCLUDED_PROPERTIES_BY_TYPE, True)
        custom_raw = group.GetString(self.KEY_CUSTOM_EXCLUDED_PROPERTIES_BY_TYPE, "")
        initialized = group.GetBool(self.KEY_CUSTOM_EXCLUDED_PROPERTIES_BY_TYPE_INITIALIZED, False)
        return ByTypeSettingState(
            use_default=use_default,
            custom_values=parse_by_type_lines(custom_raw),
            custom_initialized=initialized,
        )

    def _set_by_type_state(self, state: ByTypeSettingState) -> None:
        group = self._get_group()
        group.SetBool(self.KEY_USE_DEFAULT_EXCLUDED_PROPERTIES_BY_TYPE, state.use_default)
        group.SetString(
            self.KEY_CUSTOM_EXCLUDED_PROPERTIES_BY_TYPE,
            serialize_by_type_lines(state.custom_values),
        )
        group.SetBool(
            self.KEY_CUSTOM_EXCLUDED_PROPERTIES_BY_TYPE_INITIALIZED,
            state.custom_initialized,
        )

    def _get_float_precision(self) -> int:
        group = self._get_group()
        value = group.GetInt(self.KEY_FLOAT_PRECISION, FLOAT_PRECISION)
        return self._normalize_float_precision(value)

    def _set_float_precision(self, value: int) -> None:
        group = self._get_group()
        group.SetInt(self.KEY_FLOAT_PRECISION, self._normalize_float_precision(value))

    def _normalize_float_precision(self, value: int) -> int:
        return max(MIN_FLOAT_PRECISION, min(MAX_FLOAT_PRECISION, value))

    def _copy_default_by_type(self, values: dict[str, list[str]]) -> dict[str, list[str]]:
        return {type_id: list(properties) for type_id, properties in values.items()}

    def get_persistence_state(self) -> SettingsPersistenceState:
        """Get full persisted state including mode and initialization flags."""
        return SettingsPersistenceState(
            excluded_types=self._get_list_state(
                use_default_key=self.KEY_USE_DEFAULT_EXCLUDED_TYPES,
                custom_values_key=self.KEY_CUSTOM_EXCLUDED_TYPES,
                initialized_key=self.KEY_CUSTOM_EXCLUDED_TYPES_INITIALIZED,
            ),
            excluded_properties=self._get_list_state(
                use_default_key=self.KEY_USE_DEFAULT_EXCLUDED_PROPERTIES,
                custom_values_key=self.KEY_CUSTOM_EXCLUDED_PROPERTIES,
                initialized_key=self.KEY_CUSTOM_EXCLUDED_PROPERTIES_INITIALIZED,
            ),
            excluded_properties_by_type=self._get_by_type_state(),
            float_precision=self._get_float_precision(),
        )

    def save_persistence_state(self, state: SettingsPersistenceState) -> None:
        """Persist full settings state including mode and initialization flags."""
        self._set_list_state(
            use_default_key=self.KEY_USE_DEFAULT_EXCLUDED_TYPES,
            custom_values_key=self.KEY_CUSTOM_EXCLUDED_TYPES,
            initialized_key=self.KEY_CUSTOM_EXCLUDED_TYPES_INITIALIZED,
            state=state.excluded_types,
        )
        self._set_list_state(
            use_default_key=self.KEY_USE_DEFAULT_EXCLUDED_PROPERTIES,
            custom_values_key=self.KEY_CUSTOM_EXCLUDED_PROPERTIES,
            initialized_key=self.KEY_CUSTOM_EXCLUDED_PROPERTIES_INITIALIZED,
            state=state.excluded_properties,
        )
        self._set_by_type_state(state.excluded_properties_by_type)
        self._set_float_precision(state.float_precision)
        self._cached_settings = self._build_settings_from_state(state)

    def _build_settings_from_state(self, state: SettingsPersistenceState) -> Settings:
        normalized_state = replace(state, float_precision=self._normalize_float_precision(state.float_precision))
        return normalized_state.to_effective_settings(
            default_excluded_types=EXCLUDED_TYPES,
            default_excluded_properties=EXCLUDED_PROPERTIES,
            default_excluded_properties_by_type=EXCLUDED_PROPERTIES_BY_TYPE,
        )

    def get_excluded_types(self) -> list[str]:
        """Get list of type IDs to exclude from diff computation.

        Returns:
            List of FreeCAD type IDs to exclude (e.g., ["App::Origin"]).
            Returns default from config.py if no persisted value exists.
        """
        return list(self.get_settings().excluded_types)

    def get_excluded_properties(self) -> list[str]:
        """Get list of property names to exclude from comparison.

        Returns:
            List of property names to exclude (e.g., ["TimeStamp", "Label2"]).
            Returns default from config.py if no persisted value exists.
        """
        return list(self.get_settings().excluded_properties)

    def get_excluded_properties_by_type(self) -> dict[str, list[str]]:
        """Get type-specific property exclusions.

        Returns:
            Dict mapping type IDs to lists of property names to exclude
            for that type. Returns default from config.py if no persisted
            value exists.
        """
        return self._copy_default_by_type(self.get_settings().excluded_properties_by_type)

    def get_float_precision(self) -> int:
        """Get float precision for comparison and display.

        Returns:
            Number of decimal places for float comparison (default: 2).
        """
        return self.get_settings().float_precision

    def get_settings(self) -> Settings:
        """Get all settings as a Settings object.

        Returns:
            Settings object with excluded types, properties, and type-specific
            property exclusions from FreeCAD preferences, or defaults from
            config.py if no persisted values exist.
        """
        if self._cached_settings is None:
            self._cached_settings = self._build_settings_from_state(self.get_persistence_state())

        return self._cached_settings
