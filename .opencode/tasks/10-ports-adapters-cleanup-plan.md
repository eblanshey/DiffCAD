# Task: Clean Up Ports/Adapters Architecture

## Goal

Refactor the FreeCAD context and port factory architecture to be a clean, hand-made IoC (Inversion of Control) container. Establish clear rules for which layers can access what, ensuring domain and application layers remain testable without FreeCAD dependencies.

## Context

The current architecture has three separate port factories (`get_port()`, `get_app_port()`, `get_gui_port()`) that each independently create a `FreeCadContext` when no context is provided. Entry points (`workbench.py`, `commands.py`, `freecad_version_check.py`) call port factories without passing context, violating dependency injection principles. This makes the architecture unclear and harder to test.

**User requirement:** Domain/application layer should only receive ports as parameters, never import infrastructure directly. The container is a hand-made IoC container that holds context and creates ports at startup.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ ENTRY POINTS (workbench.py, commands.py)                           │
│   → Use _container.log(), _container.translate() helpers only      │
│   → NEVER access CTX, port factories, or create ports              │
└────────────────────────┬────────────────────────────────────────────┘
                         │ access via helpers
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ INIT_GUI.PY (Composition Root)                                      │
│   → Creates CTX ONCE                                                │
│   → Creates container ONCE                                          │
│   → Exposes _container for entry point helpers                     │
└────────────────────────┬────────────────────────────────────────────┘
                         │ creates
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CONTAINER (application/di/container.py)                            │
│   → Creates all ports (once) with CTX                              │
│   → Creates actions/presenters WITH ports injected                 │
│   → Provides helper methods: log(), translate()                    │
│   → Only infrastructure knows about CTX                            │
└────────────────────────┬────────────────────────────────────────────┘
                         │ injects into
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER (actions, queries)                               │
│   → Receives ports via constructor                                 │
│   → NEVER imports CTX, container, or port factories                │
│   → Passes ports to domain services                                │
└────────────────────────┬────────────────────────────────────────────┘
                         │ uses
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ DOMAIN LAYER (services, extractors)                                │
│   → Defines port protocols (interfaces)                            │
│   → Receives port implementations via constructor                  │
│   → NEVER imports infrastructure, CTX, or container                │
│   → Testable with fakes - no FreeCAD needed                        │
└─────────────────────────────────────────────────────────────────────┘
```

## Layer Access Rules

| Layer | Can Access Container | Can Access CTX | Can Access Port Factories | Can Create Ports |
|-------|---------------------|----------------|---------------------------|------------------|
| **Domain** | ❌ Never | ❌ Never | ❌ Never | ❌ Never |
| **Application** | ❌ Never | ❌ Never | ❌ Never | ❌ Never |
| **UI** | ❌ Never | ❌ Never | ❌ Never | ❌ Never |
| **Infrastructure** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Entry Points** | ✅ Helpers only | ❌ Never | ❌ Never | ❌ Never |

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Container stores ports and provides helpers | Entry points need logging/translation but shouldn't know about ports | Let entry points access ports directly (violates architecture) |
| CTX created only in init_gui.py | Single source of truth for FreeCAD context | Allow multiple CTX creations (leads to inconsistency) |
| Port factories require mandatory ctx | Enforces explicit dependency injection | Keep optional ctx with auto-creation (defeats purpose) |
| Container helpers for entry points | Keeps entry points simple, no port factory calls | Pass container to entry points (more complex) |

## Architecture Impact

**Target Directory Structure:**
```
infrastructure/
├── freecad/
│   ├── ports.py              # ALL ports/adapters/factories (NEW - consolidated)
│   └── settings_repo.py      # Settings repository (keeps separate)
└── persistence/
    └── ...
