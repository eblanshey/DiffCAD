# Task: Phase 9 - Diffs for Commits

## Goal
When a user selects a commit from the history list, display diffs between that commit and its parent for all FCStd files that changed between them. This completes the commit-based diffing flow alongside Working Tree and Staging.

## Context
Phases 1-8 have implemented git repository detection, commit listing, working tree diffs, staging diffs, and commit creation. Phase 9 completes the cycle by enabling users to inspect historical diffs between any two consecutive commits. The implementation reuses existing domain logic: `CreateDocumentSnapshotForCommitAction` (already supports any commit ref), `CreateDiffAction`, and `present_diffs()` with missing snapshot handling.

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Use `git diff-tree --root --no-commit-id --name-only -r <commit>` to get changed files | `--root` ensures root commits also return files; standard git command for listing files changed in a single commit | `git diff --name-only <parent>..<commit>` — requires computing parent first, more complex |
| Parent ref: `commit_hash + "^"` | Git's `^` notation works for all standard refs (hash, HEAD, HEAD~1); shorter than `~1` | `~1` — equivalent but `^` is more common in commit messages |
| Root commits: `old_snapshot=None` (same as Working Tree) | `--root` flag makes diff-tree return all files in a root commit; parent ref `hash^` fails for root commits, so `CreateDocumentSnapshotForCommitAction` returns None for parent snapshot | Skip root commits entirely — would lose data |
| Union commit_paths and parent_paths | Shows ALL files that differ between two commits, including files that existed in only one | Intersection only — would miss new files added in the commit |
| Reuse `present_diffs()` with `missing_snapshot_paths` | Existing method already handles flat warning items for missing snapshots; avoids duplication | New method — unnecessary code duplication |
| Extract per-file diff computation to `_compute_commit_diffs()` | Reduces cognitive load in `_on_commit_selected()`, follows existing pattern from `_compute_staged_diffs()` | Inline all logic in `_on_commit_selected()` — too long, hard to test |

## Architecture Impact

### New Files
| File | Responsibility |
|------|---------------|
| `freecad/diff_wb/application/actions/get_committed_file_paths.py` | `GetCommittedFilePathsAction` — application action for querying changed FCStd files in a commit |
| `tests/unit/application/actions/test_get_committed_file_paths.py` | Unit tests for `GetCommittedFilePathsAction` |
| `tests/unit/infrastructure/git/test_get_committed_files.py` | Unit tests for `GitPortAdapter.get_committed_files()` |
| `tests/unit/domain/git/test_git_service_committed_files.py` | Unit tests for `GitService.get_committed_files()` |
| `tests/unit/ui/presenters/test_diff_presenter_commit.py` | Unit tests for `_on_commit_selected()` orchestration |

### Modified Files
| File | Changes |
|------|---------|
| `freecad/diff_wb/domain/git/ports.py` | Add `get_committed_files(git_root, commit) -> list[str]` to `GitPort` protocol; update file responsibility comment |
| `freecad/diff_wb/infrastructure/git/git_port_adapter.py` | Implement `get_committed_files()` using `git diff-tree --root`; update file responsibility comment |
| `freecad/diff_wb/domain/git/git_service.py` | Add `get_committed_files(repo, commit) -> list[str]` method; update file responsibility comment |
| `freecad/diff_wb/application/di/container.py` | Wire `GetCommittedFilePathsAction` into `ApplicationContainer` |
| `freecad/diff_wb/ui/presenters/diff_presenter.py` | Implement `_on_commit_selected()` and `_compute_commit_diffs()`; add `get_committed_file_paths_action` dependency |
| `freecad/diff_wb/ui/composer.py` | Pass `get_committed_file_paths_action` to `DiffPresenter` |
| `tests/fakes/fake_git_port.py` | Add `get_committed_files()`, `set_committed_files()`, and `_committed_files` dict to fake |

## FreeCAD Dependency
- [x] No FreeCAD required for domain, application, and infrastructure layers (git CLI via subprocess, not FreeCAD API)
- [x] Presenter integration test requires FreeCAD runtime (UI event handling)

