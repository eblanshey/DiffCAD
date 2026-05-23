<p align="center">
  <img src="freecad/diff_wb/resources/icons/Logo.svg" width="96" alt="DiffCAD logo" />
</p>

<h1 align="center">Project History Workbench for FreeCAD</h1>

<p align="center">
  <strong>Track FreeCAD project history, review model changes, and build with confidence.</strong>
</p>

<p align="center">
  <a href="https://www.freecad.org/"><img alt="FreeCAD 1.1+" src="https://img.shields.io/badge/FreeCAD-1.1%2B-blue"></a>
</p>

---

<a href="https://raw.githubusercontent.com/eblanshey/DiffCAD/master/docs/LightScreenshot.png"><img src="docs/LightScreenshot.png" alt="DiffCAD light theme screenshot" /></a>
<a href="https://raw.githubusercontent.com/eblanshey/DiffCAD/master/docs/DarkScreenshot.png"><img src="docs/DarkScreenshot.png" alt="DiffCAD dark theme screenshot" /></a>

## Intro

Project History Workbench is a FreeCAD addon that helps you create projects with confidence by tracking iterations over time, reviewing in-progress work, and showing model changes as detailed 3D and parametric tree comparisons.

It helps answer questions like:

- How does my change look in 3D compared to the last iteration?
- Can I trust that my changes didn't create any unforeseen side-effects?
- Which objects, dimensions, placements, expressions, or dependencies changed?
- What did my model look like 3 iterations ago?
- Why did I change this model 2 months ago?

> [!NOTE]
> This workbench is relatively new. Opening issues, sharing feedback, and submitting pull requests are encouraged!

## Features

- **Model tree comparison:** See added, removed, and modified objects in FreeCAD's model tree hierarchy with color-coded highlighting
- **Detailed property review:** Inspect exact changes to dimensions, placements, expressions, constraints, quantities, links, and other editable properties.
- **3D feature comparison:** Open visual comparisons for Part, PartDesign, and Sketcher objects, with added, removed, and shared geometry shown in separate colors.
- **Review workflow:** Review model changes incrementally and save the result as a new iteration when ready.
- **Project history timeline:** Move between in-progress work, reviewed changes, and saved iterations from one history panel.
- **Multi-document support:** Review and iterate on multiple related documents at once, such as assemblies spread across several `.FCStd` files.
- **Noise control:** Hide generated object types or properties, tune floating-point precision, and keep comparisons focused on meaningful CAD changes.
- **Light and dark theme support:** Keep comparison highlights readable in both light and dark FreeCAD themes.
- **Local-first storage:** your project stays on your computer. Optional remote storage and sharing available for advanced users.

## Installation

Project History Workbench requires:

- FreeCAD 1.1 or newer (earlier versions may work, but are untested)
- Git installed and available on your computer for iteration tracking. **Knowledge of is Git not required to use this workbench.**
  - Install it from <https://git-scm.com/install>. Run the installer with default options.

Project History Workbench is not yet available in the official FreeCAD Addon Manager repository. Until then, install it as a custom repository:

1. Open FreeCAD.
2. Go to **Edit > Preferences > Addon Manager > Custom repositories**.
3. Add this repository URL: `https://github.com/eblanshey/DiffCAD`
4. Set the branch to `master`.
5. Open **Tools > Addon Manager**.
6. Search for **Project History Workbench** and install it.
7. Restart FreeCAD.

### Upgrading

When upgrading from an existing Addon Manager installation:

1. Open **Tools > Addon Manager**.
2. Uninstall **Project History Workbench**.
3. Close FreeCAD.
4. Reopen FreeCAD.
5. Open **Tools > Addon Manager**.
6. Install **Project History Workbench** again.
7. Restart FreeCAD.

## First Run: Project Initialization

Project History Workbench works with a Project: a folder on your computer that contains the FreeCAD files you want to track together. For an existing folder of CAD files, initialize it as a Project first, then save a baseline iteration before making new CAD changes so tree comparisons have a starting point.

