# Task: Phase 8 - 3-Column Window + Show on Activation ✅ COMPLETED

## Goal

Create the empty 3-column diff panel UI and wire it to display when the Diff workbench activates. This is a UI skeleton with no data wiring yet - the columns will be empty placeholders.

## Status: COMPLETE

The 3-column diff panel is now working. Key fix: **Set widget parent BEFORE adding to MDI area**.

### Bug Fixed

**Problem**: Empty Diff View subwindow with no widgets visible.

**Root Cause**: Calling `panel.setParent(mdi_area)` AFTER `mdi_area.addSubWindow(panel)` caused the widget not to display properly.

**Solution**: Call `panel.setParent(mdi_area)` BEFORE `mdi_area.addSubWindow(panel)`.

## Context

**From PLAN.md Phase 8:**
- Create `ui/views/diff_panel_view.py` with horizontal `QSplitter` (in views/ folder per naming conventions)
- Three columns: `QListWidget` (Snapshots) | `QTreeWidget` (Tree) | `QTableWidget` (Properties)
- Empty columns, no data wiring yet
- Wire to show when Diff workbench activates in `workbench.py`
- **Test**: Switch to Diff workbench → see empty 3 columns

**From UI.md:**
- Three columns: Snapshots | Tree | Properties
- Responsive layout using QSplitter (columns resize proportionally)
- Property column subdivided into 2 sub-columns: property key and property value

## Architecture Considerations

Based on `docs/Architecture.md`:

1. **UI Layer Responsibility**: Thin Qt views that delegate to presenters
2. **Protocol Pattern**: Views implement protocols defined in `ui/protocols/`
3. **Translation Strategy**: Views handle translation, presenters pass raw data
4. **MDI Subwindow Approach**: Use FreeCAD's QMdiArea for subwindows (like DataManager)
5. **FreeCAD Dependency**: This is a Qt feature requiring FreeCAD runtime

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Use `QSplitter` with proportions | Columns resize proportionally - matches UI.md requirement for responsive layout | Fixed column widths - less flexible |
| Use `QMdiSubWindow` via FreeCAD's workspace | Standard FreeCAD pattern; aligns with DataManager approach | QDockWidget - different UX paradigm |
| Create custom `DiffPanel` widget class | Encapsulates splitter + placeholder logic - cleaner than inline code | Create directly in workbench.py - mixes concerns |
| Use PySide6 directly | FreeCAD ships with PySide6; already imported in ports.py | PyQt5 - not what FreeCAD uses |
| Empty state placeholder labels | User knows panel is working even without data | Blank columns - confusing |
| Initialize panel in `Activated()` | Panel shows when workbench activates | Initialize once and toggle visibility - more complex |

## API Reference (Verified via Exploration and Code Review)

### FreeCAD GUI API

```python
# Get main window and MDI area
from FreeCADGui import getMainWindow
from PySide6.QtWidgets import QMdiArea

main_window = getMainWindow()  # Returns QMainWindow
# Two options for getting MDI area - see implementation notes below
mdi_area = main_window.workspace()  # Option 1: Direct access
# OR
mdi_area = main_window.findChild(QMdiArea)  # Option 2: DataManager pattern
```

**Implementation Note**: 
- **Option 1 (`workspace()`)**: Current implementation in `ports.py` - direct property access
- **Option 2 (`findChild(QMdiArea)`)**: DataManager pattern - more flexible, finds by type
- Both work; Option 2 is more robust if FreeCAD's internal structure changes
- Recommendation: Use `findChild(QMdiArea)` in this implementation (matches DataManager)

### PySide6 Widgets Used

```python
# Core imports
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QTreeWidget, QTableWidget, QLabel,
    QMdiSubWindow, QHeaderView
)
from PySide6.QtCore import Qt
```

### QSplitter Setup (Horizontal Layout)

```python
splitter = QSplitter(Qt.Orientation.Horizontal)

# Add widgets
splitter.addWidget(snapshot_list)   # Column 0
splitter.addWidget(tree_widget)     # Column 1
splitter.addWidget(properties_table) # Column 2

# Set proportional resizing (stretch factors)
snapshot_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
tree_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
properties_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

# Initial size distribution (equal thirds)
splitter.setSizes([200, 200, 200])  # Will scale with window
```

**Key Methods:**
- `setOrientation(Qt.Orientation.Horizontal)` - Default, left-to-right
- `setSizes([int, int, ...])` - Set pixel widths for each widget
- `sizes()` - Get current sizes as list
- `setStretchFactor(index, factor)` - Set stretch weight (alternative to setSizes)

