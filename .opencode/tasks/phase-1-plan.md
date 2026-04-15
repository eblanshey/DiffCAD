# Task: Phase 1 - Git Repository Detection

## Goal
Implement git repository detection based on open FreeCAD documents and display its name and path in the UI.

## Context
This is Phase 1 of the MVP implementation plan. The goal is to detect the active Git repository from open FreeCAD documents and make it available to the UI layer. This enables subsequent phases that need git context (commits, staging, diffs).

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Create `domain/git/` module | Isolates git-related domain logic from other domain concepts | Could add to existing domain modules, but git is a distinct domain concept |
| `GitPort` returns `str \| None` | Minimal interface - returns string path, no external deps in domain | Could return `GitRepository` directly, but that couples port to model |
| `GitPortAdapter` returns absolute path as string | Simpler than Path object, git CLI returns text | Path object is more type-safe but adds stdlib dependency in interface |
| `ApplicationState` in `ui/presenters/` | UI-layer state per architecture rules - domain must not depend on outer layers | Could put in application layer, but that's meant for use cases, not state |
| Generic `Result[T]` class | Consistent error handling across all actions | Could use specific result types per action |
| Infrastructure git adapter uses `git` CLI | Most portable solution for git operations | Could use GitPython, but adds dependency |
| Flat actions directory structure | Simpler imports, less nesting | Subdirectories organized by type (command/query) but adds depth |

## Architecture Impact

### New Files/Directories

```
freecad/diff_wb/
├── domain/
│   └── git/                              # NEW - git domain concepts
│       ├── __init__.py
│       ├── models.py                     # GitRepository model
│       ├── ports.py                      # GitPort protocol
│       └── git_service.py                # GitService
├── infrastructure/
│   └── git/                              # NEW - git infrastructure
│       ├── __init__.py
│       └── git_port_adapter.py           # GitPort implementation
├── application/
│   └── actions/
│       ├── __init__.py                   # MODIFIED - update exports
│       ├── find_active_git_repository.py # NEW action (flat, no subdir)
│       └── result_models.py              # MODIFIED - add Result class
└── ui/
    └── presenters/
        └── application_state.py          # NEW - application state holder
```

### Modified Files
- `application/di/container.py` - Wire new components
- `application/actions/__init__.py` - Update exports for flat structure

## FreeCAD Dependency
- [x] No FreeCAD required for domain/infrastructure code (pure Python)
- [x] FreeCAD required for integration (getting open documents, UI display)

## Implementation Plan

### Phase 1.1: Domain Layer - GitRepository Model

- [x] Write tests for `GitRepository` model creation and properties
- [x] Create `domain/git/__init__.py` with `__all__`
- [x] Create `domain/git/models.py` with `GitRepository` dataclass:
  ```python
  @dataclass(frozen=True)
  class GitRepository:
      name: str      # Directory name of git root (e.g., "my_project")
      absolute_path: str  # Absolute path to git root (e.g., "/home/user/my_project")
  ```

### Phase 1.2: Domain Layer - GitPort Protocol

- [x] Write tests for `GitPort` protocol (using fake implementation)
- [x] Create `domain/git/ports.py` with `GitPort` Protocol:
  ```python
  class GitPort(Protocol):
      def find_top_level_path(path: str) -> str | None:
          """Find git root by traversing up from path.
          
          Args:
              path: Starting path (file or directory)
          Returns:
              Absolute path to git root as string, or None if not in a git repo
          """
          ...
  ```

### Phase 1.3: Domain Layer - GitService

- [x] Write tests for `GitService.get_repository()` with fakes
- [x] Create `domain/git/git_service.py` with `GitService` class:
  ```python
  class GitService:
      def __init__(self, git_port: GitPort) -> None:
          self._git_port = git_port
      
      def get_repository(self, path: str) -> GitRepository | None:
          """Get GitRepository for path.
          
          Args:
              path: File or directory path to check
          Returns:
              GitRepository if path is in a git repo, None otherwise
          """
          git_root = self._git_port.find_top_level_git_path(path)
          if git_root is None:
              return None
          return GitRepository(...)
  ```

### Phase 1.4: Infrastructure Layer - GitPort Adapter

- [x] Write tests for `GitPortAdapter` using fixture git repos
- [x] Create `infrastructure/git/__init__.py`
- [x] Create `infrastructure/git/git_port_adapter.py`:
  ```python
  import subprocess
  
  class GitPortAdapter:
      def find_top_level_path(self, path: str) -> str | None:
          """Find git root using git CLI.
          
          Uses 'git rev-parse --show-toplevel' to find the root.
          Returns None if path is not in a git repository.
          """
          try:
              result = subprocess.run(
                  ["git", "rev-parse", "--show-toplevel"],
                  cwd=path,
                  capture_output=True,
                  text=True,
                  timeout=5
              )
              if result.returncode == 0:
                  return result.stdout.strip()
              return None
          except (subprocess.TimeoutExpired, FileNotFoundError):
              return None
  ```

### Phase 1.5: Application Layer - Result Model

