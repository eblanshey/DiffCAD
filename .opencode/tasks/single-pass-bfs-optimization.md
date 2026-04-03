# Task: Single-Pass BFS Optimization for gui_extractor.py

## Goal
Replace the multi-pass algorithm (4+ passes) with a single-pass iterative BFS that builds the flat node list directly, reducing complexity from O(N³) to O(N²).

## Context
The current implementation in `gui_extractor.py` uses:
1. `_build_effective_children_map()` - 2 internal passes to compute recursive exclusion
2. `_build_hierarchy_map()` - builds parent/children maps
3. `extract_tree()` - 2 passes (identify roots, then recursive DFS traversal)

The tests verify:
- Flat node list with `id`, `path`, `after` fields
- Path format: `root = name`, `child = parent/child`
- `after` field: first node = `None`, others = previous sibling name
- Unique IDs from FreeCAD object.ID
- Nested hierarchy (Part → Body → Sketch)
- Circular claims handling (no infinite recursion)
- Property extraction still works

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| BFS vs DFS | BFS naturally processes level-by-level, making "after" tracking simpler | DFS works but requires more complex stack management |
| Keep same output | Tests verify exact path/after format, must match | Could change output order but would break tests |
| Iterative queue | Eliminates recursion depth limits | Recursive is clearer but has stack overhead |

## Architecture Impact
- **File:** `freecad/diff_wb/domain/snapshots/gui_extractor.py`
- **Functions to modify:** `_build_effective_children_map()`, `_get_all_descendants()`, `extract_tree()`, `_build_tree_node()`
- **New function:** Add single-pass BFS function that replaces the multi-pass logic

## FreeCAD Dependency
- [ ] No FreeCAD required (pure algorithm change - tests use mocks)

## Implementation Plan

### Phase 1: Verify current tests pass first
- [x] Run `task test` to confirm baseline
- [x] Run `task test:integration` to confirm baseline

### Phase 2: Implement single-pass algorithm
- [x] Replace `_build_effective_children_map()` with direct hierarchy building in BFS
- [x] Replace `_get_all_descendants()` with integrated logic in BFS queue
- [x] Implement `extract_tree()` using iterative BFS queue
- [x] Track path and "after" directly in queue items

### Phase 3: Verify all tests pass
- [x] Run unit tests (`task test`)
- [x] Run integration tests (`task test:integration`)
- [x] Verify output matches existing tests exactly

## Test Strategy
- **Unit tests:** Use existing mocks from `test_extractor.py` - no changes needed to mock infrastructure
- **Integration tests:** Use existing `test_snapshot_extractor_flat_structure.py` - verify output format unchanged

## Findings & Notes
1. The recursive exclusion logic (`_build_effective_children_map`) must be preserved - it implements FreeCAD's tree rule: if A claims B, and B claims C, then C is excluded from A's direct children
2. The "after" field requires tracking sibling order - BFS naturally provides this via queue position
3. Path can be built incrementally: pass `(child_obj, parent_path, after_sibling)` in queue
4. Circular claims are handled by checking if child was already processed (using visited set)

## Algorithm Reference (Pseudo-code)

### Single-Pass BFS Replacement

```python
def extract_tree_single_pass(self, port: FreeCadPort, doc: DocumentLike, gui_doc: Any) -> Snapshot:
    # Step 1: Build claim_map in ONE pass
    claim_map: dict[str, list[str]] = {}
    for obj in doc.Objects:
        if not hasattr(obj, "Name"):
            continue
        vp = _get_view_provider(obj, gui_doc)
        if vp:
            children = _get_claimed_children(vp)
            if children:
                claim_map[obj.Name] = children

    # Step 2: Build parent_map directly from claim_map (no descendants calculation)
    parent_map: dict[str, str] = {}
    for parent, children in claim_map.items():
        for child in children:
            # Only set if not already set (first claim wins)
            if child not in parent_map:
                parent_map[child] = parent

    # Step 3: Single BFS pass to build flat node list
    nodes: list[TreeNode] = []
    queue: list[tuple[object, str, str | None]] = []  # (obj, path, after)
    visited: set[str] = set()  # Track processed objects

    # Find roots (objects not in parent_map) and add to queue
    root_names: list[str] = []
    for obj in doc.Objects:
        name = getattr(obj, "Name", None)
        if name and name not in parent_map:
            root_names.append(name)

    # Add roots to queue with their "after" value
    for i, name in enumerate(root_names):
        obj = port.get_object(doc, name)
        if obj:
            after = root_names[i - 1] if i > 0 else None
            queue.append((obj, name, after))

    # Process queue (BFS)
    while queue:
        obj, path, after = queue.pop(0)  # Dequeue front
        name = getattr(obj, "Name", None)
        if not name or name in visited:
            continue
        visited.add(name)

        # Extract properties
        properties = _extract_visible_properties(obj)

        # Create node
        node = TreeNode(
            id=getattr(obj, "ID", 0),
            name=name,
            type_id=getattr(obj, "TypeId", ""),
            label=getattr(obj, "Label", name),
            path=path,
            after=after,
            properties=properties,
        )
        nodes.append(node)

        # Queue children from claim_map (apply recursive exclusion via parent_map)
        # Children are those where parent_map[child] == name
        children_names = [c for c, p in parent_map.items() if p == name]
        for i, child_name in enumerate(children_names):
            child_obj = port.get_object(doc, child_name)
            if child_obj:
                child_path = f"{path}/{child_name}"
                child_after = children_names[i - 1] if i > 0 else None
                queue.append((child_obj, child_path, child_after))

    return Snapshot(snapshot_id=str(uuid.uuid4()), document_name=document_name, timestamp=datetime.now(), nodes=nodes)
```

### Key Differences from Current Implementation

| Current (multi-pass) | Optimized (single-pass) |
|---------------------|------------------------|
| `_get_all_descendants()` called per child | No separate descendant calculation |
| Two passes for effective children | Parent map built directly |
| Recursive `_build_tree_node()` | Iterative BFS queue |
| Multiple list iterations | Single queue iteration |