# Task: Property Viewer Refactor - Match FreeCAD Behavior

## Goal
Refactor the property viewer to match FreeCAD's property panel behavior:
1. Fix hidden property detection bug (check Prop_Hidden status bit)
2. Add property groups with headers
3. Add expandable properties (Placement, Vector, Lists)
4. Match property ordering
5. Add spaces to CamelCase property names

## Context
The current implementation has several issues:
- Hidden property detection only checks getEditorMode() - misses Prop_Hidden bit
- SavedGeometry incorrectly shows in our viewer (has Prop_Hidden bit)
- No property grouping (flat list)
- No expandable/collapsible properties
- Properties appear out of order
- CamelCase property names don't have spaces

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Check Prop_Hidden status bit | FreeCAD uses this to hide SavedGeometry | Only check getEditorMode (rejected - misses cases) |
| Use QTreeWidget over QTreeView | Simpler API, sufficient for display-only | Full QAbstractItemModel (too complex) |
| Explicit + generic list expansion | Good coverage, low complexity | Full type mapping (too many types) |
| Space insertion for CamelCase | Matches FreeCAD's display | Keep as-is (rejected - user requested) |

## Architecture Impact
- **gui_extractor.py**: Fix hidden detection, add group extraction
- **diff_panel_view.py**: Replace QTableWidget with QTreeWidget
- **New module**: `property_tree.py` for property tree building

## FreeCAD Dependency
- [x] Yes - Need to verify behavior with FreeCAD

---

## Implementation Plan

### Phase 1: CRITICAL FIX - Hidden Property Detection

**Priority: CRITICAL** - SavedGeometry incorrectly shows in our viewer

- [x] Write tests for hidden property detection
  - Test: SavedGeometry should be hidden (has Prop_Hidden bit)
  - Test: Label should be visible (no Prop_Hidden)
  - Test: Properties with getEditorMode=["Hidden"] are hidden
  - Test: Properties with empty group are VISIBLE (in "Base" group)
- [x] Fix `_is_property_hidden()` in gui_extractor.py
  - Check BOTH `getEditorMode()` and `getPropertyStatus()`
  - Decode Prop_Hidden bit (value 4) from status integer
  - Remove incorrect "empty group = hidden" logic
- [x] Verify with BasicFile test case

**Code change:**
```python
def _is_property_hidden(obj, prop_name: str) -> tuple[bool, str]:
    # Check 1: getEditorMode() contains "Hidden"
    get_editor_mode = getattr(obj, "getEditorMode", None)
    if get_editor_mode is not None:
        editor_mode = get_editor_mode(prop_name)
        if "Hidden" in editor_mode:
            return True, "editor_mode_hidden"
    
    # Check 2: getPropertyStatus() has Prop_Hidden bit (value 4)
    get_property_status = getattr(obj, "getPropertyStatus", None)
    if get_property_status is not None:
        status = get_property_status(prop_name)
        if status and (status[0] & 4):  # Prop_Hidden = 4
            return True, "prop_hidden_bit"
    
    # Check 3: Empty group should be visible (maps to "Base")
    # REMOVED - this was the bug!
    
    return False, ""
```

---

### Phase 2: Extract Property Groups

**Priority: HIGH** - Enables grouping in the UI

- [x] Write tests for group extraction
  - Test: Properties return correct group name
  - Test: Empty group returns "Base"
- [x] Add `_get_property_group()` function in gui_extractor.py
  - Call `getGroupOfProperty()`
  - Return "Base" for empty strings
- [x] Modify `_extract_visible_properties()` to return group info
- [x] Update Property dataclass to include group field
- [x] Verify with BasicFile - check groups for Dimension, Sketch, etc.

---

### Phase 3: CamelCase to Spaces

**Priority: MEDIUM** - Match FreeCAD's display naming

- [x] Write tests for CamelCase conversion
  - Test: "SavedGeometry" → "Saved Geometry"
  - Test: "Placement" → "Placement" (no change, single word)
  - Test: "Label2" → "Label 2"
  - Test: "XDirection" → "X Direction"
- [x] Add helper function in property_tree.py:
```python
def _camelcase_to_spaces(name: str) -> str:
    """Insert spaces before uppercase letters, matching FreeCAD display."""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0 and not name[i-1].isupper():
            result.append(' ')
        result.append(char)
    return ''.join(result)
```
- [x] Apply to property names when displaying

---

### Phase 4: Build Property Tree Structure

**Priority: HIGH** - Core data structure for tree view

- [x] Write tests for property tree building
  - Test: Group headers created for each group
  - Test: Properties sorted under correct groups
  - Test: Expandable properties have children
  - Test: Position (child of Placement) also expands to x, y, z
  - Test: Nested list elements expand to their properties
  - Test: Dict-like objects expand by key
- [x] Create `freecad/diff_wb/ui/views/property_tree.py`
- [x] Implement unified recursive expansion (single function for ALL cases):

