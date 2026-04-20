# FreeCAD Snapshot Property Handling Issues & Recommendations

## Problem Statement

The current FreeCAD snapshot implementation has two critical issues that prevent reliable snapshot comparison and serialization:

### Issue 1: Non-Deterministic Serialization

When a `Snapshot` is serialized to YAML via `SnapshotYamlSerializer` and then deserialized, comparing the original and reserialized snapshots fails even though they represent the same state. This is caused by:

- **Custom types with inconsistent equality**: Types like `Property`, `Vector`, `Placement`, and `Constraint` don't preserve their exact representation through YAML round-trips
- **List comparisons**: Lists containing custom types (e.g., `Constraint` lists) compare differently after deserialization because string representations may vary or object identities are lost

### Issue 2: Lost Sub-property Expressions

Special types with expandable sub-properties lose expression information during extraction:

- **Placement**: Has `Position` (x, y, z) and `Rotation` (Angle, Axis x/y/z) - each sub-property can have its own expression, but these are being lost
- **Constraint**: A list of constraints where each constraint has multiple properties, each potentially with expressions
- **Color, Reference Axis, Profile**: Other complex types with nested properties that support expressions

The current implementation only captures expressions at the top-level property, not for individual sub-properties.

---

## Investigation Findings

### FreeCAD's Property Tree Architecture

After examining the FreeCAD source code (`/home/flyer/Repositories/freecad-source`), I discovered that FreeCAD uses a **unified path-based system** for property expansion:

#### Core Mechanism: `getPaths()` Method

All expandable properties implement the `getPaths()` method defined in `src/App/Property.h`:

```cpp
virtual void getPaths(std::vector<ObjectIdentifier>& paths) const;
```

This method returns all valid sub-property paths as `ObjectIdentifier` objects.

#### Path Components (`ObjectIdentifier`)

Paths are constructed using components (`src/App/ObjectIdentifier.h`):
- **SimpleComponent**: Named attributes (`"x"`, `"y"`, `"z"`, `"Angle"`, `"Base"`, `"Rotation"`)
- **ArrayComponent**: Indexed access for lists (`[0]`, `[1]`, etc.)
- **MapComponent**: Key-based access for dictionaries

#### Path-based Access Methods

```cpp
void getPaths(std::vector<ObjectIdentifier>& paths) const;
const boost::any getPathValue(const ObjectIdentifier& path) const;
void setPathValue(const ObjectIdentifier& path, const boost::any& value);
```

### Type-Specific Implementations

#### 1. PropertyVector

**File**: `src/App/PropertyGeo.cpp:181-189`

```cpp
void PropertyVector::getPaths(std::vector<ObjectIdentifier>& paths) const {
    paths.push_back(ObjectIdentifier(*this) << "x");
    paths.push_back(ObjectIdentifier(*this) << "y");
    paths.push_back(ObjectIdentifier(*this) << "z");
}
```

**Expansion**: `x`, `y`, `z`

#### 2. PropertyPlacement

**File**: `src/App/PropertyGeo.cpp:558-583`

```cpp
void PropertyPlacement::getPaths(std::vector<ObjectIdentifier>& paths) const {
    // Position (Base) sub-properties
    paths.push_back(ObjectIdentifier(*this) << "Base" << "x");
    paths.push_back(ObjectIdentifier(*this) << "Base" << "y");
    paths.push_back(ObjectIdentifier(*this) << "Base" << "z");
    
    // Rotation sub-properties
    paths.push_back(ObjectIdentifier(*this) << "Rotation" << "Angle");
    paths.push_back(ObjectIdentifier(*this) << "Rotation" << "Axis" << "x");
    paths.push_back(ObjectIdentifier(*this) << "Rotation" << "Axis" << "y");
    paths.push_back(ObjectIdentifier(*this) << "Rotation" << "Axis" << "z");
}
```

**Expansion**: 
- `Base.x`, `Base.y`, `Base.z`
- `Rotation.Angle`, `Rotation.Axis.x`, `Rotation.Axis.y`, `Rotation.Axis.z`

#### 3. PropertyRotation

**File**: `src/App/PropertyGeo.cpp:1107-1119`

```cpp
void PropertyRotation::getPaths(std::vector<ObjectIdentifier>& paths) const {
    paths.push_back(ObjectIdentifier(*this) << "Angle");
    paths.push_back(ObjectIdentifier(*this) << "Axis" << "x");
    paths.push_back(ObjectIdentifier(*this) << "Axis" << "y");
    paths.push_back(ObjectIdentifier(*this) << "Axis" << "z");
}
```