## Implementation Plan

### Phase 9.1 — FakeGitPort + Domain Port + Adapter

**Goal**: Add `get_committed_files` to the GitPort protocol, implement it in the adapter, and update FakeGitPort so tests can mock committed file paths.

- [x] Add `_committed_files: dict[tuple[str, str], list[str]]` to `FakeGitPort.__init__()`
  - Key is `(git_root, commit)` tuple, value is list of FCStd paths
  - Added `"""FakeGitPort"""` docstring update to document the new attribute

- [x] Add `set_committed_files(root_path, commit, paths)` helper method
  - Sets the committed file paths for a specific commit in a repo

- [x] Add `get_committed_files(git_root, commit)` method
  - Returns `self._committed_files.get((git_root, commit), [])`

- [x] **Write tests first** for `GitPortAdapter.get_committed_files()` in `tests/unit/infrastructure/git/test_get_committed_files.py`
  - Test successful parsing of `git diff-tree` output returning FCStd files
  - Test filtering: only `.FCStd` files returned
  - Test with `HEAD`, `HEAD~1`, short hash formats
  - Test with `--root` flag for root commit (files listed correctly)
  - Test empty result (commit with no FCStd changes)
  - Test subprocess timeout → return empty list
  - Test git not found → return empty list
  - Test non-zero exit code → return empty list

- [x] Add `get_committed_files(git_root: str, commit: str) -> list[str]` to `GitPort` protocol in `domain/git/ports.py`
  - Returns list of relative FCStd file paths changed in the given commit
  - The `commit` argument accepts any git ref: hash, `HEAD`, `HEAD~1`, etc.
  - Updated file responsibility comment at top of `ports.py`

- [x] Implement `get_committed_files()` in `GitPortAdapter`
  - Use `git diff-tree --root --no-commit-id --name-only -r <commit>` command
  - **`--root` flag is critical**: without it, root commits return no files
  - Filter results to only `.FCStd` files
  - Return relative paths
  - Handle errors gracefully (return empty list)
  - Follow the same error handling pattern as existing methods: catch `(subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError, OSError)`
  - Updated file responsibility comment at top of `git_port_adapter.py`

- [x] Add `get_committed_files(repo: GitRepository, commit: str) -> list[str]` to `GitService`
  - Thin wrapper: `self._git_port.get_committed_files(repo.absolute_path, commit)`
  - Updated file responsibility comment at top of `git_service.py`

### Phase 9.2 — Application Action

**Goal**: Create the `GetCommittedFilePathsAction` and wire it in the container.

- [x] **Write tests first** for `GetCommittedFilePathsAction` in `tests/unit/application/actions/test_get_committed_file_paths.py`
  - Test `execute(repo, commit_hash)` returns list of paths
  - Test empty path list when commit has no FCStd changes
  - Test dependency injection (accepts GitService)

- [x] Create `freecad/diff_wb/application/actions/get_committed_file_paths.py`
  - File responsibility comment at top: `File responsibility: Application action for getting FCStd file paths changed in a commit.`
  - `GetCommittedFilePathsAction` class with `execute(repo, commit) -> Result[list[str]]`
  - `__all__ = ["GetCommittedFilePathsAction"]` at bottom
  - Follows the same pattern as `GetStagedFilePathsAction`:
    ```python
    class GetCommittedFilePathsAction:
        def __init__(self, git_service: GitService) -> None: ...
        def execute(self, repo: GitRepository, commit: str) -> Result:
            paths = self._git_service.get_committed_files(repo, commit)
            return Result.success(paths)
    ```

- [x] Wire action in `container.py`
  - Add `get_committed_file_paths_action: GetCommittedFilePathsAction` to `ApplicationContainer` dataclass
  - Import `GetCommittedFilePathsAction` at top
  - Instantiate: `get_committed_file_paths_action = GetCommittedFilePathsAction(git_service=git_service)`
  - Pass in the returned container