1. **(Optional) FreeCAD compression:** To keep project history more storage-efficient, see the FreeCAD Version Storage Tips section below.
2. **Open a FreeCAD file:** Start FreeCAD and open any document from the folder you want to use as the root of your Project.
3. **Initialize the Project:** Click <img src="freecad/diff_wb/resources/icons/CreateGitRepository.svg" width="16" alt="" /> **Initialize Project** in the Project History Workbench, select the folder that contains your project files, and click "Initialize".
4. **Open project documents:** Click <img src="freecad/diff_wb/resources/icons/RefreshRepository.svg" width="16" alt="" /> **Refresh Project**, then click <img src="freecad/diff_wb/resources/icons/OpenAllDocuments.svg" width="16" alt="" /> **Open All Documents** to open all FreeCAD documents in the project folder.
5. **Recompute documents:** Click <img src="freecad/diff_wb/resources/icons/RecomputeAll.svg" width="16" alt="" /> **Recompute All** to make sure document state is current. Ensure there aren't recomputation errors.
6. **Review in-progress state:** Select **In Progress** in the history list. Large projects may take some time while comparison data is generated.
7. **Mark everything reviewed:** Click **Mark All Reviewed**. The workbench saves documents and records the review data needed for future comparisons.
8. **Save the baseline iteration:** Use <img src="freecad/diff_wb/resources/icons/Commit.svg" width="16" alt="" /> **Save Iteration** or your regular version-control client.

After that baseline iteration, continue modeling normally and use the Daily Workflow instructions below to review your work.

## Daily Workflow

Use Project History Workbench as a review loop after normal CAD work.

1. **Work in FreeCAD as usual:** Model, recompute, save, and edit your project files normally.
2. **Switch to Project History Workbench:** Select **History** from the FreeCAD workbench selector.
3. **Refresh the project:** Click <img src="freecad/diff_wb/resources/icons/RefreshRepository.svg" width="16" alt="" /> **Refresh Project** so the history list and document status reflect the latest files.
4. **Review in-progress changes:** Click the **In Progress** iteration item in the history list. The document tree shows added, removed, and modified objects since the last reviewed state.
5. **Inspect detailed properties:** Click a changed object in the model tree. The property panel shows changed dimensions, placements, expressions, constraints, quantities, links, and other editable properties.
6. **Open 3D comparisons:** For changed Part, PartDesign, or Sketcher objects, click <img src="freecad/diff_wb/resources/icons/VisualDiff.svg" width="16" alt="" /> **3D Comparison** next to the object to open a separate comparison document. Removed material is shown in red, added material in green, and unchanged material in gray. You may use FreeCAD's unified measurement tool to measure changes.
7. **Mark documents reviewed:** Click **Reviewed** on individual documents when they are ready, or click **Mark All Reviewed** after reviewing the whole project. This supports incremental review across multiple related files, such as assemblies.
8. **Keep working if needed:** Return to the CAD model and make more edits. The next **In Progress** comparison is made against the documents you already marked as reviewed.
9. **Verify reviewed work:** Click the **Reviewed** iteration item in the history list to confirm exactly what will become part of project history.
10. **Save an iteration:** Click <img src="freecad/diff_wb/resources/icons/Commit.svg" width="16" alt="" /> **Save Iteration**, enter a description of the change, and confirm.

To preserve project history, previous iterations cannot be altered once they are saved. All changes require a new iteration to be saved.

> [!CAUTION]
> Tree comparisons focus on structured FreeCAD object and property data, but may not capture every CAD model change yet. Use 3D comparisons as an additional review step before saving an iteration.

## Roadmap

- [ ] Move reviewed documents back to in-progress from inside Project History Workbench
- [x] Initialize new project history repositories from inside Project History Workbench
- [ ] Move/rename review data when an `.FCStd` file is moved or renamed
- [x] 3D view comparisons