- [x] Write tests for `Result` class
- [x] Modify `application/actions/result_models.py`:
  - Add generic `Result` dataclass with static factory methods:
    ```python
    @dataclass
    class Result:
        """Generic result type for all actions.
        
        Attributes:
            is_success: True if action succeeded
            data: Value on success (type varies by action, use Any for flexibility)
            message: Error message on failure
        """
        is_success: bool
        data: Any = None      # Value on success (type varies by action)
        message: str | None = None  # Error message on failure
        
        @staticmethod
        def success(data: Any) -> Result:
            """Factory method for successful results."""
            return Result(is_success=True, data=data, message=None)
        
        @staticmethod
        def failure(message: str) -> Result:
            """Factory method for failed results."""
            return Result(is_success=False, data=None, message=message)
    ```

### Phase 1.6: Application Layer - FindActiveGitRepository Action (Flat Structure)

- [x] Write tests for `FindActiveGitRepositoryAction` with fakes
- [x] Create `application/actions/find_active_git_repository.py`:
  ```python
  class FindActiveGitRepositoryAction:
      """Find git repository from open FreeCAD documents."""
      
      def __init__(
          self,
          freecad_port: FreeCadPort,
          git_service: GitService,
      ) -> None:
          self._freecad_port = freecad_port
          self._git_service = git_service
      
      def execute(self) -> Result[GitRepository | None]:
          """Find active git repository from open documents.
          
          Returns:
              Result with GitRepository if found, or failure result
          """
          # 1. Get list of open document paths from FreeCadPort
          doc = self._freecad_port.get_active_document()
          if doc is None:
              return Result.failure("No active document")
          
          # 2. Try to get document file path
          try:
              doc_path = doc.FileName  # FreeCAD documents have FileName property
          except AttributeError:
              return Result.failure("Document has no file path (unsaved)")
          
          if not doc_path:
              return Result.failure("Document is not saved")
          
          # 3. Use GitService to find repository
          repo = self._git_service.get_repository(doc_path)
          if repo is None:
              return Result.failure("No git repository found for open documents")
          
          return Result.success(repo)
   ```
- [x] Update `application/actions/__init__.py` to export the new action directly (flat structure, no commands/queries subdirs)

### Phase 1.7: UI Layer - ApplicationState

- [x] Write tests for `ApplicationState`
- [x] Create `ui/presenters/application_state.py`:
  ```python
  @dataclass
  class ApplicationState:
      """In-memory state holder for UI layer only.
      
      This class is for UI/presentation layer use ONLY.
      It stores the currently detected GitRepository.
      Created once at startup and reused across all git-related actions.
      
      Architecture note: Domain layer must NOT depend on this class.
      Future enhancements may add observable properties using Qt signals.
      """
      git_repository: GitRepository | None = None
  ```

### Phase 1.8: Container Wiring

- [x] Write tests for container wiring
- [x] Update `application/di/container.py`:
  ```python
  @dataclass
  class ApplicationContainer:
      # ... existing fields ...
      
      # New fields
      git_port: GitPort                          # Infrastructure adapter
      git_service: GitService                    # Domain service
      find_active_git_repository_action: FindActiveGitRepositoryAction
      application_state: ApplicationState         # UI state holder
   ```
- [x] Update `create_application_container()` to wire the new components:
  1. Create `GitPortAdapter` instance
  2. Create `GitService` with `GitPortAdapter`
  3. Create `FindActiveGitRepositoryAction` with `FreeCadPort` and `GitService`
  4. Create `ApplicationState` instance (with `git_repository=None` initially)
  
  Note: `GitRepositoryPresenter` is NOT created here - it's created in Phase 1.9 during UI integration since it requires the view (DiffPanelView) which doesn't exist until `_create_diff_panel()` is called.

### Phase 1.9: UI Integration - Display Git Repository

This phase adds UI to display the detected git repository. Based on MVP spec:
- Display format: `[name] ([path])` → Example: `my_project (/home/user/documents)`
- Displayed above the current list of snapshots in the UI

#### UI Architecture Analysis

**Widget Hierarchy:**
```
DiffPanelView (QWidget)
└── QVBoxLayout
    └── QSplitter (Horizontal)
        ├── Column 1: snapshot_container (QWidget)
        │   └── QVBoxLayout
        │       ├── QLabel("Snapshots")  # Header placeholder
        │       └── QListWidget (snapshot_list)
        ├── Column 2: tree_container (QWidget)
        │   └── QVBoxLayout
        │       ├── summary_container (QHBoxLayout with _added/_deleted/_modified labels)
        │       └── QTreeWidget (tree_widget)
        └── Column 3: properties_tree (QTreeWidget)
```

**Integration Points:**
1. `DiffPanelView` in `ui/views/diff_panel_view.py` - already has snapshot_container
2. `workbench.py` `Activated()` method - calls git detection on workbench switch
3. `ApplicationState` stored in container - presenter can access it

#### Detailed Implementation Steps

- [x] **Add translation string** in `ui/translation_strings.py`:
  ```python
   REPOSITORY_INFO_TEMPLATE = "%1 (%2)"  # name, path
   REPOSITORY_NO_REPO_MESSAGE = "No git repository detected"
   ```

