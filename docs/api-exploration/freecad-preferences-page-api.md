# FreeCAD preferences page API exploration

## Verification baseline
- FreeCAD source/runtime revision used for verification: `adf77600e2526bf02804524f0d1991ab1c534abe`
- Build/version context: `1.1.0` dev snapshot `20260223` (`HEAD detached at adf7760`)
- Verification date: 2026-04-24

## Scope
- `FreeCADGui.addPreferencePage(path_or_class, group)` registration contract
- Python callback lifecycle: `loadSettings()` and `saveSettings()`
- Persistence assumptions for `Gui::PrefRadioButton` and `Gui::PrefTextEdit`

## Verified contracts

<a id="check-addpreferencepage-contract"></a>
### 1) `addPreferencePage(class, group)` usage contract

Verified from FreeCAD source (`src/Gui/ApplicationPy.cpp`):

- Python API supports both signatures:
  - `addPreferencePage(path, group) -> None`
  - `addPreferencePage(dialog, group) -> None`
- `dialog` form is parsed as a Python type (`PyType_Type`), then wrapped through `PrefPagePyProducer`.

Example shape:

```python
import FreeCADGui as Gui

class MyPrefsPage:
    def __init__(self):
        self.form = ...  # QWidget

Gui.addPreferencePage(MyPrefsPage, "Diff")
```

<a id="check-callback-lifecycle"></a>
### 2) `loadSettings()` / `saveSettings()` callback timing contract

Verified from FreeCAD source:

- `DlgPreferencesImp::createPageInGroup(...)` calls `page->loadSettings()` during page creation.
- `DlgPreferencesImp::applyChanges()` calls `page->saveSettings()` for every preference page when user applies/accepts Preferences.
- Python bridge implementation (`PreferencePagePython`) calls Python methods only when present:
  - `loadSettings()` if `hasAttr("loadSettings")`
  - `saveSettings()` if `hasAttr("saveSettings")`

Implication for Diff workbench page:

- `loadSettings()` should be idempotent and safe to call on page creation/reload.
- `saveSettings()` should be authoritative for persisting widget state.

<a id="check-pref-widgets-persistence"></a>
### 3) `Gui::PrefRadioButton` / `Gui::PrefTextEdit` persistence assumptions

Verified from FreeCAD source (`src/Gui/PrefWidgets.cpp` and `src/Gui/Dialogs/DlgPreferencesImp.h`):

- `PrefRadioButton`:
  - restore: `GetBool(entryName(), isChecked())`
  - save: `SetBool(entryName(), isChecked())`
- `PrefTextEdit`:
  - restore: `GetASCII(entryName(), toPlainText())`
  - save: `SetASCII(entryName(), toPlainText())`
- Persistence depends on `prefEntry` + `prefPath` being configured, and `onRestore()` / `onSave()` being called (usually inside page `loadSettings()` / `saveSettings()`).

Implication for this task:

- Radio mode flags map naturally to bool storage.
- Multiline custom lists map naturally to text storage (ASCII string payload in ParamGet).

Encoding note:

- `PrefTextEdit` currently persists through ASCII-oriented ParamGet calls (`GetASCII`/`SetASCII`).
- Non-ASCII input behavior is not guaranteed by this exploration and should be explicitly validated before accepting non-ASCII preference values.

## Registration location + non-duplication strategy

Confirmed registration point: `HistoryWorkbench.Initialize` in `freecad/history_wb/entrypoints/workbench.py`.

Registration strategy:

- Register preference page in `Initialize()` (first activation lifecycle hook for workbench wiring).
- Guard registration with an explicit one-time flag on the workbench class to prevent duplicate page registration when module reload/tests instantiate more than once.

Planned guard shape:

```python
if not self.__class__._preferences_page_registered:
    Gui.addPreferencePage(DiffSettingsPreferencesPage, "Diff")
    self.__class__._preferences_page_registered = True
```

## Evidence references
- FreeCAD source: `src/Gui/ApplicationPy.cpp` (`addPreferencePage` overloads and producer wiring)
- FreeCAD source: `src/Gui/WidgetFactory.cpp` (`PrefPagePyProducer`, `PreferencePagePython`, optional `.form`, callback invocation)
- FreeCAD source: `src/Gui/Dialogs/DlgPreferencesImp.cpp` (`loadSettings()` during page creation; `saveSettings()` during apply)
- FreeCAD source: `src/Gui/PrefWidgets.cpp` (`PrefRadioButton` bool persistence; `PrefTextEdit` text persistence)
