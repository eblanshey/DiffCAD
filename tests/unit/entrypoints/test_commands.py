# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Tests for FreeCAD command entry points.

These tests verify that commands correctly delegate to actions and presenters.
Focused command files (test_commit_command.py, test_open_all_documents_command.py)
own Commit and OpenAll routing behavior; this file covers commands without dedicated
test files plus resource validation for all commands.
"""

from unittest.mock import MagicMock, Mock, patch

from freecad.diff_wb.entrypoints.commands import (
    _OpenDiffWindowCommand,
    _RecomputeActiveDocumentCommand,
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

    @patch("freecad.diff_wb.ui.registry.ui_registry")
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

    def test_refresh_repository_command_resources_correct(self) -> None:
        """Menu text, tooltip, and icon path are correct."""
        command = _RefreshRepositoryCommand()

        resources = command.GetResources()

        assert resources["MenuText"] == "Refresh Project and Iterations"
        assert "refresh" in resources["ToolTip"].lower()
        assert resources["Pixmap"].endswith("RefreshRepository.svg")
        assert command.IsActive() is True


class TestRecomputeAllOpenDocumentsCommand:
    """Tests for _RecomputeAllOpenDocumentsCommand."""

    @patch("freecad.diff_wb._container.get_container")
    def test_activated_calls_application_action(self, mock_get_container: Mock) -> None:
        """Activated delegates to application action execute API."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container

        command = _RecomputeAllOpenDocumentsCommand()

        command.Activated()

        mock_container.recompute_all_open_documents_action.execute.assert_called_once_with()

    def test_resources_and_activation(self) -> None:
        """Command resources are valid and command active."""
        command = _RecomputeAllOpenDocumentsCommand()

        resources = command.GetResources()

        assert resources["MenuText"] == "Recompute All"
        assert "recompute" in resources["ToolTip"].lower()
        assert resources["Pixmap"].endswith("RecomputeAll.svg")
        assert command.IsActive() is True


class TestRecomputeActiveDocumentCommand:
    """Tests for _RecomputeActiveDocumentCommand."""

    def test_resources_and_activation(self) -> None:
        """Command resources are valid and command active."""
        command = _RecomputeActiveDocumentCommand()

        resources = command.GetResources()

        assert resources["MenuText"] == "Recompute Active Document"
        assert "recompute" in resources["ToolTip"].lower()
        assert resources["Pixmap"] == "view-refresh"
        assert command.IsActive() is True


class TestOpenDiffWindowCommand:
    """Tests for _OpenDiffWindowCommand."""

    def test_resources_and_activation(self) -> None:
        """Command resources are valid and command active."""
        command = _OpenDiffWindowCommand()

        resources = command.GetResources()

        assert resources["MenuText"] == "Open History Panel"
        assert "history" in resources["ToolTip"].lower()
        assert resources["Pixmap"].endswith("Logo.svg")
        assert command.IsActive() is True
