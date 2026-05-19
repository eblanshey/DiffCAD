# Development Setup

This guide sets up DiffCAD for local development. It installs Python dependencies, connects the checkout to FreeCAD, and configures the FreeCAD runtime scripts used by tests and API exploration.

## Prerequisites

- FreeCAD 1.1 or newer
- Git
- `uv`
- `task`
- Python 3.12 for the local development environment

DiffCAD integration tests use FreeCAD's bundled Python 3.11 on Linux. That is separate from the local `uv` environment.

## Clone The Repository

```bash
git clone https://github.com/eblanshey/DiffCAD.git
cd DiffCAD
```

If you already have a checkout, run the setup commands from the repository root.

## Install Python Dependencies

```bash
uv sync
```

This creates or updates the local `.venv` and installs development tools declared in `pyproject.toml`, including `ruff`, `mypy`, `pytest`, `radon`, `freecad-stubs`, and `taskfile-help`.

### Nix / NixOS

On Nix or NixOS, run `nix-shell` in the repository root to enter an environment with all required dependencies (including Qt libraries like libGL) and tools (`uv`, `python311`, `go-task`):

```bash
nix-shell
```

Inside the Nix shell, run `uv sync` to set up the Python virtual environment, then follow the "Link Into FreeCAD's Mod Directory" section to connect the workbench to FreeCAD.

#### Using direnv for Convenience

To automatically enter the Nix shell when opening the project directory, use `direnv`:

1. In your `configuration.nix`:
    ```nix
    programs.direnv.enable = true;
    programs.direnv.nix-direnv.enable = true;
    ```

2. Allow direnv in the repository root:
    ```bash
    direnv allow
    ```

The `.envrc` file checks if Nix is installed before loading the shell. If Nix is not available, direnv does nothing (no error).

For VSCode users, install the "direnv" extension by Martin Koehler (search for "direnv" in the extensions panel) to have VSCode automatically load the Nix environment.

## Link Into FreeCAD's Mod Directory

Create a symlink from FreeCAD's `Mod` directory to this checkout. FreeCAD will load the workbench from the live source tree, so code changes are picked up after restarting FreeCAD.

To find the correct `Mod` directory from FreeCAD:

1. Open **Tools > Addon Manager**.
2. Click the preferences icon at the bottom of the Addon Manager.
3. Click **Open Addons Folder**.
4. Use the opened folder as the target directory for the `DiffCAD` symlink.

Linux example:

```bash
ln -s /path/to/DiffCAD ~/.local/share/FreeCAD/v1-1/Mod/DiffCAD
```

Use the absolute path to your local checkout in place of `/path/to/DiffCAD`.

## Start FreeCAD

Restart FreeCAD after creating the symlink. The workbench should appear as `Diff` in the workbench selector.

During development, restart FreeCAD after changing Python files. Resource files, command registration, and workbench initialization are loaded by FreeCAD process startup and activation.

## Run Local Checks

Run all checks:

```bash
task check
```

Run tests (includes unit and integration):

```bash
task test
```

## Linux FreeCAD AppImage Runtime

The scripts `./run_with_freecad.sh` and `./run_integration_tests.sh` need an extracted FreeCAD AppImage and the `FREECAD_ROOT` environment variable.

Download the FreeCAD AppImage, then extract it:

```bash
chmod +x FreeCAD*.AppImage
./FreeCAD*.AppImage --appimage-extract
```

This creates a `squashfs-root` directory. Move it wherever you keep local tools, then export `FREECAD_ROOT`:

```bash
export FREECAD_ROOT=$HOME/Programs/freecad_extracted/squashfs-root
```

To keep the setting across shells, add that export to your shell profile, such as `~/.bashrc`, `~/.zshrc`, or your shell-specific environment file.

Verify the runtime:

```bash
./run_with_freecad.sh python -c "import FreeCAD; print(FreeCAD.Version())"
```

Integration tests rely on the FreeCAD python environment. `pytest` isn't installed there, so run:

```bash
./run_with_freecad.sh pip install pytest
```

Now run integration tests directly:

```bash
./run_integration_tests.sh
```

Run a focused integration test path:

```bash
./run_integration_tests.sh tests/integration/workbench -v
```

## FreeCAD API Exploration

Use `run_with_freecad.sh` to inspect FreeCAD's App APIs from the extracted runtime:

```bash
./run_with_freecad.sh python -c "import FreeCAD; print(dir(FreeCAD))"
```

`FreeCADGui` is not generally available through this script. GUI API debugging usually needs instrumentation inside the workbench and a manual FreeCAD run.

FreeCAD type stubs are installed in the local `uv` environment under `.venv/lib/python3.12/site-packages/`. Check those stubs before assuming FreeCAD API signatures.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| FreeCAD does not show the workbench | Check that the symlink exists under FreeCAD's active `Mod` directory and points to the repository root. Restart FreeCAD. |
| `FREECAD_ROOT environment variable is not set` | Export `FREECAD_ROOT` to the extracted AppImage `squashfs-root` path. |
| `FreeCAD Python not found` | Check that `$FREECAD_ROOT/usr/bin/python` exists. Re-extract the AppImage if needed. |
| Many integration tests are skipped | Run `task test` or `./run_integration_tests.sh`, not plain `pytest`. |
| Import errors for local tools | Run `uv sync` from the repository root. |
| FreeCAD loads stale behavior | Restart FreeCAD. Python modules are cached for the lifetime of the FreeCAD process. |
