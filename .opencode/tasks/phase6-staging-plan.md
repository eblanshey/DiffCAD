# Task: Phase 6 - Adding Files to Staging

## Goal

Implement the ability to stage FreeCAD documents to git by:
1. Adding a "+ Add" button to each document's top-level tree item in the Working Tree view
2. Persisting snapshots to `.snapshots` directories and running `git add` when the button is clicked

## Context

This is Phase 6 of the MVP implementation plan (see `docs/MVP-Implementation.md`). Phase 5 implemented working tree diff display. Phase 6 extends this to allow staging changes.

**Key constraints:**
- Domain layer must remain FreeCAD-independent (pure Python)
- All actions return `Result` type with `is_success`, `data`, `message`
- Dependencies flow inward (UI → Application → Domain → Infrastructure)

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Put `get_snapshot_directory_for_document` in `domain/snapshots` | Self-contained path logic that doesn't depend on git; reusable across phases; easier to test | Putting in GitService - rejected as couples git domain to snapshot path logic |
| `get_snapshot_directory_for_document` takes `str` argument | Consistent with codebase convention (GitRepository uses absolute_path: str); pure function, no git knowledge needed | Taking Path object - rejected as inconsistent with existing patterns |
| Use SnapshotYamlSerializer.to_yaml directly in action | The serializer already handles the format; no need for additional abstraction | Creating a separate persistence service - rejected as overkill for MVP |
| Store DiffResults keyed by git_path in presenter | Needed to retrieve correct snapshot when "+ Add" is clicked for a specific document | Storing in UIState - rejected since it's ephemeral view state, not app state |
| "+ Add" button disabled when no changes | Prevents staging unchanged documents; clear UX signal | Always enabled with no-op - rejected as confusing UX |

## Architecture Impact

**Modules affected:**
- `domain/snapshots/__init__.py` - Add `get_snapshot_directory_for_document` function
- `domain/git/ports.py` - Add `stage_files` to GitPort protocol
- `domain/git/git_service.py` - Add `stage_files` method only
- `infrastructure/git/git_port_adapter.py` - Implement `stage_files` via `git add`
- `application/actions/stage_documents.py` - NEW action for staging
- `application/di/container.py` - Wire new action
- `ui/presenters/diff_presenter.py` - Add staging callback, store diff results
- `ui/protocols/diff_view.py` - Add `set_add_button_callback` to protocol
- `ui/views/diff_panel_view.py` - Add "+ Add" buttons to tree items

**Public interfaces:**
- `get_snapshot_directory_for_document(document_path: str) -> Path` - NEW public function in `domain/snapshots`
- `GitService.stage_files(repo, paths) -> bool` - NEW public method
- `StageDocumentsAction.execute(repo, snapshots) -> Result` - NEW action
- `DiffView.set_add_button_callback(callback) -> None` - NEW protocol method

## FreeCAD Dependency

- [x] No FreeCAD required (pure code for GitPort/GitService/StageDocuments action)
- [ ] FreeCAD required (DiffPresenter and DiffPanelView use FreeCAD widgets)

**Note:** Tests for actions will use fakes/mocks. UI component testing is manual only.

## Implementation Plan

### Phase 1: Domain Layer - Snapshot path function and GitPort updates

**Task 1.1: Write tests for `get_snapshot_directory_for_document`** - ✅ Complete

Create `tests/unit/domain/snapshots/test_snapshot_path.py`:

```python
from pathlib import Path
from freecad.diff_wb.domain.snapshots import get_snapshot_directory_for_document

def test_get_snapshot_directory_returns_correct_path():
    # Given a path "/home/user/project/path/to/doc.FCStd"
    # When get_snapshot_directory_for_document is called
    # Then it returns Path("/home/user/project/path/to/.snapshots")

def test_get_snapshot_directory_strips_filename():
    # Given "path/to/mydoc.FCStd"
    # When get_snapshot_directory_for_document is called
    # Then the result is "path/to/.snapshots" not "path/to/mydoc.FCStd/.snapshots"

def test_get_snapshot_directory_file_in_root():
    # Given "mydoc.FCStd" (no directory component)
    # When get_snapshot_directory_for_document is called
    # Then it returns ".snapshots" (in current directory)
```

