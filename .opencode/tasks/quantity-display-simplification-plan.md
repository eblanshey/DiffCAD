# Task: Quantity YAML Simplification to Single String Value

## Goal
Simplify `Base.Quantity` handling so quantity properties are stored and diffed as a single root string value (for example, `"10.0 mm"`) instead of separate `Value` and `Unit` path entries.

This should eliminate noisy sub-rows in the UI and reduce model complexity, while keeping deterministic snapshot serialization and stable diff behavior.

## Context
- The recently implemented path-based model currently stores quantity as:
  - `paths["Value"] = FLOAT`
  - `paths["Unit"] = STRING`
  - optional `paths["."] = NULL + expression`
- This currently causes UI output to show quantity child rows (`Value`, `Unit`) and exposes verbose unit representations.
- Product direction has changed: there is no current need to separately track numeric magnitude vs unit semantics. A single rendered quantity change is sufficient.
- Existing architecture supports this simplification cleanly: presenter already maps root `"."` value to top property row.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Store Quantity in root path `"."` as `PropertyPathType.STRING` | Single source of truth, simple YAML shape, directly matches UI expectation | Keep `Value` + `Unit` split |
| Keep `InternalType.Quantity` (do not remap to `Primitive`) | Preserves type identity and future extension point while simplifying payload | Convert quantity to PrimitiveData |
| Use `str(quantity)` as canonical serialized display value | Produces concise user-facing representation (`"10.0 mm"`) and avoids verbose `Unit` text | Build string from `Value` + compact unit symbol |
| Store root expression on the same root string entry | Keeps expression and value co-located; removes extra NULL-only root entry for quantity | Keep dedicated expression-only root entry |
| No compatibility shim for old quantity YAML shape in this task | MVP policy: no backwards-compat support; keeps implementation straightforward | Dual-shape reader (`Value`/`Unit` + new root-string) |
| No presenter special-case required for quantity flattening | If quantity only has `"."`, presenter naturally renders one row with no children | Add quantity-specific presenter filtering |
| Add/update manual testing docs despite pure-code implementation | Final behavior is user-visible in FreeCAD GUI and should be explicitly validated manually | Unit tests only |

## Architecture Impact

### Modules affected
1. `freecad/diff_wb/domain/tree/data_path.py`
   - Redefine `QuantityData` path contract from `{Value, Unit, optional .}` to `{'.'}` only.
   - Keep serialization envelope (`type_`, `paths`) unchanged at container level.
2. `tests/unit/domain/tree/test_data_path_roundtrip.py`
   - Update quantity round-trip tests for single root-string path.
3. `tests/unit/domain/diff/test_property_path_diffs.py`
   - Update flattening expectations for quantity (only `"."` path).
4. `tests/unit/infrastructure/persistence/test_snapshot_yaml_data_path.py`
   - Update quantity persistence assertions from `Value/Unit` to root string path.
5. `tests/unit/ui/presenters/test_diff_presenter_properties.py`
   - Add/adjust tests to assert quantity appears as a single property row with no child rows.
6. `docs/manual-testing/quantity_display_tests.md` (**new**)
   - Add human verification scenarios for quantity rendering and diff output.

### Public vs private interfaces
- **Public (unchanged):**
  - `Property` API (`from_freecad`, `to_serialized`, `from_serialized`)
  - `DataPath` protocol
  - `QuantityData` class presence and `InternalType.Quantity`
- **Public contract change:**
  - `QuantityData.paths` schema now uses root `"."` string entry as canonical value.
- **Private/internal changes:**
  - `QuantityData.from_freecad_value()` and `to_python()` behavior.
  - Tests and helpers expecting `Value`/`Unit` keys.

### Dependency boundaries
- Domain remains pure and independent of infrastructure/UI.
- Persistence layer remains adapter-only (`Property.to_serialized()` / `from_serialized()`), no domain leakage.
- Presenter remains transformation-only and should not need quantity business logic if root-only shape is used.

## FreeCAD Dependency
- [x] No FreeCAD required (pure code path)
- [ ] FreeCAD required (follow exploration phase)

Rationale: This is a domain representation + serialization shape change and can be fully tested with fakes/mocks and existing unit tests. Manual GUI checks are still documented.

## Implementation Plan
**IMPORTANT:** Every phase follows TDD ordering: write tests first, implement to pass, then refactor.

### Phase 1: Redefine QuantityData root-path schema

#### Tests first
- [ ] Update quantity tests in `tests/unit/domain/tree/test_data_path_roundtrip.py`:
  - [ ] Quantity round-trip uses `paths["."]` only.
  - [ ] Root entry type is `STRING` and value is quantity text (`"10.0 mm"` style).
  - [ ] Root expression (if present) persists on the same `"."` entry.
  - [ ] Remove legacy assertions that require `paths["Value"]` / `paths["Unit"]`.

