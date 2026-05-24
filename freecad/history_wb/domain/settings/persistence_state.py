# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Defines persistence-state contracts for diff settings
# editing flows across application, UI, and infrastructure layers.
"""Persistence-state contracts for diff settings preferences."""

from dataclasses import dataclass

from .models import Settings


@dataclass(frozen=True)
class ListSettingState:
    """Persistence state for a list-based setting."""

    use_default: bool
    custom_values: list[str]
    custom_initialized: bool


@dataclass(frozen=True)
class ByTypeSettingState:
    """Persistence state for type-scoped list setting."""

    use_default: bool
    custom_values: dict[str, list[str]]
    custom_initialized: bool


@dataclass(frozen=True)
class SettingsPersistenceState:
    """Raw persistence state needed by preferences UI and save flow."""

    excluded_types: ListSettingState
    excluded_properties: ListSettingState
    excluded_properties_by_type: ByTypeSettingState
    float_precision: int

    def to_effective_settings(
        self,
        *,
        default_excluded_types: list[str],
        default_excluded_properties: list[str],
        default_excluded_properties_by_type: dict[str, list[str]],
    ) -> Settings:
        """Convert persistence state into effective runtime settings."""
        return Settings(
            excluded_types=(
                list(default_excluded_types)
                if self.excluded_types.use_default
                else list(self.excluded_types.custom_values)
            ),
            excluded_properties=(
                list(default_excluded_properties)
                if self.excluded_properties.use_default
                else list(self.excluded_properties.custom_values)
            ),
            excluded_properties_by_type=(
                _copy_by_type(default_excluded_properties_by_type)
                if self.excluded_properties_by_type.use_default
                else _copy_by_type(self.excluded_properties_by_type.custom_values)
            ),
            float_precision=self.float_precision,
        )


def _copy_by_type(values: dict[str, list[str]]) -> dict[str, list[str]]:
    """Create a deep copy of by-type list mapping."""
    return {type_id: list(properties) for type_id, properties in values.items()}
