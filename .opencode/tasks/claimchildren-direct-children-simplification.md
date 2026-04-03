# Task: Simplify Algorithm - claimChildren Returns Direct Children Only

## Goal
Simplify the tree extraction algorithm by removing unnecessary code that handles recursive exclusion, since FreeCAD's `claimChildren()` already returns only direct children (not grandchildren). Confirmed via FreeCAD source code analysis.

## Context
FreeCAD's `claimChildren()` returns only **direct children**, not recursive descendants. There's a separate method `claimChildrenRecursive()` for getting all descendants. This means the current algorithm is doing unnecessary work:

1. **`_get_descendants()`** - Recursively traverses claim_map to find all descendants (unnecessary)
2. **Recursive exclusion logic** - Filters children that are descendants of other children (unnecessary)
3. **O(N²) child lookup** - Iterates parent_map for each node to find children (inefficient)

The current algorithm was built on the incorrect assumption that claimChildren could return grandchildren.

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Remove `_get_descendants()` | claimChildren() already returns direct children only | Keep it for safety - rejected, confirmed by FreeCAD source |
| Simplify `_build_parent_map()` | No filtering needed - just map parent→children directly | Keep complex logic - rejected, unnecessary |
| Build `children_map` for O(1) lookup | Avoids O(N²) iteration in BFS phase | Keep iterating parent_map - rejected |
| Update existing tests | Must maintain same output behavior | Add new tests - rejected, existing tests should pass |

## Architecture Impact
- **File:** `freecad/diff_wb/domain/snapshots/gui_extractor.py`
- **Functions to remove:** `_get_descendants()`, `_build_effective_children_map()`
- **Functions to modify:** `_build_parent_map()`, `_build_flat_node_list()`
- **Test file:** `tests/unit/domain/snapshots/test_extractor.py` - remove test for removed function

## FreeCAD Dependency
- [ ] No FreeCAD required (pure algorithm change - tests use mocks)

## Implementation Plan

### Phase 1: Verify baseline
- [ ] Run `task test` to confirm baseline
- [ ] Run `task test:integration` to confirm baseline

### Phase 2: Implement simplification
- [ ] Remove `_get_descendants()` function entirely
- [ ] Remove `_build_effective_children_map()` function entirely
- [ ] Simplify `_build_parent_map()`: build parent_map and children_map directly from claim_map (no filtering needed)
- [ ] Optimize `_build_flat_node_list()`: use children_map.get(obj_name, []) instead of iterating parent_map
- [ ] Remove `test_build_effective_children_map_order_independent` test from test_extractor.py

### Phase 3: Verify all tests pass
- [ ] Run unit tests (`task test`)
- [ ] Run integration tests (`task test:integration`)
- [ ] Verify output matches existing tests exactly

## Test Strategy
- **Unit tests:** Existing mocks from `test_extractor.py` - remove test for removed function
- **Integration tests:** Existing `test_snapshot_extractor_flat_structure.py` - should pass unchanged
- **Key verification:** Output format must be identical to before (path, after, id fields)

## Algorithm Changes

### Before (current implementation):
```python
# _build_parent_map - does unnecessary recursive exclusion
for parent_name, children in claim_map.items():
    all_descendants: set[str] = set()
    for child_name in children:
        all_descendants.update(_get_descendants(child_name, claim_map))  # UNNECESSARY
    
    effective_child_list = [c for c in children if c not in all_descendants]  # UNNECESSARY
    effective_children[parent_name] = effective_child_list

# _build_flat_node_list - O(N²) child lookup
children_names = [c for c, p in parent_map.items() if p == obj_name]  # O(N) per node
```

### After (simplified):
```python
# _build_parent_map - direct mapping, no filtering
parent_map: dict[str, str] = {}
children_map: dict[str, list[str]] = {}

for parent_name, children in claim_map.items():
    children_map[parent_name] = children  # Already direct children!
    for child_name in children:
        if child_name not in parent_map:
            parent_map[child_name] = parent_name

# _build_flat_node_list - O(1) child lookup
children_names = children_map.get(obj_name, [])  # O(1) lookup
```

## Findings & Notes
1. Confirmed via FreeCAD source: `claimChildren()` returns direct children only
2. FreeCAD has separate `claimChildrenRecursive()` method for recursive traversal
3. The simplification maintains the exact same output - just more efficient
4. Tests verify the output format is unchanged (path, after, id fields)