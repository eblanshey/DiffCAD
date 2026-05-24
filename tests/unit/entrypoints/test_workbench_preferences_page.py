# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for workbench preference page registration behavior.
"""Tests for HistoryWorkbench preferences page registration."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock


class _FakeWorkbenchBase:
    def appendToolbar(self, _name: str, _tools: list[str]) -> None:
        return None

    def appendMenu(self, _name: str, _tools: list[str]) -> None:
        return None


def test_workbench_initializes_and_registers_preference_page_once(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_gui = ModuleType("FreeCADGui")
    fake_gui.Workbench = _FakeWorkbenchBase
    fake_gui.addPreferencePage = Mock()
    fake_gui.getMainWindow = Mock(return_value=None)

    fake_app = ModuleType("FreeCAD")
    fake_app.Qt = SimpleNamespace(QT_TRANSLATE_NOOP=lambda _ctx, text: text)

    monkeypatch.setitem(sys.modules, "FreeCADGui", fake_gui)
    monkeypatch.setitem(sys.modules, "FreeCAD", fake_app)

    workbench_module = importlib.import_module("freecad.history_wb.entrypoints.workbench")
    workbench_module = importlib.reload(workbench_module)

    monkeypatch.setattr(
        "freecad.history_wb.infrastructure.freecad.ports.get_freecad_runtime_context",
        lambda: SimpleNamespace(app=fake_app),
    )
    fake_container = SimpleNamespace(
        _freecad_port=SimpleNamespace(message=lambda _msg: None),
        get_diff_settings_action=Mock(),
        save_diff_settings_action=Mock(),
    )
    monkeypatch.setattr(
        "freecad.history_wb.application.di.container.create_application_container",
        lambda _ctx: fake_container,
    )
    monkeypatch.setattr("freecad.history_wb._container.set_container", lambda _container: None)
    monkeypatch.setattr("freecad.history_wb.entrypoints.commands.register_commands", lambda: None)
    monkeypatch.setattr(workbench_module, "set_logger", lambda _logger: None)

    workbench_module.HistoryWorkbench._preferences_page_registered = False
    workbench = workbench_module.HistoryWorkbench()

    workbench.Activated()
    workbench.Activated()

    assert fake_gui.addPreferencePage.call_count == 1
    call_args = fake_gui.addPreferencePage.call_args[0]
    assert call_args[0].__name__ == "DiffSettingsPreferencesPage"
    assert call_args[1] == "History"


def test_preference_registration_is_idempotent_across_module_reload(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_gui = ModuleType("FreeCADGui")
    fake_gui.Workbench = _FakeWorkbenchBase
    fake_gui.addPreferencePage = Mock()
    fake_gui.getMainWindow = Mock(return_value=None)

    fake_app = ModuleType("FreeCAD")
    fake_app.Qt = SimpleNamespace(QT_TRANSLATE_NOOP=lambda _ctx, text: text)

    monkeypatch.setitem(sys.modules, "FreeCADGui", fake_gui)
    monkeypatch.setitem(sys.modules, "FreeCAD", fake_app)

    def _patch_runtime() -> None:
        monkeypatch.setattr(
            "freecad.history_wb.infrastructure.freecad.ports.get_freecad_runtime_context",
            lambda: SimpleNamespace(app=fake_app),
        )
        fake_container = SimpleNamespace(
            _freecad_port=SimpleNamespace(message=lambda _msg: None),
            get_diff_settings_action=Mock(),
            save_diff_settings_action=Mock(),
        )
        monkeypatch.setattr(
            "freecad.history_wb.application.di.container.create_application_container",
            lambda _ctx: fake_container,
        )
        monkeypatch.setattr("freecad.history_wb._container.set_container", lambda _container: None)
        monkeypatch.setattr("freecad.history_wb.entrypoints.commands.register_commands", lambda: None)

    workbench_module = importlib.import_module("freecad.history_wb.entrypoints.workbench")
    workbench_module = importlib.reload(workbench_module)
    _patch_runtime()
    monkeypatch.setattr(workbench_module, "set_logger", lambda _logger: None)

    first_workbench = workbench_module.HistoryWorkbench()
    first_workbench.Activated()
    assert fake_gui.addPreferencePage.call_count == 1

    reloaded_module = importlib.reload(workbench_module)
    _patch_runtime()
    monkeypatch.setattr(reloaded_module, "set_logger", lambda _logger: None)

    second_workbench = reloaded_module.HistoryWorkbench()
    second_workbench.Initialize()
    assert fake_gui.addPreferencePage.call_count == 1
