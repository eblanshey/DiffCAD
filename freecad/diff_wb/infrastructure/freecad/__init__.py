# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: FreeCAD-specific adapters implementing
# application ports and runtime context for FreeCAD integration.
"""FreeCAD infrastructure adapters."""

from .context import FreeCadContext, FreeCadPortAdapter, get_port, get_runtime_context


__all__ = ["FreeCadContext", "FreeCadPortAdapter", "get_port", "get_runtime_context"]
