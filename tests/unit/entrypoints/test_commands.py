# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Tests for FreeCAD command entry points.

These tests verify that commands correctly delegate to actions and presenters.
"""

from unittest.mock import MagicMock, Mock, patch

from freecad.diff_wb.application.actions.result_models import CompareResult, SnapshotResult
from freecad.diff_wb.entrypoints.commands import (
    _CompareCommand,
    _SwapColumnsCommand,
    _TakeSnapshotCommand,
)


class TestTakeSnapshotCommand:
    """Tests for _TakeSnapshotCommand."""

    @patch("freecad.diff_wb._container.get_container")
    def test_take_snapshot_command_calls_action_and_presenter(self, mock_get_container: Mock) -> None:
        """Verifies flow from command to action to presenter."""
        # Setup
        mock_container = MagicMock()
        mock_action = MagicMock()
        mock_presenter = MagicMock()
        mock_container.take_snapshot_action = mock_action
        mock_container.snapshot_presenter = mock_presenter
        mock_get_container.return_value = mock_container

        expected_result = SnapshotResult(
            success=True,
            snapshot_id="test-id-123",
            snapshot_name="Test Snapshot",
            error_message=None,
        )
        mock_action.execute.return_value = expected_result

        command = _TakeSnapshotCommand()

        # Execute
        command.Activated()

        # Verify
        mock_action.execute.assert_called_once()
        mock_presenter.present_result.assert_called_once_with(expected_result)

    def test_command_resources_correct(self) -> None:
        """Menu text, tooltips, icons are correct."""
        # Setup
        command = _TakeSnapshotCommand()

        # Execute
        resources = command.GetResources()

        # Verify
        assert "MenuText" in resources
        assert "ToolTip" in resources
        assert "Pixmap" in resources
        assert resources["MenuText"] == "Take Snapshot"
        assert "snapshot" in resources["ToolTip"].lower()
        assert "TakeSnapshot.svg" in resources["Pixmap"]

    def test_is_active_returns_true(self) -> None:
        """Command is always active."""
        # Setup
        command = _TakeSnapshotCommand()

        # Execute
        result = command.IsActive()

        # Verify
        assert result is True


class TestCompareCommand:
    """Tests for _CompareCommand."""

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb._container.get_container")
    def test_compare_command_calls_view_get_selected_snapshot_ids(
        self,
        mock_get_container: Mock,
        mock_message_box: Mock,
    ) -> None:
        """Verifies that Compare command calls view's get_selected_snapshot_ids()."""
        # Setup
        mock_container = MagicMock()
        mock_action = MagicMock()
        mock_presenter = MagicMock()
        mock_container.compare_snapshots_action = mock_action
        mock_container.diff_presenter = mock_presenter
        mock_get_container.return_value = mock_container

        # Create a mock view
        mock_view = MagicMock()
        mock_view.get_selected_snapshot_ids.return_value = ["old-id-123", "new-id-456"]

        expected_diff_result = MagicMock()
        expected_result = CompareResult(
            success=True,
            diff_result=expected_diff_result,
            error_message=None,
        )
        mock_action.execute.return_value = expected_result

        command = _CompareCommand()
        # Mock the _get_view method
        with patch.object(command, "_get_view", return_value=mock_view):
            # Execute
            command.Activated()

        # Verify
        mock_view.get_selected_snapshot_ids.assert_called_once()
        mock_action.execute.assert_called_once_with("old-id-123", "new-id-456")
        mock_presenter.present_diff.assert_called_once_with(expected_diff_result)

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb._container.get_container")
    def test_compare_command_handles_zero_selected_snapshots(
        self,
        mock_get_container: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When 0 snapshots selected, shows warning and doesn't call compare action."""
        # Setup
        mock_container = MagicMock()
        mock_action = MagicMock()
        mock_container.compare_snapshots_action = mock_action
        mock_get_container.return_value = mock_container

        mock_view = MagicMock()
        mock_view.get_selected_snapshot_ids.return_value = []  # No snapshots selected

        command = _CompareCommand()
        with patch.object(command, "_get_view", return_value=mock_view):
            # Execute
            command.Activated()

        # Verify
        mock_view.get_selected_snapshot_ids.assert_called_once()
        mock_action.execute.assert_not_called()
        mock_message_box.warning.assert_called_once()
        # Verify warning message content
        call_args = mock_message_box.warning.call_args
        assert call_args[0][1] == "Selection Required"  # title
        assert "select" in call_args[0][2].lower()  # message contains "select"

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb._container.get_container")
    def test_compare_command_handles_one_selected_snapshot(
        self,
        mock_get_container: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When 1 snapshot selected, shows warning and doesn't call compare action."""
        # Setup
        mock_container = MagicMock()
        mock_action = MagicMock()
        mock_container.compare_snapshots_action = mock_action
        mock_get_container.return_value = mock_container

        mock_view = MagicMock()
        mock_view.get_selected_snapshot_ids.return_value = ["only-one-id"]  # Only one selected

        command = _CompareCommand()
        with patch.object(command, "_get_view", return_value=mock_view):
            # Execute
            command.Activated()

        # Verify
        mock_view.get_selected_snapshot_ids.assert_called_once()
        mock_action.execute.assert_not_called()
        mock_message_box.warning.assert_called_once()
        # Verify warning message content
        call_args = mock_message_box.warning.call_args
        assert call_args[0][1] == "Selection Required"  # title
        assert "select" in call_args[0][2].lower()  # message contains "select"

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb._container.get_container")
    def test_compare_command_handles_two_selected_snapshots(
        self,
        mock_get_container: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When exactly 2 snapshots selected, calls compare action with correct IDs."""
        # Setup
        mock_container = MagicMock()
        mock_action = MagicMock()
        mock_presenter = MagicMock()
        mock_container.compare_snapshots_action = mock_action
        mock_container.diff_presenter = mock_presenter
        mock_get_container.return_value = mock_container

        mock_view = MagicMock()
        mock_view.get_selected_snapshot_ids.return_value = ["old-123", "new-456"]

        expected_diff_result = MagicMock()
        expected_result = CompareResult(
            success=True,
            diff_result=expected_diff_result,
            error_message=None,
        )
        mock_action.execute.return_value = expected_result

        command = _CompareCommand()
        with patch.object(command, "_get_view", return_value=mock_view):
            # Execute
            command.Activated()

        # Verify
        mock_view.get_selected_snapshot_ids.assert_called_once()
        mock_action.execute.assert_called_once_with("old-123", "new-456")
        mock_presenter.present_diff.assert_called_once_with(expected_diff_result)
        mock_message_box.warning.assert_not_called()

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb._container.get_container")
    def test_compare_command_handles_more_than_two_selected_snapshots(
        self,
        mock_get_container: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When more than 2 snapshots selected, uses only the first 2."""
        # Setup
        mock_container = MagicMock()
        mock_action = MagicMock()
        mock_presenter = MagicMock()
        mock_container.compare_snapshots_action = mock_action
        mock_container.diff_presenter = mock_presenter
        mock_get_container.return_value = mock_container

        mock_view = MagicMock()
        # More than 2 selected - should use first 2
        mock_view.get_selected_snapshot_ids.return_value = ["old-123", "new-456", "extra-789"]

        expected_diff_result = MagicMock()
        expected_result = CompareResult(
            success=True,
            diff_result=expected_diff_result,
            error_message=None,
        )
        mock_action.execute.return_value = expected_result

        command = _CompareCommand()
        with patch.object(command, "_get_view", return_value=mock_view):
            # Execute
            command.Activated()

        # Verify - should use only first 2 IDs
        mock_action.execute.assert_called_once_with("old-123", "new-456")
        mock_message_box.warning.assert_not_called()

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb._container.get_container")
    def test_compare_command_error_result_no_presenter_call(
        self,
        mock_get_container: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When result is error, presenter is not called."""
        # Setup
        mock_container = MagicMock()
        mock_action = MagicMock()
        mock_presenter = MagicMock()
        mock_container.compare_snapshots_action = mock_action
        mock_container.diff_presenter = mock_presenter
        mock_get_container.return_value = mock_container

        mock_view = MagicMock()
        mock_view.get_selected_snapshot_ids.return_value = ["old-123", "new-456"]

        expected_result = CompareResult(
            success=False,
            diff_result=None,
            error_message="Snapshots not found",
        )
        mock_action.execute.return_value = expected_result

        command = _CompareCommand()
        with patch.object(command, "_get_view", return_value=mock_view):
            # Execute
            command.Activated()

        # Verify presenter was never called since result was an error
        mock_presenter.present_diff.assert_not_called()

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb._container.get_container")
    def test_compare_command_handles_no_view(
        self,
        mock_get_container: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When view is None, shows critical error and doesn't proceed."""
        # Setup
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container

        command = _CompareCommand()
        with patch.object(command, "_get_view", return_value=None):
            # Execute
            command.Activated()

        # Verify
        mock_message_box.critical.assert_called_once()
        mock_message_box.warning.assert_not_called()
        # Verify critical error message content
        call_args = mock_message_box.critical.call_args
        assert call_args[0][1] == "Error"  # title
        assert "view" in call_args[0][2].lower()  # message contains "view"

    def test_compare_command_resources_correct(self) -> None:
        """Menu text, tooltips, icons are correct."""
        # Setup
        command = _CompareCommand()

        # Execute
        resources = command.GetResources()

        # Verify
        assert "MenuText" in resources
        assert "ToolTip" in resources
        assert "Pixmap" in resources
        assert resources["MenuText"] == "Compare"
        assert "snapshot" in resources["ToolTip"].lower()
        assert "Compare.svg" in resources["Pixmap"]

    def test_is_active_returns_true(self) -> None:
        """Command is always active."""
        # Setup
        command = _CompareCommand()

        # Execute
        result = command.IsActive()

        # Verify
        assert result is True


class TestSwapColumnsCommand:
    """Tests for _SwapColumnsCommand."""

    def test_swap_columns_command_resources_correct(self) -> None:
        """Menu text, tooltips, icons are correct."""
        # Setup
        command = _SwapColumnsCommand()

        # Execute
        resources = command.GetResources()

        # Verify
        assert "MenuText" in resources
        assert "ToolTip" in resources
        assert "Pixmap" in resources
        assert resources["MenuText"] == "Swap Columns"
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
