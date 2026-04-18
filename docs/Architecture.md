# Architecture: Layered Architecture with DDD Principles

## Overview

The Diff Workbench uses a **layered architecture** with Domain-Driven Design (DDD) principles. The architecture enforces clear separation of concerns through distinct layers and dependency inversion via ports/interfaces.

### Architectural Style

**Hybrid Approach**: Layered architecture with hexagonal (ports & adapters) principles
- **Layered**: Clear vertical separation (UI → Application → Domain → Infrastructure)
- **Hexagonal**: Domain defines interfaces (ports), infrastructure implements them (adapters)
- **DDD**: Rich domain models organized by workbench capabilities

### Key Principles

1. **Dependency Rule**: Dependencies point inward. Outer layers (UI, Infrastructure) depend on inner layers (Domain), never the reverse.

2. **Single Responsibility**: Each module has one clear responsibility aligned with domain concepts.

3. **Testability**: Domain layer is pure Python with no external dependencies. Infrastructure adapters can be swapped with fakes for testing.

4. **Explicit Public APIs**: Each module uses `__all__` to define its public interface. Internal helpers use `_prefix` convention.

5. **Lazy Initialization**: Container and commands created on first workbench activation, not at FreeCAD startup.

---

## Frontend/Backend Analogy

Understanding the layer structure becomes intuitive when viewed through the familiar lens of frontend and backend development:

### Backend (Domain + Application Layers)

The **Domain** and **Application** layers together form the backend of this workbench:

| Backend Concept          | Diff Workbench Implementation |
|--------------------------|-------------------------------|
| **Business Logic**       | Domain layer - pure Python entities, services, and algorithms |
| **API Endpoints**        | Application layer - stateless actions that execute and return results |
| **Database**             | Infrastructure layer - adapters for FreeCAD API and persistence |
| **Inversion of Control** | ApplicationContainer - wires dependencies, provides action access |

The Application layer acts as a stateless API. When a command executes (e.g., "take snapshot"), the action performs the operation and returns a result. No state is stored between calls.

### Frontend (UI Layer)

The **UI layer** mirrors a frontend JavaScript application:

| Frontend Concept | Diff Workbench Implementation |
|------------------|-------------------------------|
| **State Store** | UIState - holds GitRepository, lives alongside presenters |
| **Components** | Presenters - transform domain data into view calls |
| **Views/Rendered Output** | Qt widgets - actual FreeCAD UI panels |
| **Component State** | Ephemeral presenter state (loading flags, etc.) |

The UI layer holds frontend-only state (UIState) and transforms backend results into user-visible content.

---

## Layer Definitions

### Entry Points (`entrypoints/`)

**Responsibility**: FreeCAD workbench lifecycle and command registration. Thin wrappers that wire FreeCAD API to application layer.

**Characteristics**:
- Contains `workbench.py` and `commands.py`
- `workbench.py`: Implements FreeCAD lifecycle methods (`Initialize`, `Activated`, `Deactivated`)
- Commands registered in `Initialize()` (called once on first activation)
- Commands access container via `get_container()` at execution time
- No business logic - delegates to application layer

**Structure** (`freecad/diff_wb/entrypoints/`):
```
entrypoints/
├── __init__.py
├── workbench.py                   # DiffWorkbench class
└── commands.py                    # Command definitions
```

---

### 1. Domain Layer (`domain/`)

**Responsibility**: Core workbench logic and concepts. Pure Python with NO external dependencies.

**Characteristics**:
- Contains workbench rules, entities, and value objects
- Defines repository interfaces (ports) but doesn't implement them
- Can be tested without FreeCAD or any external system
- No imports from `infrastructure/`, `application/`, or `ui/`

