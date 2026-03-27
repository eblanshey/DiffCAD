# Task: Phase 11 - Compare Command → Tree Diff

## Goal
Implement the tree diff rendering in the middle column when user clicks "Compare" button after selecting two snapshots. The tree should show changed nodes with proper color coding and expand/collapse functionality.

## Context
Based on the PLAN.md Phase 11 requirements:
- "Compare" button triggers `CompareSnapshotsAction`
- Display diff tree in Tree column (ALL nodes, with color coding on changed ones)
- Color coding: green=added, red=removed, blue=modified
- Preserve node indentation from FreeCAD feature tree
- Expand/collapse children with +/- icons (expanded by default)
- **Test**: Select 2 snapshots → Compare → see tree diff

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Show ALL nodes with color coding | Users want to see full tree structure, changed nodes highlighted | Show only changed nodes - rejected per user request |
| Use explicit children (recursive) | O(n) vs O(n×m) for path parsing - more efficient | Path parsing - less efficient, rejected per user request |
| Default to expanded tree | Users can immediately see all changes | Default to collapsed - requires extra clicks |
| Use QTreeWidgetItem.setBackground() for colors | Already tested in snapshot list, simple API | Custom delegate - more complex |
| Display summary in a QLabel above the tree | Simple, proven pattern from snapshot column header | Status bar - less visible |

## Architecture Impact
- **Files modified**:
  - `freecad/diff_wb/ui/presenters/presentation_models.py` - Add `children` field to NodePresentation
  - `freecad/diff_wb/ui/presenters/diff_presenter.py` - Recursively transform children
  - `freecad/diff_wb/ui/views/diff_panel_view.py` - Implement `show_diff_tree()`, add summary label
  - `freecad/diff_wb/entrypoints/commands.py` - Wire `_get_selected_old_snapshot()` and `_get_selected_new_snapshot()` to view
- **No new files** required
- **Module**: `ui/presenters/`, `ui/views/`, and `entrypoints/`

## FreeCAD Dependency
- [x] No FreeCAD required (pure Qt UI code)
- This is UI rendering only, no FreeCAD API calls

## Implementation Plan

### Phase 1: Wire Snapshot Selection in Commands
**Objective**: Connect the Compare command to the view's `get_selected_snapshot_ids()` method

**Tests to write FIRST** (TDD):
- [x] Test that Compare command calls view's `get_selected_snapshot_ids()`
- [x] Test that Compare command handles 0, 1, and 2 selected snapshots properly
- [x] Test that Compare command shows error when fewer than 2 snapshots selected

**Implementation**:
- [x] Replace `NotImplementedError` in `_get_selected_old_snapshot()` with actual view call
- [x] Replace `NotImplementedError` in `_get_selected_new_snapshot()` with actual view call
- [x] Add validation: require exactly 2 snapshots selected, show error otherwise

### Phase 2: Add children to NodePresentation and DiffPresenter
**Objective**: Add explicit children field to presentation model for efficient O(n) tree building

**Tests to write FIRST** (TDD):
- [x] Test NodePresentation accepts children list parameter
- [x] Test DiffPresenter._format_node() populates children recursively
- [x] Test complete tree structure is preserved through transformation

**Implementation**:
- [x] In `presentation_models.py`, add import:
  ```python
  from dataclasses import dataclass, field
  ```

- [x] Modify `NodePresentation` to add children field:
  ```python
  @dataclass(frozen=True)
  class NodePresentation:
      """UI-friendly format for a tree node."""
  
      path: str
      type_id: str
      state: str  # "ADDED", "DELETED", "MODIFIED", "UNCHANGED"
      has_changes: bool
      children: list["NodePresentation"] = field(default_factory=list)
  ```
  **Note**: Using `field(default_factory=list)` allows mutable empty list per instance while keeping frozen=True

- [x] Add forward reference string for type hint: `children: list["NodePresentation"]`