**Expansion**: `Angle`, `Axis.x`, `Axis.y`, `Axis.z`

#### 4. PropertyConstraintList

**File**: `src/Mod/Sketcher/App/PropertyConstraintList.cpp:633-641`

```cpp
void PropertyConstraintList::getPaths(std::vector<ObjectIdentifier>& paths) const {
    for (const Constraint* c : _lValueList) {
        if (!c->Name.empty()) {
            paths.push_back(ObjectIdentifier(*this) << c->Name);
        }
    }
}
```

**Expansion**: For each named constraint, creates paths like `"Constr0"`, `"Constr1"`, etc. Each constraint then exposes its own properties (Value, Type, Geometry indices, etc.).

### Expression Engine Integration

**File**: `src/App/PropertyExpressionEngine.cpp`

The `PropertyExpressionEngine` stores expressions **per-path**, not just per-property:

```cpp
std::map<App::ObjectIdentifier, ExpressionInfo> expressions;
```

Key methods:
```cpp
std::map<ObjectIdentifier, const Expression*> getExpressions() const;
void setExpressions(std::map<ObjectIdentifier, ExpressionPtr>&& exprs);
const boost::any getPathValue(const ObjectIdentifier& path) const;
void setValue(const ObjectIdentifier& path, ExpressionPtr expr);
```

**Critical Insight**: Each sub-property path can have its own independent expression:
- `Placement.Base.x` → `"Part.Length * 0.5"`
- `Placement.Rotation.Angle` → `"Sketch.Constr0.Value"`
- `Constraints.Constr0.Value` → `"10 mm"`

### GUI Property Editor Integration

**File**: `src/Gui/propertyeditor/PropertyItem.cpp:158-168`

```cpp
App::ObjectIdentifier id(prop);
std::vector<App::ObjectIdentifier> paths;
prop.getPaths(paths);
// Creates tree items for each path in the property editor
```

The GUI uses `getPaths()` to build the expandable tree structure shown to users.

---

## Key Discovery: No Python Access to `getPaths()`

**Critical Finding**: The `getPaths()` method exists in C++ (`Property.h:323`) but is **NOT exposed to Python**. It's only used internally by the GUI property editor.

This means we cannot directly use FreeCAD's native path discovery mechanism from Python. We must implement our own generic solution using one of these approaches:

### Option A: Dynamic Attribute Discovery (Truly Generic)

Recursively discover sub-properties by inspecting attributes at runtime:

```python
def discover_paths(obj, value, prefix=""):
    """Recursively discover all property paths dynamically."""
    paths = {}
    
    # Check if this value has sub-properties (has attributes that aren't methods)
    if hasattr(value, '__dict__') or hasattr(value, '__slots__'):
        for attr_name in dir(value):
            if attr_name.startswith('_'):
                continue
            try:
                attr_value = getattr(value, attr_name)
                # Skip methods and callables
                if callable(attr_value):
                    continue
                # Recurse into this attribute
                new_path = f"{prefix}.{attr_name}" if prefix else attr_name
                paths[new_path] = (attr_value, None)  # Will fill expressions later
                # Recurse deeper if it looks like a compound type
                if hasattr(attr_value, '__dict__') or hasattr(attr_value, 'x'):
                    paths.update(discover_paths(obj, attr_value, new_path))
            except:
                pass
    
    return paths
```

**Pros**: 
- Truly generic, works for any new property type
- No hardcoding of specific type names
- Handles unexpected types automatically

**Cons**: 
- May discover unwanted attributes
- Less precise control over what's considered a "sub-property"
- Requires careful filtering to avoid noise

### Option B: Pattern-Based Discovery (Semi-Generic)

Use common patterns to detect sub-properties without hardcoding specific names:

```python
def get_sub_properties(value):
    """Detect sub-properties using common patterns."""
    children = {}
    
    # Pattern 1: Vector-like (has x, y, z)
    if all(hasattr(value, attr) for attr in ['x', 'y', 'z']):
        return {'x': value.x, 'y': value.y, 'z': value.z}
    
    # Pattern 2: Placement-like (has Base/Position and Rotation)
    if hasattr(value, 'Base') and hasattr(value, 'Rotation'):
        return {'Base': value.Base, 'Rotation': value.Rotation}
    elif hasattr(value, 'Position') and hasattr(value, 'Rotation'):
        return {'Position': value.Position, 'Rotation': value.Rotation}
    
    # Pattern 3: Rotation-like (has Angle and Axis)
    if hasattr(value, 'Angle') and hasattr(value, 'Axis'):
        return {'Angle': value.Angle, 'Axis': value.Axis}
    
    # Default: no sub-properties
    return {}
```