**Structure** (`freecad/diff_wb/domain/`):
```
domain/
├── tree/                          # Shared tree models
│   ├── __init__.py               # __all__ = ["TreeNode", "Property", "Vector", ...]
│   ├── node.py                   # TreeNode dataclass
│   └── property.py               # Property, Vector, Rotation, Placement dataclasses
│
├── snapshots/                     # Snapshot domain concept
│   ├── __init__.py               # __all__ = ["Snapshot", "SnapshotRepository"]
│   ├── models.py                 # Snapshot dataclass
│   ├── extractor.py              # Tree extraction logic (uses FreeCAD port)
│   └── repository.py             # SnapshotRepository protocol + InMemory implementation
│
├── diff/                          # Diff domain concept
│   ├── __init__.py               # __all__ = ["DiffResult", "NodeDiff", "PropertyDiff"]
│   ├── models.py                 # DiffResult, NodeDiff, PropertyDiff, DiffState
│   ├── engine.py                 # DiffEngine orchestration (uses SettingsRepository)
│   └── comparator.py             # TreeComparator, PropertyComparator algorithms
│
├── settings/                      # Settings domain concept
│   ├── __init__.py               # __all__ = ["Settings", "SettingsRepository"]
│   ├── models.py                 # Settings dataclass (excluded_types, excluded_properties)
│   └── repository.py             # SettingsRepository protocol
│
└── logging/                       # Logging domain concept
    ├── __init__.py               # __all__ = ["Logger"]
    └── logger.py                 # Logger protocol
```

**Key Interfaces (Ports)**:
- `SnapshotRepository` - Interface for snapshot storage operations
- `SettingsRepository` - Interface for settings access
- `Logger` - Interface for logging operations

### 2. Application Layer (`application/`)

**Responsibility**: Stateless API endpoints (actions/queries) that coordinate domain objects to perform workbench operations. Like a backend API, it executes operations and returns results without storing state between calls.

**Characteristics**:
- Contains stateless actions (use cases)
- Each action receives dependencies via constructor, executes, returns result
- No state stored in the container between operations
- Depends on domain layer only

**Structure** (`freecad/diff_wb/application/`):
```
application/
├── __init__.py
├── actions/                       # Use cases / commands (stateless)
│   ├── commands/
│   │   ├── take_snapshot.py      # TakeSnapshot action
│   │   └── compare_snapshots.py  # CompareSnapshots action
│   ├── queries/
│   │   └── list_snapshots.py     # ListSnapshots query
│   └── __init__.py
├── di/                            # Dependency injection
│   ├── container.py              # ApplicationContainer (stateless factory)
│   └── ports_factory.py          # Port creation
└── presenters/                    # Application presenters
    └── presentation_models.py    # Result dataclasses
```

**Container as Stateless API Factory**:

The `ApplicationContainer` acts as a factory for backend API endpoints. It wires dependencies once at startup and provides action access:

```python
# Container provides action access (like API router)
container = get_container()
result = container.take_snapshot_action.execute()  # Stateless call
```

The container does NOT hold state. Each action is stateless and reusable.

### 3. UI Layer (`ui/`)

**Responsibility**: User interface components (presenters, views, UIState). Like a frontend application, it transforms backend API results into user-visible content and holds frontend-only state.

**Characteristics**:
- Contains presenters, view protocols, and Qt widgets
- Holds UIState (frontend-only state like GitRepository)
- Presenters transform application action results into view protocol calls
- Views are Qt widgets that render the UI
- Depends on application layer for behavior (executes actions)

**Structure** (`freecad/diff_wb/ui/`):
```
ui/
├── __init__.py
├── presenters/                    # Presenters (transform data for views)
│   ├── __init__.py
│   ├── state.py                  # UIState - frontend state store
│   ├── diff_presenter.py         # DiffPresenter - transforms DiffResult
│   ├── snapshot_presenter.py     # SnapshotPresenter - formats results
│   └── git_repository_presenter.py # GitRepositoryPresenter
├── protocols/                     # View interfaces (ports)
│   ├── diff_view.py              # DiffView protocol
│   └── snapshot_view.py          # SnapshotView protocol
└── views/                         # Qt view implementations
    └── diff_panel.py             # Qt widget (two-column diff view)
```

**Frontend/Backend Flow**:

```
UI Layer (Frontend)                 Application Layer (Backend API)
─────────────────                   ─────────────────────────────
Presenter                           Action (stateless)
    │ execute()                         │
    └──────────────────────────────────►│
                                         │ use
                                         ▼
                                    Domain Layer
                                         │
                                    returns result
                                         │
UIState ◄── transform ──────────────────┘
    │
    ▼
View Protocol ──► Qt Widget (rendered output)
```

**UIState**: Holds frontend-only state (e.g., detected GitRepository). Created by the UI composer at startup, lives alongside presenters. Not accessible to domain or application layers.

### 4. Infrastructure Layer (`infrastructure/`)

