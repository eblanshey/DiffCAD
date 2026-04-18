# Task: Enable Stage Button for Git-Tracked Changes

## Goal
Enable the "Stage" button when either:
1. There are diff changes (current behavior), OR
2. The document file itself has git-tracked changes (modified or untracked files)

## Context
Currently, when switching to "Working Tree", the Stage button compares the snapshot to itself, showing no diff changes. However, if the file has been modified in the working directory (tracked by git), the button should still be enabled to allow staging.

This addresses the missing feature where git-tracked changes (outside of FreeCAD's internal diff) should also enable the staging capability.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Add `get_dirty_paths(git_root)` to GitPort | Single git status call returns ALL dirty files; efficient for multiple documents | Per-document `is_path_dirty()` calls - rejected as inefficient (N git calls vs 1) |
| Filter for modified/untracked only | Only these can be staged via `git add`; matches user expectation of "dirty" | Include staged-only changes - rejected as already in staging area, not "dirty" |
| Create `GetDirtyDocumentsAction` | Batch operation returning dirty status for all eligible documents at once | Per-document actions - rejected as inefficient |
| Add `is_git_dirty` to DiffTreePresentation | Makes dirty state explicit in presentation model; view can make enable decision | Checking in view directly - rejected as couples view to git logic |
| Enable button if `has_changes OR is_git_dirty` | Matches user expectation; both conditions warrant staging | Only enable on diff changes - rejected as missing git changes |

## Architecture Impact
**Modules affected:**
- `domain/git/ports.py` - Add `get_dirty_paths` to GitPort protocol
- `domain/git/git_service.py` - Add `get_dirty_documents` method
- `infrastructure/git/git_port_adapter.py` - Implement `get_dirty_paths` using git status --porcelain
- `application/actions/get_dirty_documents.py` - NEW action
- `application/di/container.py` - Wire new action
- `ui/presenters/diff_presenter.py` - Use action in `_on_working_tree_selected`
- `ui/presenters/presentation_models.py` - Add `is_git_dirty` to DiffTreePresentation
- `ui/views/diff_panel_view.py` - Update button enable logic

**Public interfaces:**
- `GitPort.get_dirty_paths(git_root: str) -> list[str]` - NEW public method
- `GitService.get_dirty_documents(repo, documents) -> list[str]` - NEW public method
- `GetDirtyDocumentsAction.execute(repo, documents) -> Result` - NEW action
- `DiffTreePresentation.is_git_dirty: bool` - NEW field

## FreeCAD Dependency
- [x] No FreeCAD required (GitPort, GitService, GetDirtyDocumentsAction are pure code)
- [ ] FreeCAD required (DiffPresenter and DiffPanelView use FreeCAD widgets)

**Note:** Tests for actions will use fakes/mocks. UI component testing is manual only.

## Implementation Plan

### Phase 1: Domain Layer - GitPort and GitService updates

**Task 1.1: Write tests for `get_dirty_paths`**

Create `tests/unit/infrastructure/git/test_get_dirty_paths.py`:

```python
"""Unit tests for GitPortAdapter.get_dirty_paths."""
import subprocess
from unittest.mock import patch
from freecad.diff_wb.infrastructure.git.git_port_adapter import GitPortAdapter


def test_get_dirty_paths_returns_modified_and_untracked():
    """Given modified and untracked files in git status output, returns their paths."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=0,
        stdout="M src/file.py\n?? new.txt\n",
        stderr="",
    )
    
    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")
        
        assert set(result) == {"src/file.py", "new.txt"}


def test_get_dirty_paths_empty_for_clean_repo():
    """Given empty git status output (clean repo), returns empty list."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=0,
        stdout="",
        stderr="",
    )
    
    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")
        
        assert result == []


def test_get_dirty_paths_filters_staged_only_changes():
    """Given staged-only changes (A without M), they should NOT be included."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=0,
        stdout="A staged_file.py\n",
        stderr="",
    )
    
    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")
        
        assert result == []  # Staged-only not considered dirty


def test_get_dirty_paths_filters_deleted_files():
    """Given deleted files (D), they should NOT be included."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=0,
        stdout="D deleted_file.py\n",
        stderr="",
    )
    
    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")
        
        assert result == []  # Deleted not considered dirty


def test_get_dirty_paths_handles_git_error():
    """Given git command failure, returns empty list."""
    mock_result = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=128,
        stdout="",
        stderr="fatal: not a git repository",
    )
    
    with patch.object(subprocess, "run", return_value=mock_result):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/not/a/repo")
        
        assert result == []


def test_get_dirty_paths_handles_timeout():
    """Given git command timeout, returns empty list."""
    with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30)):
        adapter = GitPortAdapter()
        result = adapter.get_dirty_paths("/path/to/repo")
        
        assert result == []
```

**Task 1.2: Add `get_dirty_paths` to GitPort protocol**

In `domain/git/ports.py`, add to `GitPort`:

```python
def get_dirty_paths(self, git_root: str) -> list[str]:
    """Get list of dirty file paths (modified or untracked).
    
    This method runs `git status --porcelain` and filters for files that are
    modified in the working tree or untracked. These are the only files that
    can be staged via `git add`.
    
    Args:
        git_root: Absolute path to git repository root.
        
    Returns:
        List of relative paths (from git root) that are modified or untracked.
        Empty list if repo is clean or not a git repo.
    """
    ...
```

**Task 1.3: Implement `get_dirty_paths` in GitPortAdapter**

In `infrastructure/git/git_port_adapter.py`, add:

```python
def get_dirty_paths(self, git_root: str) -> list[str]:
    """Get dirty paths using git status --porcelain.
    
    Filters for modified (M) and untracked (??) files only, as these are
    the only ones that can be staged via `git add`.
    
    Args:
        git_root: Absolute path to git repository root.
        
    Returns:
        List of relative paths (from git root) that are modified or untracked.
        Empty list if repo is clean or not a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode != 0:
            return []
        
        dirty_paths = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            
            # Status is first character, path starts at position 3 (after status + space)
            # Format: "<status><space><path>"
            status = line[0]
            rel_path = line[3:] if len(line) > 3 else ""
            
            # Only include modified (M) and untracked (?) files
            # Skip staged-only (A), deleted (D), renamed (R), etc.
            if status == "M" or status == "?":
                if rel_path:
                    dirty_paths.append(rel_path)
        
        return dirty_paths
        
    except (subprocess.TimeoutExpired, FileNotFoundError):
        Log.warning("Git status command failed")
        return []
```

**Task 1.4: Add `get_dirty_documents` to GitService**

In `domain/git/git_service.py`, add:

```python
def get_dirty_documents(self, repo: GitRepository, documents: list[DocumentLike]) -> list[str]:
    """Get git paths of documents that have git changes.
    
    This method checks which of the provided documents have been modified
    or are untracked in the git repository.
    
    Args:
        repo: GitRepository to check against.
        documents: List of DocumentLike objects to check.
        
    Returns:
        List of git paths (relative from repo root) that are dirty.
    """
    dirty_paths = self._git_port.get_dirty_paths(repo.absolute_path)
    
    # Filter to only documents we care about
    dirty_doc_paths = []
    for doc in documents:
        doc_path = getattr(doc, "FileName", "")
        if doc_path and self._git_port.is_path_in_repository(repo.absolute_path, doc_path):
            # Get relative path from git root
            rel_path = os.path.relpath(doc_path, repo.absolute_path)
            if rel_path in dirty_paths:
                dirty_doc_paths.append(rel_path)
    
    return dirty_doc_paths
```

### Phase 2: Application Layer - GetDirtyDocuments action

**Task 2.1: Write tests for GetDirtyDocumentsAction**

Create `tests/unit/application/actions/test_get_dirty_documents.py`:

```python
"""Unit tests for GetDirtyDocumentsAction."""
from unittest.mock import MagicMock
from freecad.diff_wb.application.actions.get_dirty_documents import GetDirtyDocumentsAction
from freecad.diff_wb.domain.git.models import GitRepository


def test_get_dirty_documents_returns_dirty_paths():
    """Given documents with some dirty, returns list of dirty git paths."""
    # Setup
    mock_git_service = MagicMock()
    mock_git_service.get_dirty_documents.return_value = ["doc1.FCStd", "doc3.FCStd"]
    
    action = GetDirtyDocumentsAction(git_service=mock_git_service)
    repo = GitRepository(name="test", absolute_path="/path/to/repo")
    documents = [MagicMock(FileName="/path/to/repo/doc1.FCStd"), 
                 MagicMock(FileName="/path/to/repo/doc2.FCStd")]
    
    # Execute
    result = action.execute(repo, documents)
    
    # Assert
    assert result.is_success
    assert result.data == ["doc1.FCStd", "doc3.FCStd"]


def test_get_dirty_documents_empty_list_when_clean():
    """Given all documents clean, returns empty list."""
    # Setup
    mock_git_service = MagicMock()
    mock_git_service.get_dirty_documents.return_value = []
    
    action = GetDirtyDocumentsAction(git_service=mock_git_service)
    repo = GitRepository(name="test", absolute_path="/path/to/repo")
    documents = [MagicMock(FileName="/path/to/repo/doc.FCStd")]
    
    # Execute
    result = action.execute(repo, documents)
    
    # Assert
    assert result.is_success
    assert result.data == []
```

**Task 2.2: Implement GetDirtyDocumentsAction**

Create `application/actions/get_dirty_documents.py`:

```python
# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for getting dirty document paths.
# This module provides the GetDirtyDocumentsAction which checks which documents
# have git-tracked changes (modified or untracked).
"""Application action for getting dirty documents."""

import os

from ...domain.freecad_ports import DocumentLike
from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from .result_models import Result


__all__ = ["GetDirtyDocumentsAction"]


class GetDirtyDocumentsAction:
    """Get list of document git paths that have git changes.
    
    This action checks which of the provided documents have been modified
    or are untracked in the git repository. Only modified and untracked
    files are considered (not staged-only or deleted files).
    """
    
    def __init__(self, git_service: GitService):
        self._git_service = git_service
    
    def execute(self, repo: GitRepository, documents: list[DocumentLike]) -> Result:
        """Execute the action to get dirty document paths.
        
        Args:
            repo: GitRepository to check against.
            documents: List of DocumentLike objects to check.
            
        Returns:
            Result.success(list of dirty git paths relative to repo root).
        """
        dirty_paths = self._git_service.get_dirty_documents(repo, documents)
        return Result.success(dirty_paths)
```

**Task 2.3: Wire action in container**

In `application/di/container.py`:

1. Add import:
```python
from ..actions.get_dirty_documents import GetDirtyDocumentsAction
```

2. Add to `ApplicationContainer` dataclass:
```python
get_dirty_documents_action: GetDirtyDocumentsAction
```

3. Wire in `create_application_container`:
```python
get_dirty_documents_action = GetDirtyDocumentsAction(git_service=git_service)

return ApplicationContainer(
    # ... existing fields ...
    get_dirty_documents_action=get_dirty_documents_action,
    # ... rest of fields ...
)
```

### Phase 3: UI Layer - Presenter and View updates

**Task 3.1: Add `is_git_dirty` to DiffTreePresentation**

In `ui/presenters/presentation_models.py`, update:

```python
@dataclass(frozen=True)
class DiffTreePresentation:
    """Wrapper for presenting a single diff tree with metadata.
    
    Attributes:
        nodes: Transformed list of root NodePresentation objects
        git_path: Git path of the document
        warnings: List of warning strings from DiffResult.warnings
        is_git_dirty: True if document has git-tracked changes (modified/untracked)
    """
    
    nodes: list[NodePresentation]
    git_path: str
    warnings: list[str]
    is_git_dirty: bool = False  # NEW field
```

**Task 3.2: Update DiffPresenter._on_working_tree_selected**

In `ui/presenters/diff_presenter.py`:

1. Add constructor parameter:
```python
def __init__(
    self,
    view: DiffView,
    ui_state: UIState,
    get_eligible_docs_action: GetOpenEligibleDocumentsAction,
    create_working_snapshot_action: CreateDocumentSnapshotForWorkingTreeAction,
    create_commit_snapshot_action: CreateDocumentSnapshotForCommitAction,
    create_diff_action: CreateDiffAction,
    stage_documents_action: StageDocumentsAction,
    get_dirty_documents_action: GetDirtyDocumentsAction,  # NEW
) -> None:
```

2. Store as instance variable:
```python
self._stage_documents = stage_documents_action
self._get_dirty_documents = get_dirty_documents_action  # NEW
```

3. Update `_on_working_tree_selected`:
```python
def _on_working_tree_selected(self) -> None:
    """Handle Working Tree item selection.
    
    For each eligible document:
    1. Create working tree snapshot
    2. Create diff against None (old snapshot)
    3. Get dirty documents (ONE call for all eligible docs)
    4. Collect results, logging warnings for failures
    """
    repo = self._ui_state.git_repository
    if repo is None:
        Log.warning("No git repository detected")
        return
    
    docs_result = self._get_eligible_docs.execute(repo)
    if not docs_result.is_success or not docs_result.data:
        Log.warning(f"No eligible documents: {docs_result.message}")
        return
    
    eligible_docs = docs_result.data
    all_diff_results: list[DiffResult] = []
    
    for doc in eligible_docs:
        working_result = self._create_working_tree_snapshot.execute(repo, doc)
        if not working_result.is_success or working_result.data is None:
            Log.warning(f"Failed to create working snapshot: {working_result.message}")
            continue
        
        working_snapshot = working_result.data
        
        commit_result = self._create_commit_snapshot.execute(repo, None, working_snapshot.git_path)
        commit_snapshot = commit_result.data if commit_result.is_success else None
        
        diff_result = self._create_diff.execute(commit_snapshot, working_snapshot)
        if diff_result.is_success and diff_result.data is not None:
            all_diff_results.append(diff_result.data)
        else:
            Log.warning(f"Failed to compute diff: {diff_result.message}")
    
    # Get dirty documents (ONE call for all eligible docs - efficient!)
    dirty_result = self._get_dirty_documents.execute(repo, eligible_docs)
    dirty_paths = set(dirty_result.data) if dirty_result.is_success else set()
    
    # Store diff results keyed by git_path for later use by add button
    self._diff_results_by_path.clear()
    for result in all_diff_results:
        git_path = result.new_snapshot.git_path
        if git_path:
            self._diff_results_by_path[git_path] = result
    
    if all_diff_results:
        self.present_diffs(all_diff_results, dirty_paths)
    else:
        Log.warning("No diff results to display")
```

4. Update `present_diffs` signature and implementation:
```python
def present_diffs(self, diff_results: list[DiffResult], dirty_paths: set[str] | None = None) -> None:
    """Transform multiple DiffResults into presentation models and display.
    
    Args:
        diff_results: List of DiffResult objects to present.
        dirty_paths: Set of git paths that have git-tracked changes.
    """
    dirty_paths = dirty_paths or set()
    
    if not diff_results:
        self._view.show_diff_trees([])
        return
    
    presentations = []
    for diff_result in diff_results:
        nodes = [self._format_node(node) for node in diff_result.hierarchy.roots]
        git_path = diff_result.new_snapshot.git_path or diff_result.new_snapshot.document_name
        warnings = list(diff_result.warnings)
        
        # Check if this document's git path is in dirty set
        is_git_dirty = git_path in dirty_paths
        
        presentations.append(DiffTreePresentation(
            nodes=nodes, 
            git_path=git_path, 
            warnings=warnings,
            is_git_dirty=is_git_dirty  # NEW field
        ))
    
    self._view.show_diff_trees(presentations)
    
    # Show summary from first document (for now)
    first = diff_results[0]
    self._view.show_summary(
        added=first.added_count,
        deleted=first.deleted_count,
        modified=first.modified_count,
    )
```

**Task 3.3: Update DiffPanelView.show_diff_trees**

In `ui/views/diff_panel_view.py`, update the button enable logic:

```python
def show_diff_trees(self, diffs: list[DiffTreePresentation]) -> None:
    """Display multiple diff trees in the tree widget.
    
    Args:
        diffs: List of DiffTreePresentation objects, each representing
              a diff tree for one document with its metadata.
    """
    # Clear existing tree items
    self.tree_widget.clear()
    
    # Guard: no diffs to display
    if not diffs:
        return
    
    for diff in diffs:
        # Build top-level text (no emoji - icon will be shown separately)
        top_level_text = diff.git_path or "Unnamed Document"
        
        # Prepare warning text for tooltip (newline-separated)
        warning_tooltip = "\n".join(diff.warnings) if diff.warnings else ""
        
        # Check if document has changes (diff changes OR git dirty)
        has_changes = any(node.has_changes for node in diff.nodes)
        is_git_dirty = diff.is_git_dirty  # NEW field
        
        # Create root item
        root_item = QTreeWidgetItem([top_level_text])
        # Store git_path in root item's UserRole for later retrieval when children are clicked
        root_item.setData(0, Qt.ItemDataRole.UserRole, diff.git_path)
        
        # Create "+ Stage" button
        add_button = QPushButton("+ Stage")
        # Enable if EITHER diff changes OR git dirty
        add_button.setEnabled(has_changes or is_git_dirty)  # Changed from just has_changes
        add_button.setFixedWidth(60)
        # Use default argument gp=diff.git_path to capture loop variable correctly
        add_button.clicked.connect(lambda checked, gp=diff.git_path: self._on_add_button_clicked(gp))
        
        # Create container widget with layout
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        
        # Add text label
        layout.addWidget(QLabel(top_level_text))
        
        # Add warning icon label if warnings exist
        if diff.warnings and _WARNING_ICON is not None:
            warning_icon_label = QLabel()
            warning_icon_label.setPixmap(_WARNING_ICON.pixmap(16, 16))
            warning_icon_label.setToolTip(warning_tooltip)
            layout.addWidget(warning_icon_label)
        
        layout.addStretch()
        layout.addWidget(add_button)
        
        # Set the widget on the tree item
        self.tree_widget.addTopLevelItem(root_item)
        self.tree_widget.setItemWidget(root_item, 0, container)
        
        # Add child nodes from hierarchy
        for node in diff.nodes:
            item = self._create_tree_item(node)
            root_item.addChild(item)
        
        # Expand only nodes that have children with changes
        self._expand_nodes_with_changes(root_item)
    
    # Ensure tree widget is visible
    self.tree_widget.show()
```

---

## Test Strategy
- **Unit tests**: GitPortAdapter.get_dirty_paths (mock subprocess), GetDirtyDocumentsAction (fake GitService)
- **Integration tests**: Not required for MVP - manual testing covers UI integration

## Findings & Notes
- `git status --porcelain` format: `<status><space><path>` where status is at position 0
- Filter for `M` (modified) and `?` (untracked) only - these are the only ones that can be staged via `git add`
- Single git status call for efficiency (vs N calls for N documents)
- Use set for dirty_paths lookup for O(1) performance
- Staged-only files (`A` without `M`) are NOT considered dirty since they're already staged
- Deleted files (`D`) are NOT considered dirty since they cannot be staged