#### Implement
- [ ] Update `QuantityData.from_freecad_value(value, expr_map)` in `data_path.py`:
  - [ ] Build single root `PropertyPathValue(PropertyPathType.STRING, str(value), expression=_root_expression(expr_map))`.
  - [ ] Do not emit `Value` or `Unit` keys.
- [ ] Update `QuantityData.to_python()` to return a string instead of dict.
- [ ] Update `QuantityData` docstrings/comments to describe root-only quantity model.

#### Refactor
- [ ] Remove any leftover quantity-specific helper/comment references that imply split `Value`/`Unit` storage.

Detailed implementation sketch (`freecad/diff_wb/domain/tree/data_path.py`):

```python
@dataclass(frozen=True)
class QuantityData:
    """Wraps a Base.Quantity as a single root string path entry."""

    INTERNAL_TYPE: ClassVar[InternalType] = InternalType.Quantity
    paths: dict[str, PropertyPathValue]

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> "QuantityData":
        root_expr = _root_expression(expr_map)
        quantity_text = str(value)  # e.g. "10.0 mm"
        return QuantityData(
            paths={
                ".": PropertyPathValue(
                    type_=PropertyPathType.STRING,
                    value=quantity_text,
                    expression=root_expr,
                )
            }
        )

    @staticmethod
    def from_serialized_value(data: Any) -> "QuantityData":
        return QuantityData(paths=_deserialize_path_entries(data.get("paths", {})))

    def serialize(self) -> dict[str, Any]:
        return {
            "type_": self.INTERNAL_TYPE.value,
            "paths": _serialize_path_entries(self.paths),
        }

    def to_python(self) -> str | None:
        root = self.paths.get(".")
        return str(root.value) if root is not None and root.value is not None else None
```

Detailed test sketch (`tests/unit/domain/tree/test_data_path_roundtrip.py`):

```python
class TestQuantityDataRoundTrip:
    def test_roundtrip_root_string_only(self) -> None:
        original = QuantityData(
            paths={
                ".": PropertyPathValue(PropertyPathType.STRING, "10.0 mm", None),
            }
        )

        serialized = original.serialize()
        restored = data_path_from_serialized(serialized)

        assert isinstance(restored, QuantityData)
        assert set(restored.paths.keys()) == {"."}
        assert restored.paths["."].type_ == PropertyPathType.STRING
        assert restored.paths["."].value == "10.0 mm"

    def test_roundtrip_root_expression_preserved(self) -> None:
        original = QuantityData(
            paths={
                ".": PropertyPathValue(
                    PropertyPathType.STRING,
                    "5.0 mm",
                    "Body.Length",
                )
            }
        )

        restored = data_path_from_serialized(original.serialize())

        assert restored.paths["."].expression == "Body.Length"
        assert "Value" not in restored.paths
        assert "Unit" not in restored.paths
```

### Phase 2: Align diff model expectations with root-only quantity paths

#### Tests first
- [ ] Update `tests/unit/domain/diff/test_property_path_diffs.py`:
  - [ ] Quantity flattening yields only `"."` path.
  - [ ] Value diff for quantity compares root string entries.
  - [ ] Expression diff still works at root path for quantity.
  - [ ] Remove checks for `"Value"` and `"Unit"` quantity subpaths.

#### Implement
- [ ] No production diff code change expected if Phase 1 is correct.
- [ ] If any utility assumptions require non-root quantity keys, remove them.

#### Refactor
- [ ] Keep tests focused on behavior (single-root quantity path) and avoid redundant shape assertions across multiple files.

Detailed test sketch (`tests/unit/domain/diff/test_property_path_diffs.py`):

```python
def test_flatten_quantity_data_root_only() -> None:
    qd = QuantityData(
        paths={
            ".": PropertyPathValue(PropertyPathType.STRING, "10.0 mm"),
        }
    )

    result = _flatten_data_path(qd)

    assert list(result.keys()) == ["."]
    assert result["."].value == "10.0 mm"


def test_property_diff_quantity_string_modified() -> None:
    old_prop = Property(
        value=QuantityData(paths={".": PropertyPathValue(PropertyPathType.STRING, "10.0 mm")})
    )
    new_prop = Property(
        value=QuantityData(paths={".": PropertyPathValue(PropertyPathType.STRING, "12.0 mm")})
    )

    diff = PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop)

    assert diff.state == DiffState.MODIFIED
    assert len(diff.path_diffs) == 1
    assert diff.path_diffs[0].path == "."
    assert diff.path_diffs[0].value_state == DiffState.MODIFIED


def test_property_diff_quantity_expression_only_change() -> None:
    old_prop = Property(
        value=QuantityData(
            paths={".": PropertyPathValue(PropertyPathType.STRING, "10.0 mm", "Sketch.Length")}
        )
    )
    new_prop = Property(
        value=QuantityData(paths={".": PropertyPathValue(PropertyPathType.STRING, "10.0 mm", None)})
    )

    diff = PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop)

    assert diff.path_diffs[0].value_state == DiffState.UNCHANGED
    assert diff.path_diffs[0].expression_state == DiffState.DELETED
    assert diff.state == DiffState.MODIFIED
```

