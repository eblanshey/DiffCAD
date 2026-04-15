# Git Repository Detection

Test the git repository detection feature that displays the active git repository information above the snapshot list in the UI.

## Test Case 1: No Files Open

**Steps:**
1. Ensure no documents are open in FreeCAD
2. Switch to the Diff Workbench (View → Workbenches → Diff)

**Expected Result:**
- The repository info area displays: "No git repository detected"
- The text appears in gray, italic style
- No error messages or exceptions in the console

---

## Test Case 2: Files Open but No Active Git Repository

**Steps:**
1. Create a new document (File → New)
2. Save the document to a location outside any git repository (e.g., `/tmp/test.FCStd`)
3. Switch to the Diff Workbench (View → Workbenches → Diff)

**Expected Result:**
- The repository info area displays: "No git repository detected"
- The text appears in gray, italic style
- No error messages or exceptions in the console

---

## Test Case 3: Files Open with 1 Git Repository

**Steps:**
1. Open a document that is located within a git repository (e.g., `tests/freecad/BasicFile.FCStd` in this project)
2. Switch to the Diff Workbench (View → Workbenches → Diff)

**Expected Result:**
- The repository info area displays the repository name and path in format: `freecad_diff_workbench (/home/user/Repositories/freecad_diff_workbench)`
- The actual path will vary based on your installation location
- The text appears in bold style
- The repository name matches the directory name containing the `.git` folder
- No error messages or exceptions in the console

---

## Test Case 4: Files Open with Multiple Git Repositories

**Steps:**
1. Open a document from Git Repository A (e.g., `/home/user/project_a/file.FCStd`)
2. Open another document from Git Repository B (e.g., `/home/user/project_b/file.FCStd`)
3. Ensure one document is active (click on it in the document window)
4. Switch to the Diff Workbench (View → Workbenches → Diff)

**Expected Result:**
- The repository info area displays the git repository of the **active** document only
- Format: `project_name (/path/to/project)`
- The displayed repository corresponds to the document that currently has focus
- No error messages or exceptions in the console
- Note: Only ONE repository is shown at a time (the active document's repository)
