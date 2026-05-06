# Agent Rules

## General Rules

- This project uses `uv` to manage its environment.
- MUST correct outdated/incorrect documentation immediately (including this file)
- All python files MUST have a comment at the top explaining the responsibility of the file, in format: File responsibility: [responsibility here]. It should be kept updated when files change.
- All python module's `__init__.py` MUST have a comment at the top explaining the responsibility of the whole module, in format: Module responsibility: [responsibility here]
- If you are asked to copy or move a file, prefer to use the cp or mv commands.
- Run `task check` to run linters and formatters
- Run `task test` to run unit tests.
- Run `task test:integration` to run integration tests (runs tests with `./run_integration_tests.sh` instead of `uv`)
  - If you get a large number of skipped tests, it's because you didn't run it correctly!
- Integration tests use FreeCAD's Python 3.11 interpreter (not system Python 3.12) to avoid version incompatibility.
- When asked to update or fix documentation or any markdown files, do not make the changes in a way that indicates something has changed. E.g. do not write "Update: we now want to do X". Write it in a way that flows naturally as if it's the first version written.
- Use the `Log` static methods from `utils.py` for logging throughout the codebase.
- Do not write comments that reference bugs that were fixed (unless explicitly asked to), as such comments are useless long-term.
- Only git commit if you were asked to. Use Conventional Commits for the message.
- You are NEVER to check out files from git unless given approval by the user.
- No hacky patches allowed. If seems like a lot of work needed to implement something cleanly without patches, stop and ask the user for direction. Strive for 100% clean, readable, maintainable code.
  - Similarly, NO backwards-compatibility code is allowed ANYWHERE, unless explicitly approved by the user.
- All english words and phrases must use translations via the translation_strings.py file. Logs don't require translation.
- Read the `docs/Architecture.md` guidelines when planning new features.
- Do not remove useful line comments when refactoring

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

**DO write:**
- Positive tests verifying components ARE wired correctly
- Tests for behavioral contracts and public APIs
- Integration tests validating component interactions
- Tests that would catch regressions if removed

**Test cleanup principle:** If a test doesn't provide ongoing value (catch bugs, document behavior, validate architecture), don't write it or remove it.

## Type Information

FreeCAD type stubs are installed via `uv` at `.venv/lib/python3.12/site-packages/`. Check these `.pyi` files before assuming FreeCAD API behavior or when implementing FreeCAD integration code.

## FreeCAD Runtime

For exploring the actual FreeCAD runtime API, use the extracted FreeCAD AppImage:

```bash
./run_with_freecad.sh python -c "import FreeCAD; print(dir(FreeCAD))"
```

This runs Python with FreeCAD's built-in interpreter and bindings, giving access to live API inspection when stubs are incomplete or uncertain.

There is also a test freecad file you can inspect, in `tests/freecad/BasicFile.FCStd`.
The FreeCADGui module is not available using this script. So if you need to debug something that calls any of the Gui APIs, you must create a new python file in the `freecad/diff_wb` directory with logging and call it in the `workbench.py`'s Activated method. Then ask the user to run freecad and report the output logs.
