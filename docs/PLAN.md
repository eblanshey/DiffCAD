# Diff Workbench Implementation Plan

This document describes the implementation plan for the **Diff Workbench** FreeCAD addon, modeled after the DataManager workbench architecture with clean separation of concerns, ports and adapters pattern, and comprehensive testing support.

## Goals

- Provide a FreeCAD workbench entrypoint (commands, toolbar/menu, panel)
- Keep the Qt UI layer thin by delegating behavior to presenters/controllers
- Isolate FreeCAD-specific document queries/mutations from core diff logic
- Make core modules importable and testable without a running FreeCAD GUI
- Use ports and adapters for runtime boundaries (FreeCAD, GUI, Settings)
- Implement comprehensive linting and unit testing
- Store user-facing documentation in the main README.md at project root

## High-level Structure

### Directory Layout

```
freecad_diff_workbench/
├── README.md                          # User-facing documentation
├── pyproject.toml                     # Project configuration, dependencies, tooling
├── CMakeLists.txt                     # FreeCAD addon registration
├── package.xml                        # FreeCAD addon metadata
├── MANIFEST.in                        # Package inclusion rules
├── .ruff.toml                         # Ruff linting configuration
├── .editorconfig                      # Editor configuration
├── Taskfile.yml                       # Task automation (optional)
│
├── freecad/
│   └── diff_wb/                       # Main package
│       ├── __init__.py
│       ├── init_gui.py                # FreeCAD entrypoint
│       ├── version.py                 # Version info
│       ├── freecad_helpers.py         # Shared FreeCAD helpers
│       ├── freecad_version_check.py   # Version validation
│       ├── resources.py               # Resource path management
│       ├── config.py                  # Hard-coded configuration (excluded types/props)
│       │
│       ├── entrypoints/               # FreeCAD integration
│       │   ├── __init__.py
│       │   ├── commands.py            # Command registrations
│       │   └── workbench.py           # Workbench registration
│       │
│       ├── ports/                     # Runtime boundary abstractions
│       │   ├── __init__.py
│       │   ├── freecad_context.py     # FreeCadContext + get_runtime_context()
│       │   ├── freecad_port.py        # FreeCadPort + adapter
│       │   ├── gui_port.py            # GuiPort for PySideUic/MDI
│       │   ├── settings_port.py       # SettingsPort for persisted settings
│       │   └── app_port.py            # AppPort for translation
│       │
│       ├── domain/                    # Pure domain models (no FreeCAD deps)
│       │   ├── __init__.py
│       │   ├── snapshot.py            # Snapshot dataclass
│       │   ├── tree_node.py           # TreeNode dataclass
│       │   ├── diff_result.py         # DiffResult, NodeDiff, PropertyDiff
│       │   └── property_value.py      # PropertyValue dataclass
│       │
│       ├── diff/                      # Diff computation (pure algorithms)
│       │   ├── __init__.py
│       │   ├── tree_diff.py           # Tree comparison algorithm
│       │   ├── property_diff.py       # Property comparison logic
│       │   └── diff_engine.py         # Orchestrates diff computation
│       │
│       ├── ui/                        # UI layer
│       │   ├── __init__.py
│       │   ├── diff_panel.py          # Qt widget (thin view layer)
│       │   ├── diff_panel_presenter.py# Presenter for UI state/formatting
│       │   └── panel_controller.py    # UI-facing facade
│       │
│       ├── snapshot/                  # Snapshot management (uses FreeCadPort)
│       │   ├── __init__.py
│       │   ├── snapshot_query.py      # Extracts tree from FreeCAD document
│       │   ├── snapshot_mutations.py  # Creates snapshots (orchestrates query + store)
│       │   └── snapshot_store.py      # In-memory storage/retrieval
│       │
│       └── resources/
│           ├── icons/
│           │   ├── Logo.svg
│           │   ├── TakeSnapshot.svg
│           │   ├── Compare.svg
│           │   └── SwapColumns.svg
│           ├── translations/
│           │   ├── README.md
│           │   └── diff_wb_es-ES.ts
│           └── ui/
│               └── diff_panel.ui
│
├── tests/
│   ├── conftest.py                    # pytest fixtures
│   ├── unit/                          # Unit tests (no FreeCAD)
│   │   ├── test_tree_diff.py
│   │   ├── test_property_diff.py
│   │   ├── test_diff_engine.py
│   │   ├── test_diff_panel_presenter.py
│   │   ├── test_snapshot_store.py
│   │   ├── test_ports.py
│   │   └── test_version.py
│   ├── integration/                   # Integration tests (with FreeCAD)
│   │   ├── test_snapshot_query.py
│   │   ├── test_snapshot_mutations.py
│   │   └── test_diff_panel.py
│   └── freecad/                       # FreeCAD test fixtures
│       └── create_test_document.py
│
└── docs/                              # Development documentation
    ├── PLAN.md                        # Implementation plan and architecture
    ├── feature_development.md         # Development process and phases
    ├── architecture.md                # Architecture overview (optional)
    ├── development.md                 # Development setup guide (optional)
    └── tests.md                       # Testing guidelines (optional)
```

