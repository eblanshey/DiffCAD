# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Ensures the freecad/ directory remains a namespace package
# without an __init__.py file, preventing shadowing of FreeCAD's internal freecad package.
"""Tests for build and deployment configuration."""

from pathlib import Path


def test_freecad_directory_is_namespace_package():
    """Ensure freecad/ has no __init__.py to maintain namespace package structure.

    An __init__.py in freecad/ would shadow FreeCAD's internal freecad namespace,
    breaking imports like `from freecad import module_io`.
    """
    freecad_dir = Path(__file__).parents[3] / "freecad"
    init_file = freecad_dir / "__init__.py"

    assert not init_file.exists(), (
        f"{init_file} must not exist. The freecad/ directory must remain a "
        "namespace package (no __init__.py) to avoid shadowing FreeCAD's "
        "internal freecad package."
    )
