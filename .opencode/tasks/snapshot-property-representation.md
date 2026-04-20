# Task: Snapshot Property Internal Representation

## Goal
Design and implement an internal representation for FreeCAD properties that:
1. Produces IDENTICAL snapshots after YAML serialize/deserialize round-trips (primitives only)
2. Retains ALL expressions at ALL levels (top-level properties AND sub-properties like `Placement.Base.x`)
3. For complex types like Constraints, captures visible properties/expressions for diff display
4. Is as generic as possible, with custom handling only where absolutely necessary
5. Generic list/tuple handling: each item is processed individually using existing handlers; unknown objects are converted to CUSTOM_UNKNOWN string representation

## Context

### Current Problems
1. **Non-deterministic serialization**: Custom types (`Vector`, `Placement`, `Constraint`) don't preserve exact representation through YAML round-trips
2. **Lost sub-property expressions**: Only top-level property expressions are captured; sub-properties like `Placement.Base.x` lose their expressions
3. **List serialization breaks comparison**: Constraints are converted to strings, losing structure and breaking equality checks
4. **No generic list/tuple handling**: Only Constraints lists are handled specially; other lists lose their structure

### Investigation Findings

#### Expression Path Format
- ExpressionEngine stores paths with a **leading dot**: `.Placement.Base.x` not `Placement.Base.x`
- **Top-level properties** (e.g., `Length`) have NO leading dot: `('Length', '5 mm')`
- **Sub-properties** (e.g., `Placement.Base.x`) HAVE a leading dot: `('.Placement.Base.x', '100 mm')`
- **ALL levels can have expressions**: Both intermediate objects AND leaf values
  - Example: `.Placement.Rotation` (whole Rotation object)
  - Example: `.Placement.Rotation.Axis` (Axis Vector as a whole)
  - Example: `.Placement.Rotation.Axis.x` (individual component)
- Each path level can have its own independent expression
- `getPathValue()` method exists in C++ but is NOT exposed to Python bindings

#### Property Expansion Patterns
Based on FreeCAD source code analysis and runtime inspection:

| Type | Has "Value"? | Sub-properties | Pattern |
|------|-------------|----------------|---------|
| **Placement** | ❌ No | `Base`, `Base.x/y/z`, `Rotation`, `Rotation.Angle`, `Rotation.Axis`, `Rotation.Axis.x/y/z` | Has `Base`+`Rotation` |
| **Vector** | ❌ No | `x`, `y`, `z` | Has `x`+`y`+`z` |
| **Rotation** | ❌ No | `Angle`, `Axis`, `Axis.x/y/z` | Has `Angle`+`Axis` |
| **Constraint** | ✅ Yes | `Type`, `Value`, `First`, `Second`, `Third`, `Driving`, etc. | List of objects with these attrs |
| **Quantity** | ✅ Yes | `Value` (primitive), `Unit`, `Format` | Has `Value` attribute |

**Critical**: 
- Placement has NO "Value" attribute - a "Value-only" expansion strategy would lose ALL placement data.
- **Intermediate objects can have expressions**: `Rotation` itself, `Rotation.Axis` itself, not just leaf values.

#### Constraint Structure
Each constraint object has many properties:
- Visible in UI: `Type`, `Value`, `First`, `Second` (and sometimes `Third`)
- Internal: Many more properties not shown in property editor (solver metadata, reference IDs, etc.)
- Purpose of workbench: Show diffs of what users see

**Why `visible_properties` field name?**
Constraints use `visible_properties` to store only user-visible attributes for clean diff output. This allows:
- Clean diffs showing only what matters to users
- If internal state changes but visible properties don't, user sees no diff (acceptable for MVP)

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| **Flat path map storage** | Matches FreeCAD's internal representation; simplifies comparison and serialization | Nested objects with `get_children()` recursion |
| **Pattern-based expansion via registry** | Each type has a handler that provides extract/serialize/deserialize; extensible without modifying core logic | Hardcoded if/elif chains (error-prone); Type-name based dispatch (fragile) |
| **Constraints: visible props only** | Captures user-visible changes for clean diff display | Full property expansion (too verbose); String representation (loses structure) |
| **Primitives only in domain** | Ensures YAML round-trip identity; enables proper equality checks | Store FreeCAD objects directly (breaks serialization) |
| **Unified expression storage** | All expressions stored in path map with key `""` for top-level; no separate `expression` field | Separate top-level vs sub-property expression handling (complex, error-prone) |
| **Handler-based serialization** | Each handler knows how to serialize/deserialize its paths; keeps serialization logic co-located with extraction | Centralized if/elif dispatch (must update for each new type) |
| **Generic list/tuple handling** | Default behavior for lists: process each item individually; use handler registry or convert to CUSTOM_UNKNOWN | Per-type special handling (not scalable); store as raw list (loses structure) |
| **CUSTOM_UNKNOWN for unknown objects** | Unknown non-primitive objects converted to string representation; preserves type info in format `<Object TypeName>` | Store as generic object (breaks serialization); discard entirely (loses info) |

## Obsolete Code to Remove

The following existing code will be replaced by the new implementation and should be removed:

### `freecad/diff_wb/domain/tree/property.py`

| Lines | Item | Reason |
|-------|------|--------|
| 45-51 | `_PROPERTY_HANDLERS` registry + `register_handler` decorator | Replaced by `PropertyPathHandler` registry |
| 54-86 | `PropertyHandler` base class | Replaced by `PropertyPathHandler` protocol |
| 89-146 | `Vector` class + handler | Replaced by path-based extraction; no longer stores x/y/z as domain object |
| 149-186 | `Rotation` class | Replaced by path-based extraction |
| 189-256 | `Placement` class + handler | Replaced by path-based extraction |
| 343-404 | `Property.create()` factory | No longer needed; `PropertyPathValue` constructed directly during extraction |
| 406-431 | `Property.from_freecad_property()` | Replaced by handler-based extraction |
| 433-449 | `Property._infer_type_from_value()` | Path extraction uses `PropertyPathValue.from_value()` instead |
| 451-524 | `Property.get_children()` and all `_get_*` helpers | Path map is already flattened; no recursion needed |

### `freecad/diff_wb/infrastructure/persistence/snapshot_yaml.py`

| Lines | Item | Reason |
|-------|------|--------|
| 170-185 | `_serialize_property_value` VECTOR/PLACEMENT handling | Replaced by handler-based path-map serialization |
| 247-265 | `_deserialize_property_value` VECTOR/PLACEMENT handling | Replaced by handler-based path-map deserialization |

### `freecad/diff_wb/domain/snapshots/gui_extractor.py`

| Lines | Item | Reason |
|-------|------|--------|
| 230-251 | `_get_expression_for_property()` | Replaced by expression map building in path handlers |
| 274-299 | `_extract_property_value()` | Major refactor to use handler-based path extraction |

### `freecad/diff_wb/domain/tree/__init__.py`

```python
# REMOVE from exports: Vector, Rotation, Placement
# ADD to exports: PropertyPathValue, PropertyPathType, PropertyPathHandler, ConstraintData
```

## Architecture Impact

### Modules Affected

#### Domain Layer (`freecad/diff_wb/domain/tree/`)
- **`property.py`**: DELETE existing `Vector`, `Rotation`, `Placement` classes and `PropertyHandler` registry
- **`property_handlers.py`** (NEW FILE): Property path handler registry
  - `PropertyPathHandler` protocol defining `handles_value()`, `extract_paths()`, `serialize_paths()`, `deserialize_paths()`
  - `register_path_handler` decorator for registration
  - Concrete handlers:
    - `PlacementPathHandler` - for Placement-like objects (has Base + Rotation)
    - `VectorPathHandler` - for Vector-like objects (has x, y, z)
    - `RotationPathHandler` - for Rotation-like objects (has Angle + Axis)
    - `ConstraintDataPathHandler` - for ConstraintData domain objects
    - `ListPathHandler` - for generic lists/tuples (iterates items via registry)
    - `SimplePathHandler` - fallback for primitives and unknown types
- **`property.py`** UPDATE:
  - Add `PropertyPathType` enum: `FLOAT`, `INT`, `STRING`, `BOOL`, `NULL`
  - Add `PropertyPathValue` dataclass with explicit `type_` field and `from_value()` factory
  - Add `ConstraintData` dataclass for constraint representation
  - Remove `Property.expression` field (unified into path map with `""` key)
  - Keep `Property` class but simplify (type_, value, group only)

#### Infrastructure Layer (`freecad/diff_wb/infrastructure/persistence/`)
- **`snapshot_yaml.py`**: Update serialization
  - Use handler registry to serialize/deserialize path maps
  - Use `ConstraintDataPathHandler` for ConstraintData serialization/deserialization

#### Domain Layer (`freecad/diff_wb/domain/snapshots/`)
- **`gui_extractor.py`**: Update extraction
  - Use handler registry via `extract_property_paths()` function
  - Remove `_get_expression_for_property()` (replaced by handler expression map building)
  - Handle constraint special case via `ConstraintData` extraction

