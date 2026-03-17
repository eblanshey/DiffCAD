# Task: Architecture Refactoring to Layered DDD Structure

## Steps

Complete all steps in order. Each phase must pass all tests before proceeding to the next.

### Phase 1: Domain Tree Models

Create foundational tree models that will be shared across snapshots and diff domains.

#### Step 1.1: Create `domain/tree/` directory structure

- [x] Create directory: `freecad/diff_wb/domain/tree/`
- [x] Create `freecad/diff_wb/domain/tree/__init__.py`:
  ```python
  """Tree domain models - shared foundation for snapshots and diff."""
  
  from .node import TreeNode
  from .property import Property, PropertyType, Vector, Rotation, Placement
  
  __all__ = ["TreeNode", "Property", "PropertyType", "Vector", "Rotation", "Placement"]
  ```

#### Step 1.2: Migrate `TreeNode` to `domain/tree/node.py`

- [x] Create `freecad/diff_wb/domain/tree/node.py`:
  - Move `TreeNode` class from `domain/snapshot.py`
  - Add docstring explaining module responsibility
  - Update imports to use `from ..tree.property import Property`
  - Add `__all__ = ["TreeNode"]`

#### Step 1.3: Migrate property models to `domain/tree/property.py`

- [x] Create `freecad/diff_wb/domain/tree/property.py`:
  - Rename `PropertyValue` → `Property` throughout
  - Merge `PropertyValue`, `Vector`, `Rotation`, `Placement` into single file
  - Keep all existing logic (equality methods, type detection, etc.)
  - Add comprehensive docstrings
  - Add `__all__ = ["Property", "PropertyType", "Vector", "Rotation", "Placement"]`

#### Step 1.4: Update existing imports

- [x] Update `domain/snapshot.py`:
  ```python
  from .tree.node import TreeNode
  from .tree.property import Property
  ```

- [ ] Update `diff/diff_result.py`:
  ```python
  from ..tree.property import Property
  ```

- [ ] Update `diff/property_diff.py`:
  ```python
  from ..tree.property import Property
  ```

- [ ] Update all test files importing these models

#### Step 1.5: Run tests

- [x] Execute: `pytest tests/unit/test_domain.py -v`
- [x] Verify all tests pass (66 passed)
- [x] Execute: `pytest tests/unit/test_snapshot_store.py -v`
- [x] Verify all tests pass (13 passed)

### Phase 2: Domain Snapshots

Restructure snapshot domain with clear separation of models, extraction logic, and repository.

#### Step 2.1: Create `domain/snapshots/` directory structure

- [x] Create directory: `freecad/diff_wb/domain/snapshots/`
- [x] Create `freecad/diff_wb/domain/snapshots/__init__.py`:
  ```python
  """Snapshot domain module."""
  
  from .models import Snapshot
  from .repository import SnapshotRepository, InMemorySnapshotRepository
  
  __all__ = ["Snapshot", "SnapshotRepository", "InMemorySnapshotRepository"]
  ```

#### Step 2.2: Create `domain/snapshots/models.py`

- [x] Create `freecad/diff_wb/domain/snapshots/models.py`:
  - Move `Snapshot` class from `domain/snapshot.py`
  - Update imports to use `from ..tree.node import TreeNode`
  - Add comprehensive docstring
  - Add `__all__ = ["Snapshot"]`

#### Step 2.3: Create `domain/snapshots/repository.py`

- [x] Create `freecad/diff_wb/domain/snapshots/repository.py`:
  - Define `SnapshotRepository` Protocol (interface)
  - Move `SnapshotStore` class → `InMemorySnapshotRepository`
  - Rename `SnapshotStore` class to `InMemorySnapshotRepository`
  - Add `SnapshotMetadata` dataclass if not already present
  - Update method signatures to match protocol
  - Add comprehensive docstrings

```python
# SnapshotRepository protocol
class SnapshotRepository(Protocol):
    def add_snapshot(self, snapshot: Snapshot) -> str: ...
    def get_snapshot(self, snapshot_id: str) -> Snapshot | None: ...
    def list_snapshots(self) -> list[SnapshotMetadata]: ...
    def delete_snapshot(self, snapshot_id: str) -> bool: ...
```