### Phase 9.3 — Presenter Implementation

**Goal**: Implement `_on_commit_selected()` and `_compute_commit_diffs()` in `DiffPresenter` to orchestrate commit diff computation.

- [x] **Write tests first** for `_on_commit_selected()` in `tests/unit/ui/presenters/test_diff_presenter_commit.py`
  - Test that it calls `GetCommittedFilePathsAction` for both commit and parent
  - Test that it unions the path lists
  - Test that it creates snapshots and diffs for each path
  - Test case 1: both snapshots exist → diff created
  - Test case 2: commit snapshot exists, parent is None → diff with `old_snapshot=None`
  - Test case 3: parent exists, commit is None → skip (no changes possible)
  - Test case 4: both None → skip
  - Test case 5: parent snapshot missing due to YAML extraction failure → diff with warning (same as case 2, but triggered by extractor error)
  - Test `present_diffs()` is called with results and missing_snapshot_paths
  - Test no git repository → early return with warning log
  - Test root commit (parent ref fails gracefully, uses None for parent snapshot)

- [x] Modify `DiffPresenter.__init__()` to accept `get_committed_file_paths_action` parameter
  - Add to constructor signature
  - Store as `self._get_committed_file_paths`
  - Add import: `from ...application.actions.get_committed_file_paths import GetCommittedFilePathsAction`

- [x] Implement `_compute_commit_diffs(repo, commit_hash)` private method
  - Extracted from `_on_commit_selected()` to reduce complexity and improve testability
  - Follows the same pattern as `_compute_staged_diffs()` — returns `tuple[list[DiffResult], list[str]]`
  - For each path in `all_paths`:
    - `CreateDocumentSnapshotForCommitAction.execute(repo, commit_hash, path)` → `commit_snapshot`
    - `CreateDocumentSnapshotForCommitAction.execute(repo, commit_hash + "^", path)` → `parent_snapshot`
    - Handle four cases:
      1. Both exist: `CreateDiffAction.execute(parent_snapshot, commit_snapshot)` → add to results
      2. Commit exists, parent is None: `CreateDiffAction.execute(None, commit_snapshot)` → add to results + track missing
      3. Parent exists, commit is None: skip (no data to compare)
      4. Both None: skip (no data to compare)

**Code snippet — _compute_commit_diffs implementation:**
```python
def _compute_commit_diffs(
    self, repo: GitRepository, commit_hash: str
) -> tuple[list[DiffResult], list[str]]:
    """Compute diffs for files changed in a commit vs its parent.

    For each FCStd file changed between the commit and its parent:
    1. Extract snapshots from both commits
    2. Compute diff between snapshots
    3. Track paths where parent snapshot is missing

    Args:
        repo: GitRepository containing the documents.
        commit_hash: The commit hash to compute diffs for.

    Returns:
        Tuple of (list of DiffResult, list of paths with missing parent snapshots).
    """
    all_diff_results: list[DiffResult] = []
    missing_snapshot_paths: list[str] = []

    commit_result = self._get_committed_file_paths.execute(repo, commit_hash)
    parent_result = self._get_committed_file_paths.execute(repo, commit_hash + "^")

    commit_paths = set(commit_result.data) if commit_result.is_success else set()
    parent_paths = set(parent_result.data) if parent_result.is_success else set()
    all_paths = commit_paths | parent_paths

    for git_path in all_paths:
        commit_snap_result = self._create_commit_snapshot.execute(repo, commit_hash, git_path)
        parent_snap_result = self._create_commit_snapshot.execute(repo, commit_hash + "^", git_path)

        commit_snapshot = commit_snap_result.data if commit_snap_result.is_success else None
        parent_snapshot = parent_snap_result.data if parent_snap_result.is_success else None

        if commit_snapshot is not None and parent_snapshot is not None:
            # Both snapshots exist - compute diff
            diff_result = self._create_diff.execute(parent_snapshot, commit_snapshot)
            if diff_result.is_success and diff_result.data is not None:
                all_diff_results.append(diff_result.data)
        elif commit_snapshot is not None and parent_snapshot is None:
            # Parent snapshot missing (extraction failed, no YAML, etc.) - show with warning
            diff_result = self._create_diff.execute(None, commit_snapshot)
            if diff_result.is_success and diff_result.data is not None:
                all_diff_results.append(diff_result.data)
            missing_snapshot_paths.append(git_path)
        # Skip cases where commit_snapshot is None (no data to compare)

    return all_diff_results, missing_snapshot_paths
```

