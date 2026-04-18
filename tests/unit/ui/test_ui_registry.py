# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for UIRegistry.
# These tests verify that the UIRegistry correctly manages presenter registration
# and provides proper error handling when presenters are not initialized.
"""Unit tests for UIRegistry."""

import pytest

from freecad.diff_wb.ui.registry import ui_registry
from freecad.diff_wb.ui.state import UIState


class TestUIRegistry:
    """Tests for UIRegistry class."""

    def setup_method(self) -> None:
        """Reset registry state before each test."""
        ui_registry.clear()

    def test_snapshot_presenter_raises_runtime_error_when_not_set(self) -> None:
        """snapshot_presenter property raises RuntimeError when not initialized."""
        with pytest.raises(RuntimeError) as exc_info:
            _ = ui_registry.snapshot_presenter

        assert "Snapshot presenter not initialized" in str(exc_info.value)
        assert "Workbench must be activated first" in str(exc_info.value)

    def test_diff_presenter_returns_none_when_not_set(self) -> None:
        """diff_presenter property returns None when not initialized."""
        result = ui_registry.diff_presenter
        assert result is None

    def test_register_snapshot_presenter_stores_presenter(self) -> None:
        """register_snapshot_presenter() stores presenter and property returns it."""

        # Create a mock presenter
        class MockSnapshotPresenter:
            pass

        mock_presenter = MockSnapshotPresenter()

        # Register the presenter
        ui_registry.register_snapshot_presenter(mock_presenter)

        # Property should return the stored presenter
        assert ui_registry.snapshot_presenter is mock_presenter

    def test_register_diff_presenter_stores_presenter(self) -> None:
        """register_diff_presenter() stores presenter and property returns it."""

        # Create a mock presenter
        class MockDiffPresenter:
            pass

        mock_presenter = MockDiffPresenter()

        # Register the presenter
        ui_registry.register_diff_presenter(mock_presenter)

        # Property should return the stored presenter
        assert ui_registry.diff_presenter is mock_presenter

    def test_clear_resets_both_presenters(self) -> None:
        """clear() resets both presenters to initial state."""

        # Register some presenters
        class MockSnapshotPresenter:
            pass

        class MockDiffPresenter:
            pass

        ui_registry.register_snapshot_presenter(MockSnapshotPresenter())
        ui_registry.register_diff_presenter(MockDiffPresenter())

        # Verify they're set
        assert ui_registry.snapshot_presenter is not None
        assert ui_registry.diff_presenter is not None

        # Clear the registry
        ui_registry.clear()

        # Verify both are reset to initial state
        with pytest.raises(RuntimeError):
            _ = ui_registry.snapshot_presenter
        assert ui_registry.diff_presenter is None

    def test_ui_state_can_be_imported_from_new_location(self) -> None:
        """UIState can be imported from new location (ui.state)."""
        # This test verifies that UIState can be imported from the new location
        # If this import fails, the test will fail at import time
        assert UIState is not None

        # Verify it's the correct type
        state = UIState(git_repository=None)
        assert state.git_repository is None