**Task 1.2: Add `get_snapshot_directory_for_document` to `domain/snapshots`** - ✅ Complete

In `domain/snapshots/__init__.py`, add:

```python
from pathlib import Path

def get_snapshot_directory_for_document(document_path: str) -> Path:
    """Get the .snapshots directory for a given document file path.

    The snapshot directory is alongside the file in a hidden .snapshots directory.
    Example: /path/to/mydoc.FCStd -> /path/to/.snapshots

    Args:
        document_path: String path to the document file (FCStd or similar).

    Returns:
        Path to the .snapshots directory.
    """
    return Path(document_path).parent / ".snapshots"
```

Also update `__all__` in `domain/snapshots/__init__.py` to include `get_snapshot_directory_for_document`.

**Task 1.3: Update GitPort protocol** - ✅ Complete

In `domain/git/ports.py`, add to `GitPort`:

```python
def stage_files(self, git_root: str, paths: list[str]) -> bool:
    """Stage files in the git repository.

    Args:
        git_root: Absolute path to git repository root.
        paths: List of relative paths (from git root) to stage.

    Returns:
        True if staging succeeded, False otherwise.
    """
    ...
```

**Task 1.4: Update GitService** - ✅ Complete

In `domain/git/git_service.py`, add:

```python
def stage_files(self, repo: GitRepository, paths: list[str]) -> bool:
    """Stage files in the git repository.

    Args:
        repo: GitRepository to stage files in.
        paths: List of relative paths (from git root) to stage.

    Returns:
        True if staging succeeded, False otherwise.
    """
    return self._git_port.stage_files(repo.absolute_path, paths)
```

**Task 1.5: Update GitPortAdapter** - ✅ Complete

In `infrastructure/git/git_port_adapter.py`, add:

```python
def stage_files(self, git_root: str, paths: list[str]) -> bool:
    """Stage files using git add.

    Args:
        git_root: Absolute path to git repository root.
        paths: List of relative paths to stage.

    Returns:
        True if git add succeeded for all files, False otherwise.
    """
    if not paths:
        return True

    try:
        # Use git add with -v for verbose output
        result = subprocess.run(
            ["git", "add", "-v"] + paths,
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line:
                    Log.info(f"Staged: {line}")
            return True
        Log.warning(f"Git add failed: {result.stderr.strip()}")
        return False
    except subprocess.TimeoutExpired:
        Log.warning("Git add command timed out")
        return False
    except FileNotFoundError:
        Log.warning("Git command not found")
        return False
```

### Phase 2: Application Layer - StageDocuments action

**Task 2.1: Write tests for StageDocumentsAction** - ✅ Complete

Create `tests/unit/application/actions/test_stage_documents.py`:

```python
def test_stage_documents_empty_list_returns_success():
    # Given an empty list of snapshots
    # When execute is called
    # Then Result.success(True) is returned immediately (no-op)

def test_stage_documents_creates_snapshot_yaml():
    # Given a mock GitService that returns correct snapshot directory
    # And a mock SnapshotYamlSerializer
    # When execute is called with repo and list of snapshots
    # Then SnapshotYamlSerializer.to_yaml is called with correct path

def test_stage_documents_stages_both_fcstd_and_yaml():
    # Given snapshots with git_path "path/to/mydoc.FCStd"
    # When execute is called
    # Then git_service.stage_files is called with ["path/to/mydoc.FCStd", "path/to/.snapshots/mydoc.yaml"]

def test_stage_documents_returns_success_on_success():
    # Given all operations succeed
    # When execute is called
    # Then Result.success is returned

def test_stage_documents_returns_failure_on_yaml_error():
    # Given SnapshotYamlSerializer.to_yaml raises
    # When execute is called
    # Then Result.failure is returned
```

**Task 2.2: Create StageDocuments action** - ✅ Complete

Create `application/actions/stage_documents.py`:

```python
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Application action for staging documents to git."""

import os
from pathlib import Path

from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ...domain.snapshots import get_snapshot_directory
from ...domain.snapshots.models import Snapshot
from ...infrastructure.persistence.snapshot_yaml import SnapshotYamlSerializer
from ...utils import Log
from .result_models import Result


__all__ = ["StageDocumentsAction"]


class StageDocumentsAction:
    """Stage documents to git by persisting snapshots and running git add."""

    def __init__(self, git_service: GitService) -> None:
        self._git_service = git_service

    def execute(self, repo: GitRepository, snapshots: list[Snapshot]) -> Result:
        """Stage documents by persisting snapshots and adding to git.

        For each snapshot:
        1. Determine the full file path (repo.absolute_path + git_path)
        2. Determine the snapshot directory using get_snapshot_directory
        3. Persist snapshot YAML to snapshot_dir/snapshot_name.yaml
        4. Collect both the FCStd path and YAML path for staging

        Args:
            repo: GitRepository containing the documents.
            snapshots: List of Snapshots to stage.

        Returns:
            Result containing True on success, or failure message on error.
        """
        if not snapshots:
            return Result.success(True)

        all_paths_to_stage: list[str] = []

        for snapshot in snapshots:
            git_path = snapshot.git_path
            if not git_path:
                Log.warning(f"Snapshot has no git_path, cannot stage: {snapshot.document_name}")
                continue

            # Compute full path to the FCStd file
            fcstd_path = Path(repo.absolute_path) / git_path

            # Get the snapshot directory using the pure function
            snapshot_dir = get_snapshot_directory(fcstd_path)

            # Create snapshot directory if it doesn't exist
            try:
                snapshot_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                Log.exception(f"Failed to create snapshot directory {snapshot_dir}: {e}")
                return Result.failure(f"Failed to create snapshot directory: {e}")

            # Determine YAML filename (use document name without extension)
            doc_name = os.path.splitext(os.path.basename(git_path))[0]
            yaml_filename = f"{doc_name}.yaml"
            yaml_path = snapshot_dir / yaml_filename

            # Persist snapshot to YAML
            try:
                SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
                Log.info(f"Persisted snapshot to {yaml_path}")
            except Exception as e:
                Log.exception(f"Failed to persist snapshot for {git_path}: {e}")
                return Result.failure(f"Failed to persist snapshot: {e}")

            # Collect paths to stage (relative to git root)
            all_paths_to_stage.append(git_path)  # The FCStd file
            # The YAML path is absolute, convert to relative
            yaml_relative = str(yaml_path)[len(repo.absolute_path):].lstrip("/")
            all_paths_to_stage.append(yaml_relative)

        # Stage all files
        if all_paths_to_stage:
            success = self._git_service.stage_files(repo, all_paths_to_stage)
            if not success:
                return Result.failure("Failed to stage one or more files")
            Log.info(f"Staged {len(all_paths_to_stage)} files")

        return Result.success(True)
```

**Task 2.3: Update ApplicationContainer** - ✅ Complete

In `application/di/container.py`:

1. Add import:
```python
from ..actions.stage_documents import StageDocumentsAction
```

2. Add field to `ApplicationContainer` dataclass:
```python
stage_documents_action: StageDocumentsAction
```

3. Add to `create_application_container`:
```python
stage_documents_action=StageDocumentsAction(git_service=git_service),
```

### Phase 3: UI Layer - Add button and wiring

**Task 3.1: Update DiffView protocol** - ✅ Complete

In `ui/protocols/diff_view.py`, add:

```python
def set_add_button_callback(self, callback: Callable[[str], None]) -> None:
    """Set the callback for when the '+ Add' button is clicked.

    Args:
        callback: A callable that receives the git_path (str) of the
                  document whose '+ Add' button was clicked.
    """
    ...
```

**Task 3.2: Update DiffPresenter** - ✅ Complete

In `ui/presenters/diff_presenter.py`:

1. Add imports:
```python
from ...application.actions.stage_documents import StageDocumentsAction
```

2. Update constructor to inject action:
```python
def __init__(
    self,
    view: DiffView,
    ui_state: UIState,
    get_eligible_docs_action: GetOpenEligibleDocumentsAction,
    create_working_snapshot_action: CreateDocumentSnapshotForWorkingTreeAction,
    create_commit_snapshot_action: CreateDocumentSnapshotForCommitAction,
    create_diff_action: CreateDiffAction,
    stage_documents_action: StageDocumentsAction,  # NEW
) -> None:
    ...
    self._stage_documents = stage_documents_action
    self._diff_results_by_path: dict[str, DiffResult] = {}  # NEW: store for later
```

