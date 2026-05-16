<p align="center">
  <img src="freecad/diff_wb/resources/icons/Logo.svg" width="96" alt="DiffCAD logo" />
</p>

<h1 align="center">DiffCAD</h1>

<p align="center">
  <strong>Review FreeCAD model changes like code</strong>
</p>

<p align="center">
  <a href="https://www.freecad.org/"><img alt="FreeCAD 1.1+" src="https://img.shields.io/badge/FreeCAD-1.1%2B-blue"></a>
  <a href="https://www.python.org/"><img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB"></a>
  <a href="https://git-scm.com/"><img alt="Git required" src="https://img.shields.io/badge/Git-required-F05032"></a>
</p>

---

DiffCAD is a FreeCAD workbench for comparing parametric document snapshots. It gives CAD projects a review loop that feels closer to software development: inspect object changes, drill into property updates, stage model work, and commit snapshot data alongside `.FCStd` files.

<p align="center"><a href="https://raw.githubusercontent.com/eblanshey/DiffCAD/master/docs/LightScreenshot.png"><img src="docs/LightScreenshot.png" alt="DiffCAD light theme screenshot" width="75%" /></a></p>
<p align="center"><a href="https://raw.githubusercontent.com/eblanshey/DiffCAD/master/docs/DarkScreenshot.png"><img src="docs/DarkScreenshot.png" alt="DiffCAD dark theme screenshot" width="75%" /></a></p>

## Why DiffCAD?

FreeCAD documents are binary archives, so normal text diffs are not useful for model review. DiffCAD records a structured snapshot of each document's feature tree and compares those snapshots across your working tree, staging area, and git history.

Use it when you want to answer questions like:

- Which objects were added, removed, or modified?
- Which dimensions, placements, expressions, or dependencies changed?
- What changed between my working tree and the last commit?
- What exactly am I about to stage or commit?

## Features

- **Hierarchical diff view:** Review object-level changes in a color-coded tree.
- **Property-level diffing:** Drill into object properties and inspect exact value changes.
- **Expression tracking:** Compare property values and expressions independently.
- **Snapshot-based comparison:** Capture document state at meaningful points in time and diff the result.
- **Multi-document support:** Open and compare multiple FreeCAD documents in one repository.
- **Theme-aware highlighting:** Keep diff colors readable across FreeCAD light and dark themes.
- **Git-aware workflow:** Compare the working tree, staging area, and historical commits without replacing your regular git client.

## How It Works

DiffCAD writes text snapshots for FreeCAD documents and stores them next to your project files. Those snapshots are committed with the matching `.FCStd` files, giving git useful data to compare while keeping the original FreeCAD files intact.

The active git repository is detected from open FreeCAD documents. When you stage or commit through DiffCAD, the workbench saves documents, writes snapshots, and stages the relevant files together.

DiffCAD supplements your existing git client. It intentionally focuses on CAD review and does not try to replace full-featured git tools.

> [!NOTE]
> DiffCAD validates parametric CAD changes, not every byte inside an `.FCStd` archive. A document can change on disk without a detected parametric diff, especially for BREP data, view data, caches, and other generated content. Some complex property types are not fully captured yet.

## Installation

DiffCAD requires:

- FreeCAD 1.1 or newer (earlier versions may work, but are untested)
- Git installed and available on your global `PATH` (see the Git Setup instructions below)

DiffCAD is not yet available in the official FreeCAD Addon Manager repository. Until then, install it as a custom repository:

1. Open FreeCAD.
2. Go to **Edit > Preferences > Addon Manager > Custom repositories**.
3. Add this repository URL: `https://github.com/eblanshey/DiffCAD`
4. Set the branch to `master`.
5. Open **Tools > Addon Manager**.
6. Search for **DiffCAD** and install it.
7. Restart FreeCAD.

### Upgrading

When upgrading from an existing Addon Manager installation:

1. Open **Tools > Addon Manager**.
2. Uninstall **DiffCAD**.
3. Close FreeCAD.
4. Reopen FreeCAD.
5. Open **Tools > Addon Manager**.
6. Install **DiffCAD** again.
7. Restart FreeCAD.

### Git Setup (Absolute Beginner)

Don't be intimidated if you've never used Git before! If you have never used the command line, follow these steps exactly.

1. Install Git from <https://git-scm.com/install>, then run installer with default options.
2. Open terminal (`PowerShell` or `Command Prompt` on Windows, `Terminal` on macOS/Linux).
3. Set identity, which will be used for your commits (savepoints): `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`.
4. Confirm setup: `git --version`