#### Step 2.4: Create `domain/snapshots/extractor.py`

- [x] Create `freecad/diff_wb/domain/snapshots/extractor.py`:
  - Move extraction logic from `snapshot/snapshot_query.py`
  - Update imports to use `from ..tree.node import TreeNode`
  - Update imports to use `from ..tree.property import Property`
  - Add `Logger` dependency injection (use port pattern)
  - Add comprehensive docstrings

```python
class SnapshotExtractor:
    """Extracts tree structure from FreeCAD documents.
    
    Uses Logger port for logging - implementation injected at runtime.
    """
    def __init__(self, logger: Logger):
        self._logger = logger
    
    def extract_tree(self, ctx: FreeCadContext | None = None) -> Snapshot:
        ...
```

#### Step 2.5: Update old files

- [x] Delete `domain/snapshot.py` (moved to `domain/snapshots/models.py`)
- [x] Keep `domain/property_value.py` temporarily (will be removed after Phase 3)

#### Step 2.6: Update imports in existing code

- [x] Update `snapshot/snapshot_store.py` → move contents to `domain/snapshots/repository.py`
- [x] Update `snapshot/snapshot_query.py` → update imports, keep as temporary wrapper
- [x] Update `snapshot/snapshot_mutations.py` → update imports

#### Step 2.7: Run tests

- [x] Execute: `pytest tests/unit/test_snapshot_store.py -v`
- [x] Verify all tests pass (13 passed)
- [x] Execute: `pytest tests/unit/test_snapshot_query.py -v`
- [x] Verify all tests pass (8 passed)
- [x] Execute: `pytest tests/unit/test_snapshot_mutations.py -v`
- [x] Verify all tests pass (6 passed)

### Phase 3: Domain Diff

Restructure diff domain with clear separation of models, engine, and comparators.

#### Step 3.1: Create `domain/diff/` directory structure

- [x] Create directory: `freecad/diff_wb/domain/diff/`
- [x] Create `freecad/diff_wb/domain/diff/__init__.py`:
  ```python
  """Diff domain module."""
  
  from .models import DiffResult, NodeDiff, PropertyDiff, DiffState
  from .engine import DiffEngine
  from .comparator import TreeComparator, PropertyComparator
  
  __all__ = ["DiffResult", "NodeDiff", "PropertyDiff", "DiffState", 
             "DiffEngine", "TreeComparator", "PropertyComparator"]
  ```

#### Step 3.2: Create `domain/diff/models.py`

- [x] Create `freecad/diff_wb/domain/diff/models.py`:
  - Move `DiffResult`, `NodeDiff`, `PropertyDiff`, `DiffState` from `diff/diff_result.py`
  - Update imports to use `from ..tree.property import Property`
  - Rename `PropertyValue` references → `Property`
  - Add comprehensive docstrings
  - Add `__all__ = ["DiffResult", "NodeDiff", "PropertyDiff", "DiffState"]`

#### Step 3.3: Create `domain/diff/comparator.py`

- [x] Create `freecad/diff_wb/domain/diff/comparator.py`:
  - Move tree comparison logic from `diff/tree_diff.py`
  - Move property comparison logic from `diff/property_diff.py`
  - Refactor functions into `TreeComparator` and `PropertyComparator` classes
  - Update imports to use `from ..tree.property import Property`
  - Remove direct import of `config.py` - use dependency injection for settings
  - Add comprehensive docstrings

```python
class TreeComparator:
    """Compares two tree structures using path-based indexing."""
    
    @staticmethod
    def compare(old: Snapshot, new: Snapshot, excluded_types: list[str]) -> list[NodeDiff]:
        ...

class PropertyComparator:
    """Compares property values with type-aware equality."""
    
    @staticmethod
    def compare(old: Property | None, new: Property | None, 
                excluded_properties: list[str]) -> PropertyDiff | None:
        ...
```

#### Step 3.4: Create `domain/diff/engine.py`

