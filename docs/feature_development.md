# FreeCAD Diff Workbench: AI Development Process Guide

## Overview

This guide provides a structured process for AI-assisted development in the FreeCAD Diff Workbench. It leverages the project's clean architecture (ports/adapters pattern) to maximize testability while providing a mechanism for exploring the FreeCAD Python API when needed.

## Task Plan Requirement

**Before starting any feature implementation, create a task plan.**

Per AGENTS.md rules, all task plans must be written to the `tasks/` directory in the format `x-plan-name.md` where x is a sequential number. Plans must be kept up-to-date AT ALL TIMES during implementation.

### Purpose: Decision History (Like an ADR)

Task plans serve as an **Architecture Decision Record (ADR)** for AI-assisted development:

- **Capture reasoning**: Document why certain approaches were chosen over alternatives
- **Track evolution**: Record how understanding changed during API exploration
- **Enable continuity**: Provide context for future AI sessions working on related features
- **Prevent repetition**: Avoid re-exploring decisions already made

This history is made available to AIs working on subsequent tasks, enabling them to learn from past decisions and maintain consistency across the codebase.

### Task Plan Template

```markdown
# Task: [Feature Name]

## Goal
[Clear description of what this feature accomplishes]

## Context
[Background information, user requirements, constraints]

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| [What] | [Why] | [What was rejected and why] |
| ... | ... | ... |

## Architecture Impact
[Where will this code live? Which modules are affected?]

## FreeCAD Dependency
- [ ] No FreeCAD required (pure code)
- [ ] FreeCAD required (follow exploration phase)

## Implementation Plan
### Phase 1: [Name]
- [ ] [Step 1]
- [ ] [Step 2]

### Phase 2: [Name]
- [ ] ...

## Test Strategy
- Unit tests: [What will be tested with fakes/mocks]
- Integration tests: [What requires real FreeCAD]

## Findings & Notes
[API exploration results, edge cases discovered, lessons learned]
```

### When to Update the Plan

- **Before starting**: Initial plan based on requirements
- **After API exploration**: Update with discovered API behavior
- **When encountering challenges**: Document obstacles and how they were resolved
- **When scope changes**: Record new requirements or expanded functionality
- **Upon completion**: Final summary of what was implemented and why

## Architecture Summary

The project follows a **ports and adapters** pattern:

```
Entry Points → UI Layer → Controller Layer
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
    Snapshot Module       Diff Engine        Domain Models
     (uses port)         (pure code)        (pure code)
         │
         ▼
    Ports Layer (FreeCadPort, GuiPort, SettingsPort, AppPort)
         │
         ▼
   FreeCAD Runtime (when available)
```

## When FreeCAD is Needed

| Layer/Module | FreeCAD Required? | Testing Approach |
|--------------|-------------------|------------------|
| **Domain Models** (`domain/`) | No | Unit tests with pytest |
| **Diff Engine** (`diff/`) | No | Unit tests with pytest |
| **Snapshot Store** (`snapshot/snapshot_store.py`) | No | Unit tests with pytest |
| **Presenter Logic** (`ui/*_presenter.py`) | No | Unit tests with pytest |
| **Snapshot Query/Mutations** (`snapshot/`) | Yes | Unit tests with fakes + Integration tests with `run_with_freecad.sh` |
| **Port Adapters** (`ports/`) | Yes | Unit tests with mocks + Integration tests with `run_with_freecad.sh` |
| **UI Widgets** (`ui/`) | Yes | Unit tests with mocks + Integration tests with `run_with_freecad.sh` |

---

## Development Process

### For Features Requiring FreeCAD

Follow these 4 phases:

#### Phase 1: API Exploration (Requires FreeCAD)

**Goal**: Understand the FreeCAD API behavior before writing code.

1. **Identify required APIs** based on feature requirements
2. **Create a simple exploration script** that uses only the FreeCAD API:
   ```python
   import FreeCAD
   
   doc = FreeCAD.openDocument("/path/to/file.FCStd")
   # Explore objects, properties, etc.
   ```
3. **Run with FreeCAD**:
   ```bash
   ./run_with_freecad.sh python explore_script.py
   ```
4. **Document findings** in `docs/api-exploration/` if results are reusable

#### Phase 2: Plan Update (No FreeCAD)

**Goal**: Capture API knowledge before implementation.

1. Note API signatures discovered during exploration
2. Record example outputs from real FreeCAD runs
3. Identify edge cases (objects without certain properties, etc.)

#### Phase 3: Test-Driven Development (No FreeCAD)

**Goal**: Write tests using fakes/mocks before implementation.

1. **Create fake objects** that mimic FreeCAD API structure
2. **Write unit tests** against your fakes
3. **Run tests** (should fail initially)
4. **Implement the feature** using port abstractions
5. **Run tests again** (should pass)

#### Phase 4: Integration Testing (Requires FreeCAD)

**Goal**: Verify implementation works with real FreeCAD documents.

1. **Create integration test** using real FreeCAD
2. **Run with FreeCAD**:
   ```bash
   ./run_with_freecad.sh python test_integration.py
   ```
3. **Debug if needed** by creating minimal reproduction scripts

---

### For Pure Code Features (No FreeCAD Required)

For features in `domain/`, `diff/`, `snapshot/snapshot_store.py`, or presenter logic:

1. **Write unit tests** with fakes/mocks as needed
2. **Run tests** (should fail initially)
3. **Implement the feature**
4. **Run tests and linter** (`pytest`, `ruff check`)

Skip Phases 1, 2, and 4 - no FreeCAD interaction needed.

---

## Quick Reference: Common FreeCAD API Patterns

### Documents
```python
doc = FreeCAD.openDocument("/path/to/file.FCStd")
doc = FreeCAD.ActiveDocument
for obj in doc.Objects: ...
obj = doc.getObject("Name")
```

### Properties
```python
value = getattr(obj, "PropertyName")
expr = obj.getExpression("PropertyName")  # "" if none
obj.setExpression("PropertyName", "expr")
```

### Object Hierarchy
```python
parents = obj.InList      # Objects referencing this
children = obj.OutList    # Objects referenced by this
subs = obj.getSubObjects()
```

### Recompute & GUI
```python
doc.recompute()
if FreeCADGui: FreeCADGui.update()
```

---

## Artifact Generation

When API exploration produces valuable information, create artifacts:

- **`docs/api-exploration/*.md`** - API findings and patterns
- **`docs/api-exploration/examples/*.txt`** - Raw output samples
- **`scripts/generate_test_data.py`** - Test document generators

---

## Summary Workflow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│ 1. IDENTIFY: Does feature need FreeCAD? │
└─────────────────────────────────────┘
  │
  ├─ NO ──► [Pure Code Path]
  │           • Write unit tests
  │           • Implement
  │           • Run tests + linter
  │
  └─ YES ─► [FreeCAD Path]
              • Phase 1: Explore API with run_with_freecad.sh
              • Phase 2: Document findings
              • Phase 3: TDD with fakes
              • Phase 4: Integration test with FreeCAD
```

---

## Key Principles

1. **Maximize testability**: Keep core logic free from FreeCAD dependencies
2. **Explore first**: Use `run_with_freecad.sh` to understand API behavior before coding
3. **Document findings**: Create artifacts that help future development
4. **TDD approach**: Write tests with fakes before implementing real code
5. **Debug with reality**: When things don't work, verify against real FreeCAD