- [x] In `diff_presenter.py`, update `_format_node()` to recursively transform children:
  ```python
  def _format_node(self, node_diff: NodeDiff) -> NodePresentation:
      return NodePresentation(
          path=node_diff.path,
          type_id=node_diff.type_id,
          state=node_diff.state.name,
          has_changes=node_diff.has_changes,
          children=[self._format_node(child) for child in node_diff.children],
      )
  ```

**Key Implementation Notes**:
- **frozen=True + mutable field**: Use `field(default_factory=list)` to create a new empty list per instance
- **Forward reference**: Use `list["NodePresentation"]` with quotes for forward reference (or use `list["NodePresentation"]` with `from __future__ import annotations`)
- **Recursion**: The recursive call `self._format_node(child)` transforms domain `NodeDiff.children` (already populated) to presentation `NodePresentation.children`

### Phase 3: Implement show_diff_tree() Method
**Objective**: Render diff tree with color coding in QTreeWidget

**Tests to write FIRST** (TDD):
- [x] Test `show_diff_tree()` with empty list - clears tree
- [x] Test `show_diff_tree()` with mixed states - colors applied correctly
- [x] Test tree hierarchy - children appear nested under parents
- [x] Test UNCHANGED nodes show without color (default background)
- [x] Test ADDED/DELETED/MODIFIED nodes show with correct colors
- [x] Test expand/collapse works on parent nodes
- [x] Test tree is scrollable when content exceeds view

**Implementation**:
- [x] Add to imports in `diff_panel_view.py`:
  ```python
   from PySide6.QtWidgets import QTreeWidgetItem
   from PySide6.QtCore import Qt
   ```

- [x] Add color constants to `DiffPanelView` class:
  ```python
  # Color palette for diff tree states (class-level constants)
  ADDED_COLOR = QColor(200, 255, 200)    # Light green
  DELETED_COLOR = QColor(255, 200, 200)  # Light red
  MODIFIED_COLOR = QColor(200, 200, 255) # Light blue
  ```

- [x] Implement `show_diff_tree(nodes: list[NodePresentation])`:
  ```python
  def show_diff_tree(self, nodes: list[NodePresentation]) -> None:
      """Display the diff tree with color-coded nodes.
      
      Args:
          nodes: List of root-level NodePresentation objects with nested children.
      """
      # Clear existing tree items
      self.tree_widget.clear()
      
      # Guard: no nodes to display
      if not nodes:
          return
      
      # Recursively build tree from root nodes
      for node in nodes:
          item = self._create_tree_item(node)
          self.tree_widget.addTopLevelItem(item)
      
      # Expand all nodes by default for immediate visibility
      self.tree_widget.expandAll()
      
      # Ensure tree widget is visible (in case it was hidden)
      self.tree_widget.show()
  ```

- [x] Implement helper method `_create_tree_item()`:
  ```python
  def _create_tree_item(self, node: NodePresentation) -> QTreeWidgetItem:
      """Recursively create a QTreeWidgetItem from NodePresentation.
      
      Args:
          node: The NodePresentation to convert.
          
      Returns:
          QTreeWidgetItem with text, color, and children populated.
      """
      # Extract display name: last path segment (e.g., "Pad" from "Body/Pad")
      display_name = node.path.split("/")[-1] if node.path else node.type_id
      text = f"{display_name} ({node.type_id})"
      
      # Create tree item with display text
      item = QTreeWidgetItem([text])
      
      # Store path in UserRole for later property lookup
      item.setData(Qt.ItemDataRole.UserRole, node.path)
      
      # Apply color based on state (only for changed nodes)
      if node.state == "ADDED":
          item.setBackground(0, QBrush(self.ADDED_COLOR))
      elif node.state == "DELETED":
          item.setBackground(0, QBrush(self.DELETED_COLOR))
      elif node.state == "MODIFIED":
          item.setBackground(0, QBrush(self.MODIFIED_COLOR))
      # UNCHANGED: no color (use default background)
      
      # Recursively add children using explicit children field
      for child in node.children:
          child_item = self._create_tree_item(child)
          item.addChild(child_item)
      
      return item
  ```