## Architectural Principles

### 1. Ports at Runtime Boundaries

| Port | Responsibility | Implementation |
|------|---------------|----------------|
| **FreeCadPort** | Document access, recompute, GUI updates | `freecad_port.py` |
| **GuiPort** | PySideUic loading, MDI integration | `gui_port.py` |
| **SettingsPort** | Persisted settings (excluded types/properties) | `settings_port.py` |
| **AppPort** | Translation functionality | `app_port.py` |

Each port has:
- A Protocol interface definition
- A runtime adapter using real FreeCAD APIs
- Test doubles/fakes for unit testing

### 2. Dependency Injection

- Data/query/mutation functions accept `ctx: FreeCadContext | None` and call `get_port(ctx)`
- UI widgets accept optional injected ports (defaults to runtime adapters)
- Core diff logic has NO FreeCAD dependencies - fully testable

### 3. Layer Responsibilities

| Layer | Responsibility | FreeCAD Dependency |
|-------|---------------|-------------------|
| **Entrypoints** | FreeCAD registration, command wiring | Yes (guarded) |
| **UI (Qt)** | Widget wiring, signal handling | Yes (via GuiPort) |
| **Presenter** | UI state, formatting, orchestration plans | No |
| **Controller** | UI-facing facade, document refresh boundary | Yes (via FreeCadPort) |
| **Domain** | Pure data models only | No |
| **Diff** | Pure diff algorithms | No |
| **Snapshot** | FreeCAD-specific queries/mutations | Yes (via FreeCadPort) |

## Module Map

```mermaid
flowchart TB
    %% Entry points
    InitGui[init_gui.py] --> Commands[commands.py]
    InitGui --> Workbench[workbench.py]
    InitGui --> DiffPanel[diff_panel.py]
    
    Commands --> DiffPanel
    
    %% UI -> presenter -> controller
    DiffPanel --> Presenter[diff_panel_presenter.py]
    Presenter --> PanelController[panel_controller.py]
    
    %% Controller -> domain layers
    PanelController --> DiffEngine[diff/diff_engine.py]
    PanelController --> SnapshotStore[snapshot/snapshot_store.py]
    
    %% Snapshot layer
    SnapshotStore --> SnapshotQuery[snapshot/snapshot_query.py]
    SnapshotStore --> SnapshotMutations[snapshot/snapshot_mutations.py]
    
    %% Diff layer
    DiffEngine --> TreeDiff[diff/tree_diff.py]
    DiffEngine --> PropertyDiff[diff/property_diff.py]
    
    %% Ports
    DiffPanel --> AppPort[app_port.py]
    DiffPanel --> GuiPort[gui_port.py]
    DiffPanel --> SettingsPort[settings_port.py]
    PanelController --> FreeCadPort[freecad_port.py]
    SnapshotQuery --> FreeCadPort
    SnapshotMutations --> FreeCadPort
    
    %% Resources
    DiffPanel --> Resources[resources.py]
    Commands --> Resources
    Workbench --> Resources
```

## Key Components

### 1. Ports Layer (`ports/`)

#### FreeCadContext
Holds app/gui references, created at runtime:
```python
@dataclass(frozen=True)
class FreeCadContext:
    app: object  # FreeCAD module
    gui: object | None  # FreeCADGui module or None
```

#### FreeCadPort
Interface for document operations:
```python
class FreeCadPort(Protocol):
    def get_active_document(self) -> object | None: ...
    def get_object(self, doc: object, name: str) -> object | None: ...
    def get_typed_object(self, doc: object, name: str, *, type_id: str) -> object | None: ...
    def try_recompute_active_document(self) -> None: ...
    def try_update_gui(self) -> None: ...
    def translate(self, context: str, text: str) -> str: ...
    def log(self, text: str) -> None: ...
    def warn(self, text: str) -> None: ...
    def message(self, text: str) -> None: ...
```

