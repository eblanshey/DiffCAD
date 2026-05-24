# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for persistence-to-effective settings conversion helpers.
"""Tests for SettingsPersistenceState conversion helpers."""

from freecad.history_wb.domain.settings.models import Settings
from freecad.history_wb.domain.settings.persistence_state import (
    ByTypeSettingState,
    ListSettingState,
    SettingsPersistenceState,
)


def test_to_effective_settings_uses_defaults_for_default_modes() -> None:
    state = SettingsPersistenceState(
        excluded_types=ListSettingState(use_default=True, custom_values=["Ignored"], custom_initialized=False),
        excluded_properties=ListSettingState(use_default=True, custom_values=["Ignored"], custom_initialized=False),
        excluded_properties_by_type=ByTypeSettingState(
            use_default=True,
            custom_values={"Ignored::Type": ["Ignored"]},
            custom_initialized=False,
        ),
        float_precision=4,
    )

    effective = state.to_effective_settings(
        default_excluded_types=["App::Origin"],
        default_excluded_properties=["Label2"],
        default_excluded_properties_by_type={"TechDraw::DrawSVGTemplate": ["PageResult"]},
    )

    assert effective == Settings(
        excluded_types=["App::Origin"],
        excluded_properties=["Label2"],
        excluded_properties_by_type={"TechDraw::DrawSVGTemplate": ["PageResult"]},
        float_precision=4,
    )


def test_to_effective_settings_uses_custom_values_for_custom_modes() -> None:
    state = SettingsPersistenceState(
        excluded_types=ListSettingState(use_default=False, custom_values=["App::Part"], custom_initialized=True),
        excluded_properties=ListSettingState(
            use_default=False,
            custom_values=["TimeStamp"],
            custom_initialized=True,
        ),
        excluded_properties_by_type=ByTypeSettingState(
            use_default=False,
            custom_values={"App::Part": ["Tip"]},
            custom_initialized=True,
        ),
        float_precision=6,
    )

    effective = state.to_effective_settings(
        default_excluded_types=["App::Origin"],
        default_excluded_properties=["Label2"],
        default_excluded_properties_by_type={"TechDraw::DrawSVGTemplate": ["PageResult"]},
    )

    assert effective == Settings(
        excluded_types=["App::Part"],
        excluded_properties=["TimeStamp"],
        excluded_properties_by_type={"App::Part": ["Tip"]},
        float_precision=6,
    )
