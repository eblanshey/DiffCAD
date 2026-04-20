# Task: Path-Based Property Data Classes

## Goal

Design and implement path-based data classes for FreeCAD properties that:
1. Produce IDENTICAL snapshots after YAML serialize/deserialize round-trips
2. Retain ALL expressions at ALL levels (top-level properties AND sub-properties like `Placement.Base.x`)
3. Handle all FreeCAD types generically via type-to-class mappings
4. Use O(1) dict lookups instead of O(n) handler registry iteration
5. Each class knows its own serialization/deserialization logic (SRP)

## Context

### Current Problems

1. **Non-deterministic serialization**: Custom types (`Vector`, `Placement`, `Constraint`) don't preserve exact representation through YAML round-trips
2. **Lost sub-property expressions**: Only top-level property expressions are captured; sub-properties like `Placement.Base.x` lose their expressions
3. **List serialization breaks comparison**: Constraints are converted to strings, losing structure
4. **O(n) handler lookup**: Current `handles_value()` pattern matching iterates through all handlers

### Root Cause Analysis

- Custom types implement `__eq__` but YAML serialization doesn't round-trip correctly
- Expression extraction only handles top-level properties, not sub-properties
- Constraint lists are serialized as strings instead of structured data
- Handler registry uses `handles_value()` pattern matching instead of direct type lookup

### Investigation Findings

#### FreeCAD Type Hierarchy

From runtime inspection:
- `Base.Placement` - `FreeCAD.Placement` (has Base + Rotation)
- `Base.Vector` - `FreeCAD.Vector` (has x, y, z)
- `Base.Rotation` - `FreeCAD.Rotation` (has Angle + Axis)
- `Sketcher.Constraint` - constraint object (has Type, Value, First, Second, etc.)

#### Expression Path Format

- ExpressionEngine stores paths with **leading dot**: `.Placement.Base.x`
- Sub-property expressions can exist at ANY level: `Rotation`, `Rotation.Axis`, `Rotation.Axis.x`

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| **Type-to-class mapping** | O(1) lookup instead of O(n) handler iteration | `handles_value()` pattern matching (slower, less explicit) |
| **Module+type name as key** | Unique identification of FreeCAD types | isinstance checks (requires FreeCAD imports) |
| **InternalType enum** | Type safety over strings | Raw string constants (error-prone) |
| **All classes use paths dict** | Consistency across all types | Different structures per type (inconsistent) |
| **Class knows its own serialization** | SRP - each class handles its own data | Centralized if/elif dispatch (violates SRP) |
| **Two separate maps for extraction** | FREECAD_TYPE_MAP for FreeCAD objects, PYTHON_TYPE_MAP for primitives | Single mixed map (less clear) |
| **UnknownData for unrecognized types** | Graceful degradation for new FreeCAD types | Exception or silent data loss |
| **Empty string "" for root path** | Consistent key for single-value items | Special handling per type |

## Architecture Impact

### Modules Affected

#### `freecad/diff_wb/domain/tree/`

**New file: `data_path.py`**

Contains all path-based data classes implementing `DataPath` protocol:

```python
class InternalType(Enum):
    """Type identifiers for DataPath classes (used in serialization)."""
    Primitive = "Primitive"
    List = "List"
    Placement = "Placement"
    Vector = "Vector"
    Rotation = "Rotation"
    Constraint = "Constraint"
    Unknown = "Unknown"


class DataPath(Protocol):
    """Protocol for all path-based data classes."""
    
    INTERNAL_TYPE: InternalType
    
    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> "DataPath": ...
    @staticmethod
    def from_serialized_value(data: Any) -> "DataPath": ...
    def serialize(self) -> Any: ...


# Type mapping dictionaries
FREECAD_TYPE_MAP: dict[str, type[DataPath]] = {
    "Base.Placement": PlacementData,
    "Base.Vector": VectorData,
    "Base.Rotation": RotationData,
    "Sketcher.Constraint": ConstraintData,
}

PYTHON_TYPE_MAP: dict[type, type[DataPath]] = {
    bool: PrimitiveData,
    int: PrimitiveData,
    float: PrimitiveData,
    str: PrimitiveData,
    list: ListData,
    tuple: ListData,
}

INTERNAL_TYPE_MAP: dict[str, type[DataPath]] = {
    "Primitive": PrimitiveData,
    "List": ListData,
    "Placement": PlacementData,
    "Vector": VectorData,
    "Rotation": RotationData,
    "Constraint": ConstraintData,
    "Unknown": UnknownData,
}
```

**DataPath classes:**

1. **PrimitiveData** - for bool, int, float, str, None
2. **UnknownData** - for unrecognized FreeCAD types
3. **PlacementData** - for FreeCAD Placement objects
4. **VectorData** - for FreeCAD Vector objects
5. **RotationData** - for FreeCAD Rotation objects
6. **ConstraintData** - for Sketcher constraint objects
7. **ListData** - for lists/tuples of items

**PropertyPathValue** - used internally by all DataPath classes:

```python
class PropertyPathType(Enum):
    """Primitive types for path values."""
    FLOAT = auto()
    INT = auto()
    STRING = auto()
    BOOL = auto()
    NULL = auto()
    CUSTOM_UNKNOWN = auto()


@dataclass(frozen=True)
class PropertyPathValue:
    """A property value at a specific path with its expression and type."""
    type_: PropertyPathType
    value: Any
    expression: str | None = None
```

**Property class - simplified:**

