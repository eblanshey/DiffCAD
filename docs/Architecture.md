# Architecture

DiffCAD uses a layered architecture with domain-driven and ports-and-adapters patterns. The goal is to keep FreeCAD, Qt, git, and filesystem details at the edges while core comparison behavior remains understandable and testable.

## Design Principles

- Dependencies point inward where practical: entry points and UI call application actions; application actions coordinate domain services; infrastructure adapts external systems.
- Domain concepts are explicit: snapshots, diffs, settings, tree paths, and git state have dedicated models and services.
- Application actions are small use cases. They coordinate dependencies and return result objects rather than directly updating UI.
- UI state stays in the UI layer. The application container does not own presenter state or view state.
- External systems are represented through ports. Real FreeCAD and git implementations live in infrastructure; tests usually use fakes.
- FreeCAD startup work stays minimal. The workbench registers commands first, then creates the diff panel when activated or opened.

## Frontend And Backend Analogy

DiffCAD is a desktop FreeCAD workbench, but its internal shape is close to a frontend/backend application.

### Backend

The application and domain layers act like the backend.

| Backend concept | DiffCAD implementation |
| --- | --- |
| API endpoint | Application action with an `execute()` method. |
| Business logic | Domain services, models, and algorithms. |
| Request/response result | Result models returned by application actions. |
| Database or external service | Infrastructure adapters for FreeCAD, git, and snapshot files. |
| Dependency injection container | `ApplicationContainer`, which wires actions, services, repositories, and ports. |

Application actions are similar to API endpoints: they accept inputs, coordinate services, and return results. They should not hold UI state between calls.

The domain layer contains backend business concepts: snapshots, diffs, settings, tree paths, and git workflow rules.

### Frontend

The UI layer acts like the frontend.

| Frontend concept | DiffCAD implementation |
| --- | --- |
| State store | `UIState`, currently holding session state such as the detected repository. |
| Component/controller | Presenters that react to user events and action results. |
| Rendered view | Qt widgets under `ui/views/`. |
| View contract | Protocols under `ui/protocols/`. |

Presenters call backend-like application actions, transform results for display, and update views through protocols. Views own Qt rendering and translation. UI state stays in the UI layer, not in the application container or domain services.

## Runtime Flow

```text
FreeCAD loads init_gui.py
        |
        v
Workbench.Initialize()
        |
        |-- create FreeCAD runtime context
        |-- create ApplicationContainer
        |-- configure Log with FreeCADLogger
        |-- register FreeCAD commands
        |-- register preferences page
        v
Workbench.Activated() or Open Diff Window command
        |
        v
compose_and_register_ui(container)
        |
        |-- create UIState
        |-- create DiffPanelView
        |-- create presenters
        |-- register presenters in UIRegistry
        |-- detect active git repository
        v
Presenter executes application actions
        |
        v
Domain services and infrastructure adapters perform work
```

## Layer Responsibilities

### Entry Points

Location: `freecad/history_wb/entrypoints/`

Entry points integrate with FreeCAD's workbench and command APIs.

- `workbench.py` defines `HistoryWorkbench`, registers toolbars/menus, creates the application container, registers preferences, and opens the diff panel.
- `commands.py` defines FreeCAD command classes and delegates work to presenters or application actions.
- Entry points may access the global container through `freecad/history_wb/_container.py`.
- Entry points should stay thin. They translate FreeCAD callbacks into application or UI calls.

### UI Layer

Location: `freecad/history_wb/ui/`

The UI layer owns presenter state, Qt views, and view protocols.

- `composer.py` is the UI composition root. It creates views, presenters, and `UIState`.
- `state.py` stores UI-only state such as the detected `GitRepository`.
- `registry.py` stores globally reachable UI objects needed by FreeCAD commands.
- `presenters/` transforms application results into view updates.
- `protocols/` defines presenter-facing view contracts.
- `views/` contains Qt widgets and preferences UI.
- User-facing UI text is translated at display sites with literal `translate("History", "...")` calls, or defined with `QT_TRANSLATE_NOOP` when deferred.

