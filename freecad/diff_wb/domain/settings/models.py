# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Defines the Settings dataclass containing user
# configuration for diff computation including excluded types, properties,
# and type-specific property exclusions.
"""Settings data models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """User configuration for diff computation."""

    excluded_types: list[str]
    excluded_properties: list[str]
    excluded_properties_by_type: dict[str, list[str]]
    float_precision: int = 2  # Decimal places for float comparison and display
