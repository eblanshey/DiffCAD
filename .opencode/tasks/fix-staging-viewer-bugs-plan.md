# Task: Fix Staging Tree Viewer Regressions

## Goal
Fix Staging-mode tree diff behavior so that:
1. top-level root rows show the correct git path (not `Unnamed Document`), and
2. clicking a staged node updates the property viewer reliably.

## Context
User-reported flow:
1. Modify part and stage it.
2. Select **Staging** in history.
3. Root row incorrectly shows `Unnamed Document`.
4. Clicking nodes does not update property panel.

Investigation indicates the failure is in staging data plumbing (snapshot identity + selection key wiring), not in the core diff algorithm.

Notes from planning investigation:
- `docs/PLAN.md` does not currently exist in repository.
- Architecture reference used: `docs/Architecture.md`.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Populate snapshot identity (`git_path`, `document_name`) in `CreateDocumentSnapshotForCommitAction` | YAML does not persist these fields, but Staging UI logic requires them | Persist identity in YAML format (rejected: broader format migration and unnecessary for this fix) |
| Keep serializer generic (`from_yaml` remains file-content focused) | SRP: serializer reconstructs persisted payload; caller provides runtime context | Add repo/path concerns to serializer API (rejected: wrong layer responsibility) |
| Use `dataclasses.replace` for frozen dataclasses | `Snapshot` and `DiffResult` are frozen; immutable update is required | Mutating fields directly (rejected: invalid with `frozen=True`) |
| Ensure view root item always stores a stable selection key in `UserRole` | Presenter lookup depends on key from node-click callback | Infer key from displayed label text (rejected: brittle, localized text issues) |
| Add focused regression tests in action/presenter/view layers | Prevent reintroduction in Staging and Commit modes | Manual-only verification (rejected: weak long-term protection) |

## Architecture Impact
### Modules affected
- `freecad/diff_wb/application/actions/create_document_snapshot_commit.py`
- `freecad/diff_wb/ui/presenters/diff_presenter.py`
- `freecad/diff_wb/ui/views/diff_panel_view.py`
- `tests/unit/application/actions/test_create_document_snapshot_commit.py`
- `tests/unit/ui/presenters/test_diff_presenter.py`
- `tests/unit/ui/views/test_show_diff_tree.py` (or split new view-focused test module if cleaner)
- `docs/manual-testing/staging_diff_viewer_tests.md` (new)

### SRP / Boundaries
- **Application action** owns runtime context enrichment for deserialized snapshots.
- **Presenter** owns mapping between view selection key and `DiffResult` lookup.
- **View** only stores/retrieves click metadata and renders content.
- No domain/infrastructure dependency inversion violations introduced.

### Public vs Private Interfaces
- Public API unchanged for domain models.
- Internal behavior changes:
  - `CreateDocumentSnapshotForCommitAction.execute(...)` returns snapshots with populated identity fields.
  - `DiffPanelView.show_diff_trees(...)` stores root selection key even on fallback labels.

## FreeCAD Dependency
- [ ] No FreeCAD required (pure code)
- [x] FreeCAD required (follow exploration phase)

Reasoning: unit tests cover most logic, but final validation is GUI behavior in FreeCAD workbench runtime.

## Implementation Plan
**IMPORTANT:** For each phase, tests come before implementation (TDD).

### Phase 1: API/Behavior Exploration + Repro Baseline
- [ ] Write/confirm failing tests that reproduce both bugs:
  - Action returns snapshot missing `git_path`/`document_name`.
  - Staging node click fails to trigger property update when selection key is empty.
- [ ] Document exact call chain and failure points in test comments:
  - Action deserialize path
  - Presenter `_diff_results_by_path` population
  - View `_on_tree_item_clicked` callback condition

Code snippet (expected failing test shape):
```python
# tests/unit/application/actions/test_create_document_snapshot_commit.py
def test_execute_populates_git_path_and_document_name_from_fcstd_path() -> None:
    mock_git_service = MagicMock(spec=GitService)
    mock_git_service.get_file_contents.return_value = VALID_YAML

    action = CreateDocumentSnapshotForCommitAction(git_service=mock_git_service)
    repo = GitRepository(name="repo", absolute_path="/repo")

    result = action.execute(repo, "HEAD", "parts/Widget.FCStd")

    assert result.is_success is True
    assert result.data is not None
    assert result.data.git_path == "parts/Widget.FCStd"
    assert result.data.document_name == "Widget.FCStd"
```

### Phase 2: Fix snapshot identity enrichment in commit/index snapshot action
- [ ] Add/extend tests in `test_create_document_snapshot_commit.py`:
  - [ ] `commit=None` path sets identity
  - [ ] `commit="HEAD"` path sets identity
  - [ ] nested paths preserve full `git_path` and filename extraction
- [ ] Implement identity enrichment in action using immutable replacement.

Code snippet:
```python
# freecad/diff_wb/application/actions/create_document_snapshot_commit.py
from dataclasses import replace
from pathlib import PurePosixPath

...
snapshot = SnapshotYamlSerializer.from_yaml(yaml_contents)
filename = PurePosixPath(fcstd_git_path).name
snapshot = replace(
    snapshot,
    git_path=fcstd_git_path,
    document_name=filename,
)
return Result.success(snapshot)
```

