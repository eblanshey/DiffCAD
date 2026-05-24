# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: Settings subdomain containing configuration models
# and repository interface for user preferences.
"""Settings domain module."""

from .models import Settings
from .persistence_state import ByTypeSettingState, ListSettingState, SettingsPersistenceState
from .repository import SettingsPersistenceRepository, SettingsRepository
from .text_codec import (
    parse_by_type_lines,
    parse_list_lines,
    serialize_by_type_lines,
    serialize_list_lines,
)


__all__ = [
    "Settings",
    "SettingsRepository",
    "SettingsPersistenceRepository",
    "ListSettingState",
    "ByTypeSettingState",
    "SettingsPersistenceState",
    "parse_list_lines",
    "serialize_list_lines",
    "parse_by_type_lines",
    "serialize_by_type_lines",
]