**Responsibility**: External dependencies and implementations. Adapts external systems to domain interfaces.

**Characteristics**:
- Contains adapters implementing domain ports
- FreeCAD API integration
- File I/O, database access, network calls
- Can depend on any inner layer

**Structure** (`freecad/diff_wb/infrastructure/`):
```
infrastructure/
├── __init__.py
├── freecad/                       # FreeCAD integration
│   ├── __init__.py
│   ├── ports.py                   # ALL port protocols, adapters, factories
│   ├── settings_repo.py           # SettingsRepository implementation
│   └── logger.py                  # Logger implementation (FreeCAD Console)
│
└── persistence/                   # Data persistence
    ├── __init__.py
    └── snapshot_repo.py           # SnapshotRepository implementations
```

---

## Dependency Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Entry Points                              │
│              (workbench.py, commands.py)                     │
└───────────────────────┬─────────────────────────────────────┘
                         │ uses
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (UI Layer)                                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ UIState (frontend state store)                      │    │
│  │ Presenters (transform data)                         │    │
│  │ Views (Qt widgets)                                  │    │
│  └─────────────────────────────────────────────────────┘    │
└───────────────────────┬─────────────────────────────────────┘
                         │ executes actions
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  BACKEND API (Application Layer)                             │
│  ApplicationContainer (stateless factory)                    │
│  Actions (stateless use cases)                               │
└───────────────────────┬─────────────────────────────────────┘
                         │ uses
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Domain Layer                            │
│   (models, services, repository interfaces - workbench logic) │
│                                                              │
│   domain/tree/       ← Shared foundational models           │
│   domain/snapshots/  ← Snapshot workbench concepts          │
│   domain/diff/       ← Diff workbench concepts              │
│   domain/settings/   ← Settings workbench concepts          │
│   domain/logging/    ← Logging interface                    │
└───────────────────────┬─────────────────────────────────────┘
                         │ depends on interfaces (ports)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                       │
│    (adapters, implementations - external systems)            │
│                                                              │
│   infrastructure/freecad/    ← FreeCAD API adapter          │
│   infrastructure/persistence/← Storage adapter              │
└─────────────────────────────────────────────────────────────┘
```

**Key Rule**: Arrows point in the direction of dependencies. Inner layers have NO knowledge of outer layers. UIState lives in the frontend (UI layer) only.

---

## Module Boundaries and Public APIs

### `__all__` Convention

Every `__init__.py` explicitly exports public API to define clear module boundaries:

```python
# domain/snapshots/__init__.py
"""Snapshot domain module."""

from .models import Snapshot
from .repository import SnapshotRepository, InMemorySnapshotRepository

__all__ = ["Snapshot", "SnapshotRepository", "InMemorySnapshotRepository"]
```

Usage:
```python
# Public API (recommended)
from freecad.diff_wb.domain.snapshots import Snapshot, SnapshotRepository

# Internal access (allowed for testing, but signals "not for production use")
from freecad.diff_wb.domain.snapshots.extractor import _internal_helper
```

### Internal vs Public

| Naming | Visibility | Use Case |
|--------|-----------|----------|
| `public_name` | Public | Part of module's API, documented |
| `_internal_name` | Internal | Implementation detail, not for external use |
| `__private_name` | Private | Name-mangled, avoid in favor of `_prefix` |

---

## Classes vs Functions

Use both appropriately based on the use case:

### Use **Classes/Dataclasses** for:

- **Domain models/entities** (data containers with minimal behavior)
  - `TreeNode`, `Snapshot`, `Property`, `Vector`
  - `DiffResult`, `NodeDiff`, `PropertyDiff`
  - `Settings`, `SnapshotMetadata`

- **Interfaces/Protocols** (abstract contracts)
  - `SnapshotRepository`, `SettingsRepository`, `Logger`

- **Implementations with state**
   - `InMemorySnapshotRepository` (has `_snapshots` dict)
   - `FreeCADLogger` (wraps FreeCadPort, infrastructure layer)
   - `DiffEngine` (coordinates services via injected dependencies)

### Use **Functions** for:

- **Pure algorithms** (no state, deterministic)
  - `build_path_index()`, `compare_nodes_by_path()`
  - `compare_properties()`, `values_are_equal()`
  - `filter_snapshot()`, `reconstruct_hierarchy()`

- **Use cases / entry points**
  - `extract_tree()`, `create_snapshot()`
  - `compute_diff()` (when not wrapped in a class)

- **Helper utilities**
  - `should_exclude_property()`, `get_default_store()`

### Guidelines

| Aspect | Classes | Functions |
|--------|---------|-----------|
| **Data modeling** | ✅ Excellent (dataclasses) | ❌ Not suitable |
| **State management** | ✅ Natural (instance vars) | ❌ Requires globals/closures |
| **Algorithms** | ❌ Overkill | ✅ Perfect fit |
| **Testing** | ✅ Easy (mock instances) | ✅ Easier (pure functions) |
| **Composition** | ⚠️ Can be verbose | ✅ Simple |
| **Pythonic** | ✅ For data/entities | ✅ For logic/utilities |

---

## Dependency Injection

Dependencies are injected at composition root (entrypoints) rather than created internally. This enables:

1. **Testability**: Swap real implementations with fakes/mocks
2. **Flexibility**: Change implementations without modifying domain code
3. **Explicitness**: Dependencies are visible in constructors/function signatures

### Pattern

```python
# Domain service accepts interfaces via constructor
class DiffEngine:
    def __init__(self, settings_repo: SettingsRepository):
        self._settings_repo = settings_repo  # Injected dependency
    
    def compute_diff(self, old: Snapshot, new: Snapshot) -> DiffResult:
        settings = self._settings_repo.get_settings()
        # ... use settings