### Phase 3: Fix staging selection plumbing (presenter + view)
- [ ] Write presenter tests first:
  - [ ] `_on_staging_selected` stores keyed diff results when snapshot identity exists.
  - [ ] `on_node_selected(git_path, node_path)` resolves correct `DiffResult` and calls `show_properties(...)`.
  - [ ] fallback scenario: if path key is missing, properties are cleared predictably.
- [ ] Write view tests first:
  - [ ] `show_diff_trees` stores root `UserRole` selection key.
  - [ ] `_on_tree_item_clicked` forwards callback for valid root key + node path.
- [ ] Implement minimal plumbing fixes.

Code snippet (view):
```python
# freecad/diff_wb/ui/views/diff_panel_view.py
def show_diff_trees(self, diffs: list[DiffTreePresentation]) -> None:
    ...
    for diff in diffs:
        top_level_text = diff.git_path or "Unnamed Document"
        root_item = QTreeWidgetItem([top_level_text])

        # Stable key for presenter lookup (do not rely on display text)
        root_key = diff.git_path
        root_item.setData(0, Qt.ItemDataRole.UserRole, root_key)
        ...
```

Code snippet (presenter assertion-oriented behavior):
```python
# freecad/diff_wb/ui/presenters/diff_presenter.py
for result in all_diff_results:
    key = result.new_snapshot.git_path
    if key:
        self._diff_results_by_path[key] = result

...
def on_node_selected(self, git_path: str, node_path: str) -> None:
    diff_result = self._diff_results_by_path.get(git_path)
    if diff_result is None:
        self._view.show_properties([])
        return
    node_diff = diff_result.hierarchy.find_by_path(node_path)
    ...
```

### Phase 4: Regression hardening for Staging and Commit history modes
- [ ] Add tests covering both history contexts that depend on commit-snapshot action:
  - [ ] Staging root label uses git path.
  - [ ] Commit entry root label uses git path.
  - [ ] Clicking a child node updates properties for each context.
- [ ] Ensure ordering and keying behavior remains deterministic with multiple files.

Code snippet (presenter-level regression test sketch):
```python
def test_staging_selection_populates_diff_map_and_supports_property_click() -> None:
    fake_view, presenter = _create_test_presenter()
    presenter._ui_state.git_repository = GitRepository(name="r", absolute_path="/r")

    presenter._get_staged_file_paths.execute.return_value = Result.success(["a.FCStd"])
    presenter._create_commit_snapshot.execute.side_effect = [
        Result.success(snapshot_with_path("a.FCStd")),  # index
        Result.success(None),                            # head missing -> added diff path
    ]
    presenter._create_diff.execute.return_value = Result.success(diff_for("a.FCStd", node_path="Body"))

    presenter._on_staging_selected()
    presenter.on_node_selected("a.FCStd", "Body")

    assert fake_view.last_call("show_properties") is not None
```

### Phase 5: Manual testing documentation (required)
- [ ] Create `docs/manual-testing/staging_diff_viewer_tests.md` with explicit scenarios.
- [ ] Group manual tests by impacted behavior/file-location linkage.
- [ ] Ensure expected results include both root label and property panel updates.

Proposed manual test cases (to document in file):

#### For `ui/presenters/diff_presenter.py` + `ui/views/diff_panel_view.py`
1. **Staging root label uses git path**
   - Stage one FCStd document with valid snapshot.
   - Select **Staging**.
   - Expected: top-level row displays `relative/path/to/file.FCStd`, not `Unnamed Document`.

2. **Staging node click updates property panel**
   - In Staging tree, click changed node (e.g., `Body/Pad`).
   - Expected: property tree populates with grouped properties and diff colors.

3. **Multiple staged docs keep independent selection mapping**
   - Stage two FCStd files.
   - Click node under first, then second.
   - Expected: property panel updates to correct document each time (no stale data).

#### For `application/actions/create_document_snapshot_commit.py`
4. **Commit history mode label and selection still work**
   - Select a commit that changed FCStd snapshot(s).
   - Expected: root rows use git paths; clicking nodes updates properties.

5. **Missing old snapshot warning path remains clickable behavior-safe**
   - Use a case with warning-only flat row.
   - Expected: warning row shown; no crashes on clicks; property panel remains stable.

## Test Strategy
- **Unit tests (primary):**
  - Action-level identity enrichment from input git path.
  - Presenter staging orchestration + selection lookup.
  - View metadata storage/click callback wiring.
- **Integration tests (non-FreeCAD app actions only):**
  - Existing app-action integration where feasible (no FreeCADGui dependency).
- **Manual tests (FreeCAD GUI):**
  - Validate end-to-end behavior in Diff Workbench Staging and Commit selections.

## Findings & Notes
- Root causes identified:
  1. Snapshot identity fields not populated in commit/index deserialization path.
  2. Staging presenter map cannot key diff results when `git_path` is empty.
  3. View callback chain relies on root `UserRole` key, which becomes empty in affected cases.
- This fix is low-risk and localized; no domain algorithm changes required.