- [x] Implement `_on_commit_selected(commit_hash: str)` in `DiffPresenter`
  - Get repo from `self._ui_state.git_repository`, early return if None
  - Call `_compute_commit_diffs(repo, commit_hash)` → `(all_diff_results, missing_paths)`
  - Store diff results in `self._diff_results_by_path`
  - Call `present_diffs(diff_results, missing_snapshot_paths=missing_paths)`

**Code snippet — _on_commit_selected implementation:**
```python
def _on_commit_selected(self, commit_hash: str) -> None:
    """Handle commit item selection.

    Delegates per-file diff computation to _compute_commit_diffs(),
    then stores results and presents them to the view.
    """
    repo = self._ui_state.git_repository
    if repo is None:
        Log.warning("No git repository detected")
        return

    # Compute diffs for all changed files (extracted for testability)
    all_diff_results, missing_paths = self._compute_commit_diffs(repo, commit_hash)

    # Store diff results keyed by git_path for later use
    self._diff_results_by_path.clear()
    for result in all_diff_results:
        git_path = result.new_snapshot.git_path
        if git_path:
            self._diff_results_by_path[git_path] = result

    if all_diff_results or missing_paths:
        self.present_diffs(all_diff_results, set(), missing_paths)
    else:
        Log.info(f"No FCStd files changed in commit {commit_hash}")
        self._view.show_diff_trees([])
```

- [x] Update `composer.py` to pass `get_committed_file_paths_action` to `DiffPresenter`

### Phase 9.4 — Verification

- [x] Run `task test` — all unit tests pass
- [x] Run `task check` — ruff/linting passes
- [x] Manual testing with `run_with_freecad.sh` — verify commit selection works end-to-end

## Test Strategy

### Unit Tests (No FreeCAD)
- `GetCommittedFilePathsAction.execute()` — success/failure with fake GitService
- `GitPortAdapter.get_committed_files()` — subprocess mocking for git diff-tree
- `GitService.get_committed_files()` — verifies delegation to port
- `DiffPresenter._compute_commit_diffs()` — full per-file diff orchestration with mocked actions
  - All four snapshot combination cases
  - Parent snapshot missing due to YAML extraction failure
- `DiffPresenter._on_commit_selected()` — orchestration with mocked `_compute_commit_diffs()`
  - Missing git repository guard
  - Empty path list handling
  - Root commit handling (parent ref fails)

### Integration Tests
- Not applicable for Phase 9 (no FreeCAD-dependent runtime behavior beyond what's already tested in phases 5-8)

## Findings & Notes

- `CreateDocumentSnapshotForCommitAction` already supports any commit ref string (hash, HEAD, HEAD~1, etc.) — no changes needed to this action
- `CreateDiffAction` already handles `old_snapshot=None` — same behavior as Working Tree flow
- `present_diffs()` already handles `missing_snapshot_paths` parameter — creates flat warning items
- The `_on_commit_selected()` method is currently a stub (line 275-277 in `diff_presenter.py`) — exactly where implementation goes
- The `HistorySelection` model already supports `item_kind="COMMIT"` with `commit_hash` — no view model changes needed
- `git diff-tree --root --no-commit-id --name-only -r <commit>` is the correct command:
  - `--root` includes root commits (diff against empty tree)
  - `--no-commit-id` suppresses the commit hash output line
  - `--name-only` shows only file paths, no diffs
  - `-r` recurses into subdirectories
- For merge commits, `^` selects the first parent — acceptable for MVP