From here on you can use the workbench for all operations.

## First Run

DiffCAD needs baseline snapshots before it can show useful diffs. For an existing project, create those snapshots before making new CAD changes. To more efficiently use disk space for versioning, see the FreeCAD Git Tips section below before making your first git commit.

0. **(Optional) FreeCAD Compression:** to more efficiently use disk space for versioning, see the FreeCAD Git Tips section below.
1. **Open a project file:** Start FreeCAD and open any project document.
2. **Initialize repository (if needed):** If the file is not already in a git repository, click **Initialize Git Repository** in the Diff Workbench and select its project directory.
3. **Open project documents:** Click **Refresh Git Repository** first, then click **Open All Documents** to open all FreeCAD documents in the repository.
4. **Recompute documents:** Click **Recompute All** to make sure document state is current.
5. **Generate snapshots:** Select **Working Tree** in the history list. Large projects may take some time.
6. **Stage everything:** Click **Stage All**. DiffCAD saves documents, writes snapshot YAML files, and adds both to git.
7. **Commit the baseline:** Use the **Commit** toolbar command or your regular git client.

After that baseline commit, continue modeling normally and use DiffCAD to review new changes.

## Daily Workflow

1. Make FreeCAD changes as usual.
2. Open the **Working Tree** view in DiffCAD.
3. Review object and property changes.
4. Stage finished documents with the **Stage** buttons.
5. Check the **Staging Area** view for a final review.
6. Commit from DiffCAD or your regular git client.

Staging a document through DiffCAD automatically saves the `.FCStd` file, writes its snapshot, and adds both files to the git staging area.

## Configuration

FreeCAD's Preferences dialog includes a **Diff Workbench** panel.

### Exclusion Lists

Exclusion lists hide noisy generated data from the diff view. They do not affect snapshot generation.

Each exclusion list supports two modes:

- **Use default exclusion list:** Use DiffCAD's built-in defaults.
- **Use custom exclusion list:** Provide your own exclusions.

Default values are defined in [`freecad/diff_wb/domain/config.py`](freecad/diff_wb/domain/config.py).

#### Excluded Object Types

Enter one FreeCAD `TypeId` per line, such as `App::Origin`. Objects of these types and their children are removed from the diff view.

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

## FreeCAD Git Tips

FreeCAD documents are binary files by default. Small model edits can produce large file changes, and repositories can grow quickly over time.

For a simple git-friendly setup, disable document compression:

1. Open **Edit > Preferences > General > Document**.
2. Set **Document save compression level** to `0`.
3. Save future `.FCStd` files with less compression.

An `.FCStd` file is a ZIP archive. With compression disabled, more of the document remains plain XML inside the archive, which makes git storage and external diff tooling behave better.

For large or long-lived CAD repositories, also consider Git LFS for `.FCStd` files. There is a [PR in FreeCAD](https://github.com/FreeCAD/FreeCAD/pull/28312) that addresses file formats for versioning. See [this comment](https://github.com/FreeCAD/FreeCAD/issues/11936#issuecomment-4054297851) for more git-related discussions.

## Contributors

Contributions are welcome. Please open an issue for bugs, confusing diffs, setup problems, documentation gaps, or feature requests. Pull requests that improve reliability, better diffing, FreeCAD compatibility, documentation, contributor tooling, or macOS and Windows development workflows are especially helpful. Development so far has happened on Linux, so additional platform setup notes and test instructions are welcome.

- [Development setup](docs/DevSetup.md): Set up a live FreeCAD workbench checkout, install dependencies, and configure the FreeCAD AppImage runtime for tests.
- [Development guidelines](docs/Development.md): Coding standards, testing strategy, logging, translations, dependency injection, and common contributor workflows.
- [Architecture](docs/Architecture.md): Layer responsibilities, runtime flow, composition roots, and snapshot/diff pipeline.

## Roadmap

- [ ] Unstage documents from inside DiffCAD
- [x] Initialize new git repositories from inside DiffCAD
- [ ] Move/rename snapshots when FCStd file is moved/renamed
- [ ] Visual part diffs
- [ ] Manual snapshot mode for simple projects without git

## Project Status

DiffCAD is early software built for real workflows. Expect rough edges, please report issues, and include sample documents when possible if a diff looks wrong.

Bug reports and feature requests: <https://github.com/eblanshey/DiffCAD/issues>