### Phase 3: Align YAML persistence tests with new quantity envelope

#### Tests first
- [ ] Update `tests/unit/infrastructure/persistence/test_snapshot_yaml_data_path.py`:
  - [ ] Quantity envelope remains `type_: Quantity`, `paths`, `group`.
  - [ ] Quantity payload contains `paths["."]` with `type_=STRING` and value text.
  - [ ] Round-trip assertions verify root string (not split value/unit keys).
  - [ ] Remove legacy checks for `"Value"` / `"Unit"` keys.

#### Implement
- [ ] No serializer code changes expected (serializer delegates to domain model).
- [ ] Only adjust behavior if tests reveal envelope assumptions tied to old quantity shape.

#### Refactor
- [ ] Consolidate repetitive envelope assertions into small helpers where useful.

Detailed persistence test sketch (`tests/unit/infrastructure/persistence/test_snapshot_yaml_data_path.py`):

```python
@pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
def test_quantity_property_envelope_root_string_only() -> None:
    from FreeCAD import Base

    qty = Base.Quantity("10 mm")
    prop = Property.from_freecad(qty, {}, group="Base")
    result = SnapshotYamlSerializer._serialize_properties({"Length": prop})

    qty_data = result["Length"]
    assert qty_data["type_"] == "Quantity"
    assert "paths" in qty_data
    assert set(qty_data["paths"].keys()) == {"."}
    assert qty_data["paths"]["."]["type_"] == "STRING"
    assert qty_data["paths"]["."]["value"] == "10.0 mm"
    assert "Value" not in qty_data["paths"]
    assert "Unit" not in qty_data["paths"]


@pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
def test_quantity_roundtrip_preserves_root_string_and_expression() -> None:
    from FreeCAD import Base

    qty = Base.Quantity("5 mm")
    original = Property.from_freecad(qty, {".": "Sketch.Length"}, group="Base")
    restored = Property.from_serialized(original.to_serialized())

    assert isinstance(restored.value, QuantityData)
    assert set(restored.value.paths.keys()) == {"."}
    assert restored.value.paths["."].value == "5.0 mm"
    assert restored.value.paths["."].expression == "Sketch.Length"
```

### Phase 4: Confirm presenter/UI behavior with root-only quantity values

#### Tests first
- [ ] Add/adjust tests in `tests/unit/ui/presenters/test_diff_presenter_properties.py`:
  - [ ] Quantity property top row shows root string values in old/new columns.
  - [ ] Quantity property has no `Value`/`Unit` child rows.
  - [ ] Quantity expression (if present/changed) still appears according to existing root-expression behavior.
  - [ ] Non-quantity nested properties remain unchanged (regression).

#### Implement
- [ ] Prefer no presenter code changes; validate behavior emerges from root-only quantity path shape.
- [ ] If needed, only perform minimal presenter adjustment (without adding quantity-specific branching unless unavoidable).

#### Refactor
- [ ] Keep presenter logic generic; avoid hard-coded quantity exceptions if root-path model already solves display noise.

Detailed presenter test sketch (`tests/unit/ui/presenters/test_diff_presenter_properties.py`):

