# PROJECT STATE

The goal of this workbench is to help FreeCAD users track and verify parametric changes in their CAD models by comparing document snapshots, ensuring that modifications (like changing a dimension from 2mm to 3mm) don't cause unintended downstream effects on other features or properties

## Current application state

- In-memory snapshots of the active freecad document
- Ability to compare two arbitrarily selected freecad documents
- Displays diff of freecad feature tree with highlighted nodes
- Clicking a node displays the node's properties, comparing values before and after

## Functionality to Add

- Git integration
- Diffing more than one active document at a time
- Persisting snapshots in YAML files, with a standardized way of mapping YAML snapshots to their respective freecad documents
- Automatically select the git project by going through all open document file locations until one is found to be in a git repository
    - "Refresh" button to reload git repository and commits
- Empty state message when no eligible documents are open
- The commit list should contain:
    - One entry for every commit in the active git repository, sorted in DESC date order
    - One entry for "Uncommitted Changes", above the commit entries
- Selecting a commit in the list should automatically display the diff between it and the previous commit, using the standard object node diff + property diff viewer
- Selecting "Uncommitted Changes" displays a tabbed interface: "Working Tree" tab and "Staged" tab
    - The Working Tree tab shows diffs comparing dirty snapshots to staging snapshots (or HEAD if not staged)
    - The Staged tab shows diffs comparing staged snapshots to HEAD
- Diffing does NOT actually use "git diff", but compares two snapshots using our functionality
- Ability to git commit freecad documents

## Startup Flow

1. Detect git repository from opened documents
2. Load last 20 commits into the sidebar with their git messages, and create the staging and working tree entries
3. Automatically select the Uncommitted Changes entry, which loads the diffs for both the Working Tree and Staged tabs.

## How Working Tree and Staging Trees are loaded

Note: for working tree and staging tree, the only docs eligible for viewing and diffing are the ones available in both the active git repository AND open in freecad, so (REPOSITORY_DOCS & OPEN_IN_FREECAD). Diffing commits between each other doesn't have this limitation. We'll refer to the unioned files as "Eligible Docs".

Action "GenerateDiffForUncommitted":

1. `git diff` is internally used to see which documents have changes in the active repository -- the exact git changes don't matter
2. For each eligible doc, create a snapshot in-memory (existing functionality). We can call it the "dirty" snapshot.
3. `git diff --cached` is internally used to see which docs are staged -- exact git changes don't matter
4. The snapshots for the corresponding eligible files are loaded
5. Populate the Working Tree with diffs comparing the dirty snapshots to the staging snapshots
    1. If a dirty snapshot doesn't have a corresponding staging snapshot, the one from the last commit is used (similar to `git diff` command)
6. Populate the Staging Tree with diffs comparing staged eligible documents with the corresponding HEAD snapshots

## Commit Flow

- Each document in the Working Tree has an "+" button to the right which can be clicked.
- Clicking "+" on a document does the following:
    - Persist the snapshot to a YAML file
    - Run `git add [doc_path] [yaml_path]`
- The trees are updated respectively -- the doc is removed from Working tree and shows up in Staging
- User presses the "Commit" button in the toolbar, which opens a QInputDialog where they type a message and presses commit: the staged files are committed
- The staging tree is cleared and a new commit is added to the commit list

## YAML Snapshots

- Snapshots are stored in YAML files, to be able to diff using text-based tools in addition to this workbench
- Snapshots are stored in a `.snapshots` directory at the root of the git repository
- Snapshots have the same name as the freecad document
- Snapshots are stored in directories matching the document file path.

Examples freecad directory:

___
- File1.FCStd
- mydir/File2.FCStd
- .snapshots/File1.yaml
- .snapshots/mydir/File2.yaml
___

If File1.FCStd is staged, for example, the Staging tree will compare, using our snapshot comparison functionality, the staged `.snapshots/File1.yaml` file to the same yaml file as it exists in HEAD commit.

### Snapshot File Structure

```yaml
---
v: snapshot_version
timestamp: [in UTC]
uid: 2b50a4d3-05d2-48e9-a1bf-2dce33ce69e0  # doc id
objects:
- id: 43
  type_id: Sketcher::SketchObject
  name: Sketch
  after: 
  properties:
      - Contraints:
            - FirstValue
            - SecondValue
      - Label: MySketch
  path: Pad/Sketch
- id: 47
  type_id: PartDesign::Pad
  name: Pad
  after: Sketch002
  properties:
      - Length: 43mm
      - Label: MyPad
  path: Pad
- id: 48
  type_id: Sketcher::SketchObject
  name: Sketch002
  ...
```

Key points:
- objects are stored in order of the integer id -- this never changes
- the "after" is used for ordering objects on the same hierarchical level
- circular references (A -> parent B -> A) are not allowed

## Git commands supported

- git add [file]
- git commit -m "[message]"

## Application-level Actions needed

All actions return a Result object with properties:
- is_success: bool
- data: Optional[Any] = None  (on success)
- message: Optional[str] = None  (on error)

Actions to add:
- GetActiveGitRepository: looks up the git repository root path from open freecad documents. Return: Result with GitRepository in data.
- LoadCommits(GitRepository): fetches commits and their messages from the given repository. Return: Result with list[GitCommit] in data.
- GenerateDiffForCommit(GitRepository, str: commit_hash): Computes diff for the commit, compares it to previous commit. Return: Result with DiffResult in data.
- GenerateDiffForUncommitted(GitRepository): computes diff for both working and staging trees. Return: Result with tuple(DiffResult, DiffResult) in data.
- StageDocuments(GitRepository, list[str]: docs): stages the given list of documents. Generates a snapshot for each one, persists to YAML, and `git add [doc_path] [yaml_path]` for each one. Return: Result with bool success in data.
- CommitStaging(GitRepository, str: message): simply does a `git commit -m "[message]"`. Does not add files or generate snapshots. Return: Result with bool success in data.

## Domain Entities

- To add:
    - GitRepository: with properties "name" and "absolute_path". "name" is the directory name of the git root
    - GitCommit: with properties "id" (the commit hash), "message", "author", and "timestamp"
- To modify:
    - DiffResult: must support multiple documents:
  
        documents: list[DocumentDiff]
        
        class DocumentDiff:
            node_diffs: list[NodeDiff]

## Decisions

- When a commit is selected, for each FCStd file that has changed that does NOT have a corresponding YAML snapshot, it should add a bare document entry into the diff with text "no snapshot found"
    - Similarly, if the commit does contain a snapshot but the previous commit does not, display text "previous commit snapshot missing"

## Out of Scope

- git branching (it always uses current branch)
- git merging
- git reset
- all other git commands

## Future

- Comparing two arbitrary commits (currently compares only to the previous commit)
- Resetting files from staging (must be done manually for now)
- Ability to create a repository in a given directory (must be done manually)
- Ability to switch git repositories which were detected from open documents
- File renamed detection and tracking