## Configuration

FreeCAD's Preferences dialog includes a **Project History** panel.

### Exclusion Lists

Exclusion lists hide noisy generated data from tree comparison views.

Each exclusion list supports two modes:

- **Use default exclusion list:** Use Project History Workbench's built-in defaults.
- **Use custom exclusion list:** Provide your own exclusions.

Default values are defined in [`freecad/diff_wb/domain/config.py`](freecad/diff_wb/domain/config.py).

#### Excluded Object Types

Enter one FreeCAD `TypeId` per line, such as `App::Origin`. Objects of these types and their children are removed from comparison views. You can see an object's type by hovering your mouse over it in the Project History's tree panel.

#### Excluded Properties

Enter one property name per line, such as `TimeStamp`. These properties are excluded across all object types.

#### Type-Specific Excluded Properties

Enter one mapping per line in the format `TypeId -> PropertyName`. This excludes one property for one object type while keeping it visible elsewhere.

```text
TechDraw::DrawSVGTemplate -> PageResult
```

### Numeric Comparison

#### Float Precision

Set the number of decimal places used for floating-point comparison and display. The supported range is `0` to `12`; the default is `2`.

## FAQ

### The tree comparison doesn't show any changes, but the Reviewed button is enabled. Why?

No object or property changes were detected, but the FreeCAD document changed on disk. This can happen when the document was saved without model changes, view properties or internal cache data changed, or parametric changes occurred that Project History Workbench does not detect yet.

Some of these scenarios are legitimate project changes and should be tracked like any other change. If you find a parametric model change that is not shown in the tree comparison, please open an issue with a sample file when possible.

## FreeCAD Version Storage Tips

FreeCAD documents are binary files by default. Small model edits can produce large file changes, and project history disk usage can grow quickly over time.

For a simple version-control-friendly setup, disable document compression:

1. Open **Edit > Preferences > General > Document**.
2. Set **Document save compression level** to `0`.

An `.FCStd` file is a ZIP archive. With compression disabled, more of the document remains plain XML inside the archive, which makes version storage and external comparison tooling behave better.

*Advanced users:* For large or long-lived CAD projects, also consider Git LFS for `.FCStd` files. There is a [PR in FreeCAD](https://github.com/FreeCAD/FreeCAD/pull/28312) that addresses file formats for versioning. See [this comment](https://github.com/FreeCAD/FreeCAD/issues/11936#issuecomment-4054297851) for more version-control discussions.

## Advanced Usage

This section is for advanced users who want more control over project history. Project History Workbench uses Git for version control, so users familiar with Git can use regular Git tools alongside the workbench for workflows that are not implemented in the FreeCAD interface yet.

Advanced Git usage can help with tasks such as:

- Editing saved iteration messages (Git commit messages).
- Adding non-FreeCAD files to the **Reviewed** area (Git staging area) so they are saved with the same iteration, such as text documents, spreadsheets, CSV files, or reference data.
- Backing up a Project to a remote repository (Git remote), such as GitHub, GitLab, or a private Git server.
- Inspecting project history from external Git clients when you need lower-level version-control tools.

Project History Workbench still needs to be used to mark FreeCAD documents as **Reviewed**. That step stores YAML snapshot files in the Project repository, and those snapshots are required for tree comparisons.

## Contributors

This workbench is made for you, the community. Please open an issue to report bugs, confusing comparisons, setup problems, documentation gaps, or feature requests. Development so far has happened on Linux, so additional platform setup notes and test instructions are also welcome as contributions.

- [Development setup](docs/DevSetup.md): Set up a live FreeCAD workbench checkout, install dependencies, and configure the FreeCAD AppImage runtime for tests.
- [Development guidelines](docs/Development.md): Coding standards, testing strategy, logging, translations, dependency injection, and common contributor workflows.
- [Architecture](docs/Architecture.md): Layer responsibilities, runtime flow, composition roots, and snapshot/comparison pipeline.
