# Task: Convert Snapshot Structure from Hierarchical to Flat

## Goal

Convert the Snapshot domain model from a hierarchical tree structure (TreeNode with children) to a flat list of nodes with `id`, `path`, and `after` fields. This aligns with the YAML format specified in the project plan and simplifies serialization/deserialization while maintaining move detection capability.

## Context

**Current Structure:**
- `Snapshot` has `root_nodes: list[TreeNode]` 
- Each `TreeNode` has recursive `children: list[TreeNode]`
- `TreeComparator` builds path index, compares by path, rebuilds hierarchy

**Target Structure (per ProjectState.md YAML format):**
- `Snapshot` has `nodes: list[TreeNode]` (flat list)
- Each `TreeNode` has `id: int`, `name: str`, `path: str`, `after: str | None`
- No more `children` list or `is_root` flag
- Diff compares by ID with move detection via path change

**Why this change:**
1. Aligns with YAML snapshot format for easy text diffing
2. Simplifies serialization (no tree reconstruction needed for YAML)
3. Enables efficient O(n+m) diff by ID without path reconstruction
4. Maintains move detection via path comparison
5. "after" field enables sibling ordering without position indices

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Keep `path` in addition to `after` | Enables move detection ("moved from X to Y"), UI display uses path already | Only store parent+after, compute path on-the-fly (more complex for UI) |
| Diff by ID instead of path | O(n+m) complexity same as current, simpler algorithm | Reconstruct tree then diff by path (extra reconstruction step) |
| No `position` integer field | "after" is explicit (name of preceding sibling), avoids shifting numbers on insert/delete | Add integer position (more complex to maintain) |
| Remove `children` entirely from TreeNode | Flat structure stores all nodes in one list; parent-child derived from path | Keep children for backward compatibility (adds complexity) |
| Move/Reorder detection NOT implemented | Expose old_path/new_path/old_after/new_after in NodeDiff for future implementation | Implement now (not needed yet) |
| YAML uses `path` not `parent` | Aligns with domain model; path useful for text-based diffs | Use parent field (more redundant with path) |
| NodeDiff keeps hierarchical `children` | Preserves easy tree display for UI; exposes path/after for future move detection | Make NodeDiff flat too (adds complexity to UI layer) |
| Root nodes have path = name | Simple format, no special case for "/" handling at root level | Use empty string for root (more complex) |

## Architecture Impact

| Module | Changes |
|--------|---------|
| `domain/tree/node.py` | Add `id`, `after` fields; remove `children`, `is_root`; keep `path` for move detection |
| `domain/snapshots/models.py` | Change `root_nodes` to `nodes` (flat list); update methods |
| `domain/diff/comparator.py` | Index by ID instead of path; add old_path/new_path/old_after/new_after to NodeDiff |
| `domain/diff/engine.py` | Update to work with flat nodes (filter and pass nodes list) |
| `domain/snapshots/gui_extractor.py` | Build flat node list instead of hierarchical tree |
| `infrastructure/persistence/` | New YAML serialization module |

## FreeCAD Dependency

- [x] No FreeCAD required for domain changes (Phases 1-4)
- [x] FreeCAD required for extractor changes (Phase 5) - uses FreeCadPort
- [x] FreeCAD required for YAML loading (Phase 6) - tests need FreeCAD runtime

## Implementation Plan

**IMPORTANT:** Write test steps BEFORE implementation steps following TDD principles.

### Phase 1: Update TreeNode Model

- [x] Write tests for new TreeNode structure in `tests/unit/domain/tree/test_node.py`
  - Test: Creating TreeNode with all new required fields (id, path, after)
  - Test: Creating TreeNode with after=None (first child in siblings)
  - Test: Creating TreeNode with after set to sibling name
  - Test: Serializing TreeNode to dict includes id, path, after fields
  - Test: Verifying no children field exists in new structure
  - Test: Path change detection (comparing old_path vs new_path for move detection)
- [x] Implement TreeNode changes in `domain/tree/node.py`
  - Add `id: int` field (required, no default)
  - Add `after: str | None` field (None for first child or root)
  - Remove `children: list[TreeNode]` field
  - Remove `is_root: bool` field
  - Keep all existing fields: `name`, `type_id`, `label`, `path`, `properties`
  - Update `__init__` and `__str__` accordingly
  - Update docstring to remove references to `is_root` and `children`

### Phase 2: Update Snapshot Model

- [x] Write tests for flat Snapshot in `tests/unit/domain/snapshots/test_models.py`
  - Test: Creating Snapshot with flat nodes list
  - Test: Root node identification (path without "/" separator, e.g., "Body")
  - Test: Non-root node has path with "/" separator (e.g., "Body/Pad")
  - Test: `get_all_nodes()` returns flat list directly (no recursion)
  - Test: `find_node_by_path()` searches flat list efficiently
  - Test: `node_count` returns correct flat list length
  - Test: Snapshot can be created from list of flat nodes
- [x] Implement Snapshot changes in `domain/snapshots/models.py`
  - Change `root_nodes: list[TreeNode]` to `nodes: list[TreeNode]`
  - Update `node_count` property to return `len(self.nodes)`
  - Update `get_all_nodes()` to return flat list directly
  - Update `find_node_by_path()` to search flat list
  - Remove `_count_nodes()` and `_collect_nodes()` helpers (no longer needed)
  - Remove `_find_node_recursive()` (use flat search)

### Phase 3: Update TreeComparator for ID-based Diff

> **Note:** Move/Reorder DETECTION is NOT implemented yet. The diff output will expose `path` and `after` fields so this can be implemented in a future phase.

- [x] Write tests for ID-based comparison in `tests/unit/domain/diff/test_comparator.py`
  - Test: Compare two flat node lists by ID
  - Test: Detect ADDED (in new, not in old)
  - Test: Detect DELETED (in old, not in new)
  - Test: Detect MODIFIED (in both, properties differ)
  - Test: ID-based comparison produces correct added/deleted/common sets
  - Test: NodeDiff includes old_path, new_path, old_after, new_after for move/reorder detection
- [x] Implement TreeComparator changes in `domain/diff/comparator.py`
  - Rename `_build_path_index()` to `_build_id_index()` returning `dict[int, TreeNode]`
  - Update `_find_added_ids()`, `_find_deleted_ids()`, `_find_common_ids()` using ID sets
  - Update `_compare_nodes_by_id()` for property comparison
  - Update `_get_parent_path()` - still needed for UI grouping (derive from path)
  - Update `NodeDiff` to include new fields for future move/reorder detection:
    - `old_path: str | None` - path in old snapshot (None for added nodes)
    - `new_path: str | None` - path in new snapshot (None for deleted nodes)
    - `old_after: str | None` - after in old snapshot (None for added/root)
    - `new_after: str | None` - after in new snapshot (None for deleted/root)
  - Update output format: preserve hierarchical NodeDiff.children for UI
  - **Do NOT add** move/reorder detection logic - just expose path and after in NodeDiff for future implementation
  - Update `TreeDiffResult` to use ID sets instead of path strings

### Phase 4: Update DiffEngine

- [x] Write tests in `tests/unit/domain/diff/test_engine.py`
  - Test: `compute_diff()` works with flat Snapshot structure
  - Test: `compare()` works with flat node lists
- [x] Implement DiffEngine changes in `domain/diff/engine.py`
  - Update `_filter_snapshot()` to filter flat `nodes` list:
    - Iterate over `snapshot.nodes` instead of `root_nodes` with recursion
    - Use path pattern matching to identify children (nodes with path starting with "parentPath/")
  - Update `compute_diff()` to pass `snapshot.nodes` instead of `snapshot.root_nodes` to TreeComparator
  - Update `compare()` to use `nodes=` parameter in Snapshot creation instead of `root_nodes=`
  - Minimal changes - most logic already delegates to TreeComparator

> **Note:** DiffEngine output (NodeDiff) will expose `path` and `after` fields. Actual move/reorder detection logic (comparing old_path vs new_path, old_after vs new_after) will be implemented in a future phase.

### Phase 5: Update SnapshotExtractor (requires FreeCAD)

- [x] Write integration tests in `tests/integration/` (or use existing extractor tests)
  - Test: Extracted snapshot has flat node list
  - Test: Each node has id, path, after populated correctly
  - Test: Root nodes have after=null (they are first in document order)
  - Test: First child of any parent has after=null
  - Test: Subsequent children have after set to previous sibling name
  - Test: All nodes have unique ids
- [x] Implement extractor changes in `domain/snapshots/gui_extractor.py`
  - Update `_build_tree_node()` to build flat list instead of recursive tree
  - First pass: collect all nodes in document order (for "after" field)
  - Second pass: set "after" based on previous node in same parent's children
  - Remove recursive `children` building - just collect nodes
  - For each object: determine parent from claim_map, determine "after" from sibling order
  - Generate path from parent chain: "ParentName/ChildName/GrandchildName" (root = just name)
  - Use `object.ID` for the unique `id: int` field (not DocumentObjectID)

### Phase 6: Add YAML Persistence (requires FreeCAD for full tests)

- [x] Write tests in `tests/unit/infrastructure/persistence/` and `tests/integration/`
  - Test: Serialize Snapshot to YAML format matching ProjectState.md spec
  - Test: Deserialize YAML to Snapshot with flat node structure
  - Test: Round-trip (serialize → deserialize → serialize) produces identical output
  - Test: Loading YAML creates correct flat node structure
- [x] Create new module `infrastructure/persistence/snapshot_yaml.py`
  - Implement `SnapshotYamlSerializer` class
  - `to_yaml(snapshot: Snapshot, path: Path) -> None`
  - `from_yaml(path: Path) -> Snapshot`
  - Follow YAML format from ProjectState.md:
    ```yaml
    v: snapshot_version
    timestamp: [UTC timestamp]
    uid: [document UUID]
    objects:
    - id: 43
      type_id: Sketcher::SketchObject
      name: Sketch
      after: [sibling name or null]
      path: [full path for text diff readability]
      properties: [...]
    ```
  - Store objects sorted by `id` (as per spec: "objects are stored in order of the integer id")
  - Include `path` field (not `parent`) in YAML for human-readable text diffs
- [x] Update `infrastructure/persistence/__init__.py` to export new serializer

### Phase 7: Integration Verification

- [x] Run full test suite: `task test`
- [x] Run integration tests: `task test:integration`
- [x] Verify YAML loading works end-to-end with real FreeCAD file

## Test Strategy

- **Unit tests (Phases 1-4)**: Pure Python, no FreeCAD needed
  - Test new TreeNode structure
  - Test flat Snapshot behavior
  - Test ID-based diff algorithm with move/reorder detection
- **Integration tests (Phases 5-6)**: Require FreeCAD runtime
  - Test extractor produces flat structure
  - Test YAML round-trip with real FreeCAD documents
- **Test helpers**: Update fakes in `tests/fakes/` to produce new TreeNode format

## Findings & Notes

1. **Move detection**: When node ID exists in both snapshots but `path` changed → MOVED. NodeDiff includes `old_path` and `new_path` fields for UI display (not yet implemented in UI).

2. **Reorder detection**: When node ID exists in both, path unchanged, but `after` changed → REORDERED. NodeDiff includes `old_after` and `new_after` fields for UI display (not yet implemented in UI).

3. **Path format**: Use "/" separator (e.g., "Body/Pad"). Root nodes have path = name (e.g., "Body"). Parent derived by splitting on last "/" - if no "/" in path, it's a root node.

4. **"after" format**: Stores the name (not ID) of the preceding sibling. For first child in any group (root or child), `after: null`. Root nodes in document order also have after: null.

5. **Backward compatibility**: This is a breaking change to the domain model. No migration path needed since snapshots are versioned and YAML is for new commits.

6. **UI Impact**: After this change, NodeDiff maintains hierarchical `children` for easy tree display. Move/reorder detection data is exposed via old_path/new_path/old_after/new_after fields for future UI implementation.