- [x] **Add repository info label** to `DiffPanelView` in `ui/views/diff_panel_view.py`:
  - In `_setup_ui()`, modify snapshot_container layout to add a header label
  - Add `self._repository_label = QLabel("")` above the snapshot_list
  - Style it appropriately (smaller font, maybe italic or gray)
  - Add a method `show_repository(repo: GitRepository | None)`:
    ```python
    def show_repository(self, repo: GitRepository | None) -> None:
        """Display git repository info above snapshot list."""
        if repo is None:
            text = QCoreApplication.translate("Common", REPOSITORY_NO_REPO_MESSAGE)
            self._repository_label.setText(text)
            self._repository_label.setStyleSheet("color: gray; font-style: italic;")
        else:
            name = repo.name
            path = repo.absolute_path
            template = QCoreApplication.translate("Common", REPOSITORY_INFO_TEMPLATE)
            text = template % (name, path)
            self._repository_label.setText(text)
            self._repository_label.setStyleSheet("font-weight: bold;")
    ```

- [x] **Create GitRepositoryPresenter** in `ui/presenters/git_repository_presenter.py`:
  ```python
  class GitRepositoryPresenter:
      """Handles git repository detection and UI display."""
      
      def __init__(
          self,
          view: DiffPanelView,  # implements repository display method
          find_action: FindActiveGitRepositoryAction,
          application_state: ApplicationState,
      ) -> None:
          self._view = view
          self._find_action = find_action
          self._application_state = application_state
      
      def on_workbench_activated(self) -> None:
          """Detect and display git repository when workbench activates."""
          result = self._find_action.execute()
          
          if result.is_success:
              repo = result.data
              self._application_state.git_repository = repo
              self._view.show_repository(repo)
          else:
              self._application_state.git_repository = None
              self._view.show_repository(None)
             Log.warning(f"Git detection failed: {result.message}")
   ```

- [x] **Wire presenter to workbench** in `entrypoints/workbench.py`:
  - In `_create_diff_panel()`, after creating the panel and wiring other presenters:
    1. Create `GitRepositoryPresenter` with `DiffPanelView`, `FindActiveGitRepositoryAction`, and `ApplicationState`
    2. Call `git_repository_presenter.on_workbench_activated()` to detect and display repo

- [x] **Manual testing**: User will verify the complete flow manually during implementation
- [x] **Limited integration test** in `tests/integration/`: 
  - Create `test_find_active_git_repository.py`
  - Uses FreeCAD to open `tests/freecad/BasicFile.FCStd`
  - Verifies `FindActiveGitRepositoryAction.execute()` returns a valid `GitRepository`
  - The git repo root should be the project root (where `.git` exists)

#### Design Decision: Presenter vs Direct Workbench Call

**Chosen approach:** Use a `GitRepositoryPresenter` to separate concerns:
- Workbench just calls `on_workbench_activated()`
- Presenter handles action execution and view updates
- ApplicationState is updated for potential future use by other presenters

**Alternative considered:** Direct call in workbench.Activated()
- Rejected because it mixes UI logic with workbench lifecycle management
- Violates Single Responsibility Principle

## Test Strategy

### Unit Tests (No FreeCAD)
- `GitRepository` model creation and property access
- `GitPort` protocol with fake implementation
- `GitService.get_repository()` with fake GitPort
- `GitPortAdapter` with fixture git repo (subprocess mocking)
- `Result` class success/failure factory methods and data access
- `FindActiveGitRepositoryAction` with fake FreeCadPort/GitService
- `ApplicationState` getter/setter
- `GitRepositoryPresenter` with fake view and action
- `DiffPanelView.show_repository()` with mocked translation
- Container wiring with mocked dependencies

### Integration Tests (FreeCAD Required)
- Real git repository detection with actual git CLI via subprocess
- Limited test: `FindActiveGitRepository` action on `BasicFile.FCStd` returns valid `GitRepository`
- User manually verifies UI display during implementation

## Findings & Notes

### Git Detection Logic
The adapter uses `git rev-parse --show-toplevel` to detect if a path is within a git repository. This:
- Is portable (git CLI available on all platforms)
- Returns absolute path directly
- Works with any file or directory within the repo
- Returns non-zero exit code if not in a git repo

### Path Handling
GitPort returns `str` (not `Path`) for simplicity:
- Git CLI naturally works with strings
- Avoids Path vs string conversion in adapter
- Simpler interface definition

### FreeCAD Document Path
FreeCAD documents expose their file path via `document.FileName` property. This is used to determine which directory to check for git repo presence.

### Error Handling Flow
1. `FindActiveGitRepositoryAction.execute()` tries to find a repo
2. If no active document → failure with message
3. If document unsaved (no FileName) → failure with message  
4. If git_service.get_repository() returns None → failure with message
5. On success → `Result.success(GitRepository)` with data

### ApplicationState Location
`ApplicationState` in `ui/presenters/` is correct because:
- Per architecture rules, UI state lives in UI layer
- Domain layer must NOT depend on outer layers
- Document explicitly states "can be used within the ui/presentation layer only"
- Future Qt signal observables can be added without changing architecture
