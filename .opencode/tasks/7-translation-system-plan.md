# Task: Implement Qt Placeholder-Based Translation System

## Goal
Replace the current ad-hoc translation approach with Qt's native placeholder-based translation system where views handle both translation templates and parameter substitution using `%1`, `%2` placeholders. This follows Qt conventions, keeps presenters pure and testable, and supports dynamic language changes.

## Context
The user is familiar with Laravel's key-based translation system but needs to understand Qt's string-matching approach. After reviewing Qt documentation, we chose Option 1 (Qt Native Placeholders) which:
- Uses `%1`, `%2` placeholders in translation templates
- Has views handle both translation AND parameter substitution
- Keeps presenters passing raw data only (no message formatting)
- Centralizes all translation strings in one module
- Supports dynamic language changes via `LanguageChange` events

**User Decisions:**
1. **Context naming**: Use `"Common"` for shared error/loading messages
2. **Error handling**: Option A - Translate template only, append exception details as-is
3. **Summary display**: Option B - Individual labels ("Added: 5", "Deleted: 3", "Modified: 2")

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Qt placeholder system (%1, %2) | Follows Qt native conventions; translation files contain templates not variations | Laravel-style key-based system would require custom translation layer on top of Qt |
| Views handle translation + substitution | Keeps presenters pure and testable; views control their own localization | Putting translation in presenters would require mocking translation in all unit tests |
| Centralized `translation_strings.py` | Single source of truth; easy for translators to reference; prevents duplicates | Inline templates in each view would scatter strings across codebase |
| Method signatures accept raw data | Presenters pass snapshot_name instead of pre-formatted message | Passing pre-formatted messages violates separation of concerns |
| Context "Common" for shared errors | Clear semantic meaning; distinguishes from view-specific contexts | Could use "Errors" or "Shared" but "Common" is more descriptive |
| Error messages: translate template only | Exception details are runtime-specific and shouldn't be translated | Translating full message would mix static and dynamic content |
| Summary: individual labels | More flexible for different languages; clearer UI | Single template string would be simpler but less flexible |

## Architecture Impact
**Modules affected:**
- `freecad/diff_wb/ui/` - New translation strings module, updated protocols and presenters
- `freecad/diff_wb/entrypoints/` - No changes needed (already using correct pattern)
- `freecad/diff_wb/freecad_version_check.py` - Fix format placeholder usage
- `tests/unit/ui/presenters/` - Update test expectations for new method signatures
- `docs/Architecture.md` - Add comprehensive translation strategy documentation

**No changes to:**
- Domain layer (pure Python, no translation)
- Application layer actions (pass error messages as-is)
- Entry points (already using `_container.translate()` correctly for static strings)

## FreeCAD Dependency
- [x] No FreeCAD required (pure code changes)
- [ ] FreeCAD required (follow exploration phase)

All changes are in Python code and documentation. The translation infrastructure (`_container.translate()`, `QCoreApplication.translate()`) already exists and is tested. We're just updating the patterns and organization.

## Implementation Plan

### Phase 1: Create Centralized Translation Strings Module
**Test Steps:**
- [ ] Verify file can be imported without errors
- [ ] Verify all constants are exported via `__all__`
- [ ] Run `pytest tests/unit/` to ensure no import breaks

**Implementation Steps:**
- [ ] Create `freecad/diff_wb/ui/translation_strings.py` with:
  - Snapshot view templates (`SNAPSHOT_SUCCESS_TEMPLATE`, `SNAPSHOT_LOADING_DEFAULT`)
  - Diff view templates (`DIFF_SUMMARY_TEMPLATE`, `DIFF_LOADING_MESSAGE`)
  - Common errors (`ERROR_UNKNOWN`, `ERROR_NO_DOCUMENT`)
  - Comprehensive docstrings explaining context and placeholders
  - Proper `__all__` export list

### Phase 2: Update View Protocols
**Test Steps:**
- [ ] Verify Protocol definitions are syntactically correct
- [ ] Check that all protocol methods have proper type hints
- [ ] Run mypy/type checker on protocol files

**Implementation Steps:**
- [ ] Update `freecad/diff_wb/ui/protocols/snapshot_view.py`:
  - Change `show_success(message: str, snapshot_id: str)` → `show_success(snapshot_name: str)`
  - Change `show_error(message: str)` → `show_error(error_message: str)`
  - Change `show_loading(message: str = "Creating snapshot...")` → `show_loading(message: str | None = None)`
  - Add docstrings explaining translation strategy
  - Remove hardcoded default message (views handle translation)
  
