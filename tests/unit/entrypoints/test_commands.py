# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Tests for FreeCAD command entry points.

These tests verify that commands correctly delegate to actions and presenters.
Focused command files (test_commit_command.py, test_open_all_documents_command.py)
own Commit and OpenAll routing behavior; this file covers commands without dedicated
test files.
"""

from unittest.mock import MagicMock, Mock, patch

from freecad.history_wb.entrypoints.commands import (
    _RecomputeAllOpenDocumentsCommand,
    _RefreshRepositoryCommand,
    _SwapColumnsCommand,
)


class TestSwapColumnsCommand:
    """Tests for _SwapColumnsCommand."""

    def test_swap_columns_command_resources_correct(self) -> None:
        """Menu text, tooltips, icons are correct."""
        command = _SwapColumnsCommand()
        resources = command.GetResources()

        assert "MenuText" in resources
        assert "ToolTip" in resources
        assert "Pixmap" in resources
        assert resources["MenuText"] == "Swap Columns"
        assert "column" in resources["ToolTip"].lower()
        assert "SwapColumns.svg" in resources["Pixmap"]

    def test_is_active_returns_true(self) -> None:
        """Command is always active."""
        command = _SwapColumnsCommand()
        assert command.IsActive() is True


class TestRefreshRepositoryCommand:
    """Tests for _RefreshRepositoryCommand."""

    @patch("freecad.history_wb.ui.registry.ui_registry")
    def test_refresh_repository_command_calls_git_repository_presenter(
        self,
        mock_ui_registry: Mock,
    ) -> None:
        """Activated delegates to GitRepositoryPresenter refresh API."""
        mock_presenter = MagicMock()
        mock_ui_registry.git_repository_presenter = mock_presenter

        command = _RefreshRepositoryCommand()

        command.Activated()

        mock_presenter.refresh_repository_and_commits.assert_called_once_with()


class TestRecomputeAllOpenDocumentsCommand:
    """Tests for _RecomputeAllOpenDocumentsCommand."""

    @patch("freecad.history_wb._container.get_container")
    def test_activated_calls_application_action(self, mock_get_container: Mock) -> None:
        """Activated delegates to application action execute API."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container

        command = _RecomputeAllOpenDocumentsCommand()

        command.Activated()

        mock_container.recompute_all_open_documents_action.execute.assert_called_once_with()


class TestRecomputeActiveDocumentCommand:
    """Tests for _RecomputeActiveDocumentCommand."""


class TestOpenDiffWindowCommand:
    """Tests for _OpenDiffWindowCommand."""