### Public API Changes

**New Module and Types:**
```python
# In domain/tree/property_handlers.py
class PropertyPathHandler(Protocol):
    """Protocol for property path handlers."""
    @staticmethod
    def handles_value(value: Any) -> bool: ...
    @staticmethod
    def extract_paths(value: Any, expr_map: dict[str, str]) -> dict[str, PropertyPathValue]: ...
    @staticmethod
    def serialize_paths(paths: dict[str, PropertyPathValue]) -> Any: ...
    @staticmethod
    def deserialize_paths(data: Any) -> dict[str, PropertyPathValue]: ...

def register_path_handler(cls: type[PropertyPathHandler]) -> type[PropertyPathHandler]: ...
def get_path_handler(value: Any) -> PropertyPathHandler | None: ...
def extract_property_paths(value: Any, expr_map: dict[str, str]) -> dict[str, PropertyPathValue]: ...

# In domain/tree/__init__.py
__all__ = [
    "Property", "PropertyType", "PropertyPathValue", "PropertyPathType",
    "PropertyPathHandler", "register_path_handler", "extract_property_paths",
    "ConstraintData"
]
# REMOVED: Vector, Rotation, Placement (no longer domain objects)
```

**Modified `Property` structure (expression unified into path map):**
```python
# Before:
Property(type_=PLACEMENT, value=Placement(...), expression="top_level_expr")

# After (expression stored at path ""):
Property(
    type_=PLACEMENT,
    value={
        "": PropertyPathValue(type_=PropertyPathType.NULL, value=None, expression="top_level_expr"),  # Unified!
        "Base.x": PropertyPathValue(type_=PropertyPathType.FLOAT, value=0.0, expression=None),
        "Base.y": PropertyPathValue(type_=PropertyPathType.FLOAT, value=0.0, expression=None),
        "Base.z": PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0, expression="Pad.Length * 2"),
        "Rotation": PropertyPathValue(type_=PropertyPathType.NULL, value=None, expression="some_rotation_expr"),
        "Rotation.Angle": PropertyPathValue(type_=PropertyPathType.FLOAT, value=30.0, expression="30 deg"),
        "Rotation.Axis": PropertyPathValue(type_=PropertyPathType.NULL, value=None, expression="some_axis_expr"),
        "Rotation.Axis.x": PropertyPathValue(type_=PropertyPathType.FLOAT, value=0.577, expression="0.577"),
        "Rotation.Axis.y": PropertyPathValue(type_=PropertyPathType.FLOAT, value=0.577, expression="0.577"),
        "Rotation.Axis.z": PropertyPathValue(type_=PropertyPathType.FLOAT, value=0.577, expression="0.577"),
    },
    # NOTE: No separate expression field - all expressions unified into path map
)
```

**Key Changes**:
- `Property` no longer has `expression` field - expressions unified into path map with `""` key
- Every `PropertyPathValue` now has an explicit `type_` field
- Use `PropertyPathValue.from_value()` factory for convenience during extraction
- Intermediate objects use `type_=PropertyPathType.NULL` with `value=None`
- Handlers are registered via `@register_path_handler` decorator

**Example YAML Output (With Type Information):**
```yaml
Placement:
  type_: PLACEMENT
  group: Data
  value:
    "":  # Top-level expression unified as empty string key
      type_: NULL
      value: null
      expression: "top_level_expression"
    Base.x:
      type_: FLOAT  # NEW: Explicit type for deserialization
      value: 0.0
    Base.y:
      type_: FLOAT
      value: 0.0
    Base.z:
      type_: FLOAT
      value: 10.0
      expression: "Pad.Length * 2"
    Rotation:
      type_: NULL  # Intermediate object has no scalar value
      value: null
      expression: "some_rotation_expression"
    Rotation.Angle:
      type_: FLOAT
      value: 30.0
      expression: "30 deg"
    Rotation.Axis:
      type_: NULL  # Vector object has no scalar value
      value: null
      expression: "some_axis_expression"
    Rotation.Axis.x:
      type_: FLOAT
      value: 0.577
      expression: "0.577"
    Rotation.Axis.y:
      type_: FLOAT
      value: 0.577
      expression: "0.577"
    Rotation.Axis.z:
      type_: FLOAT
      value: 0.577
      expression: "0.577"
```

**Constraints List Example:**
```yaml
Constraints:
  type_: LIST
  group: Data
  value:
    - type_: CONSTRAINT  # Each item has its own type_
      visible_properties:
        Type:
          type_: STRING
          value: "Coincident"
        First:
          type_: INT
          value: 0
        Second:
          type_: INT
          value: 1
        Driving:
          type_: BOOL
          value: true
    - type_: CONSTRAINT
      visible_properties:
        Type:
          type_: STRING
          value: "Distance"
        Value:
          type_: FLOAT
          value: 10.0
          expression: "10 mm"
        First:
          type_: INT
          value: 1
        Second:
          type_: INT
          value: 2
```

**Generic List Example (list of floats):**
```yaml
SomeFloatList:
  type_: LIST
  group: Data
  value:
    "0":
      type_: FLOAT
      value: 10.0
    "1":
      type_: FLOAT
      value: 20.0
    "2":
      type_: FLOAT
      value: 30.0
```

**Generic List with Unknown Object Example:**
```yaml
SomeMixedList:
  type_: LIST
  group: Data
  value:
    "0":
      type_: FLOAT
      value: 10.0
    "1":
      type_: CUSTOM_UNKNOWN
      value: "<Object SomeSpecialType>"
```

**Key Design Decisions:**
1. **Explicit types everywhere**: Every `PropertyPathValue` includes `type_` field
2. **Item type marker**: Each list item includes `type_` for deterministic deserialization (no container-level list_type needed)
3. **No guessing needed**: Deserializer uses `type_` field instead of checking for keys
4. **Clean round-trip**: Serialize → deserialize produces identical objects
5. **Generic list handling**: Default behavior uses handler registry for each item; unknown objects become CUSTOM_UNKNOWN
6. **CUSTOM_UNKNOWN preserves type info**: Unknown objects stored as `<Object TypeName>` string
7. **Handler registry is recursive**: ConstraintData, Placement, Vector, etc. are all handled by registered handlers; lists just iterate and delegate

**YAML Design Principles:**
1. **Null omission**: Fields with `null` values are omitted to save space
2. **Deserialization**: Missing fields default to `None` via `.get("field")`
3. **Round-trip identity**: Serialize → deserialize produces identical objects
4. **Deep nesting supported**: ALL levels can have independent expressions

## FreeCAD Dependency
- [ ] No FreeCAD required (pure code)
- [x] FreeCAD required (follow exploration phase)

**Reason**: Need to test extraction logic against real FreeCAD objects and verify expression paths.

## Implementation Plan

### Phase 1: Core Data Structures (No FreeCAD)

**Goal**: Define new domain models for path-based property storage.

#### Step 1.1: Write tests for `PropertyPathType` enum and `PropertyPathValue` dataclass
```python
# tests/unit/domain/tree/test_property_paths.py

def test_property_path_type_enum_values():
    """Test: PropertyPathType has all required primitive types."""
    assert PropertyPathType.FLOAT in PropertyPathType
    assert PropertyPathType.INT in PropertyPathType
    assert PropertyPathType.STRING in PropertyPathType
    assert PropertyPathType.BOOL in PropertyPathType
    assert PropertyPathType.NULL in PropertyPathType


def test_property_path_value_from_value_auto_detects_types():
    """Test: from_value() correctly auto-detects types."""
    # Float
    pv = PropertyPathValue.from_value(10.5)
    assert pv.type_ == PropertyPathType.FLOAT
    assert pv.value == 10.5
    
    # Int
    pv = PropertyPathValue.from_value(42)
    assert pv.type_ == PropertyPathType.INT
    assert pv.value == 42
    
    # String
    pv = PropertyPathValue.from_value("hello")
    assert pv.type_ == PropertyPathType.STRING
    assert pv.value == "hello"
    
    # Bool (must check before int!)
    pv = PropertyPathValue.from_value(True)
    assert pv.type_ == PropertyPathType.BOOL
    assert pv.value is True
    
    # None
    pv = PropertyPathValue.from_value(None)
    assert pv.type_ == PropertyPathType.NULL
    assert pv.value is None


def test_property_path_value_equality_considers_type():
    """Test: PropertyPathValue equality requires matching types."""
    # Same type, same value, same expression → equal
    pv1 = PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0, expression=None)
    pv2 = PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0, expression=None)
    assert pv1 == pv2
    
    # Different types, same value → NOT equal
    pv1 = PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0, expression=None)
    pv2 = PropertyPathValue(type_=PropertyPathType.INT, value=10, expression=None)
    assert pv1 != pv2  # FLOAT vs INT
    
    # Same type, different expressions → NOT equal
    pv1 = PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0, expression=None)
    pv2 = PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0, expression="5 + 5")
    assert pv1 != pv2


def test_property_path_value_float_tolerance():
    """Test: PropertyPathValue uses float tolerance for numeric values."""
    pv1 = PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0000000001, expression=None)
    pv2 = PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0, expression=None)
    
    assert pv1 == pv2  # Within tolerance
```