```



---

## Container and Context Usage Rules

The Diff Workbench uses a hand-made IoC (Inversion of Control) container to wire dependencies at startup. This ensures the domain and application layers remain testable without FreeCAD dependencies.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ ENTRY POINTS (workbench.py, commands.py)                           │
│   → Initialize(): create container, register commands              │
│   → Commands: get_container() at execution                         │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ BACKEND API FACTORY (application/di/container.py)                  │
│   → Stateless factory - creates actions and ports                  │
│   → set_container()/get_container() for global access              │
│   → Does NOT hold UIState (that lives in UI layer)                 │
└────────────────────────┬────────────────────────────────────────────┘
                         │ injects into
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER (actions, queries) - BACKEND API                 │
│   → Receives ports via constructor                                 │
│   → Stateless - execute() returns result, no state stored          │
│   → NEVER imports CTX, container, or port factories                │
└────────────────────────┬────────────────────────────────────────────┘
                         │ uses
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ DOMAIN LAYER (services, extractors)                                │
│   → Defines port protocols (interfaces)                            │
│   → Receives port implementations via constructor                  │
│   → Testable with fakes - no FreeCAD needed                        │
└─────────────────────────────────────────────────────────────────────┘

All layers use centralized logging: `from utils import Log`
```

### Composition Root

The composition root is `workbench.Initialize()`, called once on first activation:

```python
# workbench.Initialize()
from ..utils import set_logger
from ..infrastructure.freecad import FreeCADLogger

ctx = get_freecad_runtime_context()
container = create_application_container(ctx)
set_logger(FreeCADLogger(ctx))  # Wire centralized logger
set_container(container)
register_commands(container)
```

`init_gui.py` is ultra-thin: translation setup, runtime context, workbench registration only.

### Container Responsibilities

The container (`application/di/container.py`) is a stateless factory that creates ports and wires actions. It provides `set_container()`/`get_container()` for global access. Logging goes through `utils.Log` (centralized), not container helpers.

**What the container does NOT do:**
- Does NOT hold UIState (that belongs to the UI layer)
- Does NOT store state between action executions
- Does NOT create presenters directly (that happens in the UI composer)

**What the container does:**
- Creates infrastructure ports (FreeCAD API adapters)
- Wires actions with their dependencies
- Provides action access to entry points

### Layer Access Rules

| Layer | Container | CTX | Port Factories | Logging | UIState |
|-------|-----------|-----|----------------|---------|---------|
| **Domain** | ❌ | ❌ | ❌ | ✅ Log.*() | ❌ |
| **Application** | ❌ | ❌ | ❌ | ✅ Log.*() | ❌ |
| **UI** | ❌ | ❌ | ❌ | ✅ Log.*() | ✅ (created here) |
| **Infrastructure** | ✅ | ✅ | ✅ | ✅ Log.*() | ❌ |
| **Entry Points** | get_container() | ❌ | ❌ | ✅ Log.*() | ❌ |