#### GuiPort
Interface for Qt operations:
```python
class GuiPort(Protocol):
    def load_ui(self, ui_path: str) -> object: ...
    def get_main_window(self) -> object: ...
    def get_mdi_area(self) -> object | None: ...
    def add_subwindow(self, *, mdi_area: object, widget: object) -> object: ...
```

#### SettingsPort
Interface for persisted settings:
```python
class SettingsPort(Protocol):
    def value(self, key: str, default: object | None = None) -> object | None: ...
    def set_value(self, key: str, value: object) -> None: ...
```

Settings keys:
- `DiffWorkbench/ExcludedTypes`: List of type IDs to exclude (default: App::Origin)
- `DiffWorkbench/ExcludedProperties`: List of property names to exclude

#### AppPort
Interface for translation:
```python
class AppPort(Protocol):
    def translate(self, context: str, text: str) -> str: ...
```

### 2. Domain Layer (`domain/`)

Pure data models with NO FreeCAD dependencies and NO logic:

#### Snapshot
```python
@dataclass(frozen=True)
class Snapshot:
    name: str
    timestamp: datetime
    tree_nodes: list[TreeNode]
```

#### TreeNode
```python
@dataclass(frozen=True)
class TreeNode:
    name: str
    type_id: str
    properties: dict[str, PropertyValue]
    children: list[TreeNode]  # Stub for Phase 2
```

#### PropertyValue
```python
@dataclass(frozen=True)
class PropertyValue:
    value: object
    expression: str | None  # Expression if available
```

#### DiffResult
```python
@dataclass(frozen=True)
class DiffResult:
    added: list[TreeNode]      # New on right (green)
    deleted: list[TreeNode]    # Removed from left (crossed out)
    modified: list[NodeDiff]   # Changed properties (blue)
```

#### NodeDiff
```python
@dataclass(frozen=True)
class NodeDiff:
    node_name: str
    property_diffs: list[PropertyDiff]
```

#### PropertyDiff
```python
@dataclass(frozen=True)
class PropertyDiff:
    property_name: str
    old_value: PropertyValue
    new_value: PropertyValue
    changed_expression: bool
```

### 3. Diff Module (`diff/`)

Pure Python diff computation - ZERO FreeCAD dependencies:

#### TreeDiff
- Compares two tree structures
- Identifies added/deleted/modified nodes
- Uses node name + type_id for matching

#### PropertyDiff
- Compares property values between snapshots
- Tracks expression changes separately
- Handles type-specific comparisons

#### DiffEngine
- Orchestrates tree + property diffing
- Applies excluded types/properties from settings
- Returns structured DiffResult

### 4. Snapshot Module (`snapshot/`)

Snapshot management follows the same pattern as DataManager's `varsets/` module:
- Uses `FreeCadPort` via `get_port(ctx)` for all FreeCAD access
- Accepts optional `ctx: FreeCadContext` for testability
- `SnapshotStore` is pure (no FreeCAD needed)

#### SnapshotQuery
- Queries current document state
- Extracts tree structure from FreeCAD objects
- Reads property values and expressions
- **Read-only operations only**
- Uses `FreeCadPort` via `get_port(ctx)`

#### SnapshotMutations
- Orchestrates snapshot creation workflow
- Calls `SnapshotQuery` to extract document state
- Calls `SnapshotStore` to persist the snapshot
- **Mutation coordinator, not the storage itself**
- Uses `FreeCadPort` via `get_port(ctx)`

#### SnapshotStore
- Pure in-memory storage for active session
- Stores and retrieves snapshots by name/index
- Manages snapshot lifecycle (add, get, list, delete)
- **No FreeCAD dependencies - just a data store**

### 5. UI Layer (`ui/`)

#### DiffPanel
- Qt widget loading `diff_panel.ui`
- Two-column layout (left = older, right = current)
- Synchronized scrolling
- Signal wiring for user interactions
- Color coding for diff states

#### DiffPanelPresenter
- Computes UI state from domain models
- Formatting decisions (names, labels)
- Display plans for column swapping
- Selection preservation logic

#### PanelController
- Facade owning document refresh boundary
- Orchestrates snapshot creation
- Triggers diff computation
- Handles column swap operations

### 6. Entrypoints (`entrypoints/`)

#### commands.py
Defines FreeCAD commands:
- `DiffTakeSnapshot`: Take a new snapshot
- `DiffCompare`: Compare against selected snapshot
- `DiffSwapColumns`: Swap left/right columns