**Pros**: 
- More controlled discovery
- Matches FreeCAD's actual structure well
- Predictable behavior

**Cons**: 
- Still has some type-specific logic (though abstracted)
- May miss novel property types that don't match patterns
- Requires maintenance if FreeCAD adds new patterns

### Option C: ExpressionEngine-Driven (Hybrid)

Only capture paths that appear in ExpressionEngine OR are top-level properties:

```python
def extract_property_tree(obj, prop_name, value):
    """Extract tree using ExpressionEngine as the source of truth for valid paths."""
    expr_engine = getattr(obj, "ExpressionEngine", [])
    
    # Get all expression paths for this property
    prop_paths = []
    for entry in expr_engine:
        path = entry[0].lstrip('.')
        if path.startswith(prop_name + '.') or path == prop_name:
            prop_paths.append(path)
    
    # Build tree from these paths + the value itself
    # This captures ALL paths that have expressions, plus leaf values
```

**Pros**: 
- Only captures "real" sub-properties that FreeCAD recognizes
- Leverages FreeCAD's internal path validation
- Minimal false positives

**Cons**: 
- Misses paths without expressions (but we still need their values!)
- Incomplete snapshot if some sub-properties lack expressions
- Not suitable as standalone solution

---

## Recommended Approach

Given the requirement for a generic solution, I recommend **Option A (Dynamic Discovery)** with the following refinement:

### Implementation Strategy

1. **Discovery Phase**: Recursively discover all attributes that look like sub-properties
   - Check for `__dict__` or `__slots__` to identify compound types
   - Skip attributes starting with `_` (internal/private)
   - Skip callable/method attributes

2. **Filtering Phase**: Use simple heuristics to exclude non-property attributes
   - Filter by known FreeCAD editor-visible property names if needed
   - Exclude special attributes like `__class__`, `__doc__`, etc.

3. **Expression Phase**: Query ExpressionEngine for each discovered path
   - Build full path string (e.g., `"Placement.Base.x"`)
   - Look up expression in ExpressionEngine map
   - Store (value, expression) pairs for each path

### Benefits

- ✅ **Generic** - works for any property type without hardcoding
- ✅ **Captures ALL values** at all levels of the hierarchy
- ✅ **Captures ALL expressions** at all levels
- ✅ **Simple comparison** via flattened path representation
- ✅ **Handles new types automatically** without code changes

### Tradeoff

You might capture some extra attributes that aren't "real" sub-properties visible in FreeCAD's GUI. However, you can filter these by:
- Checking against FreeCAD's known editor-visible properties (if needed)
- Validating that discovered paths work with ExpressionEngine queries
- Testing round-trip serialization to ensure consistency

---

## Investigation: Using "Value" as Expansion Determinant
**Question:** Can we skip filtering by only expanding properties that have a `"Value"` attribute?
**Findings:**
| Property Type | Has "Value" Attribute | Would Expand? | Verdict |
|--------------|----------------------|---------------|---------|
| Profile → Sketch | ❌ No | No | ✅ Good |
| **Placement** | ❌ **No** | **No** | ❌ **Fails - loses all placement data** |
| Vector | ❌ No | No | ❌ Fails - loses x,y,z |
| Rotation | ❌ No | No | ❌ Fails - loses Angle, Axis |
| Constraint | ✅ Yes | Yes | ⚠️ Partial (misses Type, First, Second) |
**Conclusion:** Placement has no "Value" attribute—only `Base` and `Rotation`. A "Value-only" strategy would prevent ANY expansion of Placement properties, losing critical snapshot data.
**Recommendation:** Use **pattern-based expansion** instead:
- Match structural patterns (`Base` + `Rotation` for Placement, `x,y,z` for Vector, `Angle` + `Axis` for Rotation)
- Stops Profile expansion naturally (Sketch matches no pattern)
- No filtering required
- Predictable and explicit

---

## Current Implementation Analysis

### What Works

Your current implementation in `freecad/diff_wb/domain/tree/property.py`:

1. ✅ Domain types (`Vector`, `Rotation`, `Placement`) with proper equality
2. ✅ Basic property extraction from FreeCAD objects
3. ✅ Top-level expression capture via `_get_expression_for_property()`
4. ✅ `get_children()` method for basic expansion (Placement → Position + Rotation)

### What's Missing

#### 1. Path-Based Expression Extraction