#### Step 1.2: Define path value types and implement `PropertyPathValue` dataclass

First, we need a type enum for path values (primitive types only):

```python
# freecad/diff_wb/domain/tree/property.py

from enum import Enum, auto

class PropertyPathType(Enum):
    """Types for individual path values within complex properties.
    
    Unlike PropertyType which describes FreeCAD property types (PLACEMENT, VECTOR, etc.),
    PropertyPathType describes the primitive Python types stored at each path.
    
    Examples:
        Placement.Base.x → PropertyPathType.FLOAT
        Constraints.Constr0.Type → PropertyPathType.STRING
        Rotation.Axis (intermediate) → PropertyPathType.NULL
        Unknown object → PropertyPathType.CUSTOM_UNKNOWN with value "<Object TypeName>"
    """
    FLOAT = auto()
    INT = auto()
    STRING = auto()
    BOOL = auto()
    NULL = auto()  # For intermediate objects like "Rotation" that have no scalar value
    CUSTOM_UNKNOWN = auto()  # For unknown objects stored as string representation


@dataclass(frozen=True)
class PropertyPathValue:
    """A property value at a specific path with its expression and type.
    
    This represents a single leaf (or intermediate node) in the property tree,
    containing the primitive value, its type, and any expression that drives it.
    
    Attributes:
        type_: The primitive type of the value (FLOAT, INT, STRING, BOOL, NULL, CUSTOM_UNKNOWN)
        value: The primitive value (must match type_; for CUSTOM_UNKNOWN, a string like "<Object TypeName>")
        expression: Optional expression string that drives this value
    
    Examples:
        # Leaf value with expression:
        PropertyPathValue(type_=FLOAT, value=10.0, expression="5 + 5")
        
        # Intermediate object (no scalar value):
        PropertyPathValue(type_=NULL, value=None, expression="some_rotation_expr")
        
        # Simple integer:
        PropertyPathValue(type_=INT, value=42, expression=None)
        
        # Unknown object (stored as string representation):
        PropertyPathValue(type_=CUSTOM_UNKNOWN, value="<Object MyType>", expression=None)
    """
    type_: PropertyPathType
    value: Any  # Must match type_: float/int/str/bool/None or CUSTOM_UNKNOWN string
    expression: str | None = None
    
    @classmethod
    def from_value(cls, value: Any, expression: str | None = None) -> "PropertyPathValue":
        """Factory method to create PropertyPathValue from a raw value.
        
        Automatically detects the type from the value. For unknown non-primitive
        objects, creates CUSTOM_UNKNOWN with string representation "<Object TypeName>".
        
        Args:
            value: The primitive value
            expression: Optional expression string
        
        Returns:
            PropertyPathValue with auto-detected type
        """
        if value is None:
            type_ = PropertyPathType.NULL
        elif isinstance(value, bool):  # Check bool before int (bool is subclass of int)
            type_ = PropertyPathType.BOOL
        elif isinstance(value, int):
            type_ = PropertyPathType.INT
        elif isinstance(value, float):
            type_ = PropertyPathType.FLOAT
        elif isinstance(value, str):
            type_ = PropertyPathType.STRING
        else:
            # Unknown non-primitive: convert to string representation
            type_ = PropertyPathType.CUSTOM_UNKNOWN
            value = f"<Object {type(value).__name__}>"
        
        return cls(type_=type_, value=value, expression=expression)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PropertyPathValue):
            return NotImplemented
        
        # Types must match
        if self.type_ != other.type_:
            return False
        
        # Expressions must match exactly
        if self.expression != other.expression:
            return False
        
        # Use approximate equality for floats (handles large/small values better)
        if self.type_ == PropertyPathType.FLOAT:
            import math
            return math.isclose(self.value, other.value, rel_tol=1e-9, abs_tol=1e-9)

        return self.value == other.value
```

#### Step 1.3: Write tests for PropertyPathHandler registry
```python
# tests/unit/domain/tree/test_property_handlers.py

def test_handler_registry_finds_placement_handler():
    """Test: get_path_handler returns PlacementPathHandler for placement values."""
    class FakePlacement:
        class Base:
            x, y, z = 0.0, 0.0, 0.0
        class Rotation:
            Angle = 0.0
            class Axis:
                x, y, z = 0.0, 0.0, 1.0
    handler = get_path_handler(FakePlacement())
    assert handler is not None
    assert isinstance(handler, type) and handler.__name__ == "PlacementPathHandler"

def test_handler_registry_falls_back_to_simple():
    """Test: get_path_handler returns SimplePathHandler for unknown types."""
    handler = get_path_handler(42)  # int
    assert handler is not None
    # SimplePathHandler is the fallback

def test_handler_registry_handles_primitives():
    """Test: Primitives are handled correctly."""
    assert get_path_handler(3.14) is not None   # float
    assert get_path_handler("hello") is not None  # string
    assert get_path_handler(True) is not None    # bool
```

#### Step 1.4: Implement PropertyPathHandler registry and protocol
```python
# freecad/diff_wb/domain/tree/property_handlers.py
"""Property path handler registry for extracting, serializing, and deserializing property values."""

from typing import Any, Protocol

from .property import PropertyPathValue


class PropertyPathHandler(Protocol):
    """Protocol for property path handlers.

    All handlers must implement extraction, serialization, and deserialization
    for their property type to ensure consistent behavior across the system.
    """

    @staticmethod
    def handles_value(value: Any) -> bool:
        """Check if this handler can handle the given value."""
        ...

    @staticmethod
    def extract_paths(
        value: Any,
        expr_map: dict[str, str],
    ) -> dict[str, PropertyPathValue]:
        """Extract all paths with their values and expressions."""
        ...

    @staticmethod
    def serialize_paths(paths: dict[str, PropertyPathValue]) -> Any:
        """Serialize path map to YAML-compatible format."""
        ...

    @staticmethod
    def deserialize_paths(data: Any) -> dict[str, PropertyPathValue]:
        """Deserialize from YAML format back to path map."""
        ...


_PROPERTY_PATH_HANDLERS: list[type[PropertyPathHandler]] = []


def register_path_handler(cls: type[PropertyPathHandler]) -> type[PropertyPathHandler]:
    """Decorator to register a property path handler.

    Handlers are tried in registration order until one returns True for handles_value().
    """
    _PROPERTY_PATH_HANDLERS.append(cls)
    return cls


def get_path_handler(value: Any) -> PropertyPathHandler | None:
    """Get the appropriate handler for a value."""
    for handler_cls in _PROPERTY_PATH_HANDLERS:
        if handler_cls.handles_value(value):
            return handler_cls
    return None


def extract_property_paths(
    value: Any,
    expr_map: dict[str, str],
) -> dict[str, PropertyPathValue]:
    """Extract property paths using the appropriate handler."""
    handler = get_path_handler(value)
    if handler is None:
        raise ValueError(f"No handler found for value type: {type(value)}")
    return handler.extract_paths(value, expr_map)
```