### QListWidget (Snapshots Column)

```python
snapshot_list = QListWidget()
# No headers needed for list
# Can add items later: snapshot_list.addItem("Snapshot 1")
```

### QTreeWidget (Tree Column - Initially Hidden)

```python
tree_widget = QTreeWidget()
tree_widget.setHeaderLabels(["Tree"])  # Single column header
tree_widget.setColumnCount(1)
tree_widget.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

# Initially hide since no data yet
tree_widget.hide()  # Or show placeholder label instead
```

**Key Methods (for future phases):**
- `setHeaderLabels([str, ...])` - Set column headers
- `addTopLevelItem(item)` - Add root node
- `expandAll()`, `collapseAll()` - Expand/collapse controls
- `setExpanded(index, True/False)` - Toggle individual item

### QTableWidget (Properties Column - Initially Hidden)

```python
properties_table = QTableWidget()
properties_table.setColumnCount(2)
properties_table.setHorizontalHeaderLabels(["Property", "Value"])
properties_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

# Initially hide since no data yet  
properties_table.hide()  # Or show placeholder label instead
```

**Key Methods (for future phases):**
- `setRowCount(int)` - Set number of rows
- `setItem(row, col, QTableWidgetItem)` - Set cell content
- `setHorizontalHeaderLabels([str, str])` - Set column headers

### MDI Subwindow Integration in FreeCAD

```python
# Using FreeCAD's GUI API
from FreeCADGui import getMainWindow

main_window = getMainWindow()
mdi_area = main_window.workspace()

# Create panel widget
panel = DiffPanelView()

# Add as subwindow (QMdiSubWindow is created automatically)
subwindow = mdi_area.addSubWindow(panel)
panel.setParent(mdi_area)  # Important: set parent to MDI area
subwindow.setWindowTitle("Diff View")
subwindow.show()
```

**Alternative using existing infrastructure:**
The `infrastructure/freecad/ports.py` already has helper methods:
- `gui_port.get_mdi_area()` - Returns the QMdiArea
- `gui_port.add_subwindow(mdi_area=mdi_area, widget=panel)` - Adds and returns subwindow

**Key QMdiArea Methods:**
- `addSubWindow(widget)` - Adds widget as subwindow, returns QMdiSubWindow
- `subWindowList()` - Returns list of all subwindows
- `activeSubWindow()` - Returns currently active subwindow
- `setActiveSubWindow(subwindow)` - Activates a specific subwindow
- `closeAllSubWindows()` - Closes all subwindows

**Key QMdiSubWindow Methods:**
- `setWindowTitle(title)` - Set window title
- `show()` / `hide()` - Show/hide window
- `widget()` - Get the internal widget
- `setAttribute(Qt.WA_DeleteOnClose)` - Auto-delete when closed (important!)

## Implementation Plan

### Phase 1: Create UI Components

**File: `ui/views/__init__.py`**

Create the views module with proper exports:

```python
"""Module responsibility: UI view implementations."""

from .diff_panel_view import DiffPanelView

__all__ = ["DiffPanelView"]
```

**File: `ui/views/diff_panel_view.py`**

Create the main panel view widget with 3-column layout implementing view protocols:

```python
"""File responsibility: Diff panel view with 3-column layout, implementing DiffView and SnapshotView protocols."""

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QSplitter,
    QTableWidget,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from ..presenters.presentation_models import NodePresentation


class DiffPanelView(QWidget):
    """Empty 3-column diff panel view implementing DiffView and SnapshotView protocols.

    Provides a horizontal QSplitter with:
    - Left: Placeholder for snapshots list (visible)
    - Middle: QTreeWidget for diff tree (hidden/empty)
    - Right: QTableWidget for properties (hidden/empty)

    Phase 8: Empty stubs - panel shows placeholder text only.

    Note: This class implements the DiffView and SnapshotView protocols through
    structural subtyping (duck typing) rather than explicit inheritance to avoid
    metaclass conflicts between QWidget and Protocol classes.
    """

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the 3-column layout with placeholders."""
        layout = QVBoxLayout(self)

        # Create horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Column 1: Snapshots list (always visible)
        snapshot_placeholder = QLabel("Snapshots\n(click Take Snapshot)")
        snapshot_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        snapshot_layout = QVBoxLayout()
        snapshot_layout.addWidget(snapshot_placeholder)
        snapshot_container = QWidget()
        snapshot_container.setLayout(snapshot_layout)
        snapshot_container.setMinimumWidth(150)

        # Column 2: Tree view (hidden initially)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Tree"])
        self.tree_widget.setColumnCount(1)
        self.tree_widget.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tree_widget.hide()  # Hide until data available

        # Column 3: Properties table (hidden initially)
        self.properties_table = QTableWidget()
        self.properties_table.setColumnCount(2)
        self.properties_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.properties_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.properties_table.hide()  # Hide until data available

        # Add to splitter
        splitter.addWidget(snapshot_container)
        splitter.addWidget(self.tree_widget)
        splitter.addWidget(self.properties_table)

        # Set initial sizes (equal thirds)
        splitter.setSizes([200, 200, 200])

        layout.addWidget(splitter)

    # SnapshotView protocol methods (Phase 8 stubs)
    def show_success(self, snapshot_name: str) -> None:
        """Show success message after taking snapshot."""
        # Phase 8: No implementation - will populate list in Phase 9
        pass

    def show_error(self, error_message: str) -> None:
        """Show error message."""
        # Phase 8: No implementation
        pass

    def show_loading(
        self,
        message: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Show loading indicator."""
        # Phase 8: No implementation
        pass

    # DiffView protocol methods (Phase 8 stubs)
    def show_diff_tree(self, nodes: list[NodePresentation]) -> None:
        """Display the diff tree."""
        # Phase 8: No implementation - tree stays hidden
        pass

    def show_summary(self, added: int, deleted: int, modified: int) -> None:
        """Display the diff summary counts."""
        # Phase 8: No implementation
        pass
```

### Phase 2: Wire Components

**File: `ui/__init__.py`**

Update to export from views module:

```python
"""Module responsibility: User interface."""

from .views.diff_panel_view import DiffPanelView

__all__ = ["DiffPanelView"]
```

**File: `entrypoints/workbench.py`**

Modify to create and show the MDI subwindow on activation:

```python
# Add imports at top
from .._container import _container

try:
    from FreeCADGui import getMainWindow
except Exception:
    getMainWindow = None


class DiffWorkbench(Gui.Workbench):
    # ... existing code ...
    
    def __init__(self):
        super().__init__()
        self._subwindow = None  # Store reference to MDI subwindow
    
    def Activated(self) -> None:
        """Called when user switches to this workbench."""
        _container.log(_container.translate("Log", "Workbench diff_wb activated.") + "\n")
        
        # Create and show MDI subwindow if not already created
        if self._subwindow is None:
            self._create_diff_panel()
        else:
            # Show existing subwindow if it was hidden
            self._subwindow.show()
    
    def _create_diff_panel(self) -> None:
        """Create the 3-column diff panel as an MDI subwindow."""
        if getMainWindow is None:
            _container.log("Warning: FreeCADGui not available\n")
            return
        
        from ..ui import DiffPanelView
        from PySide6.QtWidgets import QMdiArea
        
        # Get MDI area from FreeCAD's main window
        main_window = getMainWindow()
        # Use findChild pattern (matches DataManager - more robust)
        mdi_area = main_window.findChild(QMdiArea)
        
        if mdi_area is None:
            _container.log("Warning: Could not get MDI area\n")
            return
        
        # Create panel
        panel = DiffPanelView()
        
        # Add as subwindow (QMdiSubWindow created automatically)
        self._subwindow = mdi_area.addSubWindow(panel)
        panel.setParent(mdi_area)  # Important: set parent to MDI area
        
        # Configure subwindow
        self._subwindow.setWindowTitle("Diff View")
        self._subwindow.show()
    
    def Deactivated(self) -> None:
        """Called when this workbench is deactivated."""
        _container.log(_container.translate("Log", "Workbench diff_wb de-activated.") + "\n")
        
        # Hide subwindow (don't destroy - keep state)
        if self._subwindow:
            self._subwindow.hide()
```

### Phase 3: Integration Testing (With FreeCAD)

1. Launch FreeCAD with workbench installed
2. Switch to Diff workbench
3. Verify:
   - MDI subwindow appears with title "Diff View"
   - Panel has 3 columns with splitter handles
   - Left column shows "Snapshots" placeholder text
   - Middle and right columns are hidden (or show placeholders)
   - Resizing window resizes columns proportionally
4. Resize the MDI subwindow
5. Verify columns resize proportionally
6. Switch to another workbench and back
7. Verify subwindow maintains state and reappears

## Test Strategy