#### workbench.py
Defines the Workbench subclass:
- MenuText, ToolTip, Icon
- Toolbar configuration
- Initialize() method for command registration

## Configuration (Hard-coded for now)

Configuration is currently hard-coded in `config.py`:

```python
# Hard-coded defaults (will be moved to Preferences in a future phase)
EXCLUDED_TYPES = ["App::Origin"]
EXCLUDED_PROPERTIES = ["TimeStamp", "LastModified", "Label2"]
```

### Future Phase: FreeCAD Preferences Integration

When implemented, the FreeCAD Preferences dialog will have a "Diff Workbench" panel with:

1. **Excluded Types**: Textarea with type IDs, one per line
   - Default: `App::Origin`
   - Objects of excluded types and their children are removed from the diff view

2. **Excluded Properties**: Textarea with property names, one per line
   - Examples: `TimeStamp`, `LastModified`, etc.
   - Excludes properties that create noise in diff views

Implementation note: This can be done using FreeCAD's Parameter system, with SettingsPort reading/writing these preferences.

## Testing Strategy

### Unit Tests (`tests/unit/`)

Test core logic WITHOUT FreeCAD:

| Test File | Coverage |
|-----------|----------|
| `test_tree_diff.py` | Tree comparison algorithms |
| `test_property_diff.py` | Property value comparison |
| `test_diff_engine.py` | End-to-end diff computation |
| `test_diff_panel_presenter.py` | Presenter formatting logic |
| `test_snapshot_store.py` | In-memory store behavior |
| `test_ports.py` | Port adapter behavior |
| `test_version.py` | Version parsing/formatting |

Use fakes/mocks for ports:
```python
class FakeFreeCadPort:
    def __init__(self):
        self._documents = {}
    
    def get_active_document(self):
        return self._documents.get("active")
    
    def try_recompute_active_document(self):
        pass  # No-op for testing

class FakeSettingsPort:
    def __init__(self):
        self._store = {}
    
    def value(self, key, default=None):
        return self._store.get(key, default)
    
    def set_value(self, key, value):
        self._store[key] = value
```

### Integration Tests (`tests/integration/`)

Test with real FreeCAD (when available):

| Test File | Coverage |
|-----------|----------|
| `test_snapshot_query.py` | Real document snapshotting |
| `test_snapshot_mutations.py` | Snapshot creation/retrieval |
| `test_diff_panel.py` | Full UI integration |

## Linting & Quality Tools

Following datamanager patterns:

### Ruff
- `ruff check` for linting
- `ruff format` for formatting
- Configuration in `.ruff.toml`

### Mypy
- Strict type checking for domain/core logic
- Excludes FreeCAD GUI entrypoints
- Configuration in `pyproject.toml`

### Pylint
- Code quality metrics
- Project-specific disables
- Configuration in `pyproject.toml`

### Deadcode
- Detect unused code
- Configuration in `pyproject.toml`

## Implementation Phases

### Phase 1: Foundation
- [ ] Project structure matching datamanager
- [ ] `pyproject.toml` with dependencies and tool configuration
- [ ] Ports layer implementation (`ports/`)
- [ ] Resource management (`resources.py`)
- [ ] Basic entrypoints (`init_gui.py`, `workbench.py`)
- [ ] Version management (`version.py`)

### Phase 2: Core Domain
- [ ] Snapshot data structures (`domain/snapshot.py`)
- [ ] TreeNode representation (`domain/tree_node.py`)
- [ ] Diff result types (`domain/diff_result.py`, `domain/property_diff.py`)
- [ ] Settings persistence via SettingsPort

### Phase 3: Diff Engine
- [ ] Tree comparison algorithm (`diff/tree_diff.py`)
- [ ] Property comparison (`diff/property_diff.py`)
- [ ] Diff orchestration (`diff/diff_engine.py`)
- [ ] Unit tests for diff logic

### Phase 4: Snapshot Management
- [ ] Document state extraction (`snapshot/snapshot_query.py`)
- [ ] In-memory storage (`snapshot/snapshot_store.py`)
- [ ] Snapshot mutations (`snapshot/snapshot_mutations.py`)
- [ ] Integration tests

### Phase 5: UI Implementation
- [ ] Qt Designer file (`resources/ui/diff_panel.ui`)
- [ ] Main panel widget (`ui/diff_panel.py`)
- [ ] Presenter logic (`ui/diff_panel_presenter.py`)
- [ ] Panel controller (`ui/panel_controller.py`)

