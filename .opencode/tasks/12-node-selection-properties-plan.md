# Task: Phase 12 - Node Selection → Properties Diff

## Goal

Implement the clickable tree node to show property-level diffs in the Properties column. When a user clicks a node in the diff tree, display all property changes for that node with color coding and handle expression diffs with separate rows.

## Context

This is Phase 12 of the Diff Workbench implementation plan. The UI already has:
- 3-column layout with QSplitter (snapshots | tree | properties)
- Tree displays diff nodes with color coding (green=added, red=deleted, blue=modified)
- Node paths are stored in QTreeWidgetItem.UserRole for retrieval

The missing piece is connecting tree selection to property display in the third column.

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Expression display: separate row | More explicit about what changed (value vs expression), clearer for debugging. Users can see both value and expression changes in one view | Combined in one row - rejected as harder to read |
| Presenter handles transformation | Presenter already transforms domain data. Keep all transformation logic in presenter, keep view dumb (display only) | View handles transformation - adds complexity to view |
| Signal connected in workbench.py | Workbench has access to both panel and presenter. Cleaner than view knowing about presenter | Connect in view - requires presenter reference in view |

## Architecture Impact

**Files Modified:**
- `freecad/diff_wb/ui/views/diff_panel_view.py` - Add show_properties() method only
- `freecad/diff_wb/ui/presenters/diff_presenter.py` - Add on_node_selected() + transformation methods
- `freecad/diff_wb/ui/protocols/diff_view.py` - Add show_properties() to protocol
- `freecad/diff_wb/entrypoints/workbench.py` - Connect tree selection signal to presenter

**Files Created:**
- `tests/unit/ui/views/test_show_properties.py` - Unit tests for property display
- `tests/unit/ui/presenters/test_diff_presenter_properties.py` - Unit tests for presenter property handling

## FreeCAD Dependency

- [x] No FreeCAD required (pure code with Qt widgets)
- This feature only involves Qt UI logic, no FreeCAD document queries

## Implementation Plan

**IMPORTANT:** Each phase follows TDD principles - write tests first, then implement to pass tests.

---

### Phase 1: Update Protocol

#### Step 1: Update DiffView Protocol
**File:** `freecad/diff_wb/ui/protocols/diff_view.py`

Add `show_properties()` method to the protocol:

```python
def show_properties(self, properties: list[PropertyPresentation]) -> None:
    """Display property diffs in the properties column.

    Args:
        properties: List of PropertyPresentation objects to display.
                   Each row shows: Property Name | Old Value → New Value
                   Color coding: green=added, red=deleted, blue=modified
                   Expression changes appear as separate rows after their value row.
    """
```

Add import at top:
```python
from ..presenters.presentation_models import PropertyPresentation
```

---

### Phase 2: Implement Property Display in View (Dumb Display)

#### Step 1: Write Unit Tests First
**File:** `tests/unit/ui/views/test_show_properties.py`

Create tests covering:
1. Empty property list clears table
2. Single property diff with ADDED state (green background)
3. Single property diff with DELETED state (red background)
4. Single property diff with MODIFIED state (blue background)
5. Multiple properties with different states
6. Property with no changes (should not appear in list)

#### Step 2: Implement show_properties() in DiffPanelView
**File:** `freecad/diff_wb/ui/views/diff_panel_view.py`

Add after line 489 (after clear_selection method):

```python
def show_properties(self, properties: list[PropertyPresentation]) -> None:
    """Display property diffs in the properties column.

    Args:
        properties: List of PropertyPresentation objects. Each has:
            - name: property name
            - old_display: formatted old value ("" if added)
            - new_display: formatted new value ("" if deleted)
            - state: "ADDED", "DELETED", "MODIFIED", "UNCHANGED"
            
    Implementation notes:
    - Clear existing rows first
    - Two columns: Property | Value (showing "old → new" format)
    - Color rows by state:
      - ADDED: light green (200, 255, 200)
      - DELETED: light red (255, 200, 200)  
      - MODIFIED: light blue (200, 200, 255)
      - UNCHANGED: not displayed (filtered out)
    - Each property can generate 1-2 rows (value + expression)
    """
    # Clear existing rows
    self.properties_table.setRowCount(0)
    
    # Filter to only changed properties (no UNCHANGED)
    changed_props = [p for p in properties if p.state != "UNCHANGED"]
    
    if not changed_props:
        return
    
    # Calculate total rows needed
    total_rows = len(changed_props)
    self.properties_table.setRowCount(total_rows)
    
    # Populate rows
    for row_idx, prop in enumerate(changed_props):
        # Column 0: Property name
        name_item = QTableWidgetItem(prop.name)
        
        # Column 1: Format as "old → new" or just new/old
        if prop.state == "ADDED":
            value_text = f"+ {prop.new_display}"
        elif prop.state == "DELETED":
            value_text = f"- {prop.old_display}"
        else:  # MODIFIED
            value_text = f"{prop.old_display} → {prop.new_display}"
        
        value_item = QTableWidgetItem(value_text)
        
        # Set items
        self.properties_table.setItem(row_idx, 0, name_item)
        self.properties_table.setItem(row_idx, 1, value_item)
        
        # Apply color based on state
        if prop.state == "ADDED":
            color = self.ADDED_COLOR
        elif prop.state == "DELETED":
            color = self.DELETED_COLOR
        else:  # MODIFIED
            color = self.MODIFIED_COLOR
            
        name_item.setBackground(QBrush(color))
        value_item.setBackground(QBrush(color))
```

