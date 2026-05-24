# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Visual diff port interfaces for BREP diff document creation.
"""Visual diff port interfaces."""

from __future__ import annotations

from typing import Protocol


class FreeCADVisualDiffPort(Protocol):
    """Protocol for visual BREP diff document creation."""

    def open_brep_visual_diff(
        self,
        old_brep_path: str | None,
        new_brep_path: str | None,
        document_name: str,
    ) -> object:
        """Open visual diff document for old and new BREP paths."""
        ...
