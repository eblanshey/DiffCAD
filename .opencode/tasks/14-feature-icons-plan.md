# Task: Display FreeCAD Feature Icons in Diff Tree

## Goal

Display FreeCAD feature type icons (e.g., Part, Body, Pad, Sketch) to the left of feature names in the diff tree view, matching the appearance of FreeCAD's native feature tree.

## Context

**Current State**: The diff tree displays nodes as text-only entries like `"Pad (PartDesign::Pad)"` with color-coded backgrounds indicating change state.

**Desired State**: Each node should show its corresponding FreeCAD icon to the left of the text, improving visual recognition and matching FreeCAD's native UX.

**User's Stated Preference**: Store all icons locally as part of the diff workbench, with a hard-coded mapping of types to images. **This decision is not final** - the user wants to see all options analyzed.

## FreeCAD Icon Loading Analysis

### How FreeCAD Finds Icons for Tree Nodes

FreeCAD uses a layered system for icon resolution:

1. **ViewProvider stores icon name**: Each C++ `ViewProvider` class has a `sPixmap` member variable that stores the icon name (e.g., `"PartDesign_Body.svg"`, `"Geofeaturegroup.svg"`)

2. **getIcon() method**: The `ViewProvider::getIcon()` method retrieves the icon:
   ```cpp
   QIcon ViewProvider::getIcon() const
   {
       return mergeGreyableOverlayIcons(Gui::BitmapFactory().pixmap(sPixmap));
   }
   ```

3. **BitmapFactory searches multiple paths**: When loading an icon, `BitmapFactory::pixmap(name)` tries:
   - Exact path if absolute
   - `icons:name` (Qt resource path)
   - `icons:name.svg`, `icons:name.png`, etc. (with extensions)
   - Falls back to "help-browser" icon if not found

### Critical Finding: Workbench Icons Require Workbench to Be Loaded

Icons are stored in multiple locations:

1. **FreeCAD core icons** (`src/Gui/Icons/`) - Always available
2. **Qt resources** (`:/icons/`) - Built into FreeCAD executable
3. **Workbench-specific icons** - Compiled into workbench `.so` files

**The key limitation**: Workbench-specific icons (PartDesign, Sketcher, etc.) are stored as Qt resources compiled into workbench `.so` files. Each workbench explicitly registers its icon paths via `Gui::BitmapFactory().addPath(":/icons/...")` when loaded.

**Example from PartDesign workbench** (in `src/Mod/PartDesign/Gui/AppPartDesignGui.cpp`):
```cpp
void SetupPartDesignGui::RegisterChildren(...) {
    Gui::BitmapFactory().addPath(":/icons/PartDesign_Pad.svg");
    Gui::BitmapFactory().addPath(":/icons/PartDesign_Pocket.svg");
    // ... many more icons
}
```

If the workbench isn't loaded, the icon path doesn't exist in BitmapFactory and it returns a fallback icon.

**From source code examples**:
- `ViewProviderBody.cpp`: `sPixmap = "PartDesign_Body.svg";`
- `ViewProviderPad.cpp`: `sPixmap = "PartDesign_Pad.svg";`
- `ViewProviderPart.cpp`: `sPixmap = "Part.svg";`

### Icon Name Format

- Includes `.svg` extension: `"PartDesign_Pad.svg"`
- Uses underscores: `"PartDesign_Body.svg"` not `"PartDesign Body.svg"`
- Workbench prefix: `"PartDesign_"`, `"Sketcher_"`, `"Part_"`, etc.

### Python API Availability

- **Works**: `obj.ViewObject.getIcon()` returns a `QIcon` object
- **Does NOT work**: `obj.ViewObject.sPixmap` is not exposed to Python

## Proposed Solutions

### Solution 1: Store Icons Locally with Hard-Coded Mapping (User Preference)

**How it works**: 
1. Copy all relevant FreeCAD icons into the diff workbench
2. Create a hard-coded mapping from type_ids to icon file paths
3. Load icons from local files at display time

**Pros**:
- Works offline (no FreeCAD needed)
- No dependency on workbench activation state
- Fast (local files, no BitmapFactory lookup)
- Self-contained

**Cons**:
- Maintenance burden (must update when FreeCAD adds new types)
- Misses custom/third-party workbench icons
- Initial effort to collect and copy all icons

**Storage estimate** (SVG format, ~300 bytes per icon, 50 common types): ~15 KB

### Solution 2: Extract Icon Image at Snapshot Time

**How it works**:
1. During snapshot creation, call `obj.ViewObject.getIcon()` 
2. Convert QIcon to QPixmap to PNG bytes
3. Store base64-encoded image in snapshot
4. Decode and display at diff time

**Pros**:
- Guaranteed to work for any icon type
- Works offline with old snapshots
- No maintenance burden

