# FreeCAD Document Structure API Exploration

**Generated:** 2026-03-12  
**Document Explored:** `tests/freecad/BasicFile.FCStd`  
**Raw Output:** `examples/basic-file-output.txt`

## Executive Summary

This exploration reveals the structure of FreeCAD documents, including object types, properties, hierarchy relationships, and expression support. Key findings inform the design of snapshot domain objects and diffing logic.

---

## Object Types Found

| TypeId | Count | Description |
|--------|-------|-------------|
| App::Line | 6 | Origin axis lines |
| App::Origin | 2 | Origin groups (coordinate systems) |
| App::Part | 1 | Container/part group |
| App::Plane | 6 | Origin reference planes |
| App::Point | 2 | Origin reference points |
| App::VarSet | 1 | Variable set (custom user data) |
| PartDesign::Body | 1 | Feature container/body |
| PartDesign::Pad | 1 | Extrusion feature |
| PartDesign::Pocket | 1 | Cutout feature |
| Sketcher::SketchObject | 2 | 2D sketches |

**Total Objects:** 23

---

## Key API Findings

### 1. Object Identification

Every document object has these core attributes:
- **Name**: Unique identifier within document (e.g., "Pad", "Sketch")
- **TypeId**: Class type (e.g., "PartDesign::Pad")
- **Label**: User-displayable name (e.g., "Pad_Main")
- **PropertiesList**: List of property names

```python
obj.Name          # "Pad"
obj.TypeId        # "PartDesign::Pad"
obj.Label         # "Pad_Main"
obj.PropertiesList  # ["Label", "Placement", "Length", ...]
```

### 2. Property Access Pattern

Properties are accessed via `getattr(obj, property_name)`:

```python
for prop_name in obj.PropertiesList:
    value = getattr(obj, prop_name)
    # Note: getExpression() NOT available on most object types!
```

**CRITICAL FINDING:** The `getExpression()` method is **NOT supported** on most FreeCAD object types in this version. Only the `ExpressionEngine` property list is available, but individual property expressions cannot be queried via API.

### 3. Property Types Discovered

| Python Type | FreeCAD Property Type | Count | Example Values |
|-------------|----------------------|-------|----------------|
| `str` | App::PropertyString | 99 | "Pad_Main", "FlatFace" |
| `bool` | App::PropertyBool | 48 | True, False |
| `list` | App::PropertyLink/List | 47 | `[<object>, <object>]` |
| `Placement` | App::PropertyPlacement | 24 | Position + Rotation |
| `Quantity` | App::PropertyQuantity | 13 | "10.0 mm", "5.0 deg" |
| `NoneType` | App::PropertyLinkSub | 7 | None or object ref |
| `tuple` | App::PropertyLinkSub | 5 | `(<object>, [''])` |
| `float` | App::PropertyFloat | 4 | 1e-06, 0.0 |
| `Vector` | App::PropertyVector | 2 | (x, y, z) |
| `dict` | App::PropertyMap | 1 | {} |

### 4. Hierarchy Relationships

#### InList (Parents)
Objects that reference this object:
```python
obj.InList  # List of parent objects
```

#### OutList (Children)
Objects referenced by this object:
```python
obj.OutList  # List of child objects
```

#### getSubObjects()
Returns tuple of subobject name strings:
```python
obj.getSubObjects()  # ('Body.', 'VarSet.') for Part container
```

**Note:** `SubObjects` attribute does NOT exist - use `getSubObjects()` method instead.

### 5. Common Properties Across All Objects

These properties appear on virtually every object:

| Property | Type | Purpose | Exclude from Diff? |
|----------|------|---------|-------------------|
| Label | str | User-visible name | No |
| Label2 | str | Auto-generated internal label | **Yes** |
| Visibility | bool | Show/hide in GUI | Maybe |
| ExpressionEngine | list | Expression definitions | **Yes** (internal) |
| _ElementMapVersion | str | Internal versioning | **Yes** |
| Placement | Placement | Position/orientation | No (important!) |

### 6. Shape-Related Properties

For 3D features (Pad, Pocket, Sketch):
- **Shape**: The actual geometry (Part::TopoShape) - NOT serializable
- **ShapeMaterial**: Material assignment
- **InternalShape**: Sub-shape for sketches

**Important:** Shape objects cannot be serialized - exclude from snapshots.

---

## Document Structure Pattern

```
App::Part (Part_MyPart)
├── App::Origin (Origin)
│   ├── App::Line (X_Axis)
│   ├── App::Line (Y_Axis)
│   ├── App::Line (Z_Axis)
│   ├── App::Plane (XY_Plane)
│   ├── App::Plane (XZ_Plane)
│   ├── App::Plane (YZ_Plane)
│   └── App::Point (Origin001)
├── PartDesign::Body (Body_MyBody)
│   ├── App::Origin (Origin002)
│   │   ├── ... (similar origin structure)
│   ├── Sketcher::SketchObject (Sketch_Pad)
│   ├── PartDesign::Pad (Pad_Main)
│   │   └── references Sketch_Pad
│   ├── Sketcher::SketchObject (Sketch_Pocket)
│   └── PartDesign::Pocket (Pocket_Main)
│       └── references Pad_Main (BaseFeature)
└── App::VarSet (MyVarSet)
    └── Custom variables (PocketLength: 4.0 mm)
```