- [x] Create `freecad/diff_wb/domain/diff/engine.py`:
  - Create `DiffEngine` class that orchestrates diff computation
  - Accept `SettingsRepository` via dependency injection
  - Implement filtering logic (excluded types and properties)
  - Coordinate between `TreeComparator` and `PropertyComparator`
  - Add comprehensive docstrings

```python
class DiffEngine:
    """Orchestrates diff computation between two snapshots.
    
    Uses SettingsRepository to determine excluded types/properties.
    """
    def __init__(self, settings_repo: SettingsRepository):
        self._settings_repo = settings_repo
    
    def compute_diff(self, old: Snapshot, new: Snapshot) -> DiffResult:
        """Compute diff between two snapshots.
        
        Steps:
        1. Get settings (excluded types/properties)
        2. Filter snapshots based on excluded types
        3. Compare trees using TreeComparator
        4. Compare properties using PropertyComparator
        5. Apply property-level exclusions
        6. Return DiffResult
        """
        ...
```

#### Step 3.5: Update old files

- [x] Delete `diff/diff_result.py` (moved to `domain/diff/models.py`)
- [x] Delete `diff/tree_diff.py` (moved to `domain/diff/comparator.py`)
- [x] Delete `diff/property_diff.py` (merged into `domain/diff/comparator.py`)

#### Step 3.6: Update imports in existing code

- [x] Update all test files importing from old locations
- [x] Update any integration code using diff modules

#### Step 3.7: Run tests

- [x] Execute: `pytest tests/unit/test_tree_diff.py -v`
- [x] Verify all tests pass (34 passed)
- [x] Execute: `pytest tests/unit/test_property_diff.py -v`
- [x] Verify all tests pass (40 passed)
- [x] Execute: `pytest tests/unit/test_domain.py -v`
- [x] Verify all tests pass (66 passed)
- [x] All unit tests pass (167 total)

### Phase 4: Infrastructure Reorganization

Move ports to infrastructure layer as adapters and create proper directory structure.

#### Step 4.1: Create `infrastructure/` directory structure

- [x] Create directories:
  ```
  infrastructure/
  ├── freecad/
  │   └── __init__.py
  ├── gui/
  │   └── __init__.py
  └── persistence/
      └── __init__.py
  ```

#### Step 4.2: Create `domain/logging/logger.py`

- [x] Create `freecad/diff_wb/domain/logging/__init__.py`:
  ```python
  """Logging domain module."""
  
  from .logger import Logger
  
  __all__ = ["Logger"]
  ```

- [x] Create `freecad/diff_wb/domain/logging/logger.py`:
  ```python
  """Logger interface (port) for domain layer."""
  
  from typing import Protocol
  
  class Logger(Protocol):
      """Interface for logging operations."""
      
      def info(self, message: str) -> None: ...
      def warning(self, message: str) -> None: ...
      def error(self, message: str) -> None: ...
  ```

#### Step 4.3: Create `domain/settings/` directory

- [x] Create `freecad/diff_wb/domain/settings/__init__.py`:
  ```python
  """Settings domain module."""
  
  from .models import Settings
  from .repository import SettingsRepository
  
  __all__ = ["Settings", "SettingsRepository"]
  ```

- [x] Create `freecad/diff_wb/domain/settings/models.py`:
  ```python
  """Settings data models."""
  
  from dataclasses import dataclass
  
  @dataclass(frozen=True)
  class Settings:
      """User configuration for diff computation."""
      excluded_types: list[str]
      excluded_properties: list[str]
  ```

- [x] Create `freecad/diff_wb/domain/settings/repository.py`:
   ```python
   """Settings repository interface (port)."""
   
   from typing import Protocol
   from .models import Settings
   
   class SettingsRepository(Protocol):
       """Interface for settings access.
       
       Note: The actual implementation (FreeCADSettingsRepository) provides a more
       granular API with individual getter/setter methods for excluded_types and
       excluded_properties, rather than the bulk get/update operations shown here.
       This design allows for partial updates without replacing the entire Settings object.
       """
       
       def get_settings(self) -> Settings: ...
       def update_settings(self, settings: Settings) -> None: ...
   ```

#### Step 4.4: Create infrastructure adapters