#### Step 1.5: Implement concrete handlers
```python
# freecad/diff_wb/domain/tree/property_handlers.py (continued)

@register_path_handler
class PlacementPathHandler:
    """Handler for Placement-like objects (has Base/Position + Rotation)."""

    @staticmethod
    def handles_value(value: Any) -> bool:
        if value is None:
            return False
        has_position = hasattr(value, 'Base') or hasattr(value, 'Position')
        has_rotation = hasattr(value, 'Rotation') or hasattr(value, 'rotation')
        return has_position and has_rotation

    @staticmethod
    def extract_paths(
        value: Any,
        expr_map: dict[str, str],
    ) -> dict[str, PropertyPathValue]:
        from .property import PropertyPathType
        paths: dict[str, PropertyPathValue] = {}

        # Extract position components
        base = getattr(value, 'Base', None) or getattr(value, 'Position', None)
        if base is not None:
            for attr in ('x', 'y', 'z'):
                path_key = f"Base.{attr}"
                raw_value = getattr(base, attr, 0.0)
                paths[path_key] = PropertyPathValue(
                    type_=PropertyPathType.FLOAT,
                    value=float(raw_value),
                    expression=expr_map.get(path_key)
                )

        # Extract rotation
        rotation = getattr(value, 'Rotation', None)
        if rotation is not None:
            # Check for rotation-level expression (intermediate object)
            if 'Rotation' in expr_map:
                paths['Rotation'] = PropertyPathValue(
                    type_=PropertyPathType.NULL,
                    value=None,
                    expression=expr_map['Rotation']
                )

            angle = getattr(rotation, 'Angle', 0.0) or getattr(rotation, 'angle', 0.0)
            paths['Rotation.Angle'] = PropertyPathValue(
                type_=PropertyPathType.FLOAT,
                value=float(angle),
                expression=expr_map.get('Rotation.Angle')
            )

            axis = getattr(rotation, 'Axis', None) or getattr(rotation, 'axis', None)
            if axis is not None:
                if 'Rotation.Axis' in expr_map:
                    paths['Rotation.Axis'] = PropertyPathValue(
                        type_=PropertyPathType.NULL,
                        value=None,
                        expression=expr_map['Rotation.Axis']
                    )
                for attr in ('x', 'y', 'z'):
                    path_key = f"Rotation.Axis.{attr}"
                    raw_value = getattr(axis, attr, 0.0)
                    paths[path_key] = PropertyPathValue(
                        type_=PropertyPathType.FLOAT,
                        value=float(raw_value),
                        expression=expr_map.get(path_key)
                    )

        return paths

    @staticmethod
    def serialize_paths(paths: dict[str, PropertyPathValue]) -> dict[str, Any]:
        """Default serialization works for all path-based types."""
        result = {}
        for path, pv in paths.items():
            entry: dict[str, Any] = {"type_": pv.type_.name}
            if pv.value is not None:
                entry["value"] = pv.value
            if pv.expression is not None:
                entry["expression"] = pv.expression
            result[path] = entry
        return result

    @staticmethod
    def deserialize_paths(data: Any) -> dict[str, PropertyPathValue]:
        from .property import PropertyPathType
        result = {}
        for path, item in data.items():
            type_name = item.get("type_", "NULL")
            try:
                type_ = PropertyPathType[type_name]
            except KeyError:
                type_ = PropertyPathType.NULL
            result[path] = PropertyPathValue(
                type_=type_,
                value=item.get("value"),
                expression=item.get("expression"),
            )
        return result


@register_path_handler
class VectorPathHandler:
    """Handler for Vector-like objects (has x, y, z)."""

    @staticmethod
    def handles_value(value: Any) -> bool:
        return value is not None and hasattr(value, 'x') and hasattr(value, 'y') and hasattr(value, 'z')

    @staticmethod
    def extract_paths(
        value: Any,
        expr_map: dict[str, str],
    ) -> dict[str, PropertyPathValue]:
        from .property import PropertyPathType
        paths = {}
        for attr in ('x', 'y', 'z'):
            paths[attr] = PropertyPathValue(
                type_=PropertyPathType.FLOAT,
                value=float(getattr(value, attr, 0.0)),
                expression=expr_map.get(attr)
            )
        return paths


@register_path_handler
class RotationPathHandler:
    """Handler for Rotation-like objects (has Angle + Axis)."""

    @staticmethod
    def handles_value(value: Any) -> bool:
        if value is None:
            return False
        has_angle = hasattr(value, 'Angle') or hasattr(value, 'angle')
        has_axis = hasattr(value, 'Axis') or hasattr(value, 'axis')
        return has_angle and has_axis

    @staticmethod
    def extract_paths(
        value: Any,
        expr_map: dict[str, str],
    ) -> dict[str, PropertyPathValue]:
        from .property import PropertyPathType
        paths = {}

        angle = getattr(value, 'Angle', 0.0) or getattr(value, 'angle', 0.0)
        paths['Angle'] = PropertyPathValue(
            type_=PropertyPathType.FLOAT,
            value=float(angle),
            expression=expr_map.get('Angle')
        )

        axis = getattr(value, 'Axis', None) or getattr(value, 'axis', None)
        if axis is not None:
            if 'Axis' in expr_map:
                paths['Axis'] = PropertyPathValue(
                    type_=PropertyPathType.NULL,
                    value=None,
                    expression=expr_map['Axis']
                )
            for attr in ('x', 'y', 'z'):
                path_key = f"Axis.{attr}"
                paths[path_key] = PropertyPathValue(
                    type_=PropertyPathType.FLOAT,
                    value=float(getattr(axis, attr, 0.0)),
                    expression=expr_map.get(path_key)
                )

        return paths


@register_path_handler
class ListPathHandler:
    """Handler for generic lists/tuples - processes each item via the handler registry."""

    @staticmethod
    def handles_value(value: Any) -> bool:
        return isinstance(value, (list, tuple))

    @staticmethod
    def extract_paths(
        value: list | tuple,
        expr_map: dict[str, str],
    ) -> dict[str, PropertyPathValue]:
        """Extract paths from all items in the list.
        
        Each item is processed using extract_property_paths() to use the
        appropriate handler for that item type. Items are keyed by their
        index as strings ("0", "1", "2", etc.).
        """
        paths = {}
        for i, item in enumerate(value):
            item_index = str(i)
            # Get expression for this list item if any
            item_expr = expr_map.get(item_index)
            
            # Check if item has its own handler
            item_handler = get_path_handler(item)
            if item_handler is not None:
                # Handler-based extraction for complex items (ConstraintData, etc.)
                item_paths = item_handler.extract_paths(item, {})
                # Combine with index prefix
                for path_key, path_value in item_paths.items():
                    if path_key == "":
                        # Single value item, use index as key
                        paths[item_index] = path_value
                    else:
                        # Nested item, prefix with index
                        paths[f"{item_index}.{path_key}"] = path_value
            else:
                # Fallback for items without handler (shouldn't happen with current handlers)
                paths[item_index] = PropertyPathValue.from_value(item, expression=item_expr)
        
        return paths

    @staticmethod
    def serialize_paths(paths: dict[str, PropertyPathValue]) -> list[dict[str, Any]]:
        """Serialize a list of path values.
        
        Each path value is serialized individually based on its type_,
        using the handler registry for complex types.
        """
        # Collect all items in order by their index
        indices = sorted(paths.keys(), key=lambda x: (len(x), x))
        result = []
        for idx in indices:
            pv = paths[idx]
            entry: dict[str, Any] = {"type_": pv.type_.name}
            if pv.value is not None:
                entry["value"] = pv.value
            if pv.expression is not None:
                entry["expression"] = pv.expression
            result.append(entry)
        return result

    @staticmethod
    def deserialize_paths(data: list) -> dict[str, PropertyPathValue]:
        """Deserialize a list of items back to path map with numeric string keys."""
        from .property import PropertyPathType
        result = {}
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                result[str(i)] = PropertyPathValue.from_value(item)
                continue
            
            type_name = item.get("type_", "NULL")
            try:
                type_ = PropertyPathType[type_name]
            except KeyError:
                type_ = PropertyPathType.NULL
            
            result[str(i)] = PropertyPathValue(
                type_=type_,
                value=item.get("value"),
                expression=item.get("expression"),
            )
        return result


@register_path_handler
class SimplePathHandler:
    """Fallback handler for simple/primitive values."""

    @staticmethod
    def handles_value(value: Any) -> bool:
        # Catch-all for primitives and unhandled types
        return True

    @staticmethod
    def extract_paths(
        value: Any,
        expr_map: dict[str, str],
    ) -> dict[str, PropertyPathValue]:
        # Simple value: only one path (empty string = root)
        return {"": PropertyPathValue.from_value(value, expression=expr_map.get(""))}
```

#### Step 1.6: Write tests for ConstraintData
```python
def test_constraint_data_equality():
    """Test: ConstraintData equality compares visible_properties only."""
    cd1 = ConstraintData(
        visible_properties={
            "Type": PropertyPathValue.from_value("Distance"),
            "Value": PropertyPathValue.from_value(10.0),
        }
    )
    cd2 = ConstraintData(
        visible_properties={
            "Type": PropertyPathValue.from_value("Distance"),
            "Value": PropertyPathValue.from_value(10.0),
        }
    )
    cd3 = ConstraintData(
        visible_properties={
            "Type": PropertyPathValue.from_value("Distance"),
            "Value": PropertyPathValue.from_value(15.0),  # Different
        }
    )
    assert cd1 == cd2
    assert cd1 != cd3
```

### Phase 2: Property Extraction with Path Maps (Requires FreeCAD)

**Goal**: Extract properties as flat path maps using the handler registry.

#### Step 2.1: Write integration test for handler-based extraction
```python
# tests/integration/test_property_path_extraction.py
def test_extract_placement_via_handler(freecad_doc):
    """Test: Placement extraction uses handler registry."""
    box = freecad_doc.addObject("Part::Box", "TestBox")
    box.setExpression("Placement.Base.x", "10 mm")

    # Build expression map
    expr_map = _build_expression_map_for_property("Placement", box.ExpressionEngine)

    # Extract using handler registry
    from freecad.diff_wb.domain.tree.property_handlers import extract_property_paths
    paths = extract_property_paths(box.Placement, expr_map)

    assert "Base.x" in paths
    assert paths["Base.x"].expression == "10 mm"
    assert paths["Base.x"].value == 10.0

def test_extract_top_level_expression_unified(freecad_doc):
    """Test: Top-level expressions stored at path ''."""
    box = freecad_doc.addObject("Part::Box", "TestBox")
    box.setExpression("Placement", " Placement * 2")  # Top-level expression

    expr_map = _build_expression_map_for_property("Placement", box.ExpressionEngine)
    paths = extract_property_paths(box.Placement, expr_map)

    assert "" in paths  # Top-level expression at empty string key
    assert paths[""].expression == " Placement * 2"
    assert paths[""].type_ == PropertyPathType.NULL
    assert paths[""].value is None
```