```python
@dataclass
class Property:
    """A FreeCAD property with path-based data."""
    value: DataPath  # Always a DataPath subclass
    group: str = "Base"
    
    @classmethod
    def from_freecad(
        cls,
        prop_name: str,
        fc_value: Any,
        expr_map: dict[str, str],
        group: str,
    ) -> "Property":
        """Extract Property from FreeCAD value using type maps."""
        # Check Python type map first (primitives and lists)
        py_handler = PYTHON_TYPE_MAP.get(type(fc_value))
        if py_handler:
            return cls(value=py_handler.from_freecad_value(fc_value, expr_map), group=group)
        
        # Check FreeCAD type map
        type_key = f"{type(fc_value).__module__}.{type(fc_value).__name__}"
        handler = FREECAD_TYPE_MAP.get(type_key)
        
        if handler:
            return cls(value=handler.from_freecad_value(fc_value, expr_map), group=group)
        
        # Unknown FreeCAD type
        return cls(value=UnknownData.from_freecad_value(fc_value, expr_map), group=group)
```

#### `freecad/diff_wb/infrastructure/persistence/`

**Modified: `snapshot_yaml.py`**

Simplified serialization/deserialization using DataPath.serialize() and INTERNAL_TYPE_MAP:

```python
# Serialization
def _serialize_property(property: Property) -> dict[str, Any]:
    return property.value.serialize()

# Deserialization  
def _deserialize_property(data: dict[str, Any]) -> Property:
    type_name = data.get("type_")
    handler = INTERNAL_TYPE_MAP.get(type_name) or UnknownData
    return Property(value=handler.from_serialized_value(data))
```

## DataPath Class Specifications

### 1. PrimitiveData

```python
@dataclass(frozen=True)
class PrimitiveData(DataPath):
    """For primitives and unknown Python types."""
    INTERNAL_TYPE = InternalType.Primitive
    paths: dict[str, PropertyPathValue]  # Key is "" for single value
    
    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> "PrimitiveData":
        if value is None:
            type_ = PropertyPathType.NULL
        elif isinstance(value, bool):
            type_ = PropertyPathType.BOOL
        elif isinstance(value, int):
            type_ = PropertyPathType.INT
        elif isinstance(value, float):
            type_ = PropertyPathType.FLOAT
        elif isinstance(value, str):
            type_ = PropertyPathType.STRING
        elif isinstance(value, (list, tuple)):
            # Delegates to ListData for list/tuple
            return ListData.from_freecad_value(value, expr_map)
        else:
            raise ValueError(f"Unknown Python type: {type(value)}")
        
        return PrimitiveData(paths={
            "": PropertyPathValue(type_=type_, value=value, expression=expr_map.get(""))
        })
    
    @staticmethod
    def from_serialized_value(data: dict[str, Any]) -> "PrimitiveData":
        item = data.get("", data.get("value", {}))
        if isinstance(item, dict):
            type_name = item.get("type_", "NULL")
            type_ = PropertyPathType[type_name] if type_name in PropertyPathType._member_names_ else PropertyPathType.NULL
            return PrimitiveData(paths={
                "": PropertyPathValue(type_=type_, value=item.get("value"), expression=item.get("expression"))
            })
        return PrimitiveData(paths={"": PropertyPathValue(type_=PropertyPathType.NULL, value=item)})
    
    def serialize(self) -> dict[str, Any]:
        pv = self.paths.get("") or PropertyPathValue(type_=PropertyPathType.NULL, value=None)
        result = {"type_": self.INTERNAL_TYPE.value}
        if pv.value is not None:
            result["value"] = pv.value
        if pv.expression is not None:
            result["expression"] = pv.expression
        return result
```

### 2. UnknownData

```python
@dataclass(frozen=True)
class UnknownData(DataPath):
    """For unrecognized FreeCAD types."""
    INTERNAL_TYPE = InternalType.Unknown
    paths: dict[str, PropertyPathValue]  # Key is "" stores freecad type as string
    
    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> "UnknownData":
        type_key = f"{type(value).__module__}.{type(value).__name__}"
        return UnknownData(
            paths={
                "": PropertyPathValue(
                    type_=PropertyPathType.STRING,
                    value=type_key,
                    expression=expr_map.get("")
                )
            }
        )
    
    @staticmethod
    def from_serialized_value(data: dict[str, Any]) -> "UnknownData":
        pv = data.get("value", data.get(""))
        if isinstance(pv, dict):
            pv = pv.get("value")
        return UnknownData(
            paths={
                "": PropertyPathValue(
                    type_=PropertyPathType.STRING,
                    value=pv,
                    expression=data.get("expression"),
                )
            }
        )
    
    def serialize(self) -> dict[str, Any]:
        pv = self.paths.get("")
        return {
            "type_": self.INTERNAL_TYPE.value,
            "value": pv.value if pv else None,
            "expression": pv.expression if pv else None,
        }
```

### 3. PlacementData

```python
@dataclass(frozen=True)
class PlacementData(DataPath):
    """For FreeCAD Placement objects."""
    INTERNAL_TYPE = InternalType.Placement
    paths: dict[str, PropertyPathValue]
    
    @staticmethod
    def from_freecad_value(fc_placement, expr_map: dict[str, str]) -> "PlacementData":
        paths = {}
        
        base = fc_placement.Base
        for attr in ('x', 'y', 'z'):
            path_key = f"Base.{attr}"
            paths[path_key] = PropertyPathValue(
                type_=PropertyPathType.FLOAT,
                value=float(getattr(base, attr)),
                expression=expr_map.get(path_key)
            )
        
        rotation = fc_placement.Rotation
        if 'Rotation' in expr_map:
            paths['Rotation'] = PropertyPathValue(type_=PropertyPathType.NULL, value=None, expression=expr_map['Rotation'])
        
        paths['Rotation.Angle'] = PropertyPathValue(
            type_=PropertyPathType.FLOAT,
            value=float(rotation.Angle),
            expression=expr_map.get('Rotation.Angle')
        )
        
        axis = rotation.Axis
        if 'Rotation.Axis' in expr_map:
            paths['Rotation.Axis'] = PropertyPathValue(type_=PropertyPathType.NULL, value=None, expression=expr_map['Rotation.Axis'])
        
        for attr in ('x', 'y', 'z'):
            path_key = f"Rotation.Axis.{attr}"
            paths[path_key] = PropertyPathValue(
                type_=PropertyPathType.FLOAT,
                value=float(getattr(axis, attr)),
                expression=expr_map.get(path_key)
            )
        
        return PlacementData(paths=paths)
    
    @staticmethod
    def from_serialized_value(data: dict[str, Any]) -> "PlacementData":
        paths = {}
        for path, item in data.items():
            if path == "type_":
                continue
            type_ = PropertyPathType[item.get("type_", "NULL")]
            paths[path] = PropertyPathValue(
                type_=type_,
                value=item.get("value"),
                expression=item.get("expression"),
            )
        return PlacementData(paths=paths)
    
    def serialize(self) -> dict[str, Any]:
        result = {"type_": self.INTERNAL_TYPE.value}
        for path, pv in self.paths.items():
            entry = {"type_": pv.type_.name}
            if pv.value is not None:
                entry["value"] = pv.value
            if pv.expression is not None:
                entry["expression"] = pv.expression
            result[path] = entry
        return result
```

