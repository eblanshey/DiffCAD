# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Pytest configuration and shared fixtures for Diff Workbench tests,
# including mock FreeCAD app, GUI, context fixtures, and fake implementations for testing.
"""Pytest configuration and shared fixtures for Diff Workbench tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.fakes import FakeLogger, FakeSettingsRepository


if TYPE_CHECKING:
    from freecad.diff_wb.domain.freecad_ports import AppLike, DocumentObjectLike, FreeCadContext


@pytest.fixture
def mock_freecad_app() -> AppLike:
    """Create a mock FreeCAD application object for testing.

    Returns:
        Mock FreeCAD application object with minimal interface for testing.
    """

    class MockConsole:
        def PrintMessage(self, text: str) -> None:
            pass

        def PrintError(self, text: str) -> None:
            pass

        def PrintWarning(self, text: str) -> None:
            pass

    class MockDocument:
        Objects: list[DocumentObjectLike] = []

        def getObject(self, name: str) -> DocumentObjectLike | None:
            return None

        def recompute(self) -> None:
            pass

    class MockApp:
        ActiveDocument: MockDocument | None = None
        Console: MockConsole = MockConsole()

        def translate(self, context: str, text: str) -> str:
            return text

        def ParamGet(self, path: str) -> object:
            return MockParamGet()

    class MockParamGet:
        def GetString(self, key: str, default: str = "") -> str:
            return default

        def SetString(self, key: str, value: str) -> None:
            pass

    return MockApp()  # type: ignore[return-value]


@pytest.fixture
def mock_freecad_gui() -> object:
    """Create a mock FreeCAD GUI object for testing.

    Returns:
        Mock FreeCAD GUI object with minimal interface for testing.
    """

    class MockMainWindow:
        def workspace(self) -> None:
            return None

    class MockGui:
        @staticmethod
        def getDocument(doc_name: str) -> object | None:
            return None

        @staticmethod
        def getMainWindow() -> MockMainWindow:
            return MockMainWindow()

    return MockGui()


@pytest.fixture
def freecad_context(mock_freecad_app: AppLike, mock_freecad_gui: object) -> FreeCadContext:
    """Create a FreeCAD context with mocked app and gui.

    Args:
        mock_freecad_app: Mock FreeCAD application object.
        mock_freecad_gui: Mock FreeCAD GUI object.

    Returns:
        FreeCadContext instance with mocked components.
    """
    from freecad.diff_wb.domain.freecad_ports import FreeCadContext

    return FreeCadContext(app=mock_freecad_app, gui=mock_freecad_gui)


@pytest.fixture
def fake_logger() -> FakeLogger:
    """Create a fake logger for testing.

    Returns:
        FakeLogger instance for capturing log calls in tests.
    """
    return FakeLogger()


@pytest.fixture
def fake_settings_repo() -> FakeSettingsRepository:
    """Create a fake settings repository with default excluded types and properties.

    Returns:
        FakeSettingsRepository instance with default configuration.
    """
    return FakeSettingsRepository()
