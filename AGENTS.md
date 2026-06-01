# Agent Rules

## General Rules

- This project uses `uv` to manage its environment.
- MUST correct outdated/incorrect documentation immediately (including this file)
- All python files MUST have a comment at the top explaining the responsibility of the file, in format: File responsibility: [responsibility here]. It should be kept updated when files change.
- All python module's `__init__.py` MUST have a comment at the top explaining the responsibility of the whole module, in format: Module responsibility: [responsibility here]
- If you are asked to copy or move a file, prefer to use the cp or mv commands.
- Run `task check` to run linters and formatters
- Run `task test` to run all tests (includes unit and integration). Integration tests use FreeCAD's Python 3.11 interpreter through `./run_integration_tests.sh`. If you get a large number of skipped tests, it's because you didn't run it correctly!
- When asked to update or fix documentation or any markdown files, do not make the changes in a way that indicates something has changed. E.g. do not write "Update: we now want to do X". Write it in a way that flows naturally as if it's the first version written.
- Use the `Log` static methods from `utils.py` for logging throughout the codebase.
- Do not write comments that reference bugs that were fixed (unless explicitly asked to), as such comments are useless long-term.
- Only git commit if you were asked to. Use Conventional Commits for the message.
- You are NEVER to check out files from git unless given approval by the user.
- No hacky patches allowed. If seems like a lot of work needed to implement something cleanly without patches, stop and ask the user for direction. Strive for 100% clean, readable, maintainable code.
  - Similarly, NO backwards-compatibility code is allowed ANYWHERE, unless explicitly approved by the user.
- Do not implement fallback paths, defensive compatibility shims, or alternate code paths unless there is a confirmed, legitimate caller/use case in this codebase; if none exists, remove or refuse the fallback.
- If code reaches an impossible state, raise `RuntimeError` (or more specific exception) immediately. Do not return `None`, default values, or silently continue.
- Encode invariants in types and function signatures: if `None` is not valid, do not use optional return types. Validate preconditions at entry points, then keep inner helpers strict and non-optional.
- All user-facing English words and phrases must use `translate("History", "...")` literals at display sites, or `QT_TRANSLATE_NOOP` with correct context when deferred (command `GetResources()` uses exact command context; workbench labels use `Workbench`; property descriptions use `App::Property`). Logs do not require translation.
- When changing user-facing text, run `task translations:refresh` before the completion of your work.
- Read the `docs/Architecture.md` guidelines when planning new features.
- Do not remove useful line comments when refactoring
- DO add comments for all public functions/methods, and private/internal methods when their name doesn't describe their logic well enough
- Add comments on if-statements and other code-path decisions, when semantics are not immediately clear
- Separate code comments and previous code with an empty line, so that code comment has a line space before it
- Keep cyclomatic complexity at B (5-10) or better in the src dir: `uv run radon cc --min C freecad/history_wb --no-assert -s`

Terse like caveman. Technical substance exact. Only fluff die.
Drop: articles, filler (just/really/basically), pleasantries, hedging.
Fragments OK. Short synonyms. Code unchanged.
Pattern: [thing] [action] [reason]. [next step].
ACTIVE EVERY RESPONSE. No revert after many turns. No filler drift.
Code/commits/docs/PRs: normal. Off: "stop caveman" / "normal mode".

## Testing Philosophy

Write only meaningful, long-term tests. Avoid "dumb tests" that serve no purpose:

**DO NOT write:**
- Tests checking for non-existence of fields/classes (negative tests) - these will never fail unless architecture fundamentally changes
- Phase-specific test files (e.g., `test_*_phase2.py`) - clean up TDD artifacts after implementation
- Tests that duplicate existing coverage without adding value
- Tests for implementation details that may change during refactoring
- Tests of fake internals, protocol compliance, or method existence - fakes support tests, they are not product behavior
- Private attribute assertions (`_git_port`, `_git_service`, `hasattr` checks) - these freeze wiring details
- Dataclass default/repr/mutability trivia unless it documents a public contract
- Permanently skipped or debug-only tests

**DO write:**
- Positive tests verifying components ARE wired correctly through observable outcomes
- Tests for behavioral contracts and public APIs
- Integration tests validating component interactions that require real FreeCAD/Qt runtime
- Tests that would catch regressions if removed

**Layer ownership:** Each behavior has one owning test layer. Domain owns algorithms. Application owns orchestration and result contracts. Infrastructure owns adapter parsing and error mapping. UI owns observable presenter/view behavior. Integration owns real FreeCAD/Qt/runtime behavior. Do not duplicate tests across layers.

**Skipped tests:** Never leave skipped tests in the suite long-term. Move useful runtime-dependent coverage to integration tests; delete the rest.

**Parametrized consolidation:** Use `@pytest.mark.parametrize` when multiple tests differ only in input/output values. Keeps edge coverage concise and reduces repetitive failures.

**Mocking stdlib modules:** Use `unittest.mock.patch` context managers instead of `monkeypatch.setattr` when patching standard library modules (`subprocess`, `os`, `pathlib`). This prevents global state from leaking into IDE pytest hooks. `monkeypatch` is fine for application-specific modules.

**Path safety for tests:** Do not use `/tmp` or `/var/tmp` paths in tests. Use stable fake paths such as `/home/user/dir/...` to avoid FreeCAD Addons Report static analyzer for insecure-temp-path findings.

## Type Information

FreeCAD type stubs are installed via `uv` at `.venv/lib/python3.12/site-packages/`. Check these `.pyi` files before assuming FreeCAD API behavior or when implementing FreeCAD integration code.

## FreeCAD Runtime

For exploring the actual FreeCAD runtime API, use the extracted FreeCAD AppImage:

```bash
./run_with_freecad.sh python -c "import FreeCAD; print(dir(FreeCAD))"
```

This runs Python with FreeCAD's built-in interpreter and bindings, giving access to live API inspection when stubs are incomplete or uncertain.

There is also a test freecad file you can inspect, in `tests/freecad/BasicFile.FCStd`.
The FreeCADGui module is not available using this script. So if you need to debug something that calls any of the Gui APIs, you must create a new python file in the `freecad/history_wb` directory with logging and call it in the `workbench.py`'s Activated method. Then ask the user to run freecad and report the output logs.