### 4. VectorData

```python
@dataclass(frozen=True)
class VectorData(DataPath):
    """For FreeCAD Vector objects."""
    INTERNAL_TYPE = InternalType.Vector
    paths: dict[str, PropertyPathValue]
    
    @staticmethod
    def from_freecad_value(fc_vector, expr_map: dict[str, str]) -> "VectorData":
        paths = {}
        for attr in ('x', 'y', 'z'):
            paths[attr] = PropertyPathValue(
                type_=PropertyPathType.FLOAT,
                value=float(getattr(fc_vector, attr)),
                expression=expr_map.get(attr)
            )
        return VectorData(paths=paths)
    
    @staticmethod
    def from_serialized_value(data: dict[str, Any]) -> "VectorData":
        paths = {}
        for attr in ('x', 'y', 'z'):
            if attr in data:
                item = data[attr]
                type_ = PropertyPathType[item.get("type_", "FLOAT")]
                paths[attr] = PropertyPathValue(type_=type_, value=item.get("value"), expression=item.get("expression"))
        return VectorData(paths=paths)
    
    def serialize(self) -> dict[str, Any]:
        result = {"type_": self.INTERNAL_TYPE.value}
        for path, pv in self.paths.items():
            entry = {"type_": pv.type_.name}
            if pv.value is not None:
                entry["value"] = pv.value
            if pv.expression is not None:
                entry["expression"] = pv.expression
            result[path] = entry
        return result
```

### 5. RotationData

```python
@dataclass(frozen=True)
class RotationData(DataPath):
    """For FreeCAD Rotation objects."""
    INTERNAL_TYPE = InternalType.Rotation
    paths: dict[str, PropertyPathValue]
    
    @staticmethod
    def from_freecad_value(fc_rotation, expr_map: dict[str, str]) -> "RotationData":
        paths = {}
        
        paths['Angle'] = PropertyPathValue(
            type_=PropertyPathType.FLOAT,
            value=float(fc_rotation.Angle),
            expression=expr_map.get('Angle')
        )
        
        if 'Axis' in expr_map:
            paths['Axis'] = PropertyPathValue(type_=PropertyPathType.NULL, value=None, expression=expr_map['Axis'])
        
        axis = fc_rotation.Axis
        for attr in ('x', 'y', 'z'):
            path_key = f"Axis.{attr}"
            paths[path_key] = PropertyPathValue(
                type_=PropertyPathType.FLOAT,
                value=float(getattr(axis, attr)),
                expression=expr_map.get(path_key)
            )
        
        return RotationData(paths=paths)
    
    @staticmethod
    def from_serialized_value(data: dict[str, Any]) -> "RotationData":
        paths = {}
        for path, item in data.items():
            if path == "type_":
                continue
            type_ = PropertyPathType[item.get("type_", "NULL")]
            paths[path] = PropertyPathValue(type_=type_, value=item.get("value"), expression=item.get("expression"))
        return RotationData(paths=paths)
    
    def serialize(self) -> dict[str, Any]:
        result = {"type_": self.INTERNAL_TYPE.value}
        for path, pv in self.paths.items():
            entry = {"type_": pv.type_.name}
            if pv.value is not None:
                entry["value"] = pv.value
            if pv.expression is not None:
                entry["expression"] = pv.expression
            result[path] = entry
        return result
```

### 6. ConstraintData

```python
@dataclass(frozen=True)
class ConstraintData(DataPath):
    """For individual Sketcher constraints."""
    INTERNAL_TYPE = InternalType.Constraint
    paths: dict[str, PropertyPathValue]  # e.g., {"Type": ..., "Value": ..., "First": ...}
    
    @staticmethod
    def from_freecad_value(fc_constraint, expr_map: dict[str, str]) -> "ConstraintData":
        paths = {}
        
        if hasattr(fc_constraint, 'Type'):
            paths['Type'] = PropertyPathValue.from_value(str(fc_constraint.Type))
        if hasattr(fc_constraint, 'Value'):
            paths['Value'] = PropertyPathValue.from_value(float(fc_constraint.Value))
        for attr in ('First', 'Second', 'Third'):
            if hasattr(fc_constraint, attr):
                val = getattr(fc_constraint, attr)
                if val is not None:
                    paths[attr] = PropertyPathValue.from_value(int(val))
        if hasattr(fc_constraint, 'Driving'):
            paths['Driving'] = PropertyPathValue.from_value(bool(fc_constraint.Driving))
        
        return ConstraintData(paths=paths)
    
    @staticmethod
    def from_serialized_value(data: dict[str, Any]) -> "ConstraintData":
        paths = {}
        for path, item in data.items():
            if path == "type_":
                continue
            type_ = PropertyPathType[item.get("type_", "NULL")]
            paths[path] = PropertyPathValue(type_=type_, value=item.get("value"), expression=item.get("expression"))
        return ConstraintData(paths=paths)
    
    def serialize(self) -> dict[str, Any]:
        result = {"type_": self.INTERNAL_TYPE.value}
        for path, pv in self.paths.items():
            entry = {"type_": pv.type_.name}
            if pv.value is not None:
                entry["value"] = pv.value
            if pv.expression is not None:
                entry["expression"] = pv.expression
            result[path] = entry
        return result
```

