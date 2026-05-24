# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Manages package version reporting by reading
# from pyproject.toml for both installed and source tree scenarios.
"""Package version for `freecad.history_wb`."""

from __future__ import annotations

# We intentionally do not use `importlib.metadata.version(...)` here.
#
# In typical Python packaging flows, the workbench would be installed as a
# distribution and the version would be available via installed package
# metadata. FreeCAD Addons, however, are commonly loaded directly from a source
# checkout (e.g. `Mod/` symlink or Addon Manager install) without installing a
# distribution into the interpreter environment. Reading `pyproject.toml` keeps
# version reporting stable in both "installed" and "source tree" scenarios.
import tomllib
from pathlib import Path
from typing import Any


def _read_pyproject_toml() -> dict[str, Any] | None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        return tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _get_project_version(pyproject: dict[str, Any]) -> str | None:
    project = pyproject.get("project")
    if not isinstance(project, dict):
        return None
    version = project.get("version")
    if not isinstance(version, str) or not version:
        return None
    return version


def _read_version_from_pyproject() -> str | None:
    pyproject = _read_pyproject_toml()
    if pyproject is None:
        return None
    return _get_project_version(pyproject)


def get_version() -> str:
    """Get the package version."""
    version = _read_version_from_pyproject()
    if version is not None:
        return version
    return "0.0.0"


__version__ = get_version()
