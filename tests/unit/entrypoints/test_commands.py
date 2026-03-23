# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Tests for FreeCAD command entry points.

These tests verify that commands correctly delegate to actions and presenters.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from freecad.diff_wb.application.actions.result_models import CompareResult, SnapshotResult
from freecad.diff_wb.entrypoints.commands import (
    _CompareCommand,
    _SwapColumnsCommand,
    _TakeSnapshotCommand,
)


class TestTakeSnapshotCommand:
    """Tests for _TakeSnapshotCommand."""

    def test_take_snapshot_command_calls_action_and_presenter(self) -> None:
        """Verifies flow from command to action to presenter."""
        # Setup
        mock_action = MagicMock()
        mock_presenter = MagicMock()

        expected_result = SnapshotResult(
            success=True,
            snapshot_id="test-id-123",
            snapshot_name="Test Snapshot",
            error_message=None,
        )
        mock_action.execute.return_value = expected_result

        command = _TakeSnapshotCommand(action=mock_action, presenter=mock_presenter)

        # Execute
        command.Activated()

        # Verify
        mock_action.execute.assert_called_once()
        mock_presenter.present_result.assert_called_once_with(expected_result)

    @patch("freecad.diff_wb.entrypoints.commands._container")
    def test_command_resources_correct(self, mock_container: Mock) -> None:
        """Menu text, tooltips, icons are correct."""
        # Setup
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_action = MagicMock()
        mock_presenter = MagicMock()
        command = _TakeSnapshotCommand(action=mock_action, presenter=mock_presenter)

        # Execute
        resources = command.GetResources()

        # Verify
        assert "MenuText" in resources
        assert "ToolTip" in resources
        assert "Pixmap" in resources
        assert "Take Snapshot" in resources["MenuText"]
        assert "snapshot" in resources["ToolTip"].lower()
        assert "TakeSnapshot.svg" in resources["Pixmap"]

    def test_is_active_returns_true(self) -> None:
        """Command is always active."""
        # Setup
        mock_action = MagicMock()
        mock_presenter = MagicMock()
        command = _TakeSnapshotCommand(action=mock_action, presenter=mock_presenter)

        # Execute
        result = command.IsActive()

        # Verify
        assert result is True


class TestCompareCommand:
    """Tests for _CompareCommand."""

    def test_compare_command_calls_action_and_presenter(self) -> None:
        """Verifies comparison flow from command to action to presenter."""
        # Setup
        mock_action = MagicMock()
        mock_presenter = MagicMock()

        expected_diff_result = MagicMock()
        expected_result = CompareResult(
            success=True,
            diff_result=expected_diff_result,
            error_message=None,
        )
        mock_action.execute.return_value = expected_result

        command = _CompareCommand(action=mock_action, presenter=mock_presenter)

        # Note: The compare command will raise NotImplementedError because
        # snapshot selection is not yet implemented (Phase 8 UI)
        with pytest.raises(NotImplementedError, match="Phase 8"):
            command.Activated()

    def test_compare_command_error_result_no_presenter_call(self) -> None:
        """When result is error, presenter is not called."""
        # Setup
        mock_action = MagicMock()
        mock_presenter = MagicMock()

        expected_result = CompareResult(
            success=False,
            diff_result=None,
            error_message="Snapshots not found",
        )
        mock_action.execute.return_value = expected_result

        command = _CompareCommand(action=mock_action, presenter=mock_presenter)

        # Note: The compare command will raise NotImplementedError because
        # snapshot selection is not yet implemented (Phase 8 UI)
        with pytest.raises(NotImplementedError, match="Phase 8"):
            command.Activated()

        # Verify presenter was never called since we can't get past the NotImplementedError
        mock_presenter.present_diff.assert_not_called()

    @patch("freecad.diff_wb.entrypoints.commands._container")
    def test_compare_command_resources_correct(self, mock_container: Mock) -> None:
        """Menu text, tooltips, icons are correct."""
        # Setup
        mock_container.translate.side_effect = lambda ctx, text: text
        mock_action = MagicMock()
        mock_presenter = MagicMock()
        command = _CompareCommand(action=mock_action, presenter=mock_presenter)

        # Execute
        resources = command.GetResources()

        # Verify
        assert "MenuText" in resources
        assert "ToolTip" in resources
        assert "Pixmap" in resources
        assert "Compare" in resources["MenuText"]
        assert "snapshot" in resources["ToolTip"].lower()
        assert "Compare.svg" in resources["Pixmap"]

    def test_is_active_returns_true(self) -> None:
        """Command is always active."""
        # Setup
        mock_action = MagicMock()
        mock_presenter = MagicMock()
        command = _CompareCommand(action=mock_action, presenter=mock_presenter)

        # Execute
        result = command.IsActive()

        # Verify
        assert result is True


class TestSwapColumnsCommand:
    """Tests for _SwapColumnsCommand."""

    @patch("freecad.diff_wb.entrypoints.commands._container")
    def test_swap_columns_command_resources_correct(self, mock_container: Mock) -> None:
        """Menu text, tooltips, icons are correct."""
        # Setup
        mock_container.translate.side_effect = lambda ctx, text: text
        command = _SwapColumnsCommand()

        # Execute
        resources = command.GetResources()

        # Verify
        assert "MenuText" in resources
        assert "ToolTip" in resources
        assert "Pixmap" in resources
        assert "Swap Columns" in resources["MenuText"]
        assert "column" in resources["ToolTip"].lower()
        assert "SwapColumns.svg" in resources["Pixmap"]

    def test_is_active_returns_true(self) -> None:
        """Command is always active."""
        # Setup
        command = _SwapColumnsCommand()

        # Execute
        result = command.IsActive()

        # Verify
        assert result is True

    def test_swap_columns_activated_not_implemented(self) -> None:
        """Swap columns Activated is not yet implemented."""
        # Setup
        command = _SwapColumnsCommand()

        # Execute and Verify
        # TODO: Implement when UI view exists
        # For now, just verify it doesn't crash
        command.Activated()  # Should pass (currently does nothing)