### 7. ListData

```python
@dataclass(frozen=True)
class ListData(DataPath):
    """For lists/tuples of items."""
    INTERNAL_TYPE = InternalType.List
    items: list[DataPath]  # Each item is any DataPath subclass
    
    @staticmethod
    def from_freecad_value(fc_list: list | tuple, expr_map: dict[str, str]) -> "ListData":
        items = []
        for i, item in enumerate(fc_list):
            # Check FreeCAD type map first
            type_key = f"{type(item).__module__}.{type(item).__name__}"
            handler = FREECAD_TYPE_MAP.get(type_key)
            if handler:
                items.append(handler.from_freecad_value(item, {}))
                continue
            
            # Check Python type map
            py_handler = PYTHON_TYPE_MAP.get(type(item))
            if py_handler:
                items.append(py_handler.from_freecad_value(item, {}))
                continue
            
            # Unknown FreeCAD type
            items.append(UnknownData.from_freecad_value(item, {}))
        
        return ListData(items=items)
    
    @staticmethod
    def from_serialized_value(data: list[dict[str, Any]]) -> "ListData":
        items = []
        for item in data:
            type_name = item.get("type_", "Primitive")
            handler = INTERNAL_TYPE_MAP.get(type_name)
            if handler:
                items.append(handler.from_serialized_value(item))
            else:
                items.append(UnknownData.from_serialized_value(item))
        return ListData(items=items)
    
    def serialize(self) -> list[dict[str, Any]]:
        return [item.serialize() for item in self.items]
```

## Obsolete Code to Remove

### `freecad/diff_wb/domain/tree/property.py`

| Lines | Item | Reason |
|-------|------|--------|
| 45-51 | `_PROPERTY_HANDLERS` registry + `register_handler` decorator | Replaced by type-to-class mapping |
| 54-86 | `PropertyHandler` base class | Replaced by `DataPath` protocol |
| 89-146 | `Vector` class + handler | Replaced by `VectorData` |
| 149-186 | `Rotation` class | Replaced by `RotationData` |
| 189-256 | `Placement` class + handler | Replaced by `PlacementData` |
| 259-280 | `Property.create()` factory | No longer needed; `Property.from_freecad()` handles all |
| 343-404 | `Property.from_freecad_property()` | Replaced by `Property.from_freecad()` |
| 406-431 | `Property._infer_type_from_value()` | Path extraction uses `DataPath` classes instead |
| 451-524 | `Property.get_children()` and all `_get_*` helpers | Path map is already flattened; no recursion needed |

### `freecad/diff_wb/infrastructure/persistence/snapshot_yaml.py`

| Lines | Item | Reason |
|-------|------|--------|
| 170-185 | `_serialize_property_value` VECTOR/PLACEMENT handling | Replaced by `DataPath.serialize()` |
| 247-265 | `_deserialize_property_value` VECTOR/PLACEMENT handling | Replaced by `DataPath.from_serialized_value()` |

### `freecad/diff_wb/domain/snapshots/gui_extractor.py`

| Lines | Item | Reason |
|-------|------|--------|
| 230-251 | `_get_expression_for_property()` | Replaced by expression map building in `from_freecad_value()` |
| 274-299 | `_extract_property_value()` | Major refactor to use `Property.from_freecad()` |

## FreeCAD Dependency

- [ ] No FreeCAD required for domain/data classes (pure code)
- [x] FreeCAD required for integration testing with actual FreeCAD objects

## Implementation Plan

### Phase 1: Core Data Structures (No FreeCAD)

**Goal**: Define all DataPath classes with proper equality, serialization, and deserialization.

#### Step 1.1: Write tests for `InternalType` enum and `PropertyPathType` enum

```python
# tests/unit/domain/tree/test_data_path_types.py

def test_internal_type_enum_values():
    """Test: InternalType has all required values."""
    assert InternalType.Primitive.value == "Primitive"
    assert InternalType.List.value == "List"
    assert InternalType.Placement.value == "Placement"
    assert InternalType.Vector.value == "Vector"
    assert InternalType.Rotation.value == "Rotation"
    assert InternalType.Constraint.value == "Constraint"
    assert InternalType.Unknown.value == "Unknown"


def test_property_path_type_enum_values():
    """Test: PropertyPathType has all required primitive types."""
    assert PropertyPathType.FLOAT in PropertyPathType
    assert PropertyPathType.INT in PropertyPathType
    assert PropertyPathType.STRING in PropertyPathType
    assert PropertyPathType.BOOL in PropertyPathType
    assert PropertyPathType.NULL in PropertyPathType
    assert PropertyPathType.CUSTOM_UNKNOWN in PropertyPathType
```

#### Step 1.2: Write tests for `PropertyPathValue` dataclass

```python
# tests/unit/domain/tree/test_property_path_value.py

def test_property_path_value_from_value_auto_detects_types():
    """Test: from_value() correctly auto-detects types."""
    pv = PropertyPathValue.from_value(10.5)
    assert pv.type_ == PropertyPathType.FLOAT
    assert pv.value == 10.5
    
    pv = PropertyPathValue.from_value(42)
    assert pv.type_ == PropertyPathType.INT
    
    pv = PropertyPathValue.from_value("hello")
    assert pv.type_ == PropertyPathType.STRING
    
    pv = PropertyPathValue.from_value(True)
    assert pv.type_ == PropertyPathType.BOOL
    
    pv = PropertyPathValue.from_value(None)
    assert pv.type_ == PropertyPathType.NULL


def test_property_path_value_equality():
    """Test: PropertyPathValue equality requires matching types."""
    pv1 = PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0, expression=None)
    pv2 = PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0, expression=None)
    assert pv1 == pv2
    
    pv3 = PropertyPathValue(type_=PropertyPathType.INT, value=10, expression=None)
    assert pv1 != pv3  # Different type
    
    pv4 = PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0, expression="5 + 5")
    assert pv1 != pv4  # Different expression


def test_property_path_value_float_tolerance():
    """Test: PropertyPathValue uses float tolerance for numeric values."""
    pv1 = PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0000000001, expression=None)
    pv2 = PropertyPathValue(type_=PropertyPathType.FLOAT, value=10.0, expression=None)
    assert pv1 == pv2  # Within tolerance
```