3. Update `_on_working_tree_selected` to store diff results:
```python
def _on_working_tree_selected(self) -> None:
    ...
    # Store diff results keyed by git_path for later use by add button
    self._diff_results_by_path.clear()
    for diff_result in all_diff_results:
        git_path = diff_result.new_snapshot.git_path
        if git_path:
            self._diff_results_by_path[git_path] = diff_result  # Store single result

    if all_diff_results:
        self.present_diffs(all_diff_results)
    ...
```

4. Add new method for handling add button click:
```python
def on_add_button_clicked(self, git_path: str) -> None:
    """Handle '+ Add' button click for staging.

    Args:
        git_path: The git_path of the document to stage.
    """
    repo = self._ui_state.git_repository
    if repo is None:
        Log.warning("No git repository detected")
        return

    # Look up the DiffResult for this git_path
    diff_result = self._diff_results_by_path.get(git_path)
    if not diff_result:
        Log.warning(f"No diff result found for {git_path}")
        return

    # Get the working tree snapshot (new_snapshot) from the diff
    # Since we're in working tree view, old_snapshot may be None
    working_snapshot = diff_result.new_snapshot

    # Stage the document
    result = self._stage_documents.execute(repo, [working_snapshot])
    if not result.is_success:
        Log.warning(f"Failed to stage document: {result.message}")
        return

    Log.info(f"Successfully staged {git_path}")

    # Recalculate diff (Working Tree -> Commit None means same snapshot)
    # This will refresh the view to show no changes
    self._on_working_tree_selected()
```

**Task 3.3: Update DiffPanelView** - ✅ Complete

In `ui/views/diff_panel_view.py`:

1. Add callback instance variable:
```python
self._on_add_button_callback: Callable[[str], None] | None = None
```

2. Add method to set callback:
```python
def set_add_button_callback(self, callback: Callable[[str], None]) -> None:
    self._on_add_button_callback = callback
```

3. Update `show_diff_trees` to add buttons. In the method, after creating each root_item:
```python
# Create a horizontal layout for the top-level item with button
# This requires restructuring - we'll add a custom widget

# Instead of creating QTreeWidgetItem directly, we create a container widget
# with label and button, then set it as the tree item's widget
```

The implementation in Qt for adding a button to a tree item requires using `setItemWidget`. Here's the approach:

```python
def show_diff_trees(self, diffs: list[DiffTreePresentation]) -> None:
    ...
    for diff in diffs:
        # Build top-level text
        top_level_text = diff.git_path or "Unnamed Document"
        if diff.warnings:
            warning_text = " ⚠️ ".join(diff.warnings)
            top_level_text = f"{top_level_text} ⚠️"

        # Create root item
        root_item = QTreeWidgetItem([top_level_text])
        if diff.warnings:
            root_item.setToolTip(0, warning_text)

        # Check if document has changes
        has_changes = any(node.has_changes for node in diff.nodes)

        # Create "+ Add" button
        add_button = QPushButton("+ Add")
        add_button.setEnabled(has_changes)
        add_button.setFixedWidth(60)
        add_button.clicked.connect(lambda checked, gp=diff.git_path: self._on_add_button_clicked(gp))

        # Create container widget with layout
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.addWidget(QLabel(top_level_text))
        layout.addStretch()
        layout.addWidget(add_button)

        # Set the widget on the tree item
        self.tree_widget.addTopLevelItem(root_item)
        self.tree_widget.setItemWidget(root_item, 0, container)
        ...
```

4. Add internal callback handler:
```python
def _on_add_button_clicked(self, git_path: str) -> None:
    """Handle '+ Add' button click by invoking the callback."""
    if self._on_add_button_callback:
        self._on_add_button_callback(git_path)
```

**Task 3.4: Update DiffPresenter initialization in UI composer** - ✅ Complete

In `ui/composer.py`, update the `compose_and_register_ui()` function (line 55):

1. Add import at top of function scope (if not already present):
```python
from ..application.actions.stage_documents import StageDocumentsAction
```

2. Update DiffPresenter instantiation to include the new action:
```python
diff_presenter = DiffPresenter(
    view=view,
    ui_state=ui_state,
    get_eligible_docs_action=container.get_open_eligible_docs_action,
    create_working_snapshot_action=container.create_working_snapshot_action,
    create_commit_snapshot_action=container.create_commit_snapshot_action,
    create_diff_action=container.create_diff_action,
    stage_documents_action=container.stage_documents_action,  # NEW
)
```