**Cons**:
- Increases snapshot size (~1-5KB per unique icon)
- Slower snapshot creation

### Solution 3: Runtime Extraction (BitmapFactory at Display Time)

**How it works**:
1. Store only the icon name (sPixmap) in snapshot
2. At display time, use BitmapFactory to load icon
3. Requires FreeCAD to be running with workbench loaded

**Pros**:
- Small snapshot storage
- Always uses current FreeCAD icons

**Cons**:
- Requires workbench to be loaded for icons to appear
- Fragile (icons missing if workbench not activated)
- Doesn't work with old snapshots

### Solution 4: Runtime Extraction + Type Mapping Fallback

**How it works**:
1. At display time, try to get icon from live object
2. If object doesn't exist (deleted), fall back to type mapping
3. Type mapping is hard-coded for common types

**Pros**:
- Hybrid approach combines benefits
- Robust for most use cases

**Cons**:
- More complex implementation
- Still needs workbench for live extraction

## Architecture Impact

### Modules Affected

1. **`freecad/diff_wb/ui/views/diff_panel_view.py`** - Display icons in tree
2. **`freecad/diff_wb/ui/presenters/presentation_models.py`** - Add icon field to NodePresentation
3. **`freecad/diff_wb/domain/models/snapshot.py`** - Store icon data in snapshot
4. **`freecad/diff_wb/infrastructure/`** - New icon mapping/module
5. **New module** `freecad/diff_wb/ui/icons/` - Store icon files and mapping

## Implementation Plan (For User Preference: Solution 1)

### Phase 1: Collect Icons from FreeCAD

- [ ] Identify all common feature types used in PartDesign, Sketcher, Part, Draft workbenches
- [ ] Export/copy SVG icons from FreeCAD source (`src/Mod/*/Gui/Resources/*.svg`)
- [ ] Organize icons in `freecad/diff_wb/ui/icons/` directory

### Phase 2: Create Type-to-Icon Mapping

- [ ] Create mapping dictionary:
  ```python
  ICON_MAPPING = {
      "App::Part": "Part.svg",
      "PartDesign::Body": "PartDesign_Body.svg",
      "PartDesign::Pad": "PartDesign_Pad.svg",
      "PartDesign::Pocket": "PartDesign_Pocket.svg",
      "PartDesign::Revolution": "PartDesign_Revolution.svg",
      "PartDesign::Sketch": "PartDesign_Sketch.svg",
      "Sketcher::SketchObject": "Sketcher_Sketch.svg",
      # ... etc
  }
  ```

### Phase 3: Implement Icon Display

- [ ] Write tests for icon loading
- [ ] Implement `_get_icon_for_type()` in diff panel view
- [ ] Display icons in tree using `QTreeWidgetItem.setIcon()`

### Phase 4: Handle Edge Cases

- [ ] Unknown types → fallback icon
- [ ] Missing icon file → fallback icon
- [ ] Performance testing with large trees

## Test Strategy

### Unit Tests (No FreeCAD)

- Icon mapping dictionary correctness
- Icon loading from local files
- Fallback logic
- Backward compatibility

### Integration Tests (With FreeCAD)

- Verify icons match FreeCAD's native icons
- Test all common feature types
- Performance testing

## Findings & Notes

### Key Technical Details

1. **Icon locations in FreeCAD source**:
   - Core icons: `src/Gui/Icons/`
   - PartDesign: `src/Mod/PartDesign/Gui/Resources/PartDesign.qrc`
   - Sketcher: `src/Mod/Sketcher/Gui/Resources/Sketcher.qrc`

2. **Resource files list all icons** (e.g., `PartDesign.qrc`):
   ```xml
   <RCC>
       <qresource prefix="/icons">
           <file>PartDesign_Pad.svg</file>
           <file>PartDesign_Pocket.svg</file>
           <!-- ... many more -->
       </qresource>
   </RCC>
   ```

3. **sPixmap values from ViewProviders**:
   - `App::Part` → `"Part.svg"`
   - `PartDesign::Body` → `"PartDesign_Body.svg"`
   - `PartDesign::Pad` → `"PartDesign_Pad.svg"`
   - `Sketcher::SketchObject` → `"Sketcher_Sketch.svg"`

### Clarifying Questions

1. **Which solution do you prefer?** (1-4 above)
2. **Which workbenches/types are most important?** (PartDesign, Sketcher, Part, Draft, etc.)
3. **How should unknown types be handled?** (generic icon, no icon, or ask user)
4. **Is this critical or nice-to-have?** (affects implementation priority)

## Success Criteria

- [ ] Common feature types display correct icons
- [ ] Icons work offline (no FreeCAD required)
- [ ] Unknown types show graceful fallback
- [ ] Performance acceptable for large trees
- [ ] Tests pass