---

### Phase 3: Update Presenter (Handles All Transformation)

#### Step 1: Write Unit Tests First
**File:** `tests/unit/ui/presenters/test_diff_presenter_properties.py`

```python
"""File responsibility: Unit tests for DiffPresenter property selection handling."""

import pytest
from unittest.mock import Mock, MagicMock

from freecad.diff_wb.ui.presenters.diff_presenter import DiffPresenter
from freecad.diff_wb.domain.diff.models import (
    DiffResult, NodeDiff, PropertyDiff, DiffState
)
from freecad.diff_wb.domain.tree.property import Property, PropertyType


class TestDiffPresenterNodeSelection:
    """Tests for on_node_selected() method."""
    
    def test_on_node_selected_with_valid_path_calls_view(self) -> None:
        """on_node_selected() with valid path calls view.show_properties()."""
        # Given: DiffPresenter with mock view, DiffResult with property diffs
        # When: on_node_selected() called with valid path
        # Then: view.show_properties() called with PropertyPresentation list
        
    def test_on_node_selected_with_invalid_path_clears_properties(self) -> None:
        """on_node_selected() with unknown path clears properties."""
        # Given: DiffPresenter with mock view
        # When: on_node_selected() with path not in diff
        # Then: view.show_properties([]) called to clear
        
    def test_on_node_selected_with_no_diff_result_clears_properties(self) -> None:
        """on_node_selected() when no diff computed clears properties."""
        
    def test_property_presentation_transforms_correctly(self) -> None:
        """PropertyDiff transforms to PropertyPresentation with correct fields."""
```

#### Step 2: Update DiffPresenter
**File:** `freecad/diff_wb/ui/presenters/diff_presenter.py`

Add import for DiffState:

```python
from ...domain.diff.models import NodeDiff, DiffState
```

Add method after `present_diff()`:

```python
def on_node_selected(self, path: str) -> None:
    """Handle tree node selection to display property diffs.
    
    Called by view when user clicks a node in the diff tree.
    Looks up the property diffs for that path and displays them.
    
    Args:
        path: The path of the selected node (from QTreeWidgetItem.UserRole)
    """
    # Guard: No diff result stored
    if not hasattr(self, '_diff_result') or self._diff_result is None:
        self._view.show_properties([])
        return
    
    # Find NodeDiff by path
    node_diff = self._find_node_diff_by_path(path, self._diff_result.node_diffs)
    
    # If not found, clear properties
    if node_diff is None:
        self._view.show_properties([])
        return
    
    # Transform property diffs to presentations
    properties = self._transform_property_diffs(node_diff)
    self._view.show_properties(properties)

def _find_node_diff_by_path(self, path: str, node_diffs: list[NodeDiff]) -> NodeDiff | None:
    """Recursively find NodeDiff by path."""
    for node in node_diffs:
        if node.path == path:
            return node
        # Search children recursively
        if node.children:
            found = self._find_node_diff_by_path(path, node.children)
            if found:
                return found
    return None

def _transform_property_diffs(self, node_diff: NodeDiff) -> list[PropertyPresentation]:
    """Transform domain PropertyDiff to presentation format.
    
    Expression changes appear as separate rows.
    
    Args:
        node_diff: Domain NodeDiff with property_diffs
        
    Returns:
        List of PropertyPresentation for UI display
    """
    presentations = []
    
    for prop_diff in node_diff.property_diffs:
        # Skip unchanged properties
        if prop_diff.state == DiffState.UNCHANGED:
            continue
        
        # Format display strings
        old_display = self._format_property_value(prop_diff.old_value)
        new_display = self._format_property_value(prop_diff.new_value)
        
        # Create main property row
        presentations.append(PropertyPresentation(
            name=prop_diff.property_name,
            old_display=old_display,
            new_display=new_display,
            state=prop_diff.state.name,
        ))
        
        # Handle expression as separate row
        old_expr = getattr(prop_diff.old_value, 'expression', None) if prop_diff.old_value else None
        new_expr = getattr(prop_diff.new_value, 'expression', None) if prop_diff.new_value else None
        
        if old_expr or new_expr:
            # Expression changed - add second row
            old_expr_display = f"+{old_expr}" if old_expr else "(none)"
            new_expr_display = f"+{new_expr}" if new_expr else "(none)"
            
            # Determine expression state
            expr_state = "MODIFIED"
            if old_expr and not new_expr:
                expr_state = "DELETED"
            elif not old_expr and new_expr:
                expr_state = "ADDED"
            
            presentations.append(PropertyPresentation(
                name=f"{prop_diff.property_name} (expr)",
                old_display=old_expr_display,
                new_display=new_expr_display,
                state=expr_state,
            ))
    
    return presentations

def _format_property_value(self, prop: Property | None) -> str:
    """Format property value for display.
    
    Args:
        prop: Property object or None
        
    Returns:
        Formatted string suitable for display
    """
    if prop is None:
        return ""
    return str(prop)
```

