# Task: Fix Property Viewer Bugs

## Goal
Fix three bugs found after implementing property-viewer-refactor-plan.md:
1. Groups should be sorted alphabetically in the property tree
2. Hidden properties (Shape, ShapeMaterial) are incorrectly included in snapshots  
3. Properties with complex values are incorrectly expanding the Property object itself instead of its value

## Context
The property viewer refactor was implemented but has three bugs:
- Groups appear in insertion order, not alphabetically
- Hidden properties like Shape/ShapeMaterial still appear (need getTypeOfProperty check)
- Complex property values are being incorrectly expanded (passing Property object instead of .value)

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Sort groups alphabetically | User expectation and FreeCAD UI behavior | Keep insertion order (rejected - user requested fix) |
| Add getTypeOfProperty check | Replicates PropertyView::isPropertyHidden() from src/Gui/PropertyView.cpp line 242-246 | Only check getEditorMode (rejected - misses some hidden props) |
| Extract .value from Property | Property object has type_, value, expression, group - we need just value | Pass entire Property (rejected - causes wrong expansion) |

## Architecture Impact
- **diff_panel_view.py**: Sort groups dict before rendering
- **gui_extractor.py**: Add getTypeOfProperty check to hidden detection
- **diff_presenter.py**: Extract .value from Property object before passing to UI

## FreeCAD Dependency
- [x] Yes - Need to verify hidden property detection with FreeCAD

---

## Implementation Plan

### Phase 1: Fix Group Sorting (Alphabetical Order)

**Priority: HIGH** - User-facing bug

- [x] Write tests for group sorting
  - Test: Groups appear in alphabetical order (Base, Data, Format, etc.)
  - Test: Properties within groups maintain their order
- [x] Fix `show_properties()` in diff_panel_view.py
  - Sort groups dict by keys before iteration:
  ```python
  # Before (line ~422):
  for group_name, group_props in groups.items():
  
  # After:
  for group_name in sorted(groups.keys()):
      group_props = groups[group_name]
  ```
- [x] Verify with integration test using BasicFile

---

### Phase 2: Fix Hidden Property Detection

**Priority: HIGH** - User-facing bug

This replicates the logic from FreeCAD's `PropertyView::isPropertyHidden()` in `src/Gui/PropertyView.cpp` (line 242-246):
```cpp
bool PropertyView::isPropertyHidden(const App::Property* prop)
{
    return prop && !showAll()
        && ((prop->getType() & App::Prop_Hidden) || prop->testStatus(App::Property::Hidden));
}
```

The C++ code checks:
1. `!showAll()` - user hasn't enabled "Show Hidden" (we assume False for normal behavior)
2. `prop->getType() & App::Prop_Hidden` → `obj.getTypeOfProperty(prop_name)` returns list containing 'Hidden'
3. `prop->testStatus(App::Property::Hidden)` → `obj.getPropertyStatus(prop_name)` has 'Hidden' string OR bit 4 set

We already check conditions 2-3 partially. We need to add the missing check for `getTypeOfProperty()`.

- [x] Write tests for hidden property detection via getTypeOfProperty
   - Test: getTypeOfProperty returning ['Hidden'] is detected as hidden
   - Test: Properties with Hidden in getTypeOfProperty are filtered out
- [x] Fix `_is_property_hidden()` in gui_extractor.py
   - Add check for getTypeOfProperty returning 'Hidden':
   ```python
   # Add after existing checks:
   # Replicates FreeCAD's PropertyView::isPropertyHidden() logic
   # from src/Gui/PropertyView.cpp line 242-246
   get_type_of_property = getattr(obj, "getTypeOfProperty", None)
   if get_type_of_property is not None:
       prop_types = get_type_of_property(prop_name)
       if "Hidden" in prop_types:
           return True, "type_hidden"
   ```
- [x] Test with Body object - verify Shape and ShapeMaterial are filtered

---

### Phase 3: Fix Property Value Extraction for Expansion

**Priority: HIGH** - Core bug causing incorrect display

- [x] Write tests for property value extraction
   - Test: Property object with list value expands correctly
   - Test: Property object with dict value expands correctly
   - Test: Property with Vector/Placement expands correctly
- [x] Fix `_transform_property_diffs()` in diff_presenter.py (line ~129)
   - Extract `.value` from Property object instead of passing the Property itself:
   ```python
   # Before:
   value = prop_diff.new_value if prop_diff.new_value is not None else prop_diff.old_value
   
   # After:
   if prop_diff.new_value is not None:
       value = prop_diff.new_value.value
   elif prop_diff.old_value is not None:
       value = prop_diff.old_value.value
   else:
       value = None
   ```
- [x] Verify with Constraints property (list of Constraint objects) - should expand to show each constraint, not the Property's internal structure

---

## Test Strategy

### Unit Tests (No FreeCAD Required)
- Group sorting logic in diff_panel_view.py
- Property value extraction in diff_presenter.py

### Integration Tests (FreeCAD Required)
- Hidden property detection with Body object
- Group sorting in actual snapshot
- Property expansion with complex values (Constraints, Placement)

---

## Expected Results

### After Fix 1 - Alphabetical Groups
```
▼ Base
    Label: Body
    Placement: ...
▼ Data
    Length: 10mm
    ...
▼ Sketch
    Constraints: [50 items]
```

### After Fix 2 - Hidden Properties Filtered
- Shape property should NOT appear in snapshot
- ShapeMaterial property should NOT appear in snapshot  
- Label, Placement should still appear

### After Fix 3 - Correct Value Expansion
```
Constraints: [<Constraint 'Coincident'>, <Constraint 'Coincident'>, ...]
    ├── [0]: Coincident
    ├── [1]: Coincident
    └── [2]: ...
```
NOT:
```
Constraints: Property(...)
    ├── type_: PropertyType
    ├── value: [...]
    ├── expression
    └── group: Sketch
```

---

## Complexity Trade-offs

### What We're NOT Doing
1. Full refactoring of Property class - just fixing the value extraction bug
2. Additional UI changes beyond these three bugs

### Maintainability
- Minimal changes to existing code
- Clear separation: Property object vs Property.value
- Sorted groups improve UX