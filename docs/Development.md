# Development Guidelines

This guide describes how to make maintainable changes to DiffCAD. For environment setup, see [Development Setup](DevSetup.md). For system structure, see [Architecture](Architecture.md).

## UI Terminology Mapping

The user-facing UI uses CAD-oriented terminology while internal code keeps Git/diff terms for the time being.

| UI term | Internal term |
|---------|---------------|
| Project | Git repository |
| Iteration | Git commit |
| Save Iteration | git commit operation |
| Reviewed | Git staging/index |
| In Progress | Git working tree |
| Tree Comparison | snapshot/tree/property diff |
| 3D Comparison | visual/BREP diff |
| History Panel | Diff panel window |

**Contributor guidance:**
- User-facing text must use UI terms (see `translation_strings.py`).
- Internal code may keep Git/diff terms until additional refactoring phase.
- Do not rename internal domain/application/infrastructure classes (`GitService`, `DiffEngine`, etc.).
- Do not rename `freecad/diff_wb` package path.

## Required Checks

Run all checks before submitting changes:

```bash
task check
```

Run tests (includes unit and integration):

```bash
task test
```

## Project Layout

```text
freecad/diff_wb/
├── application/       # Use cases and dependency injection container
├── domain/            # Core models, services, settings, ports, snapshot and diff logic
├── entrypoints/       # FreeCAD workbench and command integration
├── infrastructure/    # FreeCAD, git, and persistence adapters
├── resources/         # Icons, translations, UI resources
└── ui/                # Qt views, presenters, UI state, protocols, translation strings

tests/
├── unit/              # Fast tests using fakes and pure Python behavior
├── integration/       # FreeCAD runtime tests
├── fakes/             # Test doubles for ports, views, loggers, and repositories
└── freecad/           # Test FreeCAD documents
```

Keep tests close to the source structure they cover. For example, behavior in `freecad/diff_wb/domain/diff/engine.py` belongs under `tests/unit/domain/diff/` unless it needs the FreeCAD runtime.

## Coding Standards

- Keep changes minimal and focused.
- Prefer readable functions and direct data flow over new abstractions.
- Do not add compatibility layers unless there is a real persisted-data, shipped-API, or external-consumer need.
- Do not add comments that describe old bugs or temporary phases.
- Add comments only when code would otherwise be hard to understand.
- Use ASCII in new text unless the file already uses non-ASCII or the content needs it.
- Keep user-facing English strings in `freecad/diff_wb/ui/translation_strings.py`.
- Logs do not require translation.

Every Python file must start with a responsibility comment:

```python
# File responsibility: Explains what this file owns.
```

Every package `__init__.py` must start with a module responsibility comment:

```python
# Module responsibility: Explains what this package exposes or coordinates.
```

Keep those comments accurate when files change.

### Cyclomatic Complexity

Keep function complexity at **B (5-10)** or better. Functions rated **C (10-20)** or higher must be refactored by extracting helper methods.

Check complexity before submitting changes:

```bash
uv run radon cc --min C freecad/diff_wb --no-assert -s
```

Target: No C-rated functions in the codebase.

## Dependency Injection

Create dependencies at composition roots and pass them into classes or actions. Do not create FreeCAD, git, filesystem, or UI dependencies deep inside domain or application logic.

Preferred pattern:

```python
class CreateDiffAction:
    def __init__(self, diff_engine: DiffEngine) -> None:
        self._diff_engine = diff_engine

    def execute(self, old_snapshot: Snapshot, new_snapshot: Snapshot) -> Result[DiffResult]:
        diff = self._diff_engine.compute_diff(old_snapshot, new_snapshot)
        return Result.success(diff)
```

Guidelines:

- Application actions receive services and ports in constructors.
- Domain services receive protocols or value objects, not concrete infrastructure classes.
- UI presenters receive actions, view protocols, and UI state.
- Infrastructure adapters wrap external APIs.
- `ApplicationContainer` wires application actions and domain services.
- `compose_and_register_ui()` wires views, presenters, and `UIState`.

