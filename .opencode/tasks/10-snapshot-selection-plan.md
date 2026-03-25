# Task: Phase 10 - Snapshot Selection

## Goal
Implement snapshot selection mechanism with Ctrl+click multi-selection (max 2), custom color coding (red for "from", green for "to"), and silent rejection of 3rd selection.

## Context
Phase 10 of the Diff Workbench implementation plan. Users need to select 1-2 snapshots from the list column for comparison. The selection UI must:
- Support single-click for first selection
- Support Ctrl+click for second selection
- Apply custom background colors (red/green) instead of Qt default blue
- Reject 3rd selection attempt silently
- Preserve selections when workbench deactivates/reactivates
- Clear selections when snapshot list is refreshed

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| No clear button | Clearing is rare; users naturally replace selections by selecting new ones | Add text button above list (rejected: adds UI complexity for rare operation) |
| Clear on refresh | Fresh state prevents confusion when snapshot list changes | Preserve selections if snapshots still exist (rejected: could show stale/highlighted items after list refresh) |
| Defer Compare command wiring | Phase 10 focused on selection mechanism only | Wire IsActive() to selection count (deferred: Phase 11 handles full compare flow) |
| Silent 3rd selection rejection | Cleanest UX; no visual feedback needed | Flash/tooltip/status message (rejected: adds complexity, silent is acceptable) |
| **Stable color roles** | Items remember their "from"/"to" role even when other items deselected | Shift colors based on position (rejected: unexpected role changes confuse users) |
| Track role per item | Each selected item stores its assigned role ("from"/"to") | Track only indices (rejected: can't maintain stable roles across deselections) |

## Architecture Impact
- **Modified**: `freecad/diff_wb/ui/views/diff_panel_view.py` - Add selection state and methods
- **Tested**: `tests/unit/ui/views/test_diff_panel_view.py` - Add selection test class
- **No changes needed**: `workbench.py`, `commands.py`, `container.py` (deferred to Phase 11)

## FreeCAD Dependency
- [x] No FreeCAD required (pure Qt UI code)
- [ ] FreeCAD required (follow exploration phase)

**Reasoning**: This is pure Qt widget manipulation. Tests can run with headless QApplication. No FreeCAD API calls needed.

## Implementation Plan

### Phase 1: Test-Driven Development for Selection Mechanism

#### Step 1.1: Write Failing Tests First
Create test class `TestSnapshotSelection` in `tests/unit/ui/views/test_diff_panel_view.py`:

```python
class TestSnapshotSelection:
    """Tests for snapshot selection mechanism (Phase 10)."""

    def test_single_click_selects_one_with_red_background(self, panel) -> None:
        """Single click selects one snapshot as 'from' with red background."""
        # Given: 2 snapshots in list
        # When: User clicks first snapshot
        # Then: First snapshot has red background ("from" role)
        pass

    def test_ctrl_click_selects_two_with_different_colors(self, panel) -> None:
        """Ctrl+click selects second snapshot as 'to' with green background."""
        # Given: First snapshot already selected (red, "from")
        # When: User Ctrl+clicks second snapshot
        # Then: Second snapshot has green background ("to" role)
        pass

    def test_ctrl_click_deselects_already_selected_preserves_other_role(self, panel) -> None:
        """Ctrl+click on selected item toggles it off; other item keeps its role."""
        # Given: Two snapshots selected (red="from" + green="to")
        # When: User Ctrl+clicks first (red/"from") snapshot again
        # Then: Only second remains selected with GREEN background (keeps "to" role)
        pass

    def test_deselected_item_can_be_reselected_with_original_role(self, panel) -> None:
        """Deselected item can be reselected and regains its original role."""
        # Given: Row 0 selected as "from" (red), then deselected
        # When: User clicks row 0 again
        # Then: Row 0 becomes "from" again (red background)
        pass

    def test_new_selection_gets_next_available_role(self, panel) -> None:
        """New selection gets appropriate role based on available slots."""
        # Given: Row 0 selected as "from" (red), row 1 deselected
        # When: User selects row 1
        # Then: Row 1 becomes "to" (green background)
        pass

    def test_third_selection_is_rejected(self, panel) -> None:
        """Attempting to select third snapshot is silently rejected."""
        # Given: Two snapshots already selected (red + green)
        # When: User attempts to select third snapshot
        # Then: Selection unchanged, no visual feedback
        pass

    def test_get_selected_snapshot_ids_returns_from_then_to(self, panel) -> None:
        """get_selected_snapshot_ids() returns IDs in role order: [from_id, to_id]."""
        # Given: Two snapshots selected (row 5="from", row 2="to")
        # When: Call get_selected_snapshot_ids()
        # Then: Returns [row_5_id, row_2_id] (from before to, regardless of row order)
        pass

    def test_get_selected_ids_empty_when_nothing_selected(self, panel) -> None:
        """get_selected_snapshot_ids() returns empty list when nothing selected."""
        # Given: No snapshots selected
        # When: Call get_selected_snapshot_ids()
        # Then: Returns []
        pass

    def test_clear_selection_resets_all(self, panel) -> None:
        """clear_selection() deselects all and resets backgrounds."""
        # Given: Two snapshots selected with custom colors
        # When: Call clear_selection()
        # Then: All backgrounds reset to default, no roles tracked
        pass

    def test_selection_cleared_on_refresh(self, panel) -> None:
        """Selections cleared when snapshot list refreshed."""
        # Given: Snapshot selected
        # When: Call show_snapshots() with new snapshot list
        # Then: All selections and roles cleared
        pass
```

#### Step 1.2: Implement Selection State in `DiffPanelView`
File: `freecad/diff_wb/ui/views/diff_panel_view.py`

**Add helper method for default background:**
```python
def _get_default_background(self) -> QColor:
    """Get the default background color from the widget's palette.
    
    Returns:
        The default background color used by QListWidget items.
    """
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPalette
    
    palette = QApplication.palette()
    return palette.color(QPalette.ColorRole.Base)
```

**Add instance variables in `__init__`:**
```python
from dataclasses import dataclass

@dataclass
class _SelectedItem:
    """Tracks a selected snapshot with its assigned role."""
    row: int
    role: str  # "from" or "to"

self._selected_items: dict[int, _SelectedItem] = {}  # row -> _SelectedItem
```

**Connect signal in `_setup_ui`:**
```python
from PySide6.QtWidgets import QAbstractItemView

# After creating snapshot_list:
self.snapshot_list.setSelectionMode(
    QAbstractItemView.SelectionMode.MultiSelection
)
self.snapshot_list.itemSelectionChanged.connect(self._on_selection_changed)
```

**Implement `_on_selection_changed()` method:**
```python
def _on_selection_changed(self) -> None:
    """Handle selection changes with max-2 limit and stable color roles."""
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QAbstractItemView
    
    # Get currently selected rows from Qt
    current_selected_rows = set(
        self.snapshot_list.row(item) 
        for item in self.snapshot_list.selectedItems()
    )
    existing_rows = set(self._selected_items.keys())
    
    # Detect added/removed rows
    added_rows = current_selected_rows - existing_rows
    removed_rows = existing_rows - current_selected_rows
    
    # Handle deselection: remove from tracking, restore to default background
    for row in removed_rows:
        if row in self._selected_items:
            item = self.snapshot_list.item(row)
            if item:
                item.setBackground(self._get_default_background())
            del self._selected_items[row]
    
    # Handle new selection: assign role, apply custom color
    for row in added_rows:
        # Check if we already have 2 selections
        if len(self._selected_items) >= 2:
            # Silent rejection: deselect the newly added item
            self.snapshot_list.clearSelection()
            # Re-select the previous items
            for prev_row in self._selected_items:
                self.snapshot_list.selectRow(prev_row)
            return
        
        # Assign role: "from" if available, otherwise "to"
        has_from = any(item.role == "from" for item in self._selected_items.values())
        role = "to" if has_from else "from"
        
        # Apply custom color and create tracking entry
        item = self.snapshot_list.item(row)
        if item:
            color = QColor(255, 200, 200) if role == "from" else QColor(200, 255, 200)
            item.setBackground(color)
            self._selected_items[row] = _SelectedItem(row=row, role=role)
```

**Add `get_selected_snapshot_ids()` method:**
```python
def get_selected_snapshot_ids(self) -> list[str]:
    """Return snapshot IDs in role order: [from_id, to_id].
    
    Returns:
        List of snapshot IDs ordered by role (from before to), not row order.
        Empty list if nothing selected, single-element list if only one selected.
    """
    from PySide6.QtCore import Qt
    
    ids = []
    # First add "from" if exists
    for item in self._selected_items.values():
        if item.role == "from":
            widget_item = self.snapshot_list.item(item.row)
            if widget_item:
                ids.append(widget_item.data(Qt.ItemDataRole.UserRole))
    # Then add "to" if exists
    for item in self._selected_items.values():
        if item.role == "to":
            widget_item = self.snapshot_list.item(item.row)
            if widget_item:
                ids.append(widget_item.data(Qt.ItemDataRole.UserRole))
    return ids
```

**Add `clear_selection()` method:**
```python
def clear_selection(self) -> None:
    """Clear all selections, reset backgrounds, and clear role tracking."""
    # Reset all tracked item backgrounds to default
    for row in self._selected_items:
        item = self.snapshot_list.item(row)
        if item:
            item.setBackground(self._get_default_background())
    
    # Clear selection and tracking
    self.snapshot_list.clearSelection()
    self._selected_items = {}
```

**Update `show_snapshots()` method:**
```python
# At the start of show_snapshots():
self.clear_selection()  # Clear all selections and roles on refresh
```

### Phase 2: Verify Tests Pass

#### Step 2.1: Run Unit Tests
```bash
task test tests/unit/ui/views/test_diff_panel_view.py::TestSnapshotSelection
```

Expected: All tests pass

#### Step 2.2: Run Linting
```bash
task check
```

Expected: No linting errors

### Phase 3: Manual Integration Test (Optional)

#### Step 3.1: Test in FreeCAD
```bash
task test:integration tests/integration/workbench/test_diff_panel.py
```

Or manually:
1. Switch to Diff workbench
2. Take 3+ snapshots
3. Click first snapshot → verify red background
4. Ctrl+click second snapshot → verify green background
5. Try clicking third → verify no change
6. Ctrl+click first again → verify it deselects, only green remains
7. Take new snapshot → verify selection cleared

## Test Strategy
- **Unit tests**: Pure Qt widget tests with headless QApplication
  - Test selection logic, color application, ID retrieval
  - Test refresh behavior (clear vs persist)
  - No FreeCAD runtime needed
- **Integration tests**: Optional manual testing in FreeCAD GUI
  - Visual verification of colors
  - Workflow testing (select → attempt 3rd → etc.)

## Findings & Notes
- **Qt Selection Mode**: Use `MultiSelection` but override behavior with custom signal handler
- **Background Restoration**: Use `QApplication.palette().color(QPalette.Base)` for default background (no storage needed)
- **Signal Timing**: `itemSelectionChanged` fires after Qt updates selection, so we can detect added/removed rows
- **Color Choice**: Light red/green (RGB 255/200/200, 200/255/200) for visibility without being too saturated
- **Stable Roles**: Each item remembers its "from"/"to" role even when other items are deselected
- **Role Assignment**: First selected gets "from", second gets "to". If "from" is deselected, new selection becomes "from" again.
- **Data Structure**: Use dict mapping row -> _SelectedItem for O(1) lookup and role tracking
- **ID Ordering**: `get_selected_snapshot_ids()` returns [from_id, to_id] regardless of row order
- **Theme Compatibility**: Palette-based default background works across different Qt themes/system appearances

## Dependencies
- PySide6.QtWidgets.QAbstractItemView.SelectionMode
- PySide6.QtGui.QColor
- Existing `show_snapshots()` infrastructure
- Existing `SnapshotSummary` model

## Acceptance Criteria
- [x] Single click selects one snapshot as "from" with red background
- [x] Ctrl+click selects second snapshot as "to" with green background  
- [x] Ctrl+click on selected item toggles it off; other item keeps its color/role
- [x] Deselected item can be reselected and regains its original role
- [x] New selection gets appropriate available role ("from" or "to")
- [x] Third selection attempt is silently rejected
- [x] `get_selected_snapshot_ids()` returns IDs in role order: [from_id, to_id]
- [x] `clear_selection()` resets all selections, backgrounds, and role tracking
- [x] Selections cleared when snapshot list refreshed
- [x] All unit tests pass
- [x] Linting passes (ruff, mypy)