- [ ] Review `freecad/diff_wb/ui/protocols/diff_view.py`:
  - `show_summary(added, deleted, modified)` already accepts raw integers ✓
  - Add docstring noting view should use individual labels per user decision

### Phase 3: Update Presenters
**Test Steps:**
- [ ] Write test verifying presenter calls `show_success(snapshot_name="test")` not `show_success(message="...")`
- [ ] Verify presenter doesn't format any user-facing messages
- [ ] Run existing presenter tests after signature changes

**Implementation Steps:**
- [ ] Update `freecad/diff_wb/ui/presenters/snapshot_presenter.py`:
  - Remove f-string formatting in `present_result()`
  - Change `self._view.show_success(message=f"Snapshot '{result.snapshot_name}' created successfully", ...)` 
  - To `self._view.show_success(snapshot_name=result.snapshot_name)`
  - Update docstrings to explain presenter passes raw data only
  
- [ ] Review `freecad/diff_wb/ui/presenters/diff_presenter.py`:
  - Already passes raw integers to `show_summary()` ✓
  - Add comment noting view should use individual labels ("Added: X", etc.)

### Phase 4: Fix Version Check Module
**Test Steps:**
- [ ] Verify version check still works with Python 3.12
- [ ] Check that translated strings contain correct version numbers
- [ ] Test error path when version requirements not met

**Implementation Steps:**
- [ ] Update `freecad/diff_wb/freecad_version_check.py`:
  - Define `_PYTHON_VERSION_WARNING_TEMPLATE` constant with `%s` placeholders
  - Define `_FC_VERSION_WARNING_TEMPLATE` constant with `%s` placeholders
  - Replace `.format()` calls with `%` substitution after translation
  - Pattern: `template = _container.translate("Log", TEMPLATE); translated = template % values`

### Phase 5: Update Architecture Documentation
**Test Steps:**
- [ ] Verify documentation is internally consistent
- [ ] Check all code examples are syntactically correct
- [ ] Ensure translation workflow is clearly explained

**Implementation Steps:**
- [ ] Update `docs/Architecture.md` section "UI Layer Translation Strategy" (lines 417-447):
  - Add "Translation Strategy Overview" subsection
  - Add "Centralized Translation Strings" subsection explaining `translation_strings.py`
  - Add "Static String Example" for entry points
  - Add "Dynamic String Example" for views with placeholder substitution
  - Add "Error Message Handling" subsection (Option A: translate template, append exception)
  - Add "Summary Display" subsection (Option B: individual labels)
  - Add "Translation Workflow" subsection (lupdate → translator → lrelease → runtime)
  - Add "Translation Contexts Reference" table
  - Remove incorrect example showing fully formatted messages passed to views

### Phase 6: Update Tests
**Test Steps:**
- [ ] Run `pytest tests/unit/ui/presenters/test_snapshot_presenter.py` - should fail initially
- [ ] Update test expectations to match new method signatures
- [ ] Run all unit tests - should pass
- [ ] Run `ruff check` and `ruff format` on test files

**Implementation Steps:**
- [ ] Update `tests/unit/ui/presenters/test_snapshot_presenter.py`:
  - Change mock expectations from `show_success(message="Snapshot 'test' created successfully", snapshot_id="123")`
  - To `show_success(snapshot_name="test")`
  - Update any fixtures that create mock view responses
  - Add test verifying presenter passes raw data without formatting
  
- [ ] Search for other tests calling view methods:
  - `grep -r "show_success\|show_error\|show_loading" tests/`
  - Update all matching tests to use new signatures
  - Add `# type: ignore` comments if needed for protocol changes

### Phase 7: Verification and Cleanup
**Test Steps:**
- [ ] Run full test suite: `pytest tests/unit/`
- [ ] Run linting: `ruff check .`
- [ ] Run formatting: `ruff format .`
- [ ] Verify no translation strings are hardcoded outside `translation_strings.py`
- [ ] Check that all entry points still use `_container.translate()` correctly

**Implementation Steps:**
- [ ] Run all tests and fix any failures
- [ ] Fix any linting errors
- [ ] Format all modified files
- [ ] Search for hardcoded strings that should be in `translation_strings.py`:
  - `grep -r "created successfully\|Creating snapshot" --include="*.py" freecad/diff_wb/`
  - Move any found strings to centralized module
- [ ] Update module docstrings to reference translation strategy