Note: The `stage_documents_action` must first be added to `ApplicationContainer` (Phase 2, Task 2.3).

### Phase 4: Manual Testing Documentation - ⏭️ Skipped (per user request)

**Task 4.1: Create manual test cases** - ⏭️ Skipped (per user request)

Create `docs/manual-testing/phase6-staging.md`:

```markdown
# Phase 6 Manual Testing: Staging Documents

## Test Setup
1. Open FreeCAD with a project in a git repository
2. Activate the Diff Workbench
3. Open a FreeCAD document that is inside the git repository

## Test Cases

### TC1: "+ Add" Button Visibility
**Steps:**
1. Select "Working Tree" from the history list
2. Observe the tree view

**Expected:**
- Each top-level document item has a "+ Add" button aligned to the right
- The button is enabled (clickable)

### TC2: "+ Add" Button Disabled for Unchanged Documents
**Prerequisites:** A document with no changes
**Steps:**
1. Make changes to a document, stage them, and commit
2. Open the document again (now it should have no working tree changes)
3. Select "Working Tree" from history

**Expected:**
- The "+ Add" button for that document is disabled (grayed out)

### TC3: Stage Single Document
**Steps:**
1. Make changes to a document (e.g., edit a sketch)
2. Select "Working Tree" from history
3. Click "+ Add" for that document

**Expected:**
- A `.snapshots` directory is created in the same directory as the document
- A YAML snapshot file is created in `.snapshots/`
- The document and YAML file are staged (`git status` shows them)

### TC4: Verify Diff Clears After Staging
**Steps:**
1. Make changes to a document
2. Select "Working Tree" - observe diff shows changes
3. Click "+ Add"
4. Observe the diff view again

**Expected:**
- The diff now shows no changes for the staged document (working tree matches staged version)

### TC5: Stage Multiple Documents
**Steps:**
1. Open two documents in the git repository
2. Make changes to both documents
3. Select "Working Tree" from history
4. Click "+ Add" for one document
5. Click "+ Add" for the other

**Expected:**
- Both documents' snapshots are persisted
- Both documents (and their YAML files) are staged
```

## Test Strategy

### Unit Tests

**Files to create:**
- `tests/unit/domain/snapshots/test_snapshot_path.py` - Tests for `get_snapshot_directory_for_document`
- `tests/unit/domain/git/test_git_service.py` - Tests for `stage_files` only
- `tests/unit/application/actions/test_stage_documents.py` - Tests for StageDocumentsAction

**Run with:** `task test`

### Integration Tests

None - manual testing covered by Phase 4 test cases.

## Findings & Notes

### Snapshot Directory Calculation

The `get_snapshot_directory_for_document` function in `domain/snapshots` takes a `str` path to the FCStd file and returns the `.snapshots` directory alongside it.

Example:
- FCStd path: `/home/user/project/models/box.FCStd`
- `get_snapshot_directory_for_document("/home/user/project/models/box.FCStd")` returns `Path("/home/user/project/models/.snapshots")`
- Snapshot file: `/home/user/project/models/.snapshots/box.yaml`

This is a pure function with no git dependencies, making it reusable in Phase 7 when loading snapshots from the index.

### Error Handling Strategy

All error conditions log warnings but do not crash:
- If a snapshot has no `git_path`, log warning and skip that document
- If snapshot directory creation fails, log exception and return failure Result
- If YAML serialization fails, log exception and return failure Result
- If `git add` fails, log warning and return failure Result

No submodule handling required for MVP.

### GitPort.stage_files Design

The `stage_files` method returns `bool` (success/failure) rather than a more detailed result. This is intentional for MVP simplicity - detailed error handling (e.g., which specific file failed) can be added later if needed. Warnings are logged for debugging.

### Qt Button Implementation Note

Adding buttons to QTreeWidget items requires using `setItemWidget`. The button is a child of the tree widget, not the item, which means:
1. The button must be explicitly shown/hidden when the item is expanded/collapsed
2. Button state should be set before adding to the tree
3. The git_path must be captured in the button's clicked handler via closure or default argument (`gp=diff.git_path`)
4. When the tree is refreshed after staging, old widgets are replaced entirely