- **Unit tests**: Not applicable - Qt widgets require FreeCAD runtime
- **Integration tests**: Manual testing in FreeCAD
  1. Launch FreeCAD with workbench
  2. Switch to Diff workbench
  3. Verify MDI subwindow appears with 3 columns
  4. Resize window - verify columns resize proportionally
  5. Switch away and back - verify subwindow persists

## Findings & Notes

**Verified APIs:**
- `FreeCADGui.getMainWindow()` - Returns the main window
- `main_window.findChild(QMdiArea)` - Returns the QMdiArea (recommended - matches DataManager)
- `main_window.workspace()` - Alternative: Direct property access (current ports.py implementation)
- `mdi_area.addSubWindow(widget)` - Adds widget as subwindow
- `panel.setParent(mdi_area)` - Required to properly parent the widget
- PySide6 is available in FreeCAD environment
- `QSplitter` with `Qt.Orientation.Horizontal` for left-to-right layout
- `QHeaderView.ResizeMode.Stretch` for responsive column headers

**Design Decisions:**
- Tree and Properties columns start hidden (empty data)
- Snapshots column shows placeholder text instead of empty list
- Subwindow stored as instance variable to preserve state between activations
- MDI subwindow approach matches DataManager pattern from docs

**Future Phases:**
- Phase 9: Wire `ListSnapshotsQuery` to populate snapshot list
- Phase 10: Implement snapshot selection logic
- Phase 11: Wire `CompareSnapshotsAction` to populate tree
- Phase 12: Wire node selection to properties display

## Key Qt/FreeCAD Practices Demonstrated

1. **QSplitter for responsive layouts**: Columns resize proportionally using stretch factors
2. **Protocol-based view interfaces**: Follows Architecture.md's pattern with DiffView/SnapshotView (via structural subtyping)
3. **Translation in views, not presenters**: Per Architecture.md (will be implemented when adding messages)
4. **Consolidated view class**: Widget and protocol implementation in single `DiffPanelView` class
5. **Null object pattern**: Already in container.py for views (Phase 8 uses real view)
6. **MDI subwindow pattern**: Standard FreeCAD approach matching DataManager
7. **Instance state preservation**: Store subwindow reference to maintain state across activations
8. **Proper widget parenting**: Set parent to MDI area for correct lifecycle management
9. **Structural subtyping**: Use duck typing instead of explicit protocol inheritance to avoid metaclass conflicts

## Files to Modify/Create

| File | Action | Description |
|------|--------|-------------|
| `ui/views/__init__.py` | Create | Views module with DiffPanelView export |
| `ui/views/diff_panel_view.py` | Create | Main view widget with QSplitter layout, implements protocols |
| `ui/__init__.py` | Modify | Export `DiffPanelView` from views module |
| `entrypoints/workbench.py` | Modify | Create/show MDI subwindow on activation, hide on deactivation |

**Note**: No `init_gui.py` changes needed for Phase 8 - the panel is created on-demand in `workbench.py`. Container wiring will be added in Phase 9 when data population begins.

## Naming Conventions

Per Architecture.md, UI layer should follow these conventions:
- **Views**: All view files should be in `ui/views/` directory
- **View files**: Should have `_view` suffix (e.g., `diff_panel_view.py`)
- **View classes**: Should have `View` suffix (e.g., `DiffPanelView`)
- **Presenters**: Already correctly placed in `ui/presenters/` with presenter classes
- **Protocols**: Already correctly placed in `ui/protocols/` as interface definitions

This ensures clear separation:
- `ui/views/` → Qt widgets implementing view protocols
- `ui/presenters/` → Data transformation logic
- `ui/protocols/` → View interface definitions (ports)

## Structural Subtyping for Qt Views

When implementing view protocols with Qt widgets, use **structural subtyping** (duck typing) rather than explicit protocol inheritance:

```python
# Correct: Structural subtyping
class DiffPanelView(QWidget):
    """Implements DiffView and SnapshotView protocols."""
    def show_loading(self) -> None: ...
    def show_diff_tree(self, nodes: list[NodePresentation]) -> None: ...
    # ... other protocol methods

# Incorrect: Causes metaclass conflict
class DiffPanelView(QWidget, DiffView, SnapshotView):  # TypeError!
    pass
```

**Reason**: PySide6's QWidget has a custom metaclass that conflicts with Python's Protocol metaclass. The class still satisfies the protocol through structural subtyping - if it has all the required methods with correct signatures, it implements the protocol.