```python
def get_property_children(name: str, value: Any) -> list[tuple[str, Any]]:
    """Get children for any property value.
    
    Recursively expands:
    - Explicit types (Placement, Rotation) with named children
    - Vector-like objects (x, y, z attributes)
    - Lists/tuples (by index)
    - Dicts (by key)
    - Objects with __dict__ (by attribute)
    """
    if value is None:
        return []
    
    # 1. Explicit types with known structure
    if name == "Placement":
        return _expand_placement(value)
    if name == "Rotation":
        return _expand_rotation(value)
    if name == "Material":
        return _expand_material(value)
    
    # 2. Vector-like objects (has x, y, z)
    if hasattr(value, 'x') and hasattr(value, 'y') and hasattr(value, 'z'):
        return [("x", value.x), ("y", value.y), ("z", value.z)]
    
    # 3. Lists/tuples - expand by index
    if isinstance(value, (list, tuple)) and len(value) > 0:
        return [(f"[{i}]", v) for i, v in enumerate(value)]
    
    # 4. Dicts - expand by key
    if isinstance(value, dict) and len(value) > 0:
        return [(str(k), v) for k, v in value.items()]
    
    # 5. Objects with __dict__ - expand public attributes
    attrs = getattr(value, '__dict__', None)
    if attrs:
        return [(k, v) for k, v in attrs.items() if not k.startswith('_')]
    
    return []


def is_expandable(value: Any) -> bool:
    """Check if value should display as expandable (has children)."""
    if value is None:
        return False
    
    # Check each expansion type
    if isinstance(value, (list, tuple)) and len(value) > 0:
        return True
    if isinstance(value, dict) and len(value) > 0:
        return True
    if hasattr(value, 'x') and hasattr(value, 'y') and hasattr(value, 'z'):
        return True
    if getattr(value, '__dict__', None):
        return True
    
    return False
```

**Key insight:** One unified function handles ALL cases. Children that are also expandable will automatically show expand arrows - no special recursion needed in UI.

---

### Phase 5: QTreeWidget UI

**Priority: HIGH** - Replace table with tree

- [x] Write tests for tree widget rendering
  - Test: Groups display as headers with background color
  - Test: Expandable properties show expand/collapse
  - Test: Diff coloring works
- [x] Modify diff_panel_view.py
  - Replace QTableWidget → QTreeWidget
  - Two columns: Name | Value
- [x] Implement group header rendering:
  - Background color (like FreeCAD's gray)
  - Non-selectable
- [x] Apply diff coloring:
  - Added: green background
  - Deleted: red background
  - Modified: blue background

---

### Phase 6: Integration Testing

**Note:** Generic expansion is handled by the unified `get_property_children()` in Phase 4. No separate phase needed.

**Priority: HIGH** - Verify end-to-end

- [x] Run integration tests with BasicFile
  - Verify SavedGeometry is now hidden
  - Verify groups match FreeCAD
  - Verify expandable properties work
- [x] Test with various object types:
  - App::Part (Placement, Color)
  - Sketcher::SketchObject (Constraints)
  - TechDraw::DrawViewDimension

---

## Test Strategy

### Unit Tests (No FreeCAD Required)
- CamelCase conversion
- Tree building logic
- Diff coloring logic

### Integration Tests (FreeCAD Required)
- Hidden property detection (SavedGeometry, Label)
- Group extraction
- Full tree rendering with BasicFile

---

## Expected Results

### Property Display Format (with Nested Expansion)
```
▼ Base
    Label: Dimension
    X: 0.0 mm
    Y: 50.41 mm
    ─────────────────
▼ Format
    FormatSpec: %.2w
    Arbitrary: false
    ─────────────────
▼ References
    [0]: <Edge>
    [1]: <Edge>
    ─────────────────
▼ Constraints (for Sketch)
    ├── [0]: Horizontal: 50mm
    ├── [1]: Vertical: 30mm
    └── [2]: Point: [10mm, 20mm]
        ├── x: 10mm
        └── y: 20mm
```

### Expandable Placement (Nested)
```
▼ Placement: [(0 0 1); 0°; (0 0 0)]
    ├── Angle: 0.00°
    ├── Axis: [0.00 0.00 1.00]
    │   ├── x: 0.00
    │   ├── y: 0.00
    │   └── z: 1.00
    └── Position: [0.00mm 0.00mm 0.00mm]
        ├── x: 0.00 mm
        ├── y: 0.00 mm
        └── z: 0.00 mm
```

### Constraints (Generic List Expansion)
```
▼ Constraints: [50mm; 30mm]
    ├── [0]: 50mm
    └── [1]: 30mm
```

### Nested List (List of Lists)
```
▼ BoxCorners: [[...], [...]]
    ├── [0]: Vector(-15.87, -25.87, 0)
    │   ├── x: -15.87
    │   ├── y: -25.87
    │   └── z: 0
    └── [1]: Vector(15.87, 25.87, 0)
        ├── x: 15.87
        ├── y: 25.87
        └── z: 0
```

---

## Complexity Trade-offs

### What We're NOT Doing
1. Full QAbstractItemModel - Using QTreeWidget instead
2. 20+ PropertyItem types - Only key explicit types
3. Property editing - Display only

### Maintainability
- Simple tree structure
- Clear separation of concerns
- Generic list handling for edge cases