Presenters depend on view protocols and application actions. Views render Qt widgets and perform translation. Presenters should pass raw data, not translated UI strings.

### Application Layer

Location: `freecad/history_wb/application/`

The application layer exposes workbench use cases as small action classes.

- `actions/` contains use cases such as creating snapshots, creating document diffs, staging documents, committing staged files, reading settings, and finding repositories.
- `actions/result_models.py` contains reusable result types.
- `di/container.py` wires application actions, domain services, and infrastructure adapters.

Actions should be stateless after construction. They receive dependencies through constructors, execute one operation, and return a result.

### Domain Layer

Location: `freecad/history_wb/domain/`

The domain layer contains core workbench concepts and contracts.

- `diff/` contains diff models, comparison algorithms, and `DiffEngine`.
- `git/` contains git models, git port protocols, and `GitService`.
- `settings/` contains settings models, text codec helpers, persistence state, and `SettingsRepository`.
- `snapshots/` contains snapshot models, snapshot serialization helpers, snapshot repository contracts, and `SnapshotExtractor`.
- `tree/` contains tree nodes, property models, and data-path wrappers.
- `config.py` contains default diff settings such as exclusions and float precision.
- `freecad_ports.py` defines minimal FreeCAD-facing protocols used by domain/application code.

Most domain code is pure Python. `domain/snapshots/gui_extractor.py` extracts FreeCAD's visual tree through `claimChildren()` using injected `GuiLike` from `FreeCadContext`, so domain services avoid direct `FreeCADGui` imports while still matching runtime GUI behavior.

### Infrastructure Layer

Location: `freecad/history_wb/infrastructure/`

Infrastructure adapts external systems to project protocols.

- `freecad/ports.py` adapts the runtime FreeCAD API to `FreeCadPort` and `AppPort`.
- `freecad/settings_repo.py` persists diff settings through FreeCAD preferences.
- `freecad/logger.py` sends `Log` output to the FreeCAD console.
- `git/git_port_adapter.py` implements git operations by calling the git CLI.
- `persistence/snapshot_yaml.py` writes snapshot YAML.
- `persistence/snapshot_yaml_deserializer.py` reads snapshot YAML.

Infrastructure can depend on domain and application types. Domain and application code should not depend on infrastructure implementations directly except where dependencies are wired in the container.

## Current Source Layout

```text
freecad/history_wb/
├── _container.py
├── init_gui.py
├── resources.py
├── utils.py
├── version.py
├── application/
│   ├── actions/
│   └── di/
├── domain/
│   ├── config.py
│   ├── freecad_ports.py
│   ├── diff/
│   ├── git/
│   ├── settings/
│   ├── snapshots/
│   └── tree/
├── entrypoints/
│   ├── commands.py
│   └── workbench.py
├── infrastructure/
│   ├── freecad/
│   ├── git/
│   └── persistence/
├── resources/
│   ├── icons/
│   ├── translations/
│   └── ui/
└── ui/
    ├── composer.py
    ├── registry.py
    ├── state.py
    ├── presenters/
    ├── protocols/
    └── views/
```

## Dependency Rules

```text
Entry Points
    |
    v
UI Layer --------------+
    |                  |
    v                  |
Application Layer      |
    |                  |
    v                  |
Domain Layer <---------+
    ^
    |
Infrastructure Layer
```

- Entry points may call UI registries, presenters, commands, and application container accessors.
- UI may call application actions and use domain models for display state.
- Application may use domain services, domain models, and domain ports.
- Domain should not import UI or application modules.
- Infrastructure implements domain ports and can call external APIs.
- The container is a composition mechanism, not application state.

## Composition Roots

DiffCAD has two composition roots.

### Application Composition

`workbench.Initialize()` creates the FreeCAD runtime context and calls `create_application_container(ctx)`. The container wires:

- FreeCAD adapters
- git adapter and git service
- settings repository
- snapshot extractor
- diff engine
- application actions

The container is stored through `set_container()` so FreeCAD command instances can access it at execution time.

### UI Composition

`compose_and_register_ui(container)` creates:

- `UIState`
- `DiffPanelView`
- `DiffPresenter`
- `GitRepositoryPresenter`

It then registers UI objects in `ui_registry` for command access. UI composition happens when the diff panel is created, not during initial FreeCAD module import.

## UI Composition Rules

Composite Qt views may be split into focused child widgets, but presenter-facing APIs should remain stable through view protocols.

- Presenters call view protocols, not concrete child widgets.
- The UI composer wires presenters to top-level views only.
- Top-level views act as facades for composed child widgets.
- Child widgets do not import, instantiate, or call sibling child widgets.
- Child widgets expose callbacks/events upward and narrow setter methods downward.
- Cross-widget side effects are coordinated by the top-level facade.
- Cross-widget coordination is tested at the facade level.

Example: `DiffPanelView` composes `HistoryPanelWidget`, `DocumentDiffTreeWidget`, and `PropertyDiffTreeWidget`. Selecting history in `HistoryPanelWidget` should not directly mutate `DocumentDiffTreeWidget`; `DiffPanelView` or a presenter coordinates the behavior.

## Snapshot And Diff Pipeline

DiffCAD stores textual snapshots next to `.FCStd` files so git can compare CAD model state.

```text
FreeCAD document
        |
        v
SnapshotExtractor
        |
        v
Snapshot model
        |
        |-- working tree snapshot from open document
        |-- commit snapshot from YAML deserializer
        v
DiffEngine
        |
        v
DiffResult
        |
        v
DiffPresenter
        |
        v
DiffPanelView
```

Snapshots contain normalized object payloads and occurrence paths. This allows repeated or linked objects to be represented separately from object data. Diff comparison uses settings for exclusions and numeric precision.

## Git Workflow Integration

Git support is implemented as domain service plus infrastructure adapter.

- `GitService` owns repository-level workflow rules.
- `GitPort` defines git operations.
- `GitPortAdapter` calls the git CLI.
- Application actions use `GitService` to find repositories, list commits, stage files, detect staged/committed paths, and commit staged changes.
- The UI stores the active `GitRepository` in `UIState` because repository selection is UI session state.

DiffCAD supplements normal git clients. It focuses on CAD-specific staging, snapshot generation, and review.

## Settings And Preferences

Default settings live in `domain/config.py`. Runtime settings are read and written through `SettingsRepository`, implemented by `FreeCADSettingsRepository` with FreeCAD preferences.

Settings affect diff computation and display. They do not affect snapshot generation.

## Public APIs

Module `__init__.py` files define public module APIs with `__all__` where useful. Importing from package-level modules is preferred when a symbol is exported there.

```python
from freecad.history_wb.domain.diff import DiffEngine
from freecad.history_wb.domain.snapshots import Snapshot
from freecad.history_wb.domain.tree import Property
```

Direct file imports are acceptable when a symbol is not part of a package API or when tests need focused access to implementation details.

## Known Tradeoffs

- `SnapshotExtractor` uses injected `GuiLike` to access GUI documents and `claimChildren()` behavior. This keeps extraction aligned with FreeCAD's visual tree without domain-level `FreeCADGui` imports.
- `ApplicationContainer` exposes small `log()` and `translate()` helpers for entry points. Core code should prefer `Log` and view-level translation patterns.
- Some FreeCAD APIs are difficult to type precisely. Protocols in `domain/freecad_ports.py` intentionally model only the behavior DiffCAD uses.

## Glossary

| Term | Meaning |
| --- | --- |
| Action | Application-layer use case object with an `execute()` method. |
| Adapter | Infrastructure implementation of a port, such as `GitPortAdapter`. |
| Application Container | Object that wires actions, services, repositories, and adapters. |
| Composition Root | Place where dependencies are created and connected. |
| Domain | Core model and behavior independent from presentation details. |
| Port | Protocol that describes an external dependency. |
| Presenter | UI coordinator that turns application results into view updates. |
| Snapshot | Text-friendly representation of a FreeCAD document's model state. |
| UIState | UI-session state owned by the UI layer, such as detected repository. |