```

**Files Modified:**
- `init_gui.py` - Create container, expose for entry points
- `application/di/container.py` - Store ports, add helper methods
- `infrastructure/freecad/ports.py` - New consolidated file (moved from context.py, app_port.py, qt_adapter.py)
- `infrastructure/freecad/context.py` - Remove (moved to ports.py)
- `infrastructure/freecad/app_port.py` - Remove (moved to ports.py)
- `infrastructure/gui/__init__.py` - Remove (directory deleted)
- `infrastructure/gui/qt_adapter.py` - Remove (moved to ports.py)
- `infrastructure/freecad/settings_repo.py` - Make ctx mandatory, update imports
- `entrypoints/workbench.py` - Use container helpers instead of port factories
- `entrypoints/commands.py` - Use container helpers instead of port factories
- `freecad_version_check.py` - Use container helpers instead of port factories
- `domain/snapshots/extractor.py` - Remove legacy get_port() call
- `docs/Architecture.md` - Document new rules
- `tests/fakes/` - Update imports if needed

**Files Added:**
- `infrastructure/freecad/ports.py` - Consolidated port protocols, adapters, and factories

**Files Deleted:**
- `infrastructure/freecad/context.py` - Moved to ports.py
- `infrastructure/freecad/app_port.py` - Moved to ports.py
- `infrastructure/gui/` directory - Deleted (all content moved to ports.py)

## FreeCAD Dependency

- **No API exploration needed** - Pure refactoring of existing code
- All changes are internal to Python modules
- No FreeCAD API behavior changes

## Implementation Plan

### Phase 1: Consolidate All Ports into Single File

**Goal:** Create `infrastructure/freecad/ports.py` containing all port protocols, adapters, and factory functions. Remove auto-context creation (require ctx as mandatory parameter).

#### Step 1.1: Create `infrastructure/freecad/ports.py`

Create a new file that consolidates:

- `FreeCadContext` dataclass (from context.py)
- `AppLike`, `GuiLike`, `DocumentLike`, `ConsoleLike` protocols (from context.py)
- `FreeCadPort` protocol (from context.py)
- `FreeCadPortAdapter` class (from context.py)
- `get_port(ctx: FreeCadContext)` factory (from context.py)
- `get_freecad_runtime_context()` function (from context.py)
- `AppPort` protocol (from app_port.py)
- `AppPortAdapter` class (from app_port.py)
- `get_app_port(ctx: FreeCadContext)` factory (from app_port.py)
- `GuiPort` protocol (from qt_adapter.py)
- `GuiPortAdapter` class (from qt_adapter.py)
- `get_gui_port(ctx: FreeCadContext)` factory (from qt_adapter.py)

**Requirements:**
- Make ctx a mandatory parameter in all factory functions
- Remove any `if ctx is None: ctx = get_freecad_runtime_context()` blocks
- Add proper docstrings
- Define `__all__` with all public exports

**Structure:**
```python
# infrastructure/freecad/ports.py
"""File responsibility: Consolidated FreeCAD port interfaces and adapters."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol

# Protocols (AppLike, GuiLike, DocumentLike, ConsoleLike, FreeCadPort, AppPort, GuiPort)

# FreeCadContext dataclass

# get_freecad_runtime_context() function

# Adapter classes (FreeCadPortAdapter, AppPortAdapter, GuiPortAdapter)

# Factory functions (get_port, get_app_port, get_gui_port) - all require ctx

__all__ = [
    "FreeCadContext",
    "get_freecad_runtime_context",
    "get_port",
    "get_app_port", 
    "get_gui_port",
    "FreeCadPort",
    "FreeCadPortAdapter",
    "AppPort",
    "AppPortAdapter",
    "GuiPort",
    "GuiPortAdapter",
]
```

- [ ] Run tests to verify no regressions

#### Step 1.2: Update imports in `infrastructure/freecad/settings_repo.py`

- [ ] Remove import of `get_freecad_runtime_context` (now in ports.py)
- [ ] Update import to use: `from .ports import FreeCadContext`
- [ ] Make ctx mandatory in `__init__`
- [ ] Run tests to verify no regressions

#### Step 1.3: Update imports in `application/di/container.py`

- [ ] Update import to use: `from ...infrastructure.freecad.ports import FreeCadContext, get_port`
- [ ] Run tests to verify no regressions

#### Step 1.4: Update imports in `init_gui.py`

- [ ] Update import to use: `from .infrastructure.freecad.ports import get_freecad_runtime_context`
- [ ] Run tests to verify no regressions

---

### Phase 2: Enhance Container with Helper Methods

**Goal:** Container stores all ports and provides helper methods for entry points.

#### Step 2.1: Update `application/di/container.py`

- [ ] Add `_freecad_port: FreeCadPort` field to `ApplicationContainer` dataclass
- [ ] Add `_app_port: AppPort` field to `ApplicationContainer` dataclass
- [ ] Add helper method `def log(self, message: str) -> None:` that calls `self._freecad_port.message(message)`
- [ ] Add helper method `def translate(self, context: str, text: str) -> str:` that calls `self._app_port.translate(context, text)`
- [ ] In `create_application_container()`, store created ports in container fields
- [ ] Run tests to verify no regressions

---

### Phase 3: Update init_gui.py (Composition Root)

**Goal:** Create container once and expose for entry points.

#### Step 3.1: Update `init_gui.py`

- [ ] After creating container, expose it as module-level variable: `global _container; _container = container`
- [ ] Add comment explaining this is the single composition root
- [ ] Ensure `_container` is accessible from entry points
- [ ] Run tests to verify no regressions

---

### Phase 4: Update Entry Points to Use Container Helpers

**Goal:** Entry points use container helpers instead of port factories.

#### Step 4.1: Update `entrypoints/workbench.py`

- [ ] Remove import of `get_port` from infrastructure
- [ ] Add import: `from .. import _container`
- [ ] Change `_translate()` to use `_container.translate(context, text)` instead of `get_port().translate(context, text)`
- [ ] Change all `get_port()` calls to use `_container.log()` or `_container.translate()`
- [ ] Run tests to verify no regressions

#### Step 4.2: Update `entrypoints/commands.py`

- [ ] Remove import of `get_app_port` from infrastructure
- [ ] Add import: `from .. import _container`
- [ ] Change `_translate()` to use `_container.translate(context, text)` instead of `get_app_port().translate(context, text)`
- [ ] Run tests to verify no regressions

#### Step 4.3: Update `freecad_version_check.py`

- [ ] Remove all `get_port()` calls without ctx
- [ ] Add import: `from .init_gui import _container`
- [ ] Replace `get_port()` calls with `_container.log()` or `_container.translate()` as appropriate
- [ ] Run tests to verify no regressions

---

### Phase 5: Delete Old Files

**Goal:** Remove consolidated files and delete gui directory.

#### Step 5.1: Delete old port files

- [ ] Delete `infrastructure/freecad/context.py` (content moved to ports.py)
- [ ] Delete `infrastructure/freecad/app_port.py` (content moved to ports.py)

#### Step 5.2: Delete gui directory

- [ ] Delete `infrastructure/gui/qt_adapter.py`
- [ ] Delete `infrastructure/gui/__init__.py` (if exists)
- [ ] Delete `infrastructure/gui/` directory

#### Step 5.3: Update any remaining imports

- [ ] Search for any remaining imports of old files and update
- [ ] Run tests to verify no regressions

---

### Phase 6: Fix Domain Layer Legacy Code

**Goal:** Remove any domain code that imports infrastructure.

#### Step 6.1: Update `domain/snapshots/extractor.py`

- [ ] Identify and remove legacy `extract_document_tree()` function if it exists (lines ~295-311)
- [ ] This function imports `get_port` from infrastructure - violates architecture
- [ ] Ensure `SnapshotExtractor` class receives `freecad_port` via constructor (not lazy import)
- [ ] Verify no external code depends on removed function
- [ ] Run tests to verify no regressions

---

### Phase 7: Update Architecture Documentation

**Goal:** Document the new architecture rules clearly.

#### Step 7.1: Update `docs/Architecture.md`

Add new section after "Dependency Injection" section:

```markdown
## Container and Context Usage Rules

The Diff Workbench uses a hand-made IoC (Inversion of Control) container to wire dependencies at startup. This ensures the domain and application layers remain testable without FreeCAD dependencies.

### Composition Root

The composition root is `init_gui.py`, which runs once when FreeCAD loads the workbench. It creates:

1. **CTX** - The FreeCadContext (bundles FreeCAD/FreeCADGui modules)
2. **Container** - The ApplicationContainer (creates ports, wires actions/presenters)

```python
# init_gui.py (runs once at FreeCAD startup)
ctx = get_freecad_runtime_context()  # Create CTX once
container = create_application_container(ctx)  # Create container once
```

### Container Responsibilities

The container (`application/di/container.py`) is responsible for:
- Creating all port adapters using CTX
- Creating actions and presenters with ports injected
- Providing helper methods for entry points (log, translate)

The container is a **creation-time** mechanism, not a runtime service locator. After startup, actions are called directly without accessing the container.

### CTX and Container Access Rules

| Layer | Can Access Container | Can Access CTX | Can Access Port Factories |
|-------|---------------------|----------------|---------------------------|
| **Domain** | ❌ Never | ❌ Never | ❌ Never |
| **Application** | ❌ Never | ❌ Never | ❌ Never |
| **UI** | ❌ Never | ❌ Never | ❌ Never |
| **Infrastructure** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Entry Points** | ✅ Helpers only | ❌ Never | ❌ Never |

### Entry Point Helpers

Entry points (`workbench.py`, `commands.py`) can use container helpers without knowing about ports:

```python
# Entry point code
_container.log("Workbench activated")  # Logs to FreeCAD console
_translated = _container.translate("Workbench", "My Text")  # Translates
```

### Domain Testing

Domain code is fully testable using fakes - no FreeCAD or container needed:

```python
# Unit test
fake_port = FakeFreeCadPort()  # In tests/fakes/
extractor = SnapshotExtractor(freecad_port=fake_port)  # Pass fake
result = extractor.extract_tree()
# Domain tested without FreeCAD!
```

- [ ] Add the new "Container and Context Usage Rules" section to Architecture.md
- [ ] Update the Dependency Flow diagram if needed to reflect new architecture
- [ ] Review for clarity and completeness

---

### Phase 8: Verification

Run full test suite and linting.

#### Step 8.1: Run unit tests

- [ ] Execute: `pytest tests/unit/ -v`
- [ ] Verify all tests pass
- [ ] Fix any failures

#### Step 8.2: Run linter

- [ ] Execute: `ruff check freecad/diff_wb/`
- [ ] Fix any linting errors
- [ ] Execute: `ruff format freecad/diff_wb/ --check`
- [ ] Fix any formatting issues

#### Step 8.3: Verify architecture rules

- [ ] No `get_port()`, `get_app_port()`, `get_gui_port()` calls without ctx
- [ ] No `get_freecad_runtime_context()` calls outside init_gui.py
- [ ] No domain layer imports from infrastructure
- [ ] Entry points only use `_container.log()` and `_container.translate()`
- [ ] All ports imported from single location: `infrastructure/freecad/ports.py`

---

## Test Strategy

- **Unit tests**: Existing tests should pass unchanged (they already pass ctx or use fakes)
- **Integration tests**: Verify entry points work with real FreeCAD using `run_with_freecad.sh`

## Key Points for Implementation

1. **All ports in one file** - Consolidate into `infrastructure/freecad/ports.py`
2. **Port factories require ctx** - All three (`get_port`, `get_app_port`, `get_gui_port`) must receive ctx as mandatory parameter
3. **Delete old files** - Remove context.py, app_port.py, and entire gui/ directory
4. **Container stores ports** - Container holds references to created ports
5. **Container provides helpers** - `log()` and `translate()` methods for entry points
6. **Entry points use helpers** - Never call port factories directly
7. **Domain receives ports** - Via constructor injection, never imports infrastructure
8. **CTX only in init_gui.py** - Single source of truth for context creation

## Findings & Notes

**What gets consolidated into `ports.py`:**
- `FreeCadContext` dataclass
- Protocol classes: `AppLike`, `GuiLike`, `DocumentLike`, `ConsoleLike`
- Port protocols: `FreeCadPort`, `AppPort`, `GuiPort`
- Adapter classes: `FreeCadPortAdapter`, `AppPortAdapter`, `GuiPortAdapter`
- Factory functions: `get_freecad_runtime_context()`, `get_port()`, `get_app_port()`, `get_gui_port()`

**What stays separate:**
- `infrastructure/freecad/settings_repo.py` - Different responsibility (settings)
- `infrastructure/persistence/` - Different responsibility (storage)

**Entry points to update:**
1. `workbench.py` - Uses `get_port()` for logging/translate
2. `commands.py` - Uses `get_app_port()` for translate
3. `freecad_version_check.py` - Uses `get_port()` for logging/warning

**Legacy code to remove:**
- `domain/snapshots/extractor.py` may have `extract_document_tree()` that imports `get_port`