---

## Recommendations for Domain Object Design

### TreeNode Structure

Based on exploration, each TreeNode should contain:

```python
@dataclass(frozen=True)
class TreeNode:
    name: str              # obj.Name (unique identifier)
    type_id: str           # obj.TypeId (e.g., "PartDesign::Pad")
    label: str             # obj.Label (user-friendly name)
    properties: dict[str, PropertyValue]  # Only meaningful properties
    children: list[TreeNode]  # From OutList or getSubObjects()
```

### PropertyValue Structure

```python
@dataclass(frozen=True)
class PropertyValue:
    value: object          # The actual property value
    type_name: str         # Python type name or FreeCAD type
    # Note: expression NOT available via API for most objects
```

### Excluded Properties (Default)

These should be excluded from snapshots/diffs:

| Property | Reason |
|----------|--------|
| Label2 | Auto-generated duplicate of Label |
| ExpressionEngine | Internal, expressions not queryable |
| _ElementMapVersion | Internal versioning |
| _GroupTouched | Internal state |
| TimeStamp | (if present) Auto-updated |
| Shape | Not serializable, geometry-only |
| PreviewShape | Derived from Shape |
| SuppressedShape | Derived from Shape |
| AddSubShape | Derived from Shape |
| InternalShape | Internal representation |

### Excluded TypeIds (Default)

| TypeId | Reason |
|--------|--------|
| App::Origin | Reference geometry, not user features |
| App::Line | Origin axes |
| App::Plane | Origin planes |
| App::Point | Origin points |

---

## Property Value Serialization Notes

### Types That Serialize Well
- `str` → JSON string
- `bool` → JSON boolean
- `float` → JSON number
- `int` → JSON number
- `list` → JSON array (if elements serialize)
- `dict` → JSON object (if keys/values serialize)

### Types Requiring Special Handling
- **Placement**: Store as `{base: [x,y,z], rotation: {axis: [x,y,z], angle: rad}}`
- **Vector**: Store as `[x, y, z]`
- **Quantity**: Store as `{value: float, unit: str}` e.g., `{value: 10.0, unit: "mm"}`
- **NoneType**: Store as `null`

### Types to Exclude
- **Part::TopoShape**: Geometry data - too complex, not needed for feature diffs
- **Materials::Material**: Complex object reference
- Object references: Store as object Name string instead

---

## Expression Support

**FINDING:** The `getExpression()` method is **NOT available** on any object types in this FreeCAD version. However, expressions ARE available via the `ExpressionEngine` property.

### How Expressions Work

Expressions are stored in the `ExpressionEngine` list property as tuples:

```python
# ExpressionEngine contains [(property_name, expression_string), ...]
obj.ExpressionEngine  # [('Length', '<<MyVarSet>>.PocketLength')]

# To get expression for a specific property:
def get_expression(obj, prop_name):
    for entry in getattr(obj, 'ExpressionEngine', []):
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            if entry[0] == prop_name:
                return entry[1]
    return None
```

### Example from Test Document

The Pocket object has an expression on its Length property:

```yaml
Pocket:
  ExpressionEngine: [('Length', '<<MyVarSet>>.PocketLength')]
  Properties:
    Length:
      Value: 4.0 mm
      Expression: <<MyVarSet>>.PocketLength  # Detected via ExpressionEngine parsing
      HasExpression: true
```

**Implication for Diff Logic:**
- Expressions CAN be tracked by parsing ExpressionEngine
- PropertyValue should include optional `expression` field
- Track both the resolved value AND the expression separately
- This allows detecting when a property switches from literal to expression (or vice versa)

---

## Next Steps

1. **Design domain objects** based on these findings
2. **Create test fixtures** with known expressions (if possible)
3. **Implement snapshot extraction** using the identified API patterns
4. **Validate diff logic** against real document changes

---

## Appendix: Sample Property Values

### Placement
```
Placement(Base=Vector(x=0.0, y=0.0, z=10.0), 
          Rotation=Rotation(Axis=Vector(x=0.0, y=0.0, z=1.0), Angle=0.0 rad))
```

### Quantity
```
"10.0 mm"  # Length property
"5.0 deg"  # TaperAngle property
```

### Link/Reference Properties
```
[<Sketcher::SketchObject>, ['']]  # Profile tuple
[<GeoFeature object>, ['XY_Plane001']]  # AttachmentSupport
```

### Constraint Objects (Sketcher)
```
[<Constraint 'Coincident'>, <Constraint 'DistanceY'>, ...]
