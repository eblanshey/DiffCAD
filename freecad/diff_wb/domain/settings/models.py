# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Defines the Settings dataclass containing user
# configuration for diff computation including excluded types and properties.
"""Settings data models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """User configuration for diff computation."""

    excluded_types: list[str]
    excluded_properties: list[str]