### Phase 6: Integration
- [ ] Command registration (`entrypoints/commands.py`)
- [ ] Toolbar/menu wiring
- [ ] Icon assets

### Phase 7: Preferences Integration (Optional)
- [ ] FreeCAD Preferences dialog panel
- [ ] Settings persistence via SettingsPort
- [ ] Dynamic reload of excluded types/properties

### Phase 8: Testing & Polish
- [ ] Comprehensive unit test coverage
- [ ] Integration tests
- [ ] Documentation updates (README.md)
- [ ] Icon design/finalization
- [ ] Performance optimization


## Differences from DataManager

| Aspect | DataManager | Diff Workbench |
|--------|-------------|----------------|
| **Panel Type** | Tabbed MDI subwindow | Single-panel MDI subwindow |
| **Layout** | Two tabs (VarSets, Aliases) | Two columns (old, new) |
| **Storage** | Live document access | In-memory snapshots |
| **Actions** | Remove unused references | Compare, swap columns |
| **Docs Location** | mkdocs documentation | README.md at root |
| **Configuration** | Per-tab display modes | Hard-coded (Preferences in Phase 7) |

## Key Flows

### Take Snapshot Flow

```mermaid
sequenceDiagram
    participant User
    participant Commands
    participant PanelController
    participant SnapshotMutations
    participant SnapshotQuery
    participant SnapshotStore
    participant FreeCadPort

    User->>Commands: Click "Take Snapshot"
    Commands->>PanelController: take_snapshot()
    PanelController->>SnapshotMutations: create_snapshot()
    SnapshotMutations->>SnapshotQuery: extract_tree(doc)
    SnapshotQuery->>FreeCadPort: get_active_document()
    FreeCadPort-->>SnapshotQuery: doc
    SnapshotQuery-->>SnapshotMutations: tree_nodes
    SnapshotMutations->>SnapshotStore: store(name, tree_nodes)
    SnapshotStore-->>SnapshotMutations: snapshot_id
    SnapshotMutations-->>PanelController: snapshot_id
    PanelController->>FreeCadPort: message("Snapshot created")
    PanelController-->>Commands: success
    Commands-->>User: UI updated
```

### Compare Snapshots Flow

```mermaid
sequenceDiagram
    participant User
    participant DiffPanel
    participant Presenter
    participant PanelController
    participant DiffEngine
    participant SnapshotStore

    User->>DiffPanel: Select snapshot + Compare
    DiffPanel->>Presenter: get_compare_state(selected_snapshot)
    Presenter->>PanelController: compare_snapshots(old, current)
    PanelController->>SnapshotStore: get_snapshot(old)
    SnapshotStore-->>PanelController: old_snapshot
    PanelController->>SnapshotStore: get_snapshot(current)
    SnapshotStore-->>PanelController: current_snapshot
    PanelController->>DiffEngine: compute_diff(old, current)
    DiffEngine-->>PanelController: DiffResult
    PanelController-->>Presenter: diff_result
    Presenter-->>DiffPanel: Render two columns with coloring
```

## Configuration Files to Create

1. `pyproject.toml` - Project metadata, dependencies, tool configuration
2. `.ruff.toml` - Ruff linting rules
3. `CMakeLists.txt` - FreeCAD addon registration
4. `package.xml` - FreeCAD addon metadata
5. `MANIFEST.in` - Package inclusion rules
6. `.editorconfig` - Editor consistency
7. `tests/conftest.py` - pytest fixtures
8. `docs/architecture.md` - Architecture documentation (optional)

## Success Criteria

- [ ] Workbench registers correctly in FreeCAD
- [ ] Snapshot creation works for active document
- [ ] Diff computation produces accurate results
- [ ] UI displays two-column diff with proper coloring
- [ ] Unit tests pass without FreeCAD runtime
- [ ] Integration tests pass with FreeCAD runtime
- [ ] Linting passes (ruff, mypy, pylint)
- [ ] Documentation is clear and complete

## Notes

- Tree traversal decisions postponed to Phase 2 (stubs in place)
- User documentation stays in main README.md
- Configuration is hard-coded for now; Preferences integration is Phase 7 (optional)
- MDI subwindow layout like DataManager
- `domain/` contains pure data models only (no logic, no FreeCAD deps)
- `diff/` contains pure diff algorithms (no FreeCAD deps)
- `snapshot/` uses `FreeCadPort` via `get_port(ctx)` (same pattern as DataManager's `varsets/`)
- All modules that need FreeCAD accept optional `ctx: FreeCadContext` for testability
