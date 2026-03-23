# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Validates that running FreeCAD and Python versions meet minimum requirements for the workbench.
"""Runtime version checks for supported FreeCAD and Python versions.

This module validates that the current FreeCAD and Python runtime meet the
minimum required versions for the Diff Workbench.

Translation Strategy:
    Version warning messages use templates with %s placeholders. The template
    is translated first, then parameters are substituted using Python's % operator:

        template = _container.translate("Log", _PYTHON_VERSION_WARNING_TEMPLATE)
        translated = template % (major, minor, patch)
        _container.log(translated)
"""

import sys

from ._container import _container


# Minimum required FreeCAD version (0.21.2+)
FC_MAJOR_VER_REQUIRED = 1
FC_MINOR_VER_REQUIRED = 0
FC_PATCH_VER_REQUIRED = 2
FC_COMMIT_REQUIRED = 33772

# ============================================================================
# VERSION WARNING TEMPLATES
# ============================================================================
# Context: "Log"
# These templates use %s placeholders for version numbers.
# Translation happens first, then % substitution.

_PYTHON_VERSION_WARNING_TEMPLATE = (
    "Python version (%s.%s.%s) must be at least 3.11 in order to work with FreeCAD 1.0 and above\n"
)
"""Template for Python version warning message.

Placeholders:
    %s - Python major version (int)
    %s - Python minor version (int)
    %s - Python patch version (int)

Example:
    "Python version (3.10.5) must be at least 3.11 in order to work with FreeCAD 1.0 and above"
"""

_FC_VERSION_WARNING_TEMPLATE = (
    "FreeCAD version (%s.%s.%s (%s)) must be at least %s.%s.%s (%s) in order to work with Python 3.11 and above\n"
)
"""Template for FreeCAD version warning message.

Placeholders:
    %s - FreeCAD major version (int)
    %s - FreeCAD minor version (int)
    %s - FreeCAD patch version (int)
    %s - FreeCAD git commit (int)
    %s - Required FreeCAD major version (int)
    %s - Required FreeCAD minor version (int)
    %s - Required FreeCAD patch version (int)
    %s - Required FreeCAD git commit (int)

Example:
    "FreeCAD version (0.21.1 (33700)) must be at least 0.21.2 (33772) in order to work with Python 3.11 and above"
"""


def _warn_unsupported_python_version() -> None:
    """Warn about unsupported Python version using container helpers.

    This function uses the global _container which should always be set during
    normal FreeCAD operation. In test environments where _container is None,
    this function is expected to not be called or will be handled elsewhere.
    """
    if _container is None:
        # Fallback for tests - print to stderr
        import sys as _sys

        _sys.stderr.write(
            f"Python version ({sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}) "
            "must be at least 3.11 in order to work with FreeCAD 1.0 and above\n"
        )
        return

    # Translate template first, then substitute parameters
    template = _container.translate("Log", _PYTHON_VERSION_WARNING_TEMPLATE)
    translated = template % (sys.version_info[0], sys.version_info[1], sys.version_info[2])
    _container.log(translated)


def _coerce_gitver(value: str) -> int:
    if value and value != "Unknown":
        return int(value)
    # If we don't have the git version, assume it's OK.
    return FC_COMMIT_REQUIRED


def _parse_freecad_version() -> tuple[int, int, int, int]:
    import FreeCAD as App  # pylint: disable=import-error

    ver = App.Version()
    major_ver = int(ver[0])
    minor_ver = int(ver[1])
    patch_ver = int(ver[2])

    parts = str(ver[3]).split()
    gitver_str = parts[0] if parts else ""
    gitver = _coerce_gitver(gitver_str)
    return major_ver, minor_ver, patch_ver, gitver


def _warn_unsupported_freecad_version(*, major: int, minor: int, patch: int, gitver: int) -> None:
    """Warn about unsupported FreeCAD version using container helpers.

    This function uses the global _container which should always be set during
    normal FreeCAD operation. In test environments where _container is None,
    this function is expected to not be called or will be handled elsewhere.
    """
    if _container is None:
        # Fallback for tests - print to stderr
        import sys as _sys

        _sys.stderr.write(
            f"FreeCAD version ({major}.{minor}.{patch} ({gitver})) must be at least "
            f"{FC_MAJOR_VER_REQUIRED}.{FC_MINOR_VER_REQUIRED}.{FC_PATCH_VER_REQUIRED} ({FC_COMMIT_REQUIRED}) "
            "in order to work with Python 3.11 and above\n"
        )
        return

    # Translate template first, then substitute parameters
    template = _container.translate("Log", _FC_VERSION_WARNING_TEMPLATE)
    translated = template % (
        major,
        minor,
        patch,
        gitver,
        FC_MAJOR_VER_REQUIRED,
        FC_MINOR_VER_REQUIRED,
        FC_PATCH_VER_REQUIRED,
        FC_COMMIT_REQUIRED,
    )
    _container.log(translated)


def check_supported_version(major_ver: int, minor_ver: int, patch_ver: int = 0, git_ver: int = 0) -> bool:
    """Return whether the given version tuple meets the minimum requirements.

    Args:
        major_ver: Major version.
        minor_ver: Minor version.
        patch_ver: Patch version.
        git_ver: Build/commit number when available.

    Returns:
        ``True`` if the version is supported, otherwise ``False``.
    """
    return (major_ver, minor_ver, patch_ver, git_ver) >= (
        FC_MAJOR_VER_REQUIRED,
        FC_MINOR_VER_REQUIRED,
        FC_PATCH_VER_REQUIRED,
        FC_COMMIT_REQUIRED,
    )


def check_python_and_freecad_version() -> None:
    """Validate that the current runtime is compatible with the workbench.

    This function checks:
    - The running Python version (must satisfy the minimum required).
    - The running FreeCAD version/commit (when available).

    Failures are reported via container helpers.
    No exception is raised; the workbench may continue to load with reduced
    functionality.
    """
    if not (sys.version_info[0] == 3 and sys.version_info[1] >= 11):
        _warn_unsupported_python_version()
        return

    # Check FreeCAD version
    major, minor, patch, gitver = _parse_freecad_version()

    if not check_supported_version(major, minor, patch, gitver):
        _warn_unsupported_freecad_version(
            major=major,
            minor=minor,
            patch=patch,
            gitver=gitver,
        )
