# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: Provide fake implementations for testing including FakeLogger,
# FakeSnapshotRepository, FakeSettingsRepository, FakeDiffEngine, FakeDiffView,
# FakeGitPort, and InMemorySnapshotRepository.
"""Fake implementations for testing."""

from .fake_diff_view import FakeDiffView
from .fake_freecad_port import FakeFreeCadPort
from .fake_git_port import FakeGitPort
from .fake_logger import FakeLogger
from .fake_repositories import (
    FakeDiffEngine,
    FakeSettingsRepository,
    FakeSnapshotRepository,
    InMemorySnapshotRepository,
)
from .fake_snapshot_view import FakeSnapshotView
from .null_snapshot_view import NullSnapshotView


__all__ = [
    "FakeLogger",
    "FakeSnapshotRepository",
    "FakeSettingsRepository",
    "FakeDiffEngine",
    "FakeDiffView",
    "FakeFreeCadPort",
    "FakeGitPort",
    "InMemorySnapshotRepository",
    "FakeSnapshotView",
    "NullSnapshotView",
]