**Current code** (`gui_extractor.py:230-251`):
```python
def _get_expression_for_property(obj, prop_name):
    expr_engine = getattr(obj, "ExpressionEngine", [])
    # Only checks top-level property names
    for entry in expr_engine:
        if entry[0] == prop_name:
            return str(entry[1])
```

**Problem**: This only captures expressions for top-level properties. It misses:
- `Placement.Base.x` expressions
- `Placement.Rotation.Angle` expressions
- Individual constraint property expressions

#### 2. Sub-property Value/Expression Extraction

**Current code** (`property.py:451-522`):
```python
def get_children(self):
    if self.type_ == PropertyType.PLACEMENT:
        return self._get_placement_children()
    # ... returns (name, value) tuples but no expressions
```

**Problem**: 
- Children are extracted as raw values without their individual expressions
- No mechanism to recursively extract expressions for nested properties
- The `Property` class stores a single `expression` field, not per-path expressions

#### 3. List Property Expansion

**Current code** (`property.py:478-479`):
```python
if isinstance(self.value, (list, tuple)) and self.value:
    return [(str(i), v) for i, v in enumerate(self.value)]
```

**Problem**:
- Lists are expanded by index, but FreeCAD uses named paths for constraints (`"Constr0"`, `"Constr1"`)
- Each list item's properties are not recursively extracted
- No expression capture for individual list item properties

#### 4. Serialization Round-Trip Issues

**Current code** (`snapshot_yaml.py:160-203`):
```python
def _serialize_property_value(value, type_):
    if type_ == PropertyType.LIST:
        return [str(item) for item in value] if value else []
```

**Problem**:
- Lists are converted to strings, losing structure
- After deserialization, you can't reconstruct the original object types
- String representations may vary between Python sessions or FreeCAD versions

---

## Recommendations

### Recommendation 1: Adopt Path-Based Property Storage

**Change**: Store properties as a flat map of path → (value, expression) pairs instead of nested objects.

**Before**:
```python
properties = {
    "Placement": Property(
        type_=PropertyType.PLACEMENT,
        value=Placement(position=Vector(...), rotation=Rotation(...)),
        expression=None  # Only top-level expression
    )
}
```

**After**:
```python
properties = {
    "Placement.Base.x": Property(value=10.5, expression="Part.Length * 0.5"),
    "Placement.Base.y": Property(value=20.0, expression=None),
    "Placement.Base.z": Property(value=0.0, expression=None),
    "Placement.Rotation.Angle": Property(value=90.0, expression="Sketch.Constr0.Value"),
    "Placement.Rotation.Axis.x": Property(value=0.0, expression=None),
    "Placement.Rotation.Axis.y": Property(value=0.0, expression=None),
    "Placement.Rotation.Axis.z": Property(value=1.0, expression=None),
}
```

**Benefits**:
- Exact match to FreeCAD's internal representation
- Each sub-property can have its own expression
- Simplifies comparison (just compare path maps)
- Simplifies serialization (flat structure)

### Recommendation 2: Implement `get_paths()` Method

**Add to `Property` class**:
```python
def get_paths(self) -> dict[str, tuple[Any, str | None]]:
    """Get all property paths with their values and expressions.
    
    Returns a flat dictionary mapping path strings to (value, expression) tuples.
    For simple properties, returns {"" : (value, expression)}.
    For complex properties, returns expanded paths like:
        {"Base.x": (10.5, "expr1"), "Base.y": (20.0, None), ...}
    """
```

**Implementation strategy**:
1. Recursively expand properties using the same logic as FreeCAD's `getPaths()`
2. For each leaf path, extract both value and expression from FreeCAD
3. Use the path naming convention: `Base.x`, `Rotation.Angle`, `Constr0.Value`, etc.

### Recommendation 3: Extract Expressions for All Paths

**Modify `_extract_property_value()` in `gui_extractor.py`**:

Instead of extracting one property with one expression:
```python
# Current approach (loses sub-property expressions)
expression = _get_expression_for_property(obj, prop_name)
property_obj = Property.from_freecad_property(prop_name, value, expression)
```

Use path-based extraction:
```python
# New approach (captures all expressions)
paths_data = _extract_all_property_paths(obj, prop_name, value)
# Returns: {
#     "Base.x": (10.5, "expr1"),
#     "Base.y": (20.0, None),
#     ...
# }
```