## Test Strategy
- **Unit tests**: Verify presenters pass correct raw data to views (mocked). Translation not tested at this level.
- **Integration tests**: (Future) Verify full flow with real FreeCAD translation when Qt views are implemented in Phase 8
- **Manual testing**: Create `.ts` translation files, compile to `.qm`, verify runtime translation works

## Findings & Notes

### Translation Contexts Used
| Context | Purpose | Examples |
|---------|---------|----------|
| `"Workbench"` | Menu items, tooltips, workbench name | "Take Snapshot", "Diff Workbench" |
| `"Log"` | Console messages, version warnings | "Switching to diff_wb", version check messages |
| `"SnapshotView"` | Snapshot UI messages | Success template, loading message |
| `"DiffView"` | Diff UI messages | Summary labels, loading message |
| `"Common"` | Shared error/loading messages | "Unknown error", "No active document" |

### Translation Strings Inventory (20 total)
**Entry Points (Static - Direct Translation):**
1. "Diff Workbench" - Workbench menu
2. "Compare document snapshots" - Workbench tooltip
3. "Take Snapshot" - Command menu
4. "Create a snapshot of the current document" - Tooltip
5. "Compare" - Command menu
6. "Compare snapshots" - Tooltip
7. "Swap Columns" - Command menu
8. "Swap the left and right columns" - Tooltip
9. "Switching to diff_wb" - Log message
10. "Workbench diff_wb activated." - Log message
11. "Workbench diff_wb de-activated." - Log message
12. "Checking FreeCAD version\n" - Log message

**UI Layer (Templates from translation_strings.py):**
13. "Snapshot '%1' created successfully" - SnapshotView context
14. "Creating snapshot..." - SnapshotView context
15. "Added:" - DiffView context (individual label)
16. "Deleted:" - DiffView context (individual label)
17. "Modified:" - DiffView context (individual label)
18. "Computing diff..." - DiffView context
19. "Unknown error occurred" - Common context
20. "No active document available" - Common context

**Version Warnings (Templates - Inline in freecad_version_check.py):**
21. Python version warning template - Log context
22. FreeCAD version warning template - Log context

### Error Message Pattern (Option A)
```python
# View implementation for errors
def show_error(self, error_message: str) -> None:
    if "Unknown error" in error_message:
        # Translate template only
        template = QCoreApplication.translate("Common", ERROR_UNKNOWN)
        self._label.setText(template)
    else:
        # Exception details - display as-is (may contain runtime info)
        # Could optionally wrap in translated template:
        # template = QCoreApplication.translate("Common", "Error: %1")
        # self._label.setText(template % error_message)
        self._label.setText(error_message)
```

### Summary Display Pattern (Option B - Individual Labels)
```python
# View implementation for summary
def show_summary(self, added: int, deleted: int, modified: int) -> None:
    # Translate individual labels
    added_label = QCoreApplication.translate("DiffView", "Added:")
    deleted_label = QCoreApplication.translate("DiffView", "Deleted:")
    modified_label = QCoreApplication.translate("DiffView", "Modified:")
    
    # Display with values
    self._addedLabel.setText(f"{added_label} {added}")
    self._deletedLabel.setText(f"{deleted_label} {deleted}")
    self._modifiedLabel.setText(f"{modified_label} {modified}")
```

### Key Architecture Points
1. **Entry points** use `_container.translate()` directly for static strings (already correct)
2. **Presenters** pass raw data to views, NEVER format user-facing messages (needs fixing)
3. **Views** handle both translation templates AND parameter substitution (to be implemented in Phase 8)
4. **Centralized strings** in `translation_strings.py` prevent duplication and help translators
5. **Translation happens at view creation time**, not on every message display (performance)

### Files Modified Summary
| File | Lines Changed | Type |
|------|---------------|------|
| `freecad/diff_wb/ui/translation_strings.py` | ~60 | NEW |
| `freecad/diff_wb/ui/protocols/snapshot_view.py` | ~10 | MODIFIED |
| `freecad/diff_wb/ui/presenters/snapshot_presenter.py` | ~5 | MODIFIED |
| `freecad/diff_wb/freecad_version_check.py` | ~15 | MODIFIED |
| `docs/Architecture.md` | ~100 | MODIFIED |
| `tests/unit/ui/presenters/test_snapshot_presenter.py` | ~10 | MODIFIED |
| Other tests | ~20 | MODIFIED |
| **Total** | **~220 lines** | **6 files + tests** |
