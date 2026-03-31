# Task: Matching the FreeCAD Tree

## Problem Statement

The current snapshot extraction creates a flat/incorrect tree structure that doesn't match FreeCAD's native tree. Specifically:

- **Expected (FreeCAD's tree)**: Pad contains Sketch, Pocket contains Sketch001, Page contains View, View contains Dimensions/Balloons
- **Current (our tree)**: All objects at same level, features come before their sketches, TechDraw items at root

## Root Cause Analysis

FreeCAD builds its tree using **ViewProvider::claimChildren()** - a GUI-level method that determines which objects should appear as children in the tree. The algorithm is:

1. Each ViewProvider declares its children via `claimChildren()` method
2. **Recursive exclusion**: If parent A claims child B, and B claims children C1, C2, then C1/C2 are EXCLUDED from A's direct children (they appear nested under B)
3. This is implemented in `ViewProviderGeoFeatureGroupExtension::extensionClaimChildren()` in the C++ source

### Key Implementation Details

**Source code locations:**
- Main tree building: `src/Gui/Tree.cpp`
- `claimChildren()` method: `src/Gui/ViewProvider.cpp:962`
- GeoFeatureGroup extension (App::Part, PartDesign::Body): `src/Gui/ViewProviderGeoFeatureGroupExtension.cpp:78`
- SketchBased (Pad, Pocket): `src/Mod/PartDesign/Gui/ViewProviderSketchBased.cpp:75`
- TechDraw Page: `src/Mod/TechDraw/Gui/ViewProviderPage.cpp:384`
- TechDraw ProjGroup: `src/Mod/TechDraw/Gui/ViewProviderProjGroup.cpp:178`

**How different object types claim children:**

1. **PartDesign::Body (GeoFeatureGroupExtension)**:
   - Claims all objects in its `Group` property
   - But EXCLUDES objects that are claimed by features (via recursive `claimChildren()`)

2. **PartDesign::Pad/Pocket (SketchBased)**:
   - Claims the object from its `Profile` property (the Sketch)

3. **TechDraw::DrawPage**:
   - Claims `Template` from `Template` property
   - Claims Views from `Views` property
   - EXCLUDES: Dimensions, Balloons, Hatches (they have `claimParent()`)
   - EXCLUDED: Objects in ClipGroup

4. **TechDraw::DrawProjGroup (View)**:
   - Claims Balloons, LeaderLines, RichAnnos from `getInList()`
   - Claims ProjGroupItems from `Views` property

## Solution Options

### Option A: Use GUI-level API (Recommended)

**Pros:**
- Uses FreeCAD's authoritative tree-building logic
- No need to reimplement workbench-specific logic
- Automatically handles all edge cases

**Cons:**
- Requires FreeCAD GUI to be initialized during extraction
- Need to ensure FreeCADGui module is available

**Implementation:**
```python
import FreeCAD
import FreeCADGui

# Initialize GUI (without showing main window)
FreeCADGui.setupWithoutGUI()

# Open document
doc = FreeCAD.ActiveDocument  # or FreeCAD.open(path)
gui_doc = FreeCADGui.getDocument(doc.Name)

def get_tree_children(obj):
    """Get children as they appear in FreeCAD tree."""
    vp = gui_doc.getViewProvider(obj)
    return vp.claimChildren()

# Build tree using recursive claimChildren with exclusion logic
```

### Option B: Replicate algorithm at App level

**Pros:**
- Works without GUI

**Cons:**
- Must reimplement all claimChildren logic for each workbench
- Must implement recursive exclusion algorithm
- High maintenance burden as new object types are added

**Implementation would require:**
1. For each object type, determine its "claimed children" from App-level properties
2. Implement recursive exclusion: call claimChildren on claimed children and exclude those from parent
3. Special handling for TechDraw (claimParent), Origin features, etc.

## Environment Notes

The FreeCAD AppImage Python (3.11) doesn't include GUI bindings by default. The `FreeCAD.Gui` attribute is False when importing FreeCAD in the AppImage context.

However, `FreeCADGui.so` exists at `/home/flyer/Programs/freecad_extracted/squashfs-root/usr/lib/FreeCADGui.so` and can be imported separately:

```python
import sys
sys.path.insert(0, '/path/to/freecad_extracted/usr/lib')
import FreeCADGui
FreeCADGui.setupWithoutGUI()
```

## Recommendations

1. **Primary approach**: Modify snapshot extraction to initialize FreeCAD GUI and use `ViewProvider.claimChildren()` to build the tree. This is the most maintainable solution.

2. **Alternative for headless**: If GUI initialization is not possible, implement Option B by:
   - Creating a mapping of TypeId -> child-finding function
   - Using Group property for containers
   - Using Profile property for SketchBased features
   - Using Template/Views for TechDraw pages
   - Applying recursive exclusion

3. **Testing**: The test file `tests/freecad/BasicFile.FCStd` demonstrates the tree structure with:
   - Part_MyPart (App::Part) containing Body_MyBody
   - Body_MyBody containing Pad_Main, Pocket_Main with their Sketches
   - Page containing Template and View
   - View containing Dimensions and Balloons

## Files to Modify

- `freecad/diff_wb/domain/snapshots/extractor.py` - Main extraction logic
- Potentially add new dependency on FreeCADGui

## Verification

After implementation, verify tree matches:
```
Part_MyPart
├── Origin
└── Body_MyBody
    ├── Origin004
    ├── Pad_Main
    │   └── Sketch_Pad
    ├── Pocket_Main
    │   └── Sketch_Pocket
    └── MyVarSet
└── Page
    ├── Template
    └── View
        ├── Dimension
        ├── Dimension001
        ├── Dimension002
        └── Balloon
```

## Implementation Plan

### Phase 1: Core Implementation (Completed)

- [x] **Replaced extractor.py implementation to use claimChildren()**: The main extraction logic in `freecad/diff_wb/domain/snapshots/extractor.py` now uses FreeCAD's GUI-level `ViewProvider.claimChildren()` API to build the tree hierarchy. This includes:
  - `_init_gui_and_get_doc()`: Initializes FreeCAD GUI and gets the GUI document
  - `_build_hierarchy_map()`: Builds parent/children maps using claimChildren() with recursive exclusion
  - `_build_effective_children_map()`: Implements recursive exclusion algorithm (if parent A claims child B, and B claims C, then C is excluded from A's direct children)
  - `_get_claimed_children()`: Gets children from a ViewProvider's claimChildren() method

- [x] **Updated unit tests to match the new tree building method**: All 13 unit tests in `tests/unit/domain/snapshots/test_extractor.py` pass and test the new claimChildren() functionality:
  - `test_extract_tree_with_nested_children_via_group`: Tests nested children via ViewProvider.claimChildren()
  - `test_extract_tree_discovers_children_via_group`: Tests Part container with Body and VarSet
  - `test_extract_tree_handles_nested_hierarchy`: Tests Part -> Body -> Sketch hierarchy
  - `test_extract_tree_handles_origin_features`: Tests Origin container with geometry

- [x] **Cleaned up tree_builder.py and its usage**: The old tree_builder.py file has been removed. The tree building logic is now consolidated in extractor.py using the claimChildren() approach.

### Phase 2: Optional Enhancements (Completed)

- [x] **Added edge case tests**: Added 5 new test cases covering:
  - `test_extract_tree_viewprovider_returns_string_names`: Tests when claimChildren() returns string names
  - `test_extract_tree_handles_gui_unavailable`: Tests graceful handling when FreeCADGui unavailable
  - `test_extract_tree_handles_claimchildren_exception`: Tests exception handling in claimChildren()
  - `test_extract_tree_handles_circular_claims`: Tests circular claim detection (A↔B)
  - `test_extract_tree_filters_objects_without_name`: Tests filtering of invalid objects

- [x] **Fixed extractor.py bugs discovered by tests**:
  - Fixed `_get_claimed_children`: Handle string names returned by ViewProviders
  - Fixed `_get_all_descendants`: Added cycle detection to prevent infinite recursion
  - Fixed `_build_tree_node`: Added filtering for objects without Name attribute

- [x] **Fixed getViewProvider mock consistency**: Updated 6 tests to check `obj.ViewObject` first (matching real implementation)

- [x] **Added explicit recursive exclusion assertion**: Added assertion in nested hierarchy test to verify Sketch is NOT in Part's direct children

### Phase 3: Code Quality Improvements (Completed)

#### 3.1 Throw Exception When GUI Unavailable

**Problem**: Current behavior silently returns empty children map when GUI is unavailable - this is a silent failure that's hard to debug.

**Fix**: Throw a `GuiNotAvailableError` exception instead:
- Create `GuiNotAvailableError` exception class
- Raise in `_init_gui_and_get_doc()` when FreeCADGui import fails, setup fails, or getDocument fails
- Update test `test_extract_tree_handles_gui_unavailable` to expect exception

- [x] Create `GuiNotAvailableError` exception class
- [x] Modify `_init_gui_and_get_doc()` to raise exception instead of returning None
- [x] Update test to expect exception

#### 3.2 Rename File to Clarify GUI Dependency

**Problem**: The file is named `extractor.py` but specifically requires FreeCAD GUI. When GUI is unavailable, it throws an exception.

**Fix**: Rename file to `gui_extractor.py` to make the GUI dependency explicit.

- [x] Rename `freecad/diff_wb/domain/snapshots/extractor.py` → `gui_extractor.py`
- [x] Update imports in `__init__.py` if needed
- [x] Add docstring clarifying: "Requires FreeCAD GUI. Raises GuiNotAvailableError if unavailable."

#### 3.3 Add Exception Logging

**Problem**: Lines 68 and 134 use `pylint: disable=broad-exception-caught` without logging the exception.

**Fix**: Add `Log.warning()` with exception details before returning:
- Line 68: Add `Log.warning(f"claimChildren() raised: {e}")` in `_get_claimed_children()`
- Line 134: Include exception in the existing warning message in `_init_gui_and_get_doc()`

- [x] Add exception logging in `_get_claimed_children()` (line ~68)
- [x] Add exception logging in `_init_gui_and_get_doc()` (line ~134)

#### 3.4 Clarify Recursive Exclusion Logic

**Problem**: `_build_effective_children_map()` docstring is unclear about the two-phase approach.

**Fix**: Improve docstrings and add inline comments explaining:
1. Phase 1: Build claim_map (direct claims only)
2. Phase 2: Apply exclusion via `_get_all_descendants()`
3. Phase 3: Actual tree building happens in `_build_tree_node` (recursive)

**Variable name improvements**:
- `direct_claims` → `initially_claimed`
- `result` → `effective_children`

- [x] Update `_build_effective_children_map()` docstring with clearer explanation
- [x] Add inline comments explaining the two-phase approach
- [x] Rename variables for clarity

#### 3.5 Architecture Note

The current implementation imports `FreeCADGui` directly in the domain layer. This is a deliberate choice:
- The function `_init_gui_and_get_doc` is isolated and easily patchable
- Unit tests successfully mock it via `unittest.mock.patch`
- The pattern follows pragmatic architecture over strict layered separation

For future improvement, a `GuiPort` protocol could be added to `domain/ports.py` and injected into `SnapshotExtractor`, but this adds overhead without significant benefit given the current testing approach works well.

- [x] Add comment in `gui_extractor.py` explaining the intentional direct import


#### 3.6 Remove Unused GuiLike Protocol

**Problem**: The `GuiLike` Protocol class in `domain/ports.py` is unused and unneeded. The extractor now directly imports `FreeCADGui` instead of using the protocol-based approach.

**Fix**: Remove the `GuiLike` class and its usages:
- Remove `GuiLike` Protocol class from `freecad/diff_wb/domain/ports.py`
- Update `FreeCadContext` dataclass to remove the `gui` field (or make it Any)
- Update test fixtures in `tests/conftest.py` and `tests/integration/conftest.py` to remove `GuiLike` usage

- [x] Remove `GuiLike` Protocol class from `ports.py`
- [x] Update `FreeCadContext` to not use `GuiLike`
- [x] Remove `GuiLike` imports from test fixtures
- [x] Verify all tests still pass

#### 3.7 Fix Order-Dependent Bug in `_build_effective_children_map`

**Problem**: The recursive exclusion algorithm is order-dependent. If `claim_map = {"Part": ["Sketch", "Body"], "Body": ["Sketch"]}`, the result incorrectly includes "Sketch" because Body appears after Sketch in the list, so its descendants aren't yet in the excluded set when processing Sketch.

**Fix**: Use a two-pass algorithm:
1. First pass: collect all descendants from all children
2. Second pass: add children that aren't in the collected exclusions

- [x] Fix `_build_effective_children_map()` to use two-pass algorithm
- [x] Add unit test for order-dependent edge case
- [x] Verify all tests still pass

#### 3.8 Remove Unused GUI Code from FreeCadContext

**Problem**: The `gui` field in `FreeCadContext` and related GUI code is never called in production:
- `FreeCadContext.gui` - stored but never read in production
- `FreeCadPort.try_update_gui()` - never called
- `GuiPort` Protocol - unused
- `GuiPortAdapter` class - never instantiated
- `get_gui_port()` function - never called

**Fix**: Remove all unused GUI code:
- Remove `gui` field from `FreeCadContext` in `freecad/diff_wb/domain/ports.py`
- Remove `try_update_gui()` from `FreeCadPort` Protocol
- Remove `GuiPort` Protocol class entirely
- Remove `GuiPortAdapter` class from `freecad/diff_wb/infrastructure/freecad/ports.py`
- Remove `get_gui_port()` function
- Update `__init__.py` exports
- Update tests/fakes that mock these

- [x] Remove `gui` field from `FreeCadContext` dataclass
- [x] Remove `try_update_gui()` from `FreeCadPort` Protocol
- [x] Remove `GuiPort` Protocol from `domain/ports.py`
- [x] Remove `GuiPortAdapter` class from `infrastructure/freecad/ports.py`
- [x] Remove `get_gui_port()` function
- [x] Remove `GuiPort` and related exports from `domain/__init__.py`
- [x] Remove `try_update_gui` from `tests/fakes/fake_freecad_port.py`
- [x] Remove `try_update_gui` mock from `tests/unit/domain/snapshots/test_extractor.py`
- [x] Verify all tests still pass with `task test`
- [x] Run linter with `task check`