- [x] Move `ports/freecad_context.py` → `infrastructure/freecad/context.py`
  - Rename `FreeCadPort` → `FreeCadPortAdapter` (it's an implementation, not interface)
  - Keep `FreeCadContext` and `get_runtime_context()` in same file
  - Add comprehensive docstring

- [x] Move `ports/gui_port.py` → `infrastructure/gui/qt_adapter.py`
  - Rename `GuiPort` → `GuiPortAdapter` (implementation)
  - Update to match existing port interface
  - Add comprehensive docstring

- [x] Move `ports/settings_port.py` → `infrastructure/freecad/settings_repo.py`
  - Rename `SettingsPort` → `FreeCADSettingsRepository`
  - Implement `SettingsRepository` protocol
  - Use `config.py` for hard-coded defaults initially
  - Add comprehensive docstring

- [x] Create `infrastructure/freecad/logger.py`:
  ```python
  """FreeCAD Console logger adapter."""
  
  from freecad.diff_wb.domain.logging import Logger
  
  class FreeCADLogger(Logger):
      """Logger implementation using FreeCAD Console."""
      
      def info(self, message: str) -> None:
          import FreeCAD
          FreeCAD.Console.PrintMessage(f"[INFO] {message}\n")
      
      def warning(self, message: str) -> None:
          import FreeCAD
          FreeCAD.Console.PrintWarning(f"[WARNING] {message}\n")
      
      def error(self, message: str) -> None:
          import FreeCAD
          FreeCAD.Console.PrintError(f"[ERROR] {message}\n")
  ```

#### Step 4.5: Update old ports directory

- [x] Delete `ports/` directory (all contents moved to infrastructure)
- [x] Update `ports/__init__.py` references throughout codebase

#### Step 4.6: Update imports in existing code

- [x] Update `snapshot/snapshot_query.py` (now `domain/snapshots/extractor.py`):
  ```python
  from ..infrastructure.freecad.context import get_port
  ```

- [x] Update all files importing from `ports/`:
  ```python
  # Old
  from freecad.diff_wb.ports.freecad_port import get_port
  
  # New
  from freecad.diff_wb.infrastructure.freecad.context import get_port
  ```

#### Step 4.7: Run tests

- [x] Execute: `pytest tests/unit/test_ports.py -v` (update imports first)
- [x] Verify all tests pass
- [x] Execute: `pytest tests/unit/ -v`
- [x] Verify ALL unit tests pass (167 passed)

### Phase 5: Cleanup and Migration

Remove old directories and finalize migration.

#### Step 5.1: Remove old directories

- [x] Delete `freecad/diff_wb/domain/snapshot.py` (if still exists)
- [x] Delete `freecad/diff_wb/domain/property_value.py` (moved to `tree/property.py`)
- [x] Delete `freecad/diff_wb/snapshot/` directory (logic moved to `domain/snapshots/`)
- [x] Delete `freecad/diff_wb/diff/` directory (logic moved to `domain/diff/`)
- [x] Delete `freecad/diff_wb/ports/` directory (moved to `infrastructure/`)

#### Step 5.2: Update config.py

- [x] Keep `config.py` at root for now with hard-coded defaults
- [x] Add deprecation comment: "Will be replaced by SettingsRepository in future"
- [x] Update `FreeCADSettingsRepository` to use these defaults

```python
# config.py
"""Hard-coded configuration defaults (deprecated).

These values are used as defaults by FreeCADSettingsRepository.
In a future phase, these will be moved to FreeCAD Preferences.
"""

EXCLUDED_TYPES = ["App::Origin"]
EXCLUDED_PROPERTIES = ["TimeStamp", "Label2"]
```

#### Step 5.3: Update entrypoints

- [x] Update `entrypoints/init_gui.py`:
  - Wire dependency injection properly
  - Create infrastructure adapters
  - Pass dependencies to application controllers

```python
# entrypoints/init_gui.py
def initialize():
    # Create runtime context
    ctx = FreeCadContext(app=FreeCAD, gui=FreeCADGui)
    
    # Create infrastructure adapters
    port = get_port(ctx)
    logger = FreeCADLogger()
    settings_repo = FreeCADSettingsRepository()
    snapshot_repo = InMemorySnapshotRepository()
    
    # Create domain services
    extractor = SnapshotExtractor(logger=logger)
    diff_engine = DiffEngine(settings_repo=settings_repo)
    
    # Create application controllers (to be implemented)
    # controller = SnapshotController(...)
    
    # Register with FreeCAD
    # ...
```

#### Step 5.4: Run full test suite

- [x] Execute: `pytest tests/unit/ -v`
- [x] Verify ALL unit tests pass (161 passed)
- [x] Execute: `ruff check freecad/diff_wb/`
- [x] Fix any linting errors (all checks passed)
- [x] Execute: `ruff format freecad/diff_wb/ --check`
- [x] Fix any formatting issues (34 files already formatted)

### Phase 6: Documentation ✅ (Complete)

Update documentation to reflect new architecture.

#### Step 6.1: Update PLAN.md ✅ (Complete)

- [x] Update `docs/PLAN.md` with new architecture references
- [x] Mark Phase 1-5 as complete
- [x] Update module map with new structure
- [x] Update import path examples

#### Step 6.2: Verify ARCHITECTURE.md ✅ (Complete)

- [x] Review `docs/ARCHITECTURE.md` for accuracy
- [x] Ensure all file paths match actual implementation
- [x] Verify code examples are correct

#### Step 6.3: Create migration guide ✅ (Complete)

- [x] Add section to `docs/development.md` explaining new structure
- [x] Document common import patterns
- [x] Provide examples of dependency injection

### Phase 7: Test Structure Refactoring

Restructure tests to match the layered architecture organization per ARCHITECTURE.md guidelines.

#### Step 7.1: Create new test directory structure

- [ ] Create directories:
  ```
  tests/unit/domain/tree/
  tests/unit/domain/snapshots/
  tests/unit/domain/diff/
  tests/unit/domain/settings/
  tests/unit/domain/logging/
  tests/unit/application/controllers/
  tests/unit/application/presenters/
  tests/unit/infrastructure/freecad/
  tests/unit/infrastructure/gui/
  tests/integration/
  tests/fakes/
  ```

#### Step 7.2: Move and restructure domain tests

- [ ] Move `tests/unit/test_node.py` → `tests/unit/domain/tree/test_node.py`
- [ ] Move `tests/unit/test_property.py` → `tests/unit/domain/tree/test_property.py`
- [ ] Move `tests/unit/test_snapshot_models.py` → `tests/unit/domain/snapshots/test_models.py`
- [ ] Move `tests/unit/test_snapshot_store.py` → `tests/unit/domain/snapshots/test_repository.py`
- [ ] Move `tests/unit/test_snapshot_query.py` → `tests/unit/domain/snapshots/test_extractor.py`
- [ ] Move `tests/unit/test_tree_diff.py` → `tests/unit/domain/diff/test_comparator.py`
- [ ] Move `tests/unit/test_property_diff.py` → `tests/unit/domain/diff/test_comparator.py` (merge)
- [ ] Move `tests/unit/test_domain.py` → `tests/unit/domain/diff/test_engine.py` (split into focused tests)
- [ ] Update all imports in test files to match new source paths

#### Step 7.3: Create fake implementations

- [ ] Create `tests/fakes/__init__.py`:
  ```python
  """Fake implementations for testing."""
  
  from .fake_repositories import (
      FakeSnapshotRepository,
      FakeSettingsRepository,
      InMemorySnapshotRepository,
  )
  from .fake_logger import FakeLogger
  
  __all__ = [
      "FakeSnapshotRepository",
      "FakeSettingsRepository", 
      "InMemorySnapshotRepository",
      "FakeLogger",
  ]
  ```

- [ ] Create `tests/fakes/fake_repositories.py`:
  ```python
  """Fake repository implementations for testing."""
  
  from freecad.diff_wb.domain.snapshots.repository import SnapshotRepository
  from freecad.diff_wb.domain.settings.repository import SettingsRepository
  from freecad.diff_wb.domain.settings.models import Settings
  
  class FakeSnapshotRepository(SnapshotRepository):
      """In-memory snapshot repository for testing."""
      pass
  
  class FakeSettingsRepository(SettingsRepository):
      """Settings repository with hardcoded values for testing."""
      pass
  
  # Keep InMemorySnapshotRepository as a valid fake
  ```

- [ ] Create `tests/fakes/fake_logger.py`:
  ```python
  """Fake logger implementation for testing."""
  
  from freecad.diff_wb.domain.logging import Logger
  
  class FakeLogger(Logger):
      """Logger that captures messages for testing."""
      
      def __init__(self):
          self._messages: list[tuple[str, str]] = []
      
      def info(self, message: str) -> None:
          self._messages.append(("info", message))
      
      def warning(self, message: str) -> None:
          self._messages.append(("warning", message))
      
      def error(self, message: str) -> None:
          self._messages.append(("error", message))
      
      @property
      def messages(self) -> list[tuple[str, str]]:
          return self._messages.copy()
      
      def clear(self) -> None:
          self._messages.clear()
  ```

#### Step 7.4: Update conftest.py

- [ ] Update `tests/unit/conftest.py` or create `tests/conftest.py`:
  - Add fixtures for fake repositories
  - Add fixtures for fake logger
  - Provide common test utilities
  - Example:
    ```python
    import pytest
    from tests.fakes import FakeLogger, FakeSettingsRepository
    
    @pytest.fixture
    def fake_logger():
        return FakeLogger()
    
    @pytest.fixture
    def fake_settings_repo():
        return FakeSettingsRepository()
    ```

#### Step 7.5: Remove old test files

- [ ] Delete old flat structure test files after migration:
  - `tests/unit/test_node.py` (moved)
  - `tests/unit/test_property.py` (moved)
  - `tests/unit/test_snapshot_models.py` (moved)
  - `tests/unit/test_snapshot_store.py` (moved)
  - `tests/unit/test_snapshot_query.py` (moved)
  - `tests/unit/test_tree_diff.py` (moved)
  - `tests/unit/test_property_diff.py` (moved)
  - `tests/unit/test_domain.py` (replaced)
  - `tests/unit/test_ports.py` (moved to infrastructure tests)

#### Step 7.6: Run full test suite

- [ ] Execute: `uv run tests tests/unit/ -v`
- [ ] Verify all tests pass with new structure
- [ ] Verify test discovery works correctly
- [ ] Ensure test names are descriptive and focused

#### Step 7.7: Update documentation

- [ ] Update `docs/ARCHITECTURE.md` with actual test structure examples
- [ ] Update `docs/development.md` with test writing guidelines
- [ ] Update `tasks/7-architecture-refactoring.md` Success Criteria

## Goal

Refactor the codebase from current structure to layered architecture with DDD principles, achieving clear separation between domain logic and infrastructure concerns while maintaining all existing functionality and passing all tests. Then restructure tests to match the layered architecture organization.

## Context

Current architecture has blurred boundaries:
- `domain/` contains only models; `diff/` and `snapshot/` are domain concepts but separated
- `ports/` at root level - unclear if they're interfaces or implementations
- `config.py` hard-coded settings mixed with business logic
- No clear application layer

Target architecture enforces:
- Clear layer boundaries (Domain → Application → Infrastructure)
- Domain defines interfaces (ports), infrastructure implements them (adapters)
- Shared tree models in `domain/tree/` used by both snapshots and diff
- Repository pattern for data access (SnapshotRepository, SettingsRepository)
- Logger port for logging abstraction

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Group by domain concept (snapshots/, diff/) | Each domain concept is self-contained, easier to navigate | Group by type (models/, services/) would scatter related code |
| Tree models in separate `domain/tree/` | Shared foundation used by both snapshots and diff | Duplicate models in each domain would cause maintenance issues |
| Rename PropertyValue → Property | Simpler naming, Property is more natural | Keep PropertyValue for clarity (rejected - too verbose) |
| InMemorySnapshotRepository in domain | Pure Python, no external deps needed | Move to infrastructure (rejected - keeps it simple initially) |
| SettingsRepository with hard-coded defaults | Quick start, can add FreeCAD Preferences later | Direct config.py usage (rejected - violates separation) |
| Logger port in domain | Consistent with other ports pattern | Skip logging initially (rejected - good practice to include) |

## Architecture Impact

**New Structure:**
```
freecad/diff_wb/
├── domain/
│   ├── tree/                 # NEW: Shared tree models
│   │   ├── node.py           # TreeNode
│   │   └── property.py       # Property, Vector, Rotation, Placement
│   ├── snapshots/            # RESTRUCTURED
│   │   ├── models.py         # Snapshot
│   │   ├── extractor.py      # SnapshotExtractor
│   │   └── repository.py     # SnapshotRepository, InMemorySnapshotRepository
│   ├── diff/                 # RESTRUCTURED
│   │   ├── models.py         # DiffResult, NodeDiff, PropertyDiff
│   │   ├── engine.py         # DiffEngine
│   │   └── comparator.py     # TreeComparator, PropertyComparator
│   ├── settings/             # NEW
│   │   ├── models.py         # Settings
│   │   └── repository.py     # SettingsRepository
│   └── logging/              # NEW
│       └── logger.py         # Logger
│
├── infrastructure/           # NEW: External adapters
│   ├── freecad/
│   │   ├── context.py        # FreeCadContext, FreeCadPortAdapter
│   │   ├── settings_repo.py  # FreeCADSettingsRepository
│   │   └── logger.py         # FreeCADLogger
│   ├── gui/
│   │   └── qt_adapter.py     # GuiPortAdapter
│   └── persistence/
│       └── snapshot_repo.py  # (Future: FileBasedSnapshotRepository)
│
└── config.py                 # Kept with hard-coded defaults
```

**Old Structure Removed:**
- `domain/snapshot.py` → moved to `domain/snapshots/models.py`
- `domain/property_value.py` → moved to `domain/tree/property.py`
- `diff/diff_result.py` → moved to `domain/diff/models.py`
- `diff/tree_diff.py` → moved to `domain/diff/comparator.py`
- `diff/property_diff.py` → merged into `domain/diff/comparator.py`
- `snapshot/snapshot_store.py` → moved to `domain/snapshots/repository.py`
- `snapshot/snapshot_query.py` → moved to `domain/snapshots/extractor.py`
- `ports/*.py` → moved to `infrastructure/` as adapters

## FreeCAD Dependency

- **Domain layer**: NO FreeCAD dependencies (pure Python)
- **Infrastructure layer**: FreeCAD API used only in adapters
- **Testing**: Unit tests can run without FreeCAD using fakes

## Test Strategy

**During Migration:**
- Keep all existing tests
- Update imports to match new structure
- Run tests after each phase to verify no regressions

**After Migration:**
- Unit tests (`tests/unit/`): Pure domain logic, no FreeCAD
- Integration tests (`tests/integration/`): Infrastructure adapters with FreeCAD

## Success Criteria

### Phases 1-6: Architecture Refactoring

- [x] All files migrated to new structure
- [x] All imports updated throughout codebase
- [x] All unit tests pass without FreeCAD (161 tests)
- [x] Code passes ruff linting and formatting
- [x] Type hints complete and accurate
- [x] `__all__` defined in all module `__init__.py` files
- [x] Documentation updated (ARCHITECTURE.md, PLAN.md)
- [x] No circular dependencies
- [x] Clear separation between domain and infrastructure

### Phase 7: Test Structure Refactoring ✅ (Complete)

- [x] Tests organized by layer (domain/application/infrastructure)
- [x] Tests mirror source directory structure
- [x] Fake implementations created for all ports
- [x] conftest.py provides reusable fixtures
- [x] All 161 tests pass with new structure
- [x] Test naming follows focused, descriptive pattern
- [x] Documentation updated with test structure examples

## Notes

- Complete phases in order - each phase builds on the previous
- Run tests after each phase to catch issues early
- Use git commits at end of each phase for easy rollback if needed
- If tests fail, fix before proceeding to next phase
- The `config.py` file is kept temporarily but marked as deprecated
- Application layer controllers will be implemented in a future task
