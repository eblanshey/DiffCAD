# Task: Show Unchanged Properties in Property List

## Goal

Display all properties (including unchanged ones) in the property diff list when a node is selected, with unchanged properties shown in a neutral/gray color.

## Context

Currently, Phase 12 implementation filters out UNCHANGED properties:
- **Domain layer** (`comparator.py`): Only includes properties with actual changes (ADDED, DELETED, MODIFIED)
- **Presenter** (`diff_presenter.py`): Skips UNCHANGED properties with `continue`
- **View** (`diff_panel_view.py`): Filters UNCHANGED properties before display

The user wants unchanged properties to also appear in the list, but with a neutral/gray color to distinguish them from changed properties.

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Change comparator to include all properties | Single source of truth - all downstream code gets unchanged properties automatically | Add parameter to toggle filtering - adds complexity |
| Display format: just value for unchanged | Simpler display since old == new, no need for arrows | "value ≡ value" format - rejected as too verbose |
| Light gray for unchanged | Subtle, neutral, clearly distinguishes from green/red/blue | White - not distinct enough; yellow - confusing with modified |

## Architecture Impact

**Files Modified:**
- `freecad/diff_wb/domain/diff/comparator.py` - Include all properties, not just changed
- `freecad/diff_wb/ui/presenters/diff_presenter.py` - Remove skip for UNCHANGED
- `freecad/diff_wb/ui/views/diff_panel_view.py` - Add UNCHANGED color and display logic
- `tests/unit/domain/diff/test_comparator.py` - Update test expectation

**No FreeCAD Required:**
- All changes are pure Python/ Qt - no FreeCAD API needed

## Implementation Plan

**IMPORTANT:** Follow TDD principles - write tests first, then implement to pass tests.

---

### Phase 1: Update Comparator to Include All Properties

#### Step 1: Update Test First
**File:** `tests/unit/domain/diff/test_comparator.py`

Find test `test_only_unchanged_filtered_out` (lines 1415-1426) and update to expect unchanged properties INCLUDED:

```python
def test_only_unchanged_included(self):
    """Test that unchanged properties are included in result."""
    old_props = {
        "Prop1": Property.create(PropertyType.FLOAT, 10.0),
        "Prop2": Property.create(PropertyType.STRING, "same"),
    }
    new_props = {
        "Prop1": Property.create(PropertyType.FLOAT, 10.0),
        "Prop2": Property.create(PropertyType.STRING, "same"),
    }
    result = compare_properties(old_props, new_props)
    assert len(result) == 2
    for prop_diff in result:
        assert prop_diff.state == DiffState.UNCHANGED
```

#### Step 2: Modify Comparator
**File:** `freecad/diff_wb/domain/diff/comparator.py`

**Location:** Lines 544-570 in `PropertyComparator.compare_properties()`

**Change 1:** Update docstring at line 544:
```python
# Before:
"""...List of PropertyDiff objects for non-excluded properties that have differences"""

# After:
"""...List of PropertyDiff objects for all non-excluded properties (including unchanged)"""
```

**Change 2:** Remove filter at lines 566-568:
```python
# Remove these lines:
# Only include if there's an actual difference
if prop_diff.state != DiffState.UNCHANGED:
    property_diffs.append(prop_diff)

# Replace with (always append):
property_diffs.append(prop_diff)
```

---

### Phase 2: Update Presenter to Include Unchanged Properties

#### Step 1: Modify Presenter
**File:** `freecad/diff_wb/ui/presenters/diff_presenter.py`

**Location:** Lines 118-121 in `_transform_property_diffs()`

Remove the `continue` statement that skips UNCHANGED:

```python
# Before:
for prop_diff in node_diff.property_diffs:
    # Skip unchanged properties
    if prop_diff.state == DiffState.UNCHANGED:
        continue

# After:
for prop_diff in node_diff.property_diffs:
    # Process all properties (including unchanged)
```

---

### Phase 3: Update View to Display Unchanged Properties