#### Step 2.2: Implement expression map builder for property
```python
# freecad/diff_wb/domain/snapshots/gui_extractor.py

from freecad.diff_wb.domain.tree.property_handlers import extract_property_paths

def _build_expression_map_for_property(
    prop_name: str,
    expr_engine: list
) -> dict[str, str]:
    """Build expression map for a specific property.

    Transforms ExpressionEngine entries into a simple path→expression map.
    Handles the leading dot prefix that FreeCAD uses.

    Args:
        prop_name: Property name (e.g., "Placement", "Length")
        expr_engine: ExpressionEngine list from FreeCAD object

    Returns:
        Dict mapping relative paths to expression strings.
        Empty string key "" represents top-level expression.
    """
    expr_map: dict[str, str] = {}
    for entry in expr_engine:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue

        full_path = entry[0]
        expr_str = str(entry[1])

        # Strip leading dot
        if full_path.startswith("."):
            path = full_path[1:]
        else:
            path = full_path

        # Strip property name prefix
        if path.startswith(prop_name):
            path = path[len(prop_name):]
            # path is now "" (top-level) or ".SubProp" (sub-property)
            if path.startswith("."):
                path = path[1:]

        expr_map[path] = expr_str

    return expr_map


def _extract_property_value_handler_based(
    obj: object,
    prop_name: str
) -> Property | None:
    """Extract property value using handler registry.

    This replaces the old _extract_property_value() with handler-based extraction.

    Args:
        obj: The FreeCAD object
        prop_name: The property name

    Returns:
        Property with path map value, or None on error
    """
    try:
        value = getattr(obj, prop_name)
        expr_engine = getattr(obj, "ExpressionEngine", [])
        expr_map = _build_expression_map_for_property(prop_name, expr_engine)
        group = _get_property_group(obj, prop_name)

        # Special handling for constraint lists
        if prop_name == "Constraints" and value:
            constraint_data_list = [_extract_constraint_data(c) for c in value]
            return Property(
                type_=PropertyType.LIST,
                value=constraint_data_list,
                group=group
            )

        # Use handler registry for extraction
        paths = extract_property_paths(value, expr_map)

        return Property(
            type_=PropertyType.PLACEMENT if "Base" in paths else Property._infer_type(value),
            value=paths,
            group=group
        )

    except Exception as e:
        Log.exception(f"Failed to extract property {prop_name}: {e}")
        return None
```

### Phase 3: Constraint Handling (Requires FreeCAD)

**Goal**: Extract constraint visible properties for diff display.

#### Step 3.1: Write tests for constraint extraction
```python
def test_constraint_extraction_captures_visible_properties():
    """Test: Constraint extraction captures Type, Value, First, Second."""
    # Use FakeConstraint from tests/fakes/
    constraint = FakeConstraint(Type="Distance", Value=10.0, First=0, Second=1)
    
    result = _extract_constraint_data(constraint)
    
    assert result.visible_properties["Type"].value == "Distance"
    assert result.visible_properties["Value"].value == 10.0

def test_constraint_data_equality():
    """Test: ConstraintData equality compares visible_properties only."""
    cd1 = ConstraintData(
        visible_properties={
            "Type": PropertyPathValue.from_value("Distance"),
            "Value": PropertyPathValue.from_value(10.0),
        }
    )
    cd2 = ConstraintData(
        visible_properties={
            "Type": PropertyPathValue.from_value("Distance"),
            "Value": PropertyPathValue.from_value(10.0),
        }
    )
    cd3 = ConstraintData(
        visible_properties={
            "Type": PropertyPathValue.from_value("Distance"),
            "Value": PropertyPathValue.from_value(15.0),  # Different
        }
    )
    assert cd1 == cd2
    assert cd1 != cd3
```

#### Step 3.2: Implement ConstraintData handler (ConstraintDataPathHandler)
```python
# freecad/diff_wb/domain/tree/property_handlers.py

@register_path_handler
class ConstraintDataPathHandler:
    """Handler for ConstraintData domain objects."""

    @staticmethod
    def handles_value(value: Any) -> bool:
        return isinstance(value, ConstraintData)

    @staticmethod
    def extract_paths(
        value: ConstraintData,
        expr_map: dict[str, str],
    ) -> dict[str, PropertyPathValue]:
        # ConstraintData is already extracted, just return its visible_properties
        # with path keys being the property names
        paths = {}
        for prop_name, path_value in value.visible_properties.items():
            paths[prop_name] = path_value
        return paths

    @staticmethod
    def serialize_paths(paths: dict[str, PropertyPathValue]) -> dict[str, Any]:
        result: dict[str, Any] = {"type_": "CONSTRAINT", "visible_properties": {}}
        for path, pv in paths.items():
            entry: dict[str, Any] = {"type_": pv.type_.name}
            if pv.value is not None:
                entry["value"] = pv.value
            if pv.expression is not None:
                entry["expression"] = pv.expression
            result["visible_properties"][path] = entry
        return result

    @staticmethod
    def deserialize_paths(data: Any) -> dict[str, PropertyPathValue]:
        from .property import PropertyPathType
        result = {}
        visible_props = data.get("visible_properties", {})
        for path, item in visible_props.items():
            type_name = item.get("type_", "NULL")
            try:
                type_ = PropertyPathType[type_name]
            except KeyError:
                type_ = PropertyPathType.NULL
            result[path] = PropertyPathValue(
                type_=type_,
                value=item.get("value"),
                expression=item.get("expression"),
            )
        return result

#### Step 3.3: Implement constraint extraction
```python
# freecad/diff_wb/domain/snapshots/gui_extractor.py

def _extract_constraint_data(constraint: Any) -> ConstraintData:
    """Extract visible properties from a Sketcher constraint.

    Args:
        constraint: A Sketcher.Constraint object

    Returns:
        ConstraintData with visible properties
    """
    # Extract visible properties (those shown in FreeCAD property editor)
    visible_props: dict[str, PropertyPathValue] = {}

    # Type is always visible
    if hasattr(constraint, 'Type'):
        visible_props['Type'] = PropertyPathValue.from_value(str(constraint.Type))

    # Value is visible for constraints that have it
    if hasattr(constraint, 'Value'):
        visible_props['Value'] = PropertyPathValue.from_value(float(constraint.Value))

    # First, Second, Third are geometry indices
    for attr in ['First', 'Second', 'Third']:
        if hasattr(constraint, attr):
            val = getattr(constraint, attr)
            if val is not None:
                visible_props[attr] = PropertyPathValue.from_value(int(val))

    # Driving status
    if hasattr(constraint, 'Driving'):
        visible_props['Driving'] = PropertyPathValue.from_value(bool(constraint.Driving))

    return ConstraintData(visible_properties=visible_props)
```

### Phase 4: YAML Serialization Round-Trip (No FreeCAD)

**Goal**: Ensure serialize → deserialize produces identical snapshots.

#### Step 4.1: Write tests for round-trip identity
```python
def test_property_with_path_map_roundtrip():
    """Test: Property with path map survives YAML round-trip identically."""
    original = Property(
        type_=PropertyType.PLACEMENT,
        value={
            "Base.x": PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0, expression=None),
            "Base.y": PropertyPathValue(type_=PropertyPathType.FLOAT, value=20.0, expression="Part.Length * 0.5"),
            "Rotation.Angle": PropertyPathValue(type_=PropertyPathType.FLOAT, value=90.0, expression=None),
        },
        # NOTE: expression field removed - all expressions unified into path map
    )

    # Serialize to YAML
    yaml_str = _serialize_property(original)

    # Verify type information is present
    assert '"type_": "FLOAT"' in yaml_str

    # Verify null expressions are omitted (space-efficient)
    assert '"expression": null' not in yaml_str
    assert '"expression": "Part.Length * 0.5"' in yaml_str

    # Deserialize
    restored = _deserialize_property(yaml_str, PropertyType.PLACEMENT)

    # Must be identical
    assert original == restored


def test_constraint_list_roundtrip():
    """Test: Constraint list survives YAML round-trip with type markers."""
    original = Property(
        type_=PropertyType.LIST,
        value=[
            ConstraintData(
                visible_properties={
                    "Type": PropertyPathValue(type_=PropertyPathType.STRING, value="Distance", expression=None),
                    "Value": PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0, expression="10 mm"),
                    "First": PropertyPathValue(type_=PropertyPathType.INT, value=0, expression=None),
                }
            )
        ],
        # NOTE: expression field removed
    )
    
    # Serialize to YAML
    yaml_str = _serialize_property(original)
    
    # Verify item type marker is present
    assert '"type_": "CONSTRAINT"' in yaml_str  # Item type marker
    assert '"type_": "STRING"' in yaml_str  # Field type markers
    assert '"type_": "FLOAT"' in yaml_str
    
    # Deserialize
    restored = _deserialize_property(yaml_str, PropertyType.LIST)
    
    # Must be identical
    assert original == restored


