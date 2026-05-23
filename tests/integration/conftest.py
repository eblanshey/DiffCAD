# SPDX-License-Identifier: LGPL-3.0-or-later
"""Module responsibility: Pytest fixtures for FreeCAD integration tests.

These fixtures provide access to FreeCAD runtime components and help initialize
the application container for testing.

Run these tests with: ./run_integration_tests.sh
Or: FREECAD_ROOT=/path/to/freecad python -m pytest tests/integration/ -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest


if TYPE_CHECKING:
    from freecad.diff_wb.domain.freecad_ports import FreeCadContext


def pytest_configure(config: object) -> None:
    """Configure pytest and validate FreeCAD environment."""
    freecad_root = os.environ.get("FREECAD_ROOT")

    if not freecad_root:
        print("\n⚠️  WARNING: FREECAD_ROOT environment variable is not set.\n")
        print("Integration tests that require FreeCAD runtime will be skipped.")
        print("To run all integration tests, use:\n")
        print("  ./run_integration_tests.sh\n")
        print("-" * 60 + "\n")

    # Validate FreeCAD Python is being used (only if FREECAD_ROOT is set)
    if freecad_root:
        current_python = sys.executable
        expected_python = os.path.join(freecad_root, "usr/bin/python")

        # Only warn if not using FreeCAD Python (tests may still work if paths are configured)
        if current_python != expected_python and "run_integration_tests.sh" not in current_python:
            print("Warning: Not using FreeCAD Python interpreter.")
            print(f"  Expected: {expected_python}")
            print(f"  Using: {current_python}")
            print("  Consider using ./run_integration_tests.sh")


@pytest.fixture(scope="session")
def freecad_root() -> str:
    """Get the FreeCAD root directory from environment variable.

    Returns:
        Path to FreeCAD installation root.

    Raises:
        pytest.skip: If FREECAD_ROOT is not set.
    """
    freecad_root = os.environ.get("FREECAD_ROOT")
    if not freecad_root:
        pytest.skip("FREECAD_ROOT environment variable not set")
    return freecad_root


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory.

    Returns:
        Path to project root directory.
    """
    return Path(__file__).parent.parent.parent


@pytest.fixture
def freecad_app() -> Any:
    """Import and return the FreeCAD application module.

    Returns:
        FreeCAD application module (typed as Any due to dynamic FreeCAD API).

    Raises:
        pytest.skip: If FreeCAD cannot be imported.
    """
    try:
        import FreeCAD
    except ImportError as e:
        pytest.skip(f"Cannot import FreeCAD: {e}")

    return FreeCAD


@pytest.fixture
def freecad_gui(freecad_app: Any) -> object:
    """Return mock GUI port for integration tests.

    Returns:
        GUI module-like object implementing getDocument().
    """

    class _GuiDocumentAdapter:
        def __init__(self, doc: Any) -> None:
            self._doc = doc

        @property
        def Modified(self) -> bool:
            return False

        def getViewProvider(self, obj: object) -> object | None:
            if hasattr(obj, "ViewObject"):
                return obj.ViewObject
            return None

    class _GuiAdapter:
        def __init__(self, app: Any) -> None:
            self._app = app

        def getDocument(self, doc_name: str) -> _GuiDocumentAdapter | None:
            doc = self._app.getDocument(doc_name)
            if doc is None:
                return None
            return _GuiDocumentAdapter(doc)

    return _GuiAdapter(freecad_app)


@pytest.fixture
def freecad_context(freecad_app: Any, freecad_gui: Any) -> FreeCadContext:
    """Create a FreeCAD runtime context for testing.

    Args:
        freecad_app: FreeCAD application module.

    Returns:
        FreeCadContext instance.
    """
    from freecad.diff_wb.domain.freecad_ports import FreeCadContext

    return FreeCadContext(app=freecad_app, gui=freecad_gui)


@pytest.fixture
def temp_document(freecad_app: Any) -> object:
    """Create and yield a fresh FreeCAD document, cleaning up after test.

    Usage:
        def test_something(temp_document):
            doc = temp_document
            # ... do work ...

    Args:
        freecad_app: FreeCAD application module.

    Yields:
        FreeCAD document object.
    """
    doc_name = f"TestDoc_{id(temp_document)}"
    doc = freecad_app.newDocument(doc_name)
    yield doc
    freecad_app.closeDocument(doc.Name)


@pytest.fixture
def initialized_workbench(project_root: Path) -> Any:
    """Initialize the Diff Workbench and return the workbench instance.

    This fixture:
    1. Adds project to sys.path (after Gui imports Mod dirs)
    2. Removes any cached workbench modules
    3. Initializes the application container
    4. Imports and registers the workbench
    5. Returns the workbench instance

    Usage:
        def test_workbench_behavior(initialized_workbench):
            wb = initialized_workbench
            # ... test workbench behavior ...

    Args:
        project_root: Project root directory.

    Returns:
        DiffWorkbench instance.

    Raises:
        pytest.skip: If FreeCADGui.Workbench is not available (headless mode).
    """
    Gui = sys.modules.get("FreeCADGui")
    if Gui is None:
        pytest.skip("FreeCADGui module not loaded - cannot initialize workbench")

    # Check if full GUI is available (Gui.Workbench must exist)
    # Note: Gui.Workbench is only available when FreeCAD runs with a real display
    # Xvfb/offscreen mode doesn't provide it - this is a FreeCAD limitation
    if not hasattr(Gui, "Workbench"):
        pytest.skip("Gui.Workbench requires real display (not available in offscreen/Xvfb mode)")

    # Remove any cached diff_wb modules to force reload
    mods_to_remove = [k for k in list(sys.modules.keys()) if "diff_wb" in k]
    for mod in mods_to_remove:
        del sys.modules[mod]

    # Now insert project root at the VERY beginning (before Mod paths)
    project_path = str(project_root)
    if project_path in sys.path:
        sys.path.remove(project_path)
    sys.path.insert(0, project_path)

    # Import and initialize
    from freecad.diff_wb.application.di.container import create_application_container
    from freecad.diff_wb.domain.snapshots import InMemorySnapshotRepository
    from freecad.diff_wb.entrypoints.workbench import DiffWorkbench
    from freecad.diff_wb.infrastructure.freecad.ports import get_freecad_runtime_context

    # Create container (diff_view=None for now)
    ctx = get_freecad_runtime_context()
    snapshot_repo = InMemorySnapshotRepository()
    container = create_application_container(
        ctx=ctx,
        snapshot_repo=snapshot_repo,
        diff_view=None,
    )

    # Set container before importing workbench
    from freecad.diff_wb import _container as container_module

    container_module.set_container(container)

    # Create workbench instance
    wb = DiffWorkbench()  # type: ignore[no-untyped-call]

    return wb