**Helper function to implement**:
```python
def _extract_all_property_paths(obj, prop_name, value) -> dict[str, tuple[Any, str | None]]:
    """Extract all sub-property paths with values and expressions.
    
    Uses FreeCAD's ExpressionEngine to get expressions for each sub-path.
    """
    # Get full expression engine map
    expr_engine = getattr(obj, "ExpressionEngine", [])
    expr_map = {entry[0]: entry[1] for entry in expr_engine}
    
    # Recursively extract paths
    result = {}
    _extract_paths_recursive(obj, prop_name, value, "", expr_map, result)
    return result
```

### Recommendation 4: Define Standard Path Naming Convention

Establish consistent path naming that matches FreeCAD's convention:

| Type | Path Pattern | Example |
|------|-------------|---------|
| Vector | `{prop}.x`, `{prop}.y`, `{prop}.z` | `Placement.Base.x` |
| Placement | `{prop}.Base.{x,y,z}`, `{prop}.Rotation.{Angle,Axis.{x,y,z}}` | `Placement.Rotation.Angle` |
| Rotation | `{prop}.Angle`, `{prop}.Axis.{x,y,z}` | `Rotation.Axis.x` |
| Constraint List | `Constraints.{name}.{property}` | `Constraints.Constr0.Value` |
| Simple property | `{prop}` or `` (empty for root) | `Length` |

### Recommendation 5: Fix List/Constraint Serialization

**Problem**: Converting constraints to strings loses structure and causes comparison failures.

**Solution A (Recommended)**: Store structured data
```yaml
properties:
  Constraints:
    type_: LIST
    value:
      - name: Constr0
        properties:
          Type: {"type_": "INT", "value": 6, "expression": null}
          Value: {"type_": "FLOAT", "value": 10.0, "expression": "10 mm"}
          First: {"type_": "INT", "value": 0, "expression": null}
      - name: Constr1:
        properties:
          ...
```

**Solution B (Simpler)**: Use canonical string representation
```yaml
properties:
  Constraints:
    type_: LIST
    value:
      - "Constr0: Type=Distance, Value=10.0mm, First=0"
      - "Constr1: Type=Horizontal, First=1"
```

**Recommendation**: Use Solution A if you need to compare individual constraint properties. Use Solution B if you only need to detect that constraints changed.

### Recommendation 6: Implement Proper Equality Comparison

**For path-based storage**, equality becomes straightforward:

```python
def __eq__(self, other):
    if not isinstance(other, Snapshot):
        return NotImplemented
    
    # Compare all paths
    self_paths = {path: (prop.value, prop.expression) 
                  for node in self.nodes 
                  for path, prop in node.properties.items()}
    other_paths = {path: (prop.value, prop.expression) 
                   for node in other.nodes 
                   for path, prop in node.properties.items()}
    
    return self_paths == other_paths
```

---

## Implementation Priority

### Phase 1: Core Path-Based System (High Priority)
1. Implement `get_paths()` method on `Property` class
2. Modify extraction to capture all sub-property paths with expressions
3. Update YAML serializer to handle flat path structure
4. Test round-trip serialization equality

### Phase 2: List Property Expansion (Medium Priority)
1. Implement proper Constraint list expansion with named paths
2. Extract expressions for each constraint's properties
3. Choose serialization strategy (structured vs. canonical string)

### Phase 3: Additional Types (Low Priority)
1. Add support for Color properties
2. Add support for Reference Axis properties  
3. Add support for Profile properties

---

## Testing Strategy

### Unit Tests
- Test `get_paths()` for each property type
- Test expression extraction for sub-properties
- Test path-based equality comparison

### Integration Tests
- Round-trip serialization test: extract → serialize → deserialize → compare
- Verify all sub-property expressions are preserved
- Verify Constraint list preservation

### Manual Verification
- Open a FreeCAD file with complex placements and constraints
- Take a snapshot, serialize to YAML, inspect the output
- Verify all expected paths and expressions are present

---

## References

### FreeCAD Source Files Examined
- `src/App/Property.h` - Base Property class and getPaths() definition
- `src/App/PropertyGeo.h/cpp` - PropertyVector, PropertyPlacement, PropertyRotation implementations
- `src/App/ObjectIdentifier.h` - Path component types and construction
- `src/App/PropertyExpressionEngine.h/cpp` - Expression storage per-path
- `src/Mod/Sketcher/App/PropertyConstraintList.h/cpp` - Constraint list expansion
- `src/Gui/propertyeditor/PropertyItem.cpp` - GUI integration

### Current Project Files
- `freecad/diff_wb/domain/tree/property.py` - Property domain models
- `freecad/diff_wb/domain/snapshots/gui_extractor.py` - Property extraction logic
- `freecad/diff_wb/infrastructure/persistence/snapshot_yaml.py` - YAML serialization