## Classes And Functions

Use classes when identity, state, interface contracts, or dependency injection make behavior clearer.

Good class use cases:

- Domain models and dataclasses: `Snapshot`, `TreeNode`, `Property`, `DiffResult`.
- Protocols and interfaces: `GitPort`, `SettingsRepository`, `FreeCadPort`.
- Services with injected dependencies: `DiffEngine`, `GitService`.
- Stateful infrastructure adapters: `GitPortAdapter`, `FreeCADSettingsRepository`.
- UI presenters and views.

Use functions for stateless, deterministic behavior.

Good function use cases:

- Pure transformations.
- Small comparison helpers.
- Serialization helpers.
- Test data builders.
- Local helpers that do not need injected dependencies.

Do not wrap a simple pure algorithm in a class only to make it look architectural.

## Imports And Public APIs

Prefer package-level imports when symbols are exported by `__init__.py`:

```python
from freecad.diff_wb.domain.diff import DiffEngine
from freecad.diff_wb.domain.snapshots import Snapshot
from freecad.diff_wb.domain.tree import Property
```

Direct module imports are fine when a symbol is intentionally not re-exported:

```python
from freecad.diff_wb.infrastructure.git.git_port_adapter import GitPortAdapter
```

Use `__all__` for clear module APIs when a package or module exposes a stable set of public symbols. Internal helpers should use a leading underscore.

## Logging

Use `Log` from `freecad.diff_wb.utils` for project logging:

```python
from freecad.diff_wb.utils import Log

Log.info("Repository refreshed")
Log.warning("No active document")
Log.error("Snapshot could not be loaded")
```

Behavior:

- Before FreeCAD initialization, logging falls back to stdout/stderr.
- After workbench initialization, logs go through `FreeCADLogger` to the FreeCAD console.
- Tests can install `FakeLogger` with `set_logger()`.
- Log messages are developer-facing and do not need translation.

## Translations

All user-facing English UI text belongs in `freecad/diff_wb/ui/translation_strings.py`.

Pattern:

- Define a named constant in `translation_strings.py`.
- Export it through `__all__`.
- Translate in views or entry point UI code with the appropriate Qt context.
- Use Qt-style placeholders such as `%1` and `%2` in templates.
- Presenters should pass raw data rather than formatted translated messages.

Example:

```python
REPOSITORY_INFO_TEMPLATE = "Repository: %1"
```

Avoid scattering literal button labels, dialog titles, tooltips, and status messages through views or commands.

## Testing Strategy

Write tests that protect real behavior and document useful contracts. Avoid tests that only freeze implementation details.

Good tests:

- Verify public behavior and result contracts.
- Verify components are wired correctly through observable outcomes.
- Verify domain algorithms with meaningful examples.
- Verify integration between application actions and services.
- Verify FreeCAD runtime behavior when stubs or fakes are insufficient.

Avoid tests that:

- Check non-existence of fields or classes (negative tests).
- Duplicate existing coverage without adding a new failure mode.
- Assert private implementation details like `_git_port`, `_git_service`, or internal action wiring.
- Test fake internals, protocol compliance, or method existence.
- Verify dataclass defaults, `hasattr` checks, repr output, or construction trivia.
- Preserve temporary development phases in filenames or test names.

### Test Ownership Rules

Each behavior should have one owning layer. Duplicate tests across layers create noise when failures occur.

- **Domain tests** own pure business behavior and algorithms: models, services, diff logic, snapshot extraction rules, git workflow rules.
- **Application tests** own orchestration, result contracts, and dependency forwarding only when forwarding is part of the action contract.
- **Infrastructure tests** own adapter parsing, command construction, subprocess invocation shape, and external error mapping.
- **UI tests** own observable presenter/view behavior, state updates, and callback wiring. Do not test private Qt styling details unless styling is an explicit product contract.
- **Integration tests** own behavior that requires real FreeCAD, Qt runtime, real document structure, workbench activation, or real runtime wiring.

Integration tests run with FreeCAD's Python interpreter and real App runtime. In CLI/headless runs where `FreeCADGui` is unavailable, integration fixtures provide a `GuiLike` mock adapter that implements the required port surface (`getDocument()`, `isModified()`, `getViewProvider()`) against real App documents. This keeps integration coverage stable without requiring a full interactive GUI session.

### Skipped Tests

Skipped tests should not remain in the suite long-term. If a unit test needs FreeCAD or Qt runtime, move useful coverage to integration tests and delete the skipped version. Debug-only or permanently skipped files provide no value and should be removed.

### Parametrized Consolidation

Use `@pytest.mark.parametrize` to keep edge-case coverage concise. When multiple tests differ only in input values or expected outputs, consolidate them into a single parametrized test. This reduces file size, prevents repetitive failures, and makes the test suite easier to scan.

### Mocking Guidelines

When patching standard library modules (`subprocess`, `os`, `pathlib`) in unit tests, use `unittest.mock.patch` context managers instead of `pytest.monkeypatch.setattr`. Context managers limit the scope of patches and prevent global state from leaking into IDE pytest hooks.

For application-specific modules, `monkeypatch` is appropriate and convenient.

### Unit Tests

Location: `tests/unit/`

Use unit tests for fast feedback on pure behavior. Unit tests should not require FreeCAD to be running. Follow the ownership rules above: domain algorithms, application orchestration, infrastructure adapters (without real subprocess or git), and UI presenter logic with fakes.

Run tests (includes unit and integration):

```bash
task test
```

## Common Contributor Tasks

### Add An Application Action

1. Add a focused action class under `freecad/diff_wb/application/actions/`.
2. Return an existing result model or add a small result model when needed.
3. Inject domain services or ports through the constructor.
4. Wire the action in `application/di/container.py`.
5. Add unit tests under `tests/unit/application/actions/`.

### Add UI Text

1. Add constants to `ui/translation_strings.py`.
2. Export constants through `__all__`.
3. Translate in the view or command dialog code.
4. Avoid formatting translated strings in presenters.

### Add A FreeCAD Command

1. Add a command class in `entrypoints/commands.py`.
2. Keep FreeCAD-specific code in the command.
3. Delegate behavior to a presenter or application action.
4. Register the command in `register_commands()`.
5. Add the command name to the workbench toolbox if it should appear in toolbar/menu.
6. Add command tests under `tests/unit/entrypoints/`.

### Add A Setting Or Preference

1. Add default values in `domain/config.py` if needed.
2. Update settings models or codecs under `domain/settings/`.
3. Update `FreeCADSettingsRepository` persistence behavior.
4. Update preferences UI in `ui/views/settings_preferences_page.py`.
5. Add tests for model/codec behavior and repository persistence behavior.

### Add Snapshot Or Diff Behavior

1. Put pure comparison behavior under `domain/diff/`.
2. Put snapshot model or serialization behavior under `domain/snapshots/` or `infrastructure/persistence/` depending on whether it is core model behavior or file format behavior.
3. Use focused unit tests for algorithms.
4. Add integration tests if real FreeCAD documents or runtime APIs are required.

## FreeCAD Runtime Notes

FreeCAD type stubs are installed by `uv` under `.venv/lib/python3.12/site-packages/`. Check them before assuming FreeCAD signatures.

Use the extracted AppImage runtime for live API checks:

```bash
./run_with_freecad.sh python -c "import FreeCAD; print(dir(FreeCAD))"
```

The `FreeCADGui` module is not generally available through `run_with_freecad.sh`. GUI behavior often needs manual FreeCAD testing or integration tests that run through FreeCAD's runtime.

## Additional Resources

- [Development Setup](DevSetup.md)
- [Architecture](Architecture.md)
- [FreeCAD preferences page API exploration](api-exploration/freecad-preferences-page-api.md)
- [FreeCAD document structure exploration](api-exploration/document-structure.md)