### Consolidated Ports

All port protocols, adapters, and factories live in `infrastructure/freecad/ports.py`. Factory functions require explicit `FreeCadContext` parameter - no automatic context creation.

### Access Patterns

Commands access container via `get_container()` at execution:

```python
from freecad.diff_wb._container import get_container
from freecad.diff_wb.utils import Log

def Activated(self):
    container = get_container()
    container.take_snapshot_action.execute()
    Log.info("Snapshot completed")
```

Translation uses Qt's `QCoreApplication.translate()` in views.

### Testing with Fakes

Domain code is fully testable using fakes - no FreeCAD, container, or logger needed:

```python
# Unit test
fake_port = FakeFreeCadPort()
extractor = SnapshotExtractor(freecad_port=fake_port)
result = extractor.extract_tree()
```

Set `set_logger(FakeLogger())` in tests to capture log output.

### UI Layer Translation

Translation happens in views via `QCoreApplication.translate()`. Presenters pass raw data; views handle translation and parameter substitution using Qt-style placeholders (`%1`, `%2`). See `ui/translation_strings.py` for templates.

---

## Testing Strategy

### Unit Tests (No FreeCAD)

**Location**: `tests/unit/`

**Coverage**:
- Domain models and services
- Repository interfaces (with fakes)
- Diff algorithms
- Tree extraction logic
- Application actions and queries
- Presenters
- Entry point commands

**Characteristics**:
- Pure Python, no FreeCAD imports
- Fast execution (< 1 second total)
- Use inline fixtures or fakes from `tests/fakes/`

### Integration Tests (With FreeCAD)

**Location**: `tests/integration/`

**Coverage**:
- Infrastructure adapters
- FreeCAD context handling
- Full end-to-end workflows
- Workbench loading and activation
- UI widgets with FreeCAD runtime

**Characteristics**:
- Requires FreeCAD runtime via `run_with_freecad.sh`
- Slower execution
- Test real FreeCAD API interactions

### Unit Tests vs Integration Tests

**Unit Tests** (`tests/unit/`):
- Focus: Error handling paths, input validation, orchestration logic
- Dependencies: Fakes and mocks only
- Examples: No document error, snapshot not found, extraction failures, command routing

**Integration Tests** (`tests/integration/`):
- Focus: Happy path with real domain services, end-to-end workflows
- Dependencies: Real services (DiffEngine, SnapshotExtractor) + fake ports
- Examples: Successful snapshot creation, complex diff scenarios, exclusion rules, workbench lifecycle

**Principle**: Unit tests provide fast feedback for common errors; integration tests verify real services work together correctly.

---

## Testing Directory Structure

Tests use **strict mirroring** of source structure:

```
tests/
├── unit/          ← mirrors freecad/diff_wb/ (domain, application, ui, infrastructure)
├── integration/   ← FreeCAD runtime tests (workbench, application actions)
├── fakes/         ← fake implementations for dependency injection
└── conftest.py    ← pytest fixtures
```

**Running Tests**:
- Unit tests: `task test`
- Integration tests: `task test:integration`

---

## Configuration Management

### Hard-coded Defaults (Phase 1)

Configuration defaults are stored in `config.py` at project root. These are used by `FreeCADSettingsRepository` as initial values.

### FreeCAD Preferences (Phase 2+)

Eventually, settings will be persisted via FreeCAD's Parameter system, readable/writable through `SettingsRepository`.

---

## Glossary

| Term | Definition |
|------|------------|
| **Domain** | Core workbench logic and concepts |
| **Port** | Interface defined in domain layer (e.g., `SnapshotRepository`) |
| **Adapter** | Implementation of a port in infrastructure layer (e.g., `InMemorySnapshotRepository`) |
| **Use Case / Action** | Stateless application-level operation (e.g., "TakeSnapshot") that executes and returns a result |
| **Entity** | Domain object with identity (e.g., `Snapshot`, `TreeNode`) |
| **Value Object** | Immutable object defined by its attributes (e.g., `Property`, `Vector`) |
| **Composition Root** | Location where dependencies are wired together (entrypoints) |
| **UIState** | Frontend-only state store held in the UI layer (e.g., GitRepository), analogous to Redux/Pinia store |
| **Presenter** | UI component that transforms domain/application data into view calls, analogous to React component |