#### Step 1: Add UNCHANGED_COLOR Constant
**File:** `freecad/diff_wb/ui/views/diff_panel_view.py`

**Location:** Line ~125 (after MODIFIED_COLOR)

```python
MODIFIED_COLOR = QColor(200, 200, 255)  # Light blue
UNCHANGED_COLOR = QColor(240, 240, 240)  # Light gray (neutral)
```

#### Step 2: Update show_properties() Method
**File:** `freecad/diff_wb/ui/views/diff_panel_view.py`

**Location:** Lines 384-419 in `show_properties()`

**Change 1:** Remove filter at line 385:
```python
# Before:
changed_properties = [p for p in properties if p.state != "UNCHANGED"]

# After (include ALL properties):
all_properties = properties
```

**Change 2:** Update loop to handle UNCHANGED state:
```python
# Before: for row, prop in enumerate(changed_properties):
for row, prop in enumerate(all_properties):

# Add UNCHANGED handling in color logic:
if prop.state == "ADDED":
    bg_color = self.ADDED_COLOR
    value_text = f"+ {prop.new_display}"
elif prop.state == "DELETED":
    bg_color = self.DELETED_COLOR
    value_text = f"- {prop.old_display}"
elif prop.state == "MODIFIED":
    bg_color = self.MODIFIED_COLOR
    value_text = f"{prop.old_display} → {prop.new_display}"
else:  # UNCHANGED
    bg_color = self.UNCHANGED_COLOR
    value_text = prop.new_display  # Just the value, no arrows
```

---

### Phase 4: Run Tests and Fix Issues

#### Step 1: Run Unit Tests
```bash
cd /home/flyer/Repositories/freecad_diff_workbench
uv run pytest tests/unit/domain/diff/test_comparator.py -v -k "unchanged"
uv run pytest tests/unit/ui/presenters/test_diff_presenter_properties.py -v
uv run pytest tests/unit/ui/views/test_diff_panel_view.py -v
```

#### Step 2: Run Linters
```bash
cd /home/flyer/Repositories/freecad_diff_workbench
uv run ruff check freecad/diff_wb/domain/diff/comparator.py
uv run ruff check freecad/diff_wb/ui/presenters/diff_presenter.py
uv run ruff check freecad/diff_wb/ui/views/diff_panel_view.py
uv run mypy freecad/diff_wb/domain/diff/comparator.py
uv run mypy freecad/diff_wb/ui/presenters/diff_presenter.py
uv run mypy freecad/diff_wb/ui/views/diff_panel_view.py
```

---

## Test Strategy

### Unit Tests (No FreeCAD)
- **Comparator tests**: Verify all properties included, including unchanged
- **Presenter tests**: Transform includes unchanged properties
- **View tests**: Display with correct color and format

### No Integration Tests Needed
- Pure Python/ Qt changes - no FreeCAD API involved

---

## Display Format Summary

| State | Background Color | Value Format |
|-------|------------------|--------------|
| ADDED | Light green (200, 255, 200) | `+ {new_value}` |
| DELETED | Light red (255, 200, 200) | `- {old_value}` |
| MODIFIED | Light blue (200, 200, 255) | `{old_value} → {new_value}` |
| UNCHANGED | Light gray (240, 240, 240) | `{value}` (just the value) |

---

## Findings & Notes

### Why This Works

1. **Domain first**: Changing the comparator at the source means all downstream code automatically gets all properties
2. **No parameter bloat**: No need to add flags like `include_unchanged=True` to multiple methods
3. **Statistics still work**: `NodeDiff.changed_properties()` continues to filter for stats/counts - it was already designed for this purpose

### Backward Compatibility

- `NodeDiff.property_diffs` now includes ALL properties (changed + unchanged)
- Code that was filtering UNCHANGED (like `_are_properties_modified()`) uses `.changed_properties` instead - already works correctly
- Existing code that iterates `property_diffs` will now see more items - fine since UNCHANGED state is handled gracefully