# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: Provide fake implementations for testing including FakeLogger,
# FakeSnapshotRepository, FakeSettingsRepository, and InMemorySnapshotRepository.
"""Fake implementations for testing."""

from .fake_logger import FakeLogger
from .fake_repositories import (
    FakeSettingsRepository,
    FakeSnapshotRepository,
    InMemorySnapshotRepository,
)


__all__ = ["FakeLogger", "FakeSnapshotRepository", "FakeSettingsRepository", "InMemorySnapshotRepository"]