#### Step 1.3: Write tests for `PrimitiveData` round-trip

First, create a conftest.py with test fixtures:

```python
# tests/integration/data_paths/conftest.py
"""Test fixtures and helpers for DataPath integration tests."""

import pytest
from unittest.mock import patch

from freecad.diff_wb.domain.tree.data_path import (
    FREECAD_TYPE_MAP,
    PYTHON_TYPE_MAP,
    ConstraintData,
    InternalType,
)


class MockVector:
    """Mock FreeCAD Vector for testing."""
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z


class MockRotation:
    """Mock FreeCAD Rotation for testing."""
    def __init__(self, Angle: float, Axis: MockVector):
        self.Angle = Angle
        self.Axis = Axis


class MockPlacement:
    """Mock FreeCAD Placement for testing."""
    def __init__(self, Base: MockVector, Rotation: MockRotation):
        self.Base = Base
        self.Rotation = Rotation


class MockConstraint:
    """Mock Sketcher Constraint for testing."""
    def __init__(
        self,
        Type: str,
        Value: float | None = None,
        First: int | None = None,
        Second: int | None = None,
        Third: int | None = None,
        Driving: bool | None = None,
    ):
        self.Type = Type
        self.Value = Value
        self.First = First
        self.Second = Second
        self.Third = Third
        self.Driving = Driving


@pytest.fixture
def freecad_type_map_with_mock_constraint():
    """Fixture that patches FREECAD_TYPE_MAP to include MockConstraint -> ConstraintData mapping."""
    mock_map = FREECAD_TYPE_MAP.copy()
    # Register MockConstraint to map to ConstraintData
    mock_map["tests.integration.data_paths.conftest.MockConstraint"] = ConstraintData
    
    with patch("freecad.diff_wb.domain.tree.data_path.FREECAD_TYPE_MAP", mock_map):
        yield mock_map
```

Then write tests:

```python
# tests/integration/data_paths/test_primitive_data_roundtrip.py

def test_primitive_data_bool_roundtrip():
    """Test: bool survives serialize->deserialize round-trip."""
    original = PrimitiveData.from_freecad_value(True, {})
    serialized = original.serialize()
    restored = PrimitiveData.from_serialized_value(serialized)
    assert original == restored


def test_primitive_data_int_roundtrip():
    """Test: int survives serialize->deserialize round-trip."""
    original = PrimitiveData.from_freecad_value(42, {})
    serialized = original.serialize()
    restored = PrimitiveData.from_serialized_value(serialized)
    assert original == restored


def test_primitive_data_float_roundtrip():
    """Test: float survives serialize->deserialize round-trip."""
    original = PrimitiveData.from_freecad_value(3.14, {})
    serialized = original.serialize()
    restored = PrimitiveData.from_serialized_value(serialized)
    assert original == restored


def test_primitive_data_string_roundtrip():
    """Test: string survives serialize->deserialize round-trip."""
    original = PrimitiveData.from_freecad_value("hello", {})
    serialized = original.serialize()
    restored = PrimitiveData.from_serialized_value(serialized)
    assert original == restored


def test_primitive_data_null_roundtrip():
    """Test: None survives serialize->deserialize round-trip."""
    original = PrimitiveData.from_freecad_value(None, {})
    serialized = original.serialize()
    restored = PrimitiveData.from_serialized_value(serialized)
    assert original == restored


def test_primitive_data_with_expression():
    """Test: expression is preserved through round-trip."""
    original = PrimitiveData.from_freecad_value(10.0, {"": "Part.Length * 2"})
    assert original.paths[""].expression == "Part.Length * 2"
    serialized = original.serialize()
    restored = PrimitiveData.from_serialized_value(serialized)
    assert original == restored
```

#### Step 1.4: Write tests for `UnknownData` round-trip

```python
# tests/integration/data_paths/test_unknown_data_roundtrip.py

def test_unknown_data_roundtrip():
    """Test: UnknownData survives serialize->deserialize round-trip."""
    class FakeUnknownType:
        pass
    
    original = UnknownData.from_freecad_value(FakeUnknownType(), {})
    serialized = original.serialize()
    restored = UnknownData.from_serialized_value(serialized)
    assert original == restored
    assert original.paths[""].value == "tests.integration.data_paths.test_unknown_data_roundtrip.FakeUnknownType"


def test_unknown_data_type_stored_as_string():
    """Test: FreeCAD type is stored as string in path value."""
    original = UnknownData(
        paths={
            "": PropertyPathValue(type_=PropertyPathType.STRING, value="Sketcher.SomeUnknown")
        }
    )
    assert original.paths[""].type_ == PropertyPathType.STRING
```

#### Step 1.5: Write tests for `PlacementData` round-trip

```python
# tests/integration/data_paths/test_placement_data_roundtrip.py

class MockVector:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class MockRotation:
    def __init__(self, Angle, Axis):
        self.Angle = Angle
        self.Axis = Axis

class MockPlacement:
    def __init__(self, Base, Rotation):
        self.Base = Base
        self.Rotation = Rotation


def test_placement_data_basic_roundtrip():
    """Test: PlacementData survives serialize->deserialize round-trip."""
    mock_placement = MockPlacement(
        Base=MockVector(x=1.0, y=2.0, z=3.0),
        Rotation=MockRotation(Angle=45.0, Axis=MockVector(x=0, y=0, z=1))
    )
    
    original = PlacementData.from_freecad_value(mock_placement, {})
    serialized = original.serialize()
    restored = PlacementData.from_serialized_value(serialized)
    assert original == restored


def test_placement_data_with_expressions():
    """Test: expressions at all levels preserved through round-trip."""
    mock_placement = MockPlacement(
        Base=MockVector(x=1.0, y=2.0, z=3.0),
        Rotation=MockRotation(Angle=45.0, Axis=MockVector(x=0, y=0, z=1))
    )
    expr_map = {
        "Base.x": "Part.Length",
        "Rotation": "App.ActiveDocument.Rotation",
        "Rotation.Angle": "90",
        "Rotation.Axis": "App.ActiveDocument.Axis",
    }
    
    original = PlacementData.from_freecad_value(mock_placement, expr_map)
    serialized = original.serialize()
    restored = PlacementData.from_serialized_value(serialized)
    assert original == restored
    
    # Verify expressions
    assert original.paths["Base.x"].expression == "Part.Length"
    assert original.paths["Rotation"].expression == "App.ActiveDocument.Rotation"
    assert original.paths["Rotation.Angle"].expression == "90"
    assert original.paths["Rotation.Axis"].expression == "App.ActiveDocument.Axis"


def test_placement_data_intermediate_objects():
    """Test: intermediate objects (Rotation, Rotation.Axis) with NULL values."""
    mock_placement = MockPlacement(
        Base=MockVector(x=0, y=0, z=0),
        Rotation=MockRotation(Angle=0, Axis=MockVector(x=0, y=0, z=1))
    )
    expr_map = {
        "Rotation": "some_rotation_expr",
        "Rotation.Axis": "some_axis_expr",
    }
    
    original = PlacementData.from_freecad_value(mock_placement, expr_map)
    assert original.paths["Rotation"].type_ == PropertyPathType.NULL
    assert original.paths["Rotation.Axis"].type_ == PropertyPathType.NULL
    
    serialized = original.serialize()
    restored = PlacementData.from_serialized_value(serialized)
    assert original == restored
```

#### Step 1.6: Write tests for `VectorData` round-trip

```python
# tests/integration/data_paths/test_vector_data_roundtrip.py

class MockVector:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


def test_vector_data_roundtrip():
    """Test: VectorData survives serialize->deserialize round-trip."""
    mock_vector = MockVector(x=1.0, y=2.0, z=3.0)
    
    original = VectorData.from_freecad_value(mock_vector, {})
    serialized = original.serialize()
    restored = VectorData.from_serialized_value(serialized)
    assert original == restored


def test_vector_data_with_expressions():
    """Test: expressions preserved through round-trip."""
    mock_vector = MockVector(x=1.0, y=2.0, z=3.0)
    expr_map = {"x": "Part.Length", "y": "Part.Width"}
    
    original = VectorData.from_freecad_value(mock_vector, expr_map)
    serialized = original.serialize()
    restored = VectorData.from_serialized_value(serialized)
    assert original == restored
    assert original.paths["x"].expression == "Part.Length"
    assert original.paths["y"].expression == "Part.Width"
```

#### Step 1.7: Write tests for `RotationData` round-trip

```python
# tests/integration/data_paths/test_rotation_data_roundtrip.py

class MockVector:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class MockRotation:
    def __init__(self, Angle, Axis):
        self.Angle = Angle
        self.Axis = Axis


def test_rotation_data_roundtrip():
    """Test: RotationData survives serialize->deserialize round-trip."""
    mock_rotation = MockRotation(Angle=45.0, Axis=MockVector(x=0, y=0, z=1))
    
    original = RotationData.from_freecad_value(mock_rotation, {})
    serialized = original.serialize()
    restored = RotationData.from_serialized_value(serialized)
    assert original == restored


def test_rotation_data_with_expressions():
    """Test: expressions preserved through round-trip."""
    mock_rotation = MockRotation(Angle=45.0, Axis=MockVector(x=0, y=0, z=1))
    expr_map = {"Angle": "90", "Axis": "App.ActiveDocument.Axis"}
    
    original = RotationData.from_freecad_value(mock_rotation, expr_map)
    serialized = original.serialize()
    restored = RotationData.from_serialized_value(serialized)
    assert original == restored
```

#### Step 1.8: Write tests for `ConstraintData` round-trip

```python
# tests/integration/data_paths/test_constraint_data_roundtrip.py
import pytest
from .conftest import MockConstraint, MockVector, MockRotation
from freecad.diff_wb.domain.tree.data_path import (
    ConstraintData,
    ListData,
    InternalType,
)


def test_constraint_data_basic_roundtrip():
    """Test: ConstraintData survives serialize->deserialize round-trip."""
    mock_constraint = MockConstraint(Type="Distance", Value=10.0, First=0, Second=1)
    
    original = ConstraintData.from_freecad_value(mock_constraint, {})
    serialized = original.serialize()
    restored = ConstraintData.from_serialized_value(serialized)
    assert original == restored


def test_constraint_data_all_visible_properties():
    """Test: all visible properties captured."""
    mock_constraint = MockConstraint(
        Type="Coincident",
        First=0,
        Second=1,
        Driving=True
    )
    
    original = ConstraintData.from_freecad_value(mock_constraint, {})
    assert original.paths["Type"].value == "Coincident"
    assert original.paths["First"].value == 0
    assert original.paths["Second"].value == 1
    assert original.paths["Driving"].value == True


def test_constraint_data_optional_properties():
    """Test: optional properties (Third) not present if None."""
    mock_constraint = MockConstraint(Type="Distance", Value=10.0, First=0, Second=1)
    
    original = ConstraintData.from_freecad_value(mock_constraint, {})
    assert "Third" not in original.paths


def test_constraint_data_with_expression():
    """Test: expression preserved through round-trip."""
    mock_constraint = MockConstraint(Type="Distance", Value=10.0, First=0, Second=1)
    expr_map = {"Value": "10 mm"}
    
    original = ConstraintData.from_freecad_value(mock_constraint, expr_map)
    serialized = original.serialize()
    restored = ConstraintData.from_serialized_value(serialized)
    assert original == restored
    assert original.paths["Value"].expression == "10 mm"


def test_constraint_data_via_list_data(freecad_type_map_with_mock_constraint):
    """Test: ConstraintData works when processed through ListData with patched type map."""
    constraints = [
        MockConstraint(Type="Distance", Value=10.0, First=0, Second=1),
        MockConstraint(Type="Coincident", First=1, Second=2),
    ]
    
    # With the fixture, FREECAD_TYPE_MAP is patched to include MockConstraint -> ConstraintData
    # So ListData.from_freecad_value will automatically dispatch to ConstraintData
    list_data = ListData.from_freecad_value(constraints, {})
    
    assert len(list_data.items) == 2
    assert list_data.items[0].INTERNAL_TYPE == InternalType.Constraint
    assert list_data.items[1].INTERNAL_TYPE == InternalType.Constraint
    
    # Verify round-trip
    serialized = list_data.serialize()
    restored = ListData.from_serialized_value(serialized)
    assert list_data == restored
```

#### Step 1.9: Write tests for `ListData` round-trip

```python
# tests/integration/data_paths/test_list_data_roundtrip.py
import pytest
from .conftest import MockConstraint
from freecad.diff_wb.domain.tree.data_path import (
    ListData,
    PrimitiveData,
    ConstraintData,
    InternalType,
)


def test_list_data_primitive_list_roundtrip():
    """Test: list of primitives survives round-trip."""
    original = ListData.from_freecad_value([1, 2, 3], {})
    serialized = original.serialize()
    restored = ListData.from_serialized_value(serialized)
    assert original == restored


def test_list_data_mixed_types_roundtrip():
    """Test: list with mixed types survives round-trip."""
    original = ListData.from_freecad_value([1, "hello", 3.14, True], {})
    serialized = original.serialize()
    restored = ListData.from_serialized_value(serialized)
    assert original == restored


def test_list_data_constraint_list_with_patched_map(freecad_type_map_with_mock_constraint):
    """Test: list of MockConstraint objects processed with patched type map."""
    constraints = [
        MockConstraint(Type="Distance", Value=10.0, First=0, Second=1),
        MockConstraint(Type="Coincident", First=1, Second=2),
    ]
    
    # With the fixture, FREECAD_TYPE_MAP is patched to include MockConstraint -> ConstraintData
    list_data = ListData.from_freecad_value(constraints, {})
    
    assert len(list_data.items) == 2
    assert list_data.items[0].INTERNAL_TYPE == InternalType.Constraint
    assert list_data.items[1].INTERNAL_TYPE == InternalType.Constraint
    
    # Verify round-trip
    serialized = list_data.serialize()
    restored = ListData.from_serialized_value(serialized)
    assert list_data == restored


def test_list_data_empty_list():
    """Test: empty list survives round-trip."""
    original = ListData.from_freecad_value([], {})
    serialized = original.serialize()
    restored = ListData.from_serialized_value(serialized)
    assert original == restored
    assert len(restored.items) == 0


def test_list_data_nested_lists():
    """Test: nested lists survive round-trip."""
    original = ListData.from_freecad_value([[1, 2], [3, 4]], {})
    serialized = original.serialize()
    restored = ListData.from_serialized_value(serialized)
    assert original == restored
```

#### Step 1.10: Write tests for Property.from_freecad integration

```python
# tests/integration/data_paths/test_property_from_freecad.py
import pytest
from .conftest import (
    MockVector,
    MockRotation,
    MockPlacement,
    MockConstraint,
    freecad_type_map_with_mock_constraint,
)
from freecad.diff_wb.domain.tree.data_path import (
    Property,
    ConstraintData,
    InternalType,
)


def test_property_from_freecad_primitive():
    """Test: Property.from_freecad handles primitives."""
    prop = Property.from_freecad("Length", 10.0, {}, "Base")
    assert prop.value.INTERNAL_TYPE == InternalType.Primitive


def test_property_from_freecad_list():
    """Test: Property.from_freecad handles lists."""
    prop = Property.from_freecad("Constraints", [1, 2, 3], {}, "Data")
    assert prop.value.INTERNAL_TYPE == InternalType.List


def test_property_from_freecad_unknown():
    """Test: Property.from_freecad handles unknown types."""
    class UnknownType:
        pass
    
    prop = Property.from_freecad("Unknown", UnknownType(), {}, "Base")
    assert prop.value.INTERNAL_TYPE == InternalType.Unknown


def test_property_from_freecad_constraint_list_with_patched_map(freecad_type_map_with_mock_constraint):
    """Test: Property.from_freecad handles constraint list with patched type map."""
    constraints = [
        MockConstraint(Type="Distance", Value=10.0, First=0, Second=1),
        MockConstraint(Type="Coincident", First=1, Second=2),
    ]
    
    # With the fixture, FREECAD_TYPE_MAP is patched to include MockConstraint -> ConstraintData
    # So when Property creates a ListData, it will dispatch to ConstraintData automatically
    prop = Property.from_freecad("Constraints", constraints, {}, "Data")
    
    assert prop.value.INTERNAL_TYPE == InternalType.List
    assert len(prop.value.items) == 2
    assert prop.value.items[0].INTERNAL_TYPE == InternalType.Constraint
    assert prop.value.items[1].INTERNAL_TYPE == InternalType.Constraint
```

#### Step 1.11: Implement `data_path.py` module

After all tests pass, implement the actual module:
- `InternalType` enum
- `PropertyPathType` enum
- `PropertyPathValue` dataclass with `from_value()` method
- `DataPath` protocol
- `PrimitiveData`, `UnknownData`, `PlacementData`, `VectorData`, `RotationData`, `ConstraintData`, `ListData` classes
- `FREECAD_TYPE_MAP`, `PYTHON_TYPE_MAP`, `INTERNAL_TYPE_MAP`
- Simplified `Property` class with `from_freecad()` class method

### Phase 2: YAML Serialization Integration (No FreeCAD)

**Goal**: Update `snapshot_yaml.py` to use DataPath classes.

#### Step 2.1: Write tests for YAML round-trip with Property

```python
# tests/integration/test_snapshot_yaml_roundtrip.py

def test_property_placement_yaml_roundtrip():
    """Test: Property with PlacementData survives YAML round-trip."""
    mock_placement = MockPlacement(...)
    prop = Property.from_freecad("Placement", mock_placement, {}, "Base")
    
    yaml_str = serialize_property_to_yaml(prop)
    restored_prop = deserialize_property_from_yaml(yaml_str)
    
    assert prop.value == restored_prop.value


def test_property_constraint_list_yaml_roundtrip():
    """Test: Property with ListData of constraints survives YAML round-trip."""
    constraints = [MockConstraint(...), MockConstraint(...)]
    prop = Property.from_freecad("Constraints", constraints, {}, "Data")
    
    yaml_str = serialize_property_to_yaml(prop)
    restored_prop = deserialize_property_from_yaml(yaml_str)
    
    assert prop.value == restored_prop.value
```

#### Step 2.2: Update `snapshot_yaml.py`

Update serialization to use `property.value.serialize()` and deserialization to use `INTERNAL_TYPE_MAP`.

### Phase 3: GUI Extractor Integration (Requires FreeCAD)

**Goal**: Update `gui_extractor.py` to use `Property.from_freecad()`.

#### Step 3.1: Write integration test with FreeCAD

```python
# tests/integration/test_gui_extractor_integration.py

def test_extract_placement_with_expressions(freecad_doc):
    """Test: Placement extraction captures all expressions."""
    box = freecad_doc.addObject("Part::Box", "TestBox")
    box.setExpression("Placement.Base.x", "10 mm")
    box.setExpression("Placement.Rotation.Angle", "45 deg")
    
    prop = Property.from_freecad("Placement", box.Placement, build_expr_map(box), "Base")
    
    assert prop.value.paths["Base.x"].value == 10.0
    assert prop.value.paths["Base.x"].expression == "10 mm"
    assert prop.value.paths["Rotation.Angle"].expression == "45 deg"
```

#### Step 3.2: Update `gui_extractor.py`

Replace `_extract_property_value()` with calls to `Property.from_freecad()`.

### Phase 4: Legacy Code Removal (After Integration)

**Goal**: Remove obsolete code identified in Obsolete Code to Remove section.

#### Step 4.1: Remove obsolete code from `property.py`

Remove `Vector`, `Rotation`, `Placement`, `PropertyHandler`, `_PROPERTY_HANDLERS`, etc.

#### Step 4.2: Update imports across codebase

Ensure all imports reference new module structure.

#### Step 4.3: Run full test suite

Verify all tests pass with new implementation.

## Test Strategy

### Test Type Maps

Tests use mock types that don't exist in the real FreeCAD type maps. The `conftest.py` provides:
- Mock classes (`MockVector`, `MockRotation`, `MockPlacement`, `MockConstraint`) for testing DataPath classes directly
- Pytest fixtures that patch `FREECAD_TYPE_MAP` using `@patch` decorator
- Tests use the patched maps automatically via pytest fixtures

```python
# Example: Using the fixture to patch FREECAD_TYPE_MAP
def test_constraint_list(freecad_type_map_with_mock_constraint):
    constraints = [MockConstraint(...), MockConstraint(...)]
    # With the fixture, ListData.from_freecad_value will automatically dispatch
    # MockConstraint to ConstraintData because FREECAD_TYPE_MAP is patched
    list_data = ListData.from_freecad_value(constraints, {})
    assert list_data.items[0].INTERNAL_TYPE == InternalType.Constraint
```

### Unit Tests (No FreeCAD)
- `PropertyPathValue` type detection and equality
- `InternalType` and `PropertyPathType` enums
- Each DataPath class's `from_freecad_value`, `from_serialized_value`, and `serialize` methods

### Integration Tests (No FreeCAD)
- Round-trip tests for each DataPath class using mocks
- Property.from_freecad() with all type mappings (using pytest patch fixtures)
- YAML serialization/deserialization round-trips

### Integration Tests (Requires FreeCAD)
- Actual FreeCAD Placement extraction with expressions
- Actual constraint list extraction
- Real file round-trips

## Findings & Notes

### Type Mapping Strategy

Using two separate maps provides clarity:
- `FREECAD_TYPE_MAP` for FreeCAD module types (e.g., `"Base.Placement"`)
- `PYTHON_TYPE_MAP` for Python built-in types (e.g., `int`, `str`)

This separation makes the code easier to understand and maintain.

### Why DataPath Classes Know Their Own Serialization

Each DataPath class has unique structure:
- `PrimitiveData` has single path "" with type marker
- `PlacementData` has multiple named paths
- `ListData` serializes to a list of items

Having each class implement `serialize()` and `from_serialized_value()` follows SRP and makes adding new types straightforward.

### Empty String "" for Root Values

Using `""` (empty string) as the path key for single-value items (primitives, unknown types) provides:
- Consistency with path-based approach
- Easy distinction between "no path" and "root path"
- Simple iteration (paths.keys() includes "")

### UnknownData Serialization

UnknownData uses the actual FreeCAD module+type as its value, stored as STRING type. This preserves the type information for debugging while allowing graceful handling of unrecognized types.