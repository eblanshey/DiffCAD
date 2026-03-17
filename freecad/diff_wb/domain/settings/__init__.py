# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: Settings subdomain containing configuration models
# and repository interface for user preferences.
"""Settings domain module."""

from .models import Settings
from .repository import SettingsRepository


__all__ = ["Settings", "SettingsRepository"]