Update `present_diff()` to store DiffResult:

```python
def present_diff(self, diff_result: DiffResult) -> None:
    """..."""
    # Store diff result for property lookup
    self._diff_result = diff_result
    
    # ... rest of method unchanged
```

---

### Phase 4: Wire Up Event Handler

**File:** `freecad/diff_wb/entrypoints/workbench.py`

In `_create_diff_panel()`, after creating presenters (around line 138):

```python
# Connect tree selection to diff presenter
panel.tree_widget.itemClicked.connect(
    lambda item, col: _container.diff_presenter.on_node_selected(
        item.data(0, Qt.ItemDataRole.UserRole)
    )
)
```

---

### Phase 5: Run Tests and Fix Issues

#### Step 1: Run Unit Tests
```bash
cd /home/flyer/Repositories/freecad_diff_workbench
uv run pytest tests/unit/ui/views/test_show_properties.py -v
uv run pytest tests/unit/ui/presenters/test_diff_presenter_properties.py -v
```

#### Step 2: Run Integration Tests
```bash
cd /home/flyer/Repositories/freecad_diff_workbench
uv run pytest tests/integration/workbench/test_diff_panel.py -v
```

#### Step 3: Run Linters
```bash
cd /home/flyer/Repositories/freecad_diff_workbench
uv run ruff check freecad/diff_wb/ui/views/diff_panel_view.py
uv run ruff check freecad/diff_wb/ui/presenters/diff_presenter.py
uv run ruff check freecad/diff_wb/entrypoints/workbench.py
uv run mypy freecad/diff_wb/ui/views/diff_panel_view.py
uv run mypy freecad/diff_wb/ui/presenters/diff_presenter.py
```

---

## Test Strategy

### Unit Tests (No FreeCAD)
- **View tests**: Test show_properties() with various property states, empty lists
- **Presenter tests**: Test on_node_selected() with valid/invalid paths, transformation logic
- **Protocol tests**: Verify protocol defines show_properties()

### Integration Tests (With FreeCAD)
- **Panel tests**: Verify panel can be created and methods work
- **Manual testing**: Click nodes in tree, verify properties appear

---

## Findings & Notes

### Expression Handling

For properties with expressions, display TWO rows:

1. **Value row** - shows the computed value change
   - Name: property name (e.g., "Length")
   - Value: "10.0 → 20.0" (or "+ 20.0" if added, "- 10.0" if deleted)
   - Color: based on value change state

2. **Expression row** - shows the expression change  
   - Name: property name + " (expr)" suffix (e.g., "Length (expr)")
   - Value: "+Sketch.ConstraintA" or "(none)" if removed
   - Color: based on expression change state (ADDED/DELETED/MODIFIED)

### Color Constants

Use existing constants from DiffPanelView:
- ADDED_COLOR = QColor(200, 255, 200)  # Light green
- DELETED_COLOR = QColor(255, 200, 200)  # Light red
- MODIFIED_COLOR = QColor(200, 200, 255)  # Light blue

### Property Value Format

Display format in value column:
- **ADDED**: `+ {new_value}` (e.g., "+ 20.0")
- **DELETED**: `- {old_value}` (e.g., "- 10.0")
- **MODIFIED**: `{old_value} → {new_value}` (e.g., "10.0 → 20.0")

This clearly shows the direction of change with + and - prefixes.

### Edge Cases

1. **No node selected**: Clear properties table (call show_properties([]))
2. **Node has no property changes**: Empty list passed to show_properties()
3. **Node path not found in diff**: Clear properties table
4. **No diff computed yet**: Clear properties table
5. **All properties excluded**: Empty table (no changes to show)