def test_primitive_type_preservation():
    """Test: Different primitive types are preserved through round-trip."""
    test_cases = [
        (42, PropertyPathType.INT),
        (10.5, PropertyPathType.FLOAT),
        ("hello", PropertyPathType.STRING),
        (True, PropertyPathType.BOOL),
        (False, PropertyPathType.BOOL),
        (None, PropertyPathType.NULL),
    ]
    
    for value, expected_type in test_cases:
        pv = PropertyPathValue.from_value(value)
        assert pv.type_ == expected_type, f"Expected {expected_type} for {value!r}"
        
        # Serialize and deserialize
        serialized = {"type_": pv.type_.name, "value": pv.value}
        deserialized = _deserialize_path_value(serialized)
        
        assert deserialized.type_ == expected_type
        assert deserialized.value == value
```


def test_placement_with_intermediate_expressions():
    """Test: Intermediate levels (Rotation, Rotation.Axis) with expressions survive round-trip."""
    original = Property(
        type_=PropertyType.PLACEMENT,
        value={
            "Base.x": PropertyPathValue(value=0.0, expression=None),
            "Base.y": PropertyPathValue(value=0.0, expression=None),
            "Base.z": PropertyPathValue(value=10.0, expression="Pad.Length * 2"),
            "Rotation": PropertyPathValue(value=None, expression="some_rotation_expr"),  # Intermediate!
            "Rotation.Angle": PropertyPathValue(value=30.0, expression="30 deg"),
            "Rotation.Axis": PropertyPathValue(value=None, expression="some_axis_expr"),  # Intermediate!
            "Rotation.Axis.x": PropertyPathValue(value=0.577, expression="0.577"),
            "Rotation.Axis.y": PropertyPathValue(value=0.577, expression="0.577"),
            "Rotation.Axis.z": PropertyPathValue(value=0.577, expression="0.577"),
        },
        # NOTE: expression field removed
    )

    # Serialize and deserialize
    yaml_str = _serialize_property(original)
    restored = _deserialize_property(yaml_str, PropertyType.PLACEMENT)

    # Must be identical
    assert original == restored

    # Verify intermediate expressions preserved
    assert restored.value["Rotation"].expression == "some_rotation_expr"
    assert restored.value["Rotation"].value is None  # No scalar value for objects
    assert restored.value["Rotation.Axis"].expression == "some_axis_expr"
    assert restored.value["Rotation.Axis"].value is None  # No scalar value for vectors

    # Verify leaf values preserved
    assert restored.value["Rotation.Axis.x"].expression == "0.577"
    assert restored.value["Rotation.Axis.x"].value == 0.577


def test_placement_with_deep_nesting_roundtrip():
    """Test: Deep nesting (Rotation.Axis.x/y/z) survives round-trip."""
    original = Property(
        type_=PropertyType.PLACEMENT,
        value={
            "Base.x": PropertyPathValue(value=0.0, expression=None),
            "Base.y": PropertyPathValue(value=0.0, expression=None),
            "Base.z": PropertyPathValue(value=10.0, expression="Pad.Length * 2"),
            "Rotation.Angle": PropertyPathValue(value=30.0, expression="30 deg"),
            "Rotation.Axis.x": PropertyPathValue(value=0.577, expression="0.577"),
            "Rotation.Axis.y": PropertyPathValue(value=0.577, expression="0.577"),
            "Rotation.Axis.z": PropertyPathValue(value=0.577, expression="0.577"),
        },
        # NOTE: expression field removed
    )
    
    # Serialize and deserialize
    yaml_str = _serialize_property(original)
    restored = _deserialize_property(yaml_str, PropertyType.PLACEMENT)
    
    # Must be identical
    assert original == restored
    
    # Verify all deep paths preserved
    assert restored.value["Rotation.Axis.x"].expression == "0.577"
    assert restored.value["Rotation.Axis.y"].expression == "0.577"
    assert restored.value["Rotation.Axis.z"].expression == "0.577"


def test_constraint_data_roundtrip():
    """Test: ConstraintData survives YAML round-trip identically."""
    original = ConstraintData(
        visible_properties={
            "Type": PropertyPathValue(value="Distance"),
            "Value": PropertyPathValue(value=10.0, expression="10 mm"),
            "First": PropertyPathValue(value=0),
        }
    )
    
    # Serialize using handler
    handler = get_path_handler(original)
    serialized = handler.serialize_paths(original.visible_properties)
    
    # Verify type marker and null expressions omitted
    assert serialized["type_"] == "CONSTRAINT"
    assert '"expression": null' not in str(serialized)
    
    # Deserialize
    restored_paths = handler.deserialize_paths(serialized)
    restored = ConstraintData(visible_properties=restored_paths)
    
    assert original == restored
```

#### Step 4.2: Update YAML serializer to use handler registry
```python
# freecad/diff_wb/infrastructure/persistence/snapshot_yaml.py

from freecad.diff_wb.domain.tree import PropertyPathValue, ConstraintData, PropertyPathType
from freecad.diff_wb.domain.tree.property_handlers import get_path_handler, ConstraintDataPathHandler

# Map PropertyType to handler class for serialization
_TYPE_TO_HANDLER: dict[PropertyType, type] = {}


@staticmethod
def _serialize_property_value(value: Any, type_: PropertyType) -> Any:
    """Serialize a property value to YAML-compatible format.

    Uses handler registry to serialize path-based types, ensuring consistency
    between extraction and serialization.

    Args:
        value: The property value (primitive, path map, or ConstraintData list)
        type_: The property type

    Returns:
        YAML-serializable value with type information
    """
    # Path-map types: PLACEMENT, VECTOR, ROTATION
    if type_ in (PropertyType.PLACEMENT, PropertyType.VECTOR, PropertyType.ROTATION):
        # value is a dict of path -> PropertyPathValue
        handler = _TYPE_TO_HANDLER.get(type_)
        if handler:
            return handler.serialize_paths(value)
        # Fallback: generic serialization if no handler registered
        result = {}
        for path, path_value in value.items():
            entry: dict[str, Any] = {"type_": path_value.type_.name}
            if path_value.value is not None:
                entry["value"] = path_value.value
            if path_value.expression is not None:
                entry["expression"] = path_value.expression
            result[path] = entry
        return result

    # Lists with type information
    elif type_ == PropertyType.LIST:
        # Serialize each item using handler registry (recursive)
        serialized_items = []
        for item in value:
            handler = get_path_handler(item)
            if handler is not None:
                # Handler-based serialization for ConstraintData, Placement, etc.
                item_data = handler.serialize_paths({"": PropertyPathValue.from_value(item)})
                serialized_items.append(item_data[""])
            else:
                # Fallback for primitives and unknown types
                ppv = PropertyPathValue.from_value(item)
                item_data: dict[str, Any] = {"type_": ppv.type_.name}
                if ppv.value is not None:
                    item_data["value"] = ppv.value
                if ppv.expression is not None:
                    item_data["expression"] = ppv.expression
                serialized_items.append(item_data)
        return serialized_items

    # Primitive types: serialize directly
    else:
        return value
```

Now update the deserialization code similarly. Let me find that section:

**Step 4.3: Update YAML deserializer to use handler registry (for lists, iterate and delegate)**
```python
@staticmethod
def _deserialize_property_value(data: Any, type_: PropertyType) -> Any:
    """Deserialize a property value from YAML format.

    Uses handler registry to deserialize path-based types, ensuring consistency
    between extraction and serialization.

    Args:
        data: The serialized value from YAML
        type_: The property type

    Returns:
        The deserialized value (path map or primitive)
    """
    # Path-map types: PLACEMENT, VECTOR, ROTATION
    if type_ in (PropertyType.PLACEMENT, PropertyType.VECTOR, PropertyType.ROTATION):
        if isinstance(data, dict):
            handler = _TYPE_TO_HANDLER.get(type_)
            if handler:
                return handler.deserialize_paths(data)
            # Fallback: generic deserialization
            return {
                path: _deserialize_path_value(item)
                for path, item in data.items()
            }
        return data

    # Lists - deserialize each item using handler registry
    elif type_ == PropertyType.LIST:
        if not isinstance(data, list):
            return data if data else []
        
        result = []
        for item_data in data:
            if not isinstance(item_data, dict):
                result.append(item_data)
                continue
            
            type_name = item_data.get("type_")
            if type_name is None:
                result.append(item_data.get("value"))
                continue
            
            # Look up handler by type name
            handler = _TYPE_NAME_TO_HANDLER.get(type_name)
            if handler is not None:
                # Handler-based deserialization
                item_paths = handler.deserialize_paths(item_data)
                # Handler returns dict with "" key for single-item extraction
                result.append(item_paths.get(""))
            else:
                # Fallback: generic PropertyPathValue deserialization
                result.append(_deserialize_path_value(item_data))
        
        return result

    # Primitive types: return as-is
    else:
        return data


# Map type name string to handler class for deserialization
_TYPE_NAME_TO_HANDLER: dict[str, type] = {
    "CONSTRAINT": ConstraintDataHandler,
    "PLACEMENT": PlacementPathHandler,
    "VECTOR": VectorPathHandler,
    "ROTATION": RotationPathHandler,
}

#### Step 4.3: Update YAML deserializer to use handler registry
```python
@staticmethod
def _deserialize_property_value(data: Any, type_: PropertyType) -> Any:
    """Deserialize a property value from YAML format.

    Uses handler registry to deserialize path-based types, ensuring consistency
    between extraction and serialization.

    Args:
        data: The serialized value from YAML
        type_: The property type

    Returns:
        The deserialized value (path map or primitive)
    """
    # Path-map types: PLACEMENT, VECTOR, ROTATION
    if type_ in (PropertyType.PLACEMENT, PropertyType.VECTOR, PropertyType.ROTATION):
        if isinstance(data, dict):
            handler = _TYPE_TO_HANDLER.get(type_)
            if handler:
                return handler.deserialize_paths(data)
            # Fallback: generic deserialization
            return {
                path: _deserialize_path_value(item)
                for path, item in data.items()
            }
        return data

    # Lists - deserialize each item using handler registry
    elif type_ == PropertyType.LIST:
        if not isinstance(data, list):
            return data if data else []

        result = []
        for item_data in data:
            if not isinstance(item_data, dict):
                result.append(item_data)
                continue

            type_name = item_data.get("type_")
            if type_name is None:
                result.append(item_data.get("value"))
                continue

            # Look up handler by type name
            handler = _TYPE_NAME_TO_HANDLER.get(type_name)
            if handler is not None:
                # Handler-based deserialization
                item_paths = handler.deserialize_paths(item_data)
                # For ConstraintData, item_paths is the visible_properties dict
                # We need to reconstruct the ConstraintData
                if type_name == "CONSTRAINT":
                    result.append(ConstraintData(visible_properties=item_paths))
                else:
                    result.append(item_paths.get(""))
            else:
                # Fallback: generic PropertyPathValue deserialization
                result.append(_deserialize_path_value(item_data))

        return result

    # Primitive types: return as-is
    else:
        return data