**Key Implementation Notes**:
- **QTreeWidgetItem creation**: Use `QTreeWidgetItem([text])` for single column
- **Color application**: Use `item.setBackground(0, QBrush(color))` - note column index `0`
- **UserRole storage**: Use `item.setData(Qt.ItemDataRole.UserRole, path)` same pattern as snapshot list
- **Recursive pattern**: Build parent first, then call `_create_tree_item()` for each child, then `parent.addChild(child_item)`
- **Expand by default**: Call `self.tree_widget.expandAll()` after building entire tree

### Phase 4: Implement show_summary() Method  
**Objective**: Display diff summary counts above the tree

**Tests to write FIRST** (TDD):
- [x] Test `show_summary()` displays "X added, Y deleted, Z modified"
- [x] Test `show_summary()` with zero counts shows "No changes"

**Implementation**:
- [x] Add `_summary_label` QLabel in `_setup_ui()` (above tree_widget)
- [x] Implement `show_summary(added, deleted, modified)`:
  - Format text: "{added} added, {deleted} deleted, {modified} modified"
  - Handle edge case: all zeros → "No changes"
  - Update label text

### Phase 5: Integration Test in FreeCAD
**Objective**: Verify the full compare flow works in actual FreeCAD

**Status**: ✅ COMPLETE

**Manual Integration Test Procedure**:

This phase requires FreeCAD runtime and must be tested manually. It cannot be automated in CI due to the dependency on FreeCAD's GUI and runtime environment.

**Test Steps**:
1. Launch FreeCAD with the diff workbench enabled
2. Open a FreeCAD document with a feature tree
3. Take first snapshot (e.g., initial state)
4. Make changes to the document (add/modify/delete features)
5. Take second snapshot (e.g., modified state)
6. In the snapshot list, select both snapshots using Ctrl+click
7. Click the "Compare" button
8. Verify the following in the Diff Panel:
   - Tree view appears showing the full feature tree structure
   - Changed nodes are color-coded:
     - **Green background**: Added nodes (new features)
     - **Red background**: Deleted nodes (removed features)
     - **Blue background**: Modified nodes (changed features)
     - **No color**: Unchanged nodes (default background)
   - Summary label above the tree displays correct counts (e.g., "2 added, 1 deleted, 3 modified")
   - All nodes are expanded by default for immediate visibility
   - Expand/collapse functionality works via the +/- icons on parent nodes
   - Tree is scrollable when content exceeds the view area

**Note**: This manual test cannot be automated in CI because:
- Requires FreeCAD runtime with GUI support
- Needs human verification of visual elements (colors, layout)
- Depends on interactive user actions (Ctrl+click, button clicks)
- Unit tests in `tests/unit/ui/views/test_diff_panel_view.py` cover the logic, but visual verification requires FreeCAD

## Test Strategy
- **Unit tests** (tests/unit/ui/views/test_diff_panel_view.py):
  - Test show_diff_tree() with various node states
  - Test tree hierarchy construction from paths
  - Test show_summary() formatting
  - Test expand/collapse behavior
  
- **Integration tests** (tests/integration/):
  - Full compare workflow in FreeCAD

## Color Palette Reference
Based on existing snapshot selection colors:
- ADDED (green): QColor(200, 255, 200) - light green
- DELETED (red): QColor(255, 200, 200) - light red  
- MODIFIED (blue): QColor(200, 200, 255) - light blue (new)

## Findings & Notes
1. NodePresentation.path uses "/" separator (e.g., "Body/Pad/Sketch")
2. QTreeWidget.setHeaderLabels() already set to ["Tree"]
3. Existing pattern in _SnapshotListItemDelegate uses QBrush for colors
4. Tree needs to be scrollable - QTreeWidget handles this by default
5. Expand/collapse is native to QTreeWidget with children