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

---

## Layer Definitions

### 1. Domain Layer (`domain/`)

**Responsibility**: Core workbench logic and concepts. Pure Python with NO external dependencies.

**Characteristics**:
- Contains workbench rules, entities, and value objects
- Defines repository interfaces (ports) but doesn't implement them
- Can be tested without FreeCAD or any external system
- No imports from `infrastructure/`, `application/`, or `ui/`

**Structure**:
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
│   ├── extractor.py              # Tree extraction logic (uses Logger port)
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

**Responsibility**: Use cases, orchestration, and presentation logic. Coordinates domain objects to perform workbench operations and prepares data for UI display.

**Characteristics**:
- Contains application services, controllers, and presenters
- Orchestrates flow between domain services
- Handles transaction boundaries
- Formats domain data for UI consumption
- Depends on domain layer only

**Structure**:
```
application/
├── __init__.py
├── controllers/
│   ├── __init__.py
│   ├── snapshot_controller.py    # TakeSnapshot use case
│   └── compare_controller.py     # CompareSnapshots use case
└── presenters/
    ├── __init__.py
    ├── diff_presenter.py         # Format diff for display
    └── snapshot_presenter.py     # Format snapshots for display
```

### 3. UI Layer (`ui/`)

**Responsibility**: User interface widgets only. Thin Qt views that wire user interactions to application controllers.

**Characteristics**:
- Contains only Qt widgets and UI files
- No workbench logic - delegates to application layer
- Receives formatted data from presenters
- Depends on application layer for behavior

**Structure**:
```
ui/
├── __init__.py
└── diff_panel.py                 # Qt widget (two-column diff view)
```

### 4. Infrastructure Layer (`infrastructure/`)

**Responsibility**: External dependencies and implementations. Adapts external systems to domain interfaces.

**Characteristics**:
- Contains adapters implementing domain ports
- FreeCAD API integration
- File I/O, database access, network calls
- Can depend on any inner layer

**Structure**:
```
infrastructure/
├── __init__.py
├── freecad/                       # FreeCAD integration
│   ├── __init__.py
│   ├── context.py                 # FreeCadContext + FreeCadPort adapter
│   ├── settings_repo.py           # SettingsRepository implementation
│   └── logger.py                  # Logger implementation (FreeCAD Console)
│
├── gui/                           # Qt GUI integration
│   ├── __init__.py
│   └── qt_adapter.py              # GuiPort implementation
│
└── persistence/                   # Data persistence
    ├── __init__.py
    └── snapshot_repo.py           # SnapshotRepository implementations
```

---

## Dependency Flow

```
┌─────────────────────────────────────────────────────────────┐
│                         UI Layer                             │
│                    (Qt widgets only)                         │
└───────────────────────┬─────────────────────────────────────┘
                        │ uses
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│       (controllers, presenters - orchestration & formatting) │
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
│   infrastructure/gui/        ← Qt adapter                   │
│   infrastructure/persistence/← Storage adapter              │
└─────────────────────────────────────────────────────────────┘
```

**Key Rule**: Arrows point in the direction of dependencies. Inner layers have NO knowledge of outer layers.

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
  - `FreeCADLogger` (might have config state later)
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

### Composition Root

At application startup (in `entrypoints/init_gui.py`), wire all dependencies:

1. Create infrastructure adapters (real implementations)
2. Create domain services with injected adapters
3. Create application controllers with injected domain services
4. Register with FreeCAD

This keeps dependency wiring centralized and explicit.

---

## Testing with Fakes

Domain layer is fully testable without FreeCAD by using fake implementations of repository interfaces.

### Fake Implementations

Create simple in-memory implementations for testing:

```python
# tests/unit/fakes/fake_repositories.py
class FakeSnapshotRepository(SnapshotRepository):
    """In-memory snapshot repository for testing."""
    pass

class FakeSettingsRepository(SettingsRepository):
    """Settings repository with hardcoded values for testing."""
    pass

class FakeLogger(Logger):
    """Logger that captures messages for testing."""
    pass
```

### Test Strategy

1. **Unit tests** (`tests/unit/`):
   - Use fakes for all repository interfaces
   - Test domain logic without FreeCAD
   - Fast execution (< 1 second total)

2. **Integration tests** (`tests/integration/`):
   - Use real infrastructure adapters
   - Test FreeCAD API interactions
   - Slower execution, requires FreeCAD runtime

This approach ensures core workbench logic is tested independently from external dependencies.

---

## File Import Paths

### Current → Target Migration

| Current Import | Target Import |
|----------------|---------------|
| `from freecad.diff_wb.domain.snapshot import Snapshot` | `from freecad.diff_wb.domain.snapshots.models import Snapshot` |
| `from freecad.diff_wb.domain.property_value import PropertyValue` | `from freecad.diff_wb.domain.tree.property import Property` |
| `from freecad.diff_wb.diff.diff_result import DiffResult` | `from freecad.diff_wb.domain.diff.models import DiffResult` |
| `from freecad.diff_wb.snapshot.snapshot_store import SnapshotStore` | `from freecad.diff_wb.domain.snapshots.repository import InMemorySnapshotRepository` |
| `from freecad.diff_wb.ports.freecad_port import get_port` | `from freecad.diff_wb.infrastructure.freecad.context import get_port` |
| `from freecad.diff_wb.config import EXCLUDED_TYPES` | `from freecad.diff_wb.domain.settings.models import Settings` (via SettingsRepository) |

---

## Testing Strategy

### Unit Tests (No FreeCAD)

**Location**: `tests/unit/`

**Coverage**:
- Domain models and services
- Repository interfaces (with fakes)
- Diff algorithms
- Tree extraction logic

**Characteristics**:
- Pure Python, no FreeCAD imports
- Fast execution (< 1 second total)
- Use inline fixtures or fakes

### Integration Tests (With FreeCAD)

**Location**: `tests/integration/`

**Coverage**:
- Infrastructure adapters
- FreeCAD context handling
- Full end-to-end workflows

**Characteristics**:
- Requires FreeCAD runtime
- Slower execution
- Test real FreeCAD API interactions

---

## Testing Directory Structure

Tests use **strict mirroring** of source structure:

```
tests/
├── unit/domain/tree/test_node.py      ← mirrors domain/tree/node.py
├── unit/domain/snapshots/test_models.py
├── unit/application/controllers/...
├── unit/infrastructure/freecad/...
├── integration/
├── fakes/
└── conftest.py
```

**Naming**: `test_<module>.py` (pytest standard).

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
| **Use Case** | Application-level operation (e.g., "Compare Snapshots") |
| **Entity** | Domain object with identity (e.g., `Snapshot`, `TreeNode`) |
| **Value Object** | Immutable object defined by its attributes (e.g., `Property`, `Vector`) |
| **Composition Root** | Location where dependencies are wired together (entrypoints) |