@staticmethod
def _deserialize_path_value(data: dict) -> PropertyPathValue:
    """Deserialize a single PropertyPathValue from YAML format."""
    type_name = data.get("type_", "NULL")
    try:
        type_ = PropertyPathType[type_name]
    except KeyError:
        type_ = PropertyPathType.NULL

    return PropertyPathValue(
        type_=type_,
        value=data.get("value"),
        expression=data.get("expression")  # Returns None if missing
    )
```

### Phase 5: Integration and Cleanup (Requires FreeCAD)

**Goal**: Wire everything together and verify end-to-end.

#### Step 5.1: Register handlers with snapshot_yaml
```python
# freecad/diff_wb/infrastructure/persistence/snapshot_yaml.py

from freecad.diff_wb.domain.tree.property_handlers import (
    PlacementPathHandler, VectorPathHandler, RotationPathHandler, ConstraintDataPathHandler
)

# Register handlers for serialization/deserialization
_TYPE_TO_HANDLER: dict[PropertyType, type] = {
    PropertyType.PLACEMENT: PlacementPathHandler,
    PropertyType.VECTOR: VectorPathHandler,
    PropertyType.ROTATION: RotationPathHandler,
}

# Map type name string to handler for list item deserialization
_TYPE_NAME_TO_HANDLER: dict[str, type] = {
    "CONSTRAINT": ConstraintDataPathHandler,
    "PLACEMENT": PlacementPathHandler,
    "VECTOR": VectorPathHandler,
    "ROTATION": RotationPathHandler,
}
```

#### Step 5.2: Update `_extract_property_value()` to use handler-based extraction
```python
# freecad/diff_wb/domain/snapshots/gui_extractor.py

from freecad.diff_wb.domain.tree import PropertyPathValue, ConstraintData
from freecad.diff_wb.domain.tree.property_handlers import extract_property_paths

def _extract_property_value(obj: object, prop_name: str) -> Property | None:
    """Extract a single property value from a FreeCAD object.

    Uses handler registry for path-based extraction. All expressions
    (including top-level) are unified into the path map with "" key.
    """
    try:
        value = getattr(obj, prop_name)
        expr_engine = getattr(obj, "ExpressionEngine", [])
        expr_map = _build_expression_map_for_property(prop_name, expr_engine)
        group = _get_property_group(obj, prop_name)

        # Special handling for constraint lists
        if prop_name == "Constraints" and value:
            constraint_data_list = [_extract_constraint_data(c) for c in value]
            return Property(
                type_=PropertyType.LIST,
                value=constraint_data_list,
                group=group
            )

        # Use handler registry for extraction
        paths = extract_property_paths(value, expr_map)

        # Determine property type from value
        type_ = PropertyType.PLACEMENT if "Base" in paths else Property._infer_type(value)

        return Property(
            type_=type_,
            value=paths,
            group=group
        )

    except Exception as e:
        Log.exception(f"Failed to extract property {prop_name}: {e}")
        return None
```

#### Step 5.3: Clean up obsolete code

**DELETE from `freecad/diff_wb/domain/tree/property.py`:**
- Remove `Vector` class (lines 89-146)
- Remove `Rotation` class (lines 149-186)
- Remove `Placement` class (lines 189-256)
- Remove `PropertyHandler` base class and `_PROPERTY_HANDLERS` registry (lines 45-86)
- Remove `Property.create()` method (lines 343-404)
- Remove `Property.from_freecad_property()` method (lines 406-431)
- Remove `Property._infer_type_from_value()` method (lines 433-449)
- Remove `Property.get_children()` and all `_get_*` helpers (lines 451-524)
- Remove `Property.expression` field (line 275) - expressions now unified into path map

**DELETE from `freecad/diff_wb/domain/snapshots/gui_extractor.py`:**
- Remove `_get_expression_for_property()` (lines 230-251) - replaced by `_build_expression_map_for_property()`

**DELETE from `freecad/diff_wb/domain/tree/__init__.py`:**
- Remove `Vector`, `Rotation`, `Placement` from exports

**UPDATE `freecad/diff_wb/infrastructure/persistence/snapshot_yaml.py`:**
- Remove old VECTOR/PLACEMENT handling in `_serialize_property_value()` and `_deserialize_property_value()`

#### Step 5.4: Run integration tests
```bash
./run_with_freecad.sh python -m pytest tests/integration/test_property_path_extraction.py -v
./run_with_freecad.sh python -m pytest tests/integration/test_snapshot_roundtrip.py -v
```

#### Step 5.5: Verify end-to-end
1. Create a Part with expressions at multiple levels
2. Take snapshot
3. Serialize to YAML, inspect for proper structure
4. Deserialize from YAML
5. Compare original and restored snapshots - must be equal

---

## End-to-End Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. EXTRACTION PHASE (gui_extractor.py)                              │
├─────────────────────────────────────────────────────────────────────┤
│ FreeCAD Object                                                       │
│     │                                                                │
│     ▼                                                                │
│ _extract_properties()                                                │
│     │                                                                │
│     ├─► For each property:                                           │
│     │     _extract_property_value(obj, prop_name)                    │
│     │         │                                                      │
│     │         ├─► Get value = getattr(obj, prop_name)                │
│     │         ├─► Build expression map via _build_expression_map()   │
│     │         │     (paths like ".Placement.Base.x" → "Base.x")      │
│     │         ├─► If Constraints:                                    │
│     │         │     [_extract_constraint_data(c) for c in value]     │
│     │         │     └─► Property(type=LIST, value=[ConstraintData...])│
│     │         └─► Else:                                              │
│     │             extract_property_paths(value, expr_map)            │
│     │                 │                                              │
│     │                 ├─► Handler registry finds appropriate handler │
│     │                 ├─► Handler.extract_paths(value, expr_map)     │
│     │                 └─► Return {path: PropertyPathValue(...)}      │
│     │                     NOTE: Top-level expr at path ""            │
│     │                                                                │
│     └─► Property(                                                    │
│           type_=PLACEMENT,                                           │
│           value={                                                    │
│             "": PropertyPathValue(expression="top_level_expr"),      │  # Unified!
│             "Base.x": PropertyPathValue(...),                        │
│             ...                                                      │
│           }                                                          │
│         )                                                            │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. TREE BUILDING (gui_extractor.py)                                  │
├─────────────────────────────────────────────────────────────────────┤
│ TreeNode(                                                            │
│   id=43,                                                             │
│   name="Pad",                                                        │
│   properties={                                                       │
│     "Length": Property(...),                                         │
│     "Placement": Property(value={path: PropertyPathValue...}),       │
│     "Constraints": Property(value=[ConstraintData...])               │
│   }                                                                  │
│ )                                                                    │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. SERIALIZATION (snapshot_yaml.py)                                  │
├─────────────────────────────────────────────────────────────────────┤
│ SnapshotYamlSerializer.to_yaml(snapshot, path)                       │
│     │                                                                │
│     ├─► _serialize_properties(node.properties)                       │
│     │     │                                                          │
│     │     └─► For each Property:                                     │
│     │           _serialize_property_value(prop.value, prop.type_)    │
│     │               │                                                │
│     │               ├─► If PLACEMENT/VECTOR/ROTATION:                │
│     │               │     Handler.serialize_paths(value)             │
│     │               │     → {"Base.x": {"value": 10.0, ...},        │
│     │               │         "Rotation": {"value": null,            │
│     │               │                    "expression": "..."},       │
│     │               │         "": {"type_":"NULL","expression":"..."}}│
│     │               ├─► If LIST:                                     │
│     │               │     For each item: get_path_handler(item)      │
│     │               │     → Call handler.serialize_paths(item)       │
│     │               └─► Else: return value directly                  │
│     └─► Write YAML file                                              │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. DESERIALIZATION (snapshot_yaml.py)                                │
├─────────────────────────────────────────────────────────────────────┤
│ SnapshotYamlSerializer.from_yaml_file(path)                          │
│     │                                                                │
│     ├─► Load YAML                                                    │
│     ├─► _from_data(data)                                             │
│     │     │                                                          │
│     │     └─► For each object:                                       │
│     │           _deserialize_properties(obj["properties"])           │
│     │               │                                                │
│     │               └─► For each property:                           │
│     │                     _deserialize_property_value(data, type_)   │
│     │                         │                                      │
│     │                         ├─► If PLACEMENT/VECTOR/ROTATION:      │
│     │                         │     Handler.deserialize_paths(data)  │
│     │                         │     → {path: PropertyPathValue(...)} │
│     │                         ├─► If LIST:                         │
│     │                         │     For each item: get_path_handler(item)│
│     │                         │     → Call handler.deserialize_paths(item)│
│     │                         └─► Else: return data directly         │
│     └─► Return Snapshot(nodes=[TreeNode(...)])                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Critical Integration Points

### 1. **Property Extraction** (`gui_extractor.py`)
- `_extract_property_value()` is the main entry point
- Uses handler registry via `extract_property_paths()` - no hardcoded type checks
- All expressions (including top-level) unified into path map with `""` key

### 2. **Handler Registry** (`property_handlers.py`)
- `PropertyPathHandler` protocol defines `handles_value()`, `extract_paths()`, `serialize_paths()`, `deserialize_paths()`
- `PlacementPathHandler`, `VectorPathHandler`, `RotationPathHandler`, `SimplePathHandler` (fallback)
- Handlers are registered via `@register_path_handler` decorator
- `_TYPE_TO_HANDLER` map in `snapshot_yaml.py` links `PropertyType` to handler class

### 3. **Serialization** (`snapshot_yaml.py`)
- Uses handler's `serialize_paths()` method for path-based types
- Omit null expressions for space efficiency
- Use `ConstraintDataPathHandler` for ConstraintData serialization

### 4. **Deserialization** (`snapshot_yaml.py`)
- Uses handler's `deserialize_paths()` method for path-based types
- Use `.get("expression")` to handle missing fields (treat as None)
- Use `ConstraintDataPathHandler` for ConstraintData reconstruction

## Test Strategy

### Unit Tests (No FreeCAD)
- **`tests/unit/domain/tree/test_property_paths.py`**: PropertyPathValue equality, pattern detection functions
- **`tests/unit/domain/tree/test_constraint_data.py`**: ConstraintData equality
- **`tests/unit/infrastructure/persistence/test_snapshot_yaml_paths.py`**: Round-trip serialization for new structures

### Integration Tests (With FreeCAD)
- **`tests/integration/test_property_path_extraction.py`**: Extract placement/constraint properties with expressions
- **`tests/integration/test_snapshot_roundtrip.py`**: Full snapshot extract → serialize → deserialize → compare

### Manual Test Cases

#### File: `docs/manual-testing/property-path-extraction.md`

**Test Case 1: Placement with Expression-Driven Sub-Properties**
```
Steps:
1. Create new Part::Box
2. Set Placement.Base.x = 5
3. Set expression: Placement.Base.x = "10 mm"
4. Take snapshot
5. Inspect YAML output

Expected:
- YAML contains: "Base.x": {"value": 10.0, "expression": "10 mm"}
- Other sub-properties omit expression field if null (e.g., "Base.y": {"value": 0.0})
- After round-trip, snapshot compares equal
```

**Test Case 1b: Intermediate Level Expressions (Rotation, Rotation.Axis)**
```
Steps:
1. Create new Part::Box
2. Set expressions on ALL levels:
   - Placement.Rotation = "some_rotation_expr"
   - Placement.Rotation.Axis = "some_axis_expr"
   - Placement.Rotation.Axis.x = "0.577"
   - Placement.Rotation.Axis.y = "0.577"
   - Placement.Rotation.Axis.z = "0.577"
3. Take snapshot
4. Inspect YAML output

Expected:
- YAML contains ALL levels including intermediate objects:
  "Rotation": {"value": null, "expression": "some_rotation_expr"}
  "Rotation.Axis": {"value": null, "expression": "some_axis_expr"}
  "Rotation.Axis.x": {"value": 0.577, "expression": "0.577"}
  "Rotation.Axis.y": {"value": 0.577, "expression": "0.577"}
  "Rotation.Axis.z": {"value": 0.577, "expression": "0.577"}
- Intermediate objects have value=null but preserve their expressions
- After round-trip, snapshot compares equal
```

**Test Case 1c: Leaf-Only Expressions (No Intermediate)**
```
Steps:
1. Create new Part::Box
2. Set expressions only on leaf values:
   - Placement.Rotation.Axis.x = "0.577"
   - Placement.Rotation.Axis.y = "0.577"
   - Placement.Rotation.Axis.z = "0.577"
3. Take snapshot
4. Inspect YAML output

Expected:
- YAML contains ONLY leaf paths (no intermediate objects):
  "Rotation.Axis.x": {"value": 0.577, "expression": "0.577"}
  "Rotation.Axis.y": {"value": 0.577, "expression": "0.577"}
  "Rotation.Axis.z": {"value": 0.577, "expression": "0.577"}
- No "Rotation" or "Rotation.Axis" entries (they have no expressions)
- After round-trip, snapshot compares equal
```

**Test Case 2: Sketch Constraints Change Detection**
```
Steps:
1. Open BasicFile.FCStd
2. Take snapshot A
3. Modify a constraint value in Sketch (e.g., change Distance from 10 to 15)
4. Take snapshot B
5. Compare snapshots

Expected:
- Diff shows: Constraints.ConstrN.Value changed from 10.0 to 15.0
```

**Test Case 3: Sketch Constraints List with Multiple Items**
```
Steps:
1. Create sketch with multiple constraints
2. Take snapshot A
3. Insert a new constraint at position 0 (shifts all existing)
4. Take snapshot B
5. Compare snapshots

Expected:
- Diff shows all constraints appear modified (because indices shifted)
- This is expected behavior for positional lists
```

## Findings & Notes

### API Exploration Results
1. **Expression path format**: 
   - Top-level: `('Length', '5 mm')` (no leading dot)
   - Sub-properties: `('.Placement.Base.x', '100 mm')` (with leading dot)
2. **ALL levels can have expressions** (critical finding!):
   - Intermediate objects: `.Placement.Rotation`, `.Placement.Rotation.Axis`
   - Leaf values: `.Placement.Rotation.Axis.x`, `.y`, `.z`
   - Each level is independent and can have its own expression
3. **No Python access to `getPathValue()`**: Must use direct attribute access
4. **Constraints have many properties**: Only Type, Value, First, Second, Third are typically visible
5. **Placement has no "Value"**: Only Base and Rotation attributes
6. **Intermediate objects have no scalar value**: `Rotation` and `Axis` objects have `value=None` but can have expressions

### Edge Cases Discovered
1. **Empty constraints list**: Handle gracefully (empty list, not None)
2. **Missing sub-properties**: Some placements might not have all sub-properties defined
3. **Expression evaluation timing**: ExpressionEngine shows the expression string; actual value is already evaluated in the property
4. **Null expression handling**: Omit from YAML to save space; deserialize with `.get()` returning None

### Lessons Learned
1. **Handler registry > hardcoded if/elif**: Each type handler implements all operations (extract, serialize, deserialize); adding new types only requires registering a new handler
2. **Unified expressions**: Top-level and sub-property expressions are the same concept; storing at path `""` eliminates special cases
3. **Float comparison**: Use `math.isclose()` for approximate equality (handles large/small values better than `abs(a-b) < tol`)
4. **Pattern detection > type names**: More robust across FreeCAD versions
5. **Flat paths simplify comparison**: No recursion needed during diff computation
6. **Space-efficient YAML**: Omit null fields, reconstruct on deserialize
7. **Explicit types everywhere**: Every `PropertyPathValue` includes `type_` field for deterministic deserialization
8. **Item type suffices**: Each list item has its own `type_`; no container-level `list_type` needed
9. **visible_properties naming**: Clear distinction between user-visible vs internal constraint properties
10. **Capture ALL levels**: Both intermediate objects AND leaf values can have expressions
11. **Handler registry is recursive**: Lists iterate and delegate to handlers for each item
