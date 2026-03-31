# Task: 3-Column Property Diff Layout

## Goal
Change the property diff tree from 2 columns (Property, Value) to 3 columns (Property, Value Left, Value Right), with proper diff display for expandable properties and correct coloring rules.

## Context
Currently the property diff tree shows modified values as `oldval -> newval` in a single Value column. The user wants separate columns for left (old) and right (new) values, with correct expansion behavior and coloring for sub-properties.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Add old_value field to PropertyPresentation | Need access to both old and new values to compute sub-property diffs in the view | Parse old_display string, but that's fragile and doesn't work for all types |
| Compute child diffs in view layer | Keeps presenter changes minimal; view already has expansion logic | Move logic to presenter, but that's more invasive |
| Color unchanged children with default background | User explicitly requested this behavior | Color all children consistently, but user specified default for unchanged |

## Architecture Impact
- **Files affected**:
  - `freecad/diff_wb/ui/presenters/presentation_models.py` - Add old_value field
  - `freecad/diff_wb/ui/presenters/diff_presenter.py` - Pass old_value to PropertyPresentation
  - `freecad/diff_wb/ui/views/diff_panel_view.py` - Change column layout and child rendering

## FreeCAD Dependency
- [x] No FreeCAD required (pure Qt UI changes)

## Implementation Plan
**IMPORTANT:** For each phase, ALWAYS write test steps BEFORE implementation steps to follow TDD principles.

### Phase 1: Update PropertyPresentation model
- [ ] Add `old_value: Any = None` field to PropertyPresentation dataclass
- [ ] Add `new_value: Any = None` field to PropertyPresentation dataclass (rename current `value` to `new_value` for clarity)
- [ ] Write unit tests verifying the new fields are properly set

### Phase 2: Update DiffPresenter to pass both values
- [ ] Update `_transform_property_diffs` to pass old_value to PropertyPresentation
- [ ] Pass both old and new values for expandable properties
- [ ] Write unit tests verifying old_value is correctly passed

### Phase 3: Update DiffPanelView 3-column layout
- [ ] Change column count from 2 to 3: `setColumnCount(3)`
- [ ] Update header labels: `["Property", "Value Left", "Value Right"]`
- [ ] Update `_create_group_header_item` to use 3 columns
- [ ] Update `_create_property_tree_item`:
  - For ADDED: column 1 empty, column 2 = new_display
  - For DELETED: column 1 = old_display, column 2 empty  
  - For MODIFIED: column 1 = old_display, column 2 = new_display
  - For UNCHANGED: column 1 = new_display, column 2 = new_display
- [ ] Apply diff coloring to all 3 columns for the property row
- [ ] Update group header creation to use 3 columns

### Phase 4: Handle expandable properties with child diffs
- [ ] Modify `_create_property_tree_item` to accept old_value for computing child diffs
- [ ] For each child:
  - Get old_child_value and new_child_value
  - Compare to determine state (MODIFIED/ADDED/DELETED/UNCHANGED)
  - Create child item with 3 columns: name, old_value_str, new_value_str
  - Apply background color only if state is MODIFIED/ADDED/DELETED
- [ ] If any child has MODIFIED/ADDED/DELETED state, color the parent row blue (MODIFIED color)
- [ ] Write tests for expandable properties with child diffs

### Phase 5: Run linters and tests
- [ ] Run `task check` to verify code style
- [ ] Run `task test` to verify all unit tests pass
- [ ] Fix any issues found

## Test Strategy
- **Unit tests**: Test PropertyPresentation fields, presenter transformation, view column layout
- **Unit tests**: Test expandable properties with both old/new values showing
- **Unit tests**: Test coloring rules (colored for changed, default for unchanged children)

## Findings & Notes
- The current implementation only stores `value` (new value) in PropertyPresentation
- Need to also pass old_value to enable child diff computation
- The `get_property_children` function in property_tree.py needs to be used twice: once for old value, once for new value
- Child state comparison: compare old and new child values to determine state