```python
def test_quantity_property_single_row_from_root_string() -> None:
    fake_view, presenter = _create_test_presenter()

    old_prop = Property(
        value=QuantityData(paths={".": PropertyPathValue(PropertyPathType.STRING, "10.0 mm")}),
        group="Base",
    )
    new_prop = Property(
        value=QuantityData(paths={".": PropertyPathValue(PropertyPathType.STRING, "12.0 mm")}),
        group="Base",
    )

    node_diff = NodeDiff(
        path="Part",
        type_id="Part::Feature",
        property_diffs=[PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop)],
        _force_state=DiffState.MODIFIED,
    )
    diff_result = _build_diff_result(node_diff)

    presenter.present_diff(diff_result)
    presenter.on_node_selected(diff_result.new_snapshot.document_name, "Part")

    call = next(c for c in fake_view.get_calls() if c["method"] == "show_properties")
    prop_pres = call["properties"][0]

    assert prop_pres.name == "Length"
    assert prop_pres.old_value == "10.0 mm"
    assert prop_pres.new_value == "12.0 mm"
    assert prop_pres.state == DiffState.MODIFIED
    assert prop_pres.children == []


def test_quantity_expression_row_still_supported_on_root_path() -> None:
    fake_view, presenter = _create_test_presenter()

    old_prop = Property(
        value=QuantityData(
            paths={".": PropertyPathValue(PropertyPathType.STRING, "10.0 mm", "Sketch.Length")}
        ),
        group="Base",
    )
    new_prop = Property(
        value=QuantityData(paths={".": PropertyPathValue(PropertyPathType.STRING, "10.0 mm", None)}),
        group="Base",
    )

    node_diff = NodeDiff(
        path="Part",
        type_id="Part::Feature",
        property_diffs=[PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop)],
        _force_state=DiffState.MODIFIED,
    )
    diff_result = _build_diff_result(node_diff)

    presenter.present_diff(diff_result)
    presenter.on_node_selected(diff_result.new_snapshot.document_name, "Part")

    call = next(c for c in fake_view.get_calls() if c["method"] == "show_properties")
    prop_pres = call["properties"][0]

    assert len(prop_pres.children) == 1
    expr_pres = prop_pres.children[0]
    assert expr_pres.name == "Expression"
    assert expr_pres.state == DiffState.DELETED
    assert expr_pres.old_value == "Sketch.Length"
    assert expr_pres.new_value is None
```

### Phase 5: Manual testing documentation

#### Tests/documentation first
- [ ] Create `docs/manual-testing/quantity_display_tests.md` with explicit cases grouped by file/location.

#### Implement
- [ ] Ensure manual test steps reflect current Diff Workbench UX and terminology.
- [ ] Keep expected results precise and visually verifiable.

#### Refactor
- [ ] Cross-check style/format with existing manual test docs in `docs/manual-testing/`.

## Proposed Manual Test Cases (grouped by file location)

### File: `docs/manual-testing/quantity_display_tests.md`

#### Test asset location: `tests/freecad/BasicFile.FCStd`

1. **Single-row quantity rendering (length)**
   - **Steps:** Open `BasicFile.FCStd` in FreeCAD, switch to Diff WB, select node containing `Pad.Length`.
   - **Expected:** Property row shows one value (`e.g. 10.0 mm`) with no nested `Value` or `Unit` rows.

2. **Single-row quantity rendering (angle)**
   - **Steps:** Select node containing `Pad.TaperAngle` or comparable angle quantity.
   - **Expected:** One row with compact angle string (`e.g. 5.0 deg`), no unit signature tuple text.

3. **Modified quantity diff visual**
   - **Steps:** Change a quantity (e.g. pad length), compare working vs committed/previous snapshot.
   - **Expected:** Top quantity row marked MODIFIED; old/new columns show quantity strings.

4. **Added/deleted quantity row visual**
   - **Steps:** Add or remove feature with quantity properties and open diff.
   - **Expected:** Quantity row shows ADDED/DELETED state correctly in single-row form.

5. **Quantity expression behavior sanity**
   - **Steps:** Attach expression to a quantity, then modify/remove expression and diff.
   - **Expected:** Quantity value remains single row; expression display behavior remains consistent with existing root expression handling.

6. **Regression check for non-quantity nested properties**
   - **Steps:** Inspect placement/vector/list properties in same diff session.
   - **Expected:** Nested path rendering still works for non-quantity types; only quantity shape is simplified.

## Test Strategy
- **Unit tests**
  - Domain/tree tests validate quantity schema and round-trip behavior.
  - Domain/diff tests validate flattening and path-level diff semantics for root-only quantity.
  - Persistence tests validate YAML envelope and round-trip consistency.
  - Presenter tests validate final UI model (single row, no `Value`/`Unit` children).
- **Integration tests**
  - Not required for this scope (pure model and presentation adaptation).
- **Manual tests**
  - Required for final GUI confidence and user-facing behavior validation.

## Findings & Notes
1. This change intentionally optimizes for clarity and implementation simplicity over semantic unit/magnitude decomposition.
2. Keeping `InternalType.Quantity` while simplifying to root string minimizes architectural churn and preserves future extensibility.
3. Because backward compatibility is out of scope for MVP, existing snapshots using split quantity keys are not migrated in this plan.
4. `docs/PLAN.md` was not found in repository during planning; architecture and existing task plans were used as primary planning context.
5. Ensure Python file/module responsibility headers remain accurate in any